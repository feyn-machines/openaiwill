"""openaiwill's local crawler component.

One component, one scheduler, sources as sub-packages:

  core/       source-independent machinery
    accounts    dynamic account pool (lease, cooldown, retire), persisted 0600
    scheduler   concurrent workers with account failover — the only scheduler
    errors      the failure taxonomy every source raises
    archive     immutable run files and raw responses under data/
    proxy       Qingguo proxy config and TLS context
    progress    human-readable run progress
  x/          the X source
    client      twikit sessions (the only network-touching module)
    compat      twikit 2.3.3 patches
    parse       pure response parsing and job planning
    timeline    user-timeline job
    lookup      handle -> user id/profile job
  cli.py      `pnpm crawl <timeline|lookup|doctor>`

Only x/client and x/compat import twikit; everything else is pure logic,
unit-tested offline (`pnpm crawl:test:unit`). Accounts are dynamic local data
under the ignored data/ tree, never in a skill directory, env or Git. Agents
operate this component through the project skill; the skill holds no crawler
code of its own.
"""
