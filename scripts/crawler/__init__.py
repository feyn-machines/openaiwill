"""Project-owned X collection crawler.

Replaces the earlier dependency on the social-qingguo-collector skill. The fetch
engine is account-agnostic (it is handed a session and a target); the account
pool, proxy sessions, concurrency and progress are project responsibilities.
Account data is dynamic and lives under the ignored data/ tree, never in the
skill directory, env, or Git.

Only x_client and x_compat import twikit; every other module is pure logic that
can be unit-tested without network access or twikit installed.
"""
