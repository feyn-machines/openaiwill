"""Pick, from a list of options, the ones that apply — batched, with a fallback.

Three mapping passes need the same shape: given one subject and a few hundred
candidate options, which options apply? Jev answers several hundred questions in
one request (measured ceiling 874-903; 903 and above return max_tokens_exceeded),
so the batching is about staying under that, not about one call per option.

Two things this deliberately keeps that a multi-select answer would lose: a
certainty per option, and an explicit negative. Without the second there is no
way to tell "asked and rejected" from "never asked", which is exactly the
distinction the gate and evidence passes depend on.

The fallback exists because it already bit this project once: TypeSafe's credit
ran out partway through a sweep, the comparison model silently finished the job,
and nothing recorded the switch — a permissive reading and a strict one ended up
in the same column. Falling back is fine. Not saying so is not.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from .judge import (
    DeepSeekJudge,
    JudgeError,
    TypeSafeJudge,
    TYPESAFE_URL,
    _post,
)

# Under the measured ceiling with room for a long option label.
BATCH = 400


@dataclass(frozen=True)
class Option:
    id: str
    label: str


@dataclass(frozen=True)
class Reading:
    option_id: str
    value: float
    judge: str


class Classifier:
    """Jev first, the comparison model only when Jev fails, and it says which."""

    def __init__(self, question: str, criteria: dict, subject_key: str,
                 option_key: str, batch: int = BATCH, timeout: int = 300,
                 retries: int = 4, backoff: float = 2.0):
        self.question = question
        self.criteria = criteria
        self.subject_key = subject_key
        self.option_key = option_key
        self.batch = batch
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.primary = TypeSafeJudge()
        self._fallback: DeepSeekJudge | None = None
        self.fallback_batches = 0
        self.failed_batches = 0

    @property
    def fallback(self) -> DeepSeekJudge:
        # Built on first use: a run that never needs it should not require the
        # comparison model to be configured at all.
        if self._fallback is None:
            self._fallback = DeepSeekJudge()
        return self._fallback

    def _jev(self, state: dict, options: list[Option]) -> list[Reading]:
        questions = {
            f"q{index}": {
                "type": "noul",
                "instructions": {"question": self.question, self.option_key: option.label},
                "criteria": self.criteria,
            }
            for index, option in enumerate(options)
        }
        body = _post(
            TYPESAFE_URL,
            {"state": state, "model": self.primary.model, "questions": questions},
            self.primary.api_key,
            self.timeout,
        )
        answers = body.get("answers") or {}
        out = []
        for index, option in enumerate(options):
            value = (answers.get(f"q{index}") or {}).get("noul")
            # A missing answer is left out rather than defaulted: a short reply
            # must not read as a row of rejections.
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out.append(Reading(option.id, float(value), "typesafe"))
        return out

    def _deepseek(self, state: dict, options: list[Option]) -> list[Reading]:
        listing = [{"index": i, "label": o.label} for i, o in enumerate(options)]
        system = (
            f"{self.question}\n"
            f"true: {self.criteria['true']}\n"
            f"false: {self.criteria['false']}\n"
            "For every option return a JSON object with index:int, applies:bool, "
            "confidence:0..1. Judge each option on its own; do not limit how many "
            "may apply. "
            # The word "json" has to appear for response_format=json_object; without
            # it the API rejects the request, which is how every fallback in the
            # first routing run failed at once.
            'Return ONLY the JSON object {"answers": [...]} covering every index.'
        )
        payload = {
            "model": self.fallback.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(
                    {"subject": state, "options": listing}, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "stream": False,
        }
        body = _post(f"{self.fallback.base_url}/chat/completions",
                     payload, self.fallback.api_key, self.timeout)
        choices = body.get("choices") or []
        if not choices:
            raise JudgeError("no choices in response")
        try:
            parsed = json.loads(choices[0]["message"]["content"])
        except (KeyError, TypeError, ValueError):
            raise JudgeError("model content was not JSON") from None
        out = []
        for answer in parsed.get("answers") or []:
            index = answer.get("index")
            if not isinstance(index, int) or not 0 <= index < len(options):
                continue
            confidence = answer.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
                confidence = 1.0 if answer.get("applies") else 0.0
            # Put it on the same scale as Jev's noul, where 0.5 is undecided.
            value = float(confidence) if answer.get("applies") else 1.0 - float(confidence)
            out.append(Reading(options[index].id, max(0.0, min(1.0, value)), "deepseek"))
        return out

    def classify(self, state: dict, options: list[Option], progress=None) -> list[Reading]:
        readings: list[Reading] = []
        for start in range(0, len(options), self.batch):
            chunk = options[start:start + self.batch]
            # Retry before falling back. Every failure in the first routing run
            # was transient — SSL EOF, DNS, a dropped connection — and switching
            # judges for those trades a strict reading for a loose one over a
            # network blip.
            error = None
            for attempt in range(self.retries):
                try:
                    readings.extend(self._jev(state, chunk))
                    error = None
                    break
                except JudgeError as failure:
                    error = failure
                    if attempt + 1 < self.retries:
                        time.sleep(self.backoff * (2 ** attempt))
            if error is None:
                continue
            if progress:
                progress(f"    jev failed on {len(chunk)} options after "
                         f"{self.retries} tries: {error}")
            try:
                readings.extend(self._deepseek(state, chunk))
                self.fallback_batches += 1
                if progress:
                    progress(f"    fell back to the comparison model for {len(chunk)} options")
            except JudgeError as error:
                self.failed_batches += 1
                if progress:
                    progress(f"    both judges failed on {len(chunk)} options: {error}")
        return readings
