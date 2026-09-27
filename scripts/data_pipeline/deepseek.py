"""DeepSeek extraction call — the one non-deterministic step of event extraction.

DeepSeek exposes an OpenAI-compatible chat/completions endpoint, so this stays a
thin stdlib HTTP client (no new dependency). The API key is infrastructure and
lives in the environment (DEEPSEEK_API_KEY), never in the pool file, the skill, a
committed file or NEXT_PUBLIC. Model and endpoint are overridable via
DEEPSEEK_MODEL / DEEPSEEK_BASE_URL. The prompt is versioned by its SHA-256 so a
prompt change is visible in every extraction run's provenance.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import semantic
from .pipeline import digest


class DeepSeekError(RuntimeError):
    """A recoverable model-call error: one batch may be retried, then skipped."""

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"

EXTRACTION_VERSION_TAG = "deepseek-events-2"


def system_prompt():
    """The extraction prompt, built from the semantic layer instead of hand-typed.

    Everything that decides a classification - the 15 event kinds, their
    boundaries and the event identity rule - is rendered from
    datasets/semantic/semantic-model.v2.json. The previous prompt carried a bare
    ten-word list, which is why the same model drew a different boundary on every
    run and parked a quarter of the events in "other". A boundary now changes in
    one place, and `prompt_sha256` moves when it does.
    """
    return "\n".join([
        "You extract structured records of real AI product and capability updates "
        "from official company posts.",
        "",
        "You are given a batch of posts from official AI-company accounts. Identify the "
        "distinct real-world UPDATES they announce, classify each one, and merge every post "
        "that describes the SAME update into ONE event.",
        "",
        semantic.event_kind_rubric(),
        "",
        semantic.event_identity_rule(),
        "",
        "Classification rules:",
        "- `kind` MUST be one of the controlled terms above, spelled exactly. There is no "
        "\"other\" bucket and inventing one (\"other\", \"misc\", \"announcement\", a term of your "
        "own) is an error.",
        "- If you cannot decide between terms, or none of them fits, set `kind` to null and "
        "write a short `unresolved_reason` saying what you were stuck on. `unresolved_reason` "
        "must be non-empty whenever `kind` is null, and is ignored when `kind` is set. A null "
        "with a reason is useful; a wrong term is not.",
        "- Give `subject_key` for EVERY event: the canonical name of the thing being "
        "announced, evaluated or adopted (product line plus version, benchmark plus track, "
        "event plus year), lowercase, punctuation and spaces replaced by hyphens. Leave it "
        "empty only when the posts genuinely name no subject.",
        "- Give `primary_org` for EVERY event: the company behind the update, written as one "
        "plain company name (\"xAI\", never \"xAI / SpaceXAI\"; \"Zhipu\", \"Moonshot\", "
        "\"Google\", \"Alibaba\"). An event whose company cannot be named is dropped.",
        "- Merge by identity, not by wording: two posts with the same "
        "(primary_org, kind, subject_key) are ONE event however differently they are titled. "
        "Do not split one announcement because another post phrased it differently.",
        "",
        "Return STRICT JSON, an object: {\"events\": [ ... ]}. Each event:",
        '- "kind": one of the controlled terms above, or null',
        '- "unresolved_reason": short reason, required when "kind" is null, otherwise omitted',
        '- "subject_key": canonical name of the subject (see above), or null',
        '- "title": short factual title (<=120 chars), no marketing language; display only',
        '- "summary": one or two factual sentences',
        '- "primary_org": the company behind the update (e.g. "OpenAI")',
        '- "occurred_at": ISO 8601 UTC timestamp of when it happened, or null',
        '- "occurrence_status": one of unknown, scheduled, occurred, postponed, cancelled',
        '- "confidence": number 0..1, your confidence this is a genuine distinct update',
        '- "source_ids": array of the given post ids that evidence this event (at least one)',
        '- "relations": optional array of {"to_index": <index of another event in THIS batch>, '
        '"kind": one of part_of, follows, supersedes, refines, duplicate_of, "rationale": short reason}',
        "",
        "Rules: use only the given posts as evidence; do not invent facts. A repost or a reply "
        "is usually not its own update. If a batch has no genuine update, return "
        '{"events": []}. Output ONLY the JSON object.',
    ])


def prompt_sha256():
    """Version anchor for the extraction prompt (recorded on every run).

    Hashes the rubric alongside the prompt text: the rendered rubric is already
    inside the prompt, but a separate rubric hash keeps a semantic-layer edit
    legible in provenance instead of hidden inside one opaque digest.
    """
    return digest({"system": system_prompt(), "schema": EXTRACTION_VERSION_TAG,
                   "rubric_sha256": semantic.rubric_sha256(),
                   "semantic_version": semantic.SEMANTIC_VERSION})


def load_env(root):
    """Populate os.environ from local .env without overriding real env."""
    path = Path(root) / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def config_from_env():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DeepSeek is not configured. Set DEEPSEEK_API_KEY in .env")
    return {
        "api_key": key,
        "model": os.environ.get("DEEPSEEK_MODEL", "").strip() or DEFAULT_MODEL,
        "base_url": (os.environ.get("DEEPSEEK_BASE_URL", "").strip() or DEFAULT_BASE_URL).rstrip("/"),
    }


def _post_message(candidates):
    """Compact, id-tagged rendering of one batch of candidate posts."""
    lines = ["Posts:"]
    for c in candidates:
        published = c["published_at"]
        when = published.isoformat() if hasattr(published, "isoformat") else str(published)
        lines.append(json.dumps({
            "id": c["source_id"], "org": c.get("company") or c.get("handle"),
            "handle": c.get("handle"), "published_at": when,
            "text": c.get("excerpt", ""),
        }, ensure_ascii=False))
    return "\n".join(lines)


def chat(messages, cfg, timeout=120):
    """One OpenAI-compatible chat/completions call in JSON mode; returns parsed content.

    Raises DeepSeekError on any transport, HTTP, empty-response or malformed-JSON
    problem so the caller can retry that one batch and, failing that, skip it.
    """
    payload = json.dumps({
        "model": cfg["model"], "messages": messages,
        "response_format": {"type": "json_object"}, "temperature": 0, "stream": False,
    }).encode()
    request = urllib.request.Request(
        f"{cfg['base_url']}/chat/completions", data=payload, method="POST",
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise DeepSeekError(f"HTTP {error.code}: {error.read().decode()[:200]}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise DeepSeekError(f"request failed: {error}") from None
    if isinstance(body, dict) and body.get("error"):
        raise DeepSeekError(f"api error: {str(body['error'])[:200]}")
    choices = (body or {}).get("choices") or []
    if not choices:
        raise DeepSeekError(f"no choices: {json.dumps(body)[:200]}")
    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise DeepSeekError("empty content")
    try:
        return json.loads(content)
    except ValueError:
        raise DeepSeekError("model did not return valid JSON") from None


def extract_events(candidates, cfg=None, batch_size=25, progress=None, max_attempts=3):
    """Extract events from candidates in batches. Returns (batches, failures).

    Each batch is retried up to `max_attempts` on a DeepSeekError with backoff; a batch
    that still fails is recorded in `failures` and skipped (empty), so one bad call does
    not lose the whole run. Output is deterministic-shaped ({"events": [...]}) so
    `assemble_extraction` can turn it into an immutable document.
    """
    cfg = cfg or config_from_env()
    prompt = system_prompt()
    batches, failures = [], []
    total = (len(candidates) + batch_size - 1) // batch_size
    for number, index in enumerate(range(0, len(candidates), batch_size), 1):
        chunk = candidates[index:index + batch_size]
        messages = [{"role": "system", "content": prompt},
                    {"role": "user", "content": _post_message(chunk)}]
        result, error = None, None
        for attempt in range(max_attempts):
            try:
                result = chat(messages, cfg)
                break
            except DeepSeekError as exc:
                error = exc
                time.sleep(2 * (attempt + 1))
        if result is None:
            failures.append({"batch": number, "error": str(error)})
            batches.append({"events": []})
            if progress:
                progress(number, total, 0)
            continue
        events = result.get("events", []) if isinstance(result, dict) else []
        batches.append({"events": events})
        if progress:
            progress(number, total, len(events))
    return batches, failures
