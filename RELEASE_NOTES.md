# Void Translator — Release Candidate (Phase 12)

This release candidate consolidates the staged modular-monolith refactoring and includes bounded in-process queues, repository boundaries, session lifecycle cleanup, image/file handling improvements, Persona/Prompt organization, shared document delivery, Telegram handler registration separation, runtime safeguards, and local capacity benchmark tooling.

## Compatibility and upgrade

- Python 3.11 or newer.
- Preserve the existing SQLite database when upgrading. The historical default database path remains `manga_bot.db` in the project working directory unless explicitly configured.
- Install dependencies from `requirements.txt` in a clean virtual environment.
- Configure credentials in a private `.env` file; do not commit or distribute it.
- Run one polling process per bot token.

Follow `DEPLOYMENT.md` for backup, upgrade, Docker, systemd, health-check, and restore guidance.

## Validation status

The source-level test suite and Python compilation checks passed in the Phase 12 build environment. No live Telegram/Gemini end-to-end test, target-host benchmark, sustained soak test, or production credential validation was performed. This is a release candidate, not a production certification.

## Known limitations

1. Jobs, job registry, and active sessions are in memory; process restarts can lose queued/in-progress work and session state.
2. The target 0.5 CPU / 512 MB host has not been benchmarked directly.
3. Live Telegram/Gemini connectivity, API quotas, and production credentials were not validated.
4. SQLite stores API keys as plaintext in the current schema; restrict access to the database and backups.
5. A local advisory lock does not provide distributed/multi-host coordination.
6. `max_running_jobs` remains a deprecated compatibility setting; use `MANGA_BOT_AI_WORKER_COUNT` and `MANGA_BOT_DELIVERY_WORKER_COUNT`.

If credentials may have been present in any previously distributed archive, rotate them before deployment.
