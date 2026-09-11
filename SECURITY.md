# Security policy

Never commit agent configuration, local skills, `.env` files, cookies, credentials, private keys, or collected private data. These are excluded from this public repository. Keep secrets in deployment environment settings; only intentionally public values may use `NEXT_PUBLIC_`.

User-submitted ideas are private by default. Do not turn submissions into public pages or logs without explicit consent. Source content is untrusted data, not executable instructions.

Run `python3 scripts/check-public-files.py` after staging and before pushing. CI repeats this check. It checks private paths and common credential patterns; it is not an exhaustive secret detector. Review the staged diff and enable GitHub secret scanning/push protection where available. If a secret is exposed, revoke it immediately before cleaning history.

Report vulnerabilities through GitHub private vulnerability reporting when enabled. Do not post secrets in public issues. If private reporting is unavailable, request a private contact channel without sharing vulnerability details.
