# Stage 10 — Final Audit & Release

## Release scope

This release is based on the Stage 9 source tree. Previous stage archives were not modified.

## Final changes

- Removed legacy Gemini 2.5 model IDs from the default fallback list. The default now uses the documented stable `gemini-3.5-flash-lite` and `gemini-3.8-flash` model IDs. Model availability and quotas remain project/key dependent; the list is configurable through `MANGA_BOT_GEMINI_MODELS`.
- Added `python-dotenv` to `pyproject.toml` so editable/package installs include the dependency required by Pydantic Settings to read `.env` files.
- Hardened the manual GitHub Actions workflow: validate the requested run duration as an integer from 1 to 359 before passing it to `timeout`.
- Removed automatic upload of the SQLite database as a GitHub Actions artifact. The database can contain user records and API keys; it must not be published as a routine CI artifact.
- Removed generated Python bytecode and pytest cache from the release archive.

## Validation

- `python -m compileall -q .` — passed.
- `pytest -q` — 31 passed.
- `pip check` — reports an unrelated pre-existing environment conflict: globally installed `moviepy 2.2.1` requires `Pillow <12`, while this environment has `Pillow 12.3.0`. `moviepy` is not a project dependency. The project test suite passes; install the project in a clean virtual environment to avoid unrelated global-package conflicts.
- Secret-pattern scan — no real Telegram token or Gemini API key found in the release tree. `.env` is excluded; `.env.example` contains placeholders only. The source still contains configured super-admin Telegram user IDs; review/replace these before publishing the source publicly.
- Archive hygiene — `.env`, `.git`, databases, Python bytecode, and test caches are excluded from the release archive.

## Known limitations / operational risks

1. The queue and user session state are still in memory. A process restart can lose queued/in-progress jobs and active session state. Durable job recovery is not part of this release.
2. The job orchestration currently serializes active user sessions globally in parts of the workflow. Worker count settings do not imply that multiple user sessions are processed fully in parallel.
3. The target 0.5 CPU / 512 MB host has not been benchmarked directly. Stage 9 measurements were made on a different local environment and are not an acceptance guarantee.
4. Live Telegram and Gemini end-to-end tests, API quota checks, and key-permission checks were not performed because this release process does not use production credentials.
5. `max_running_jobs` remains as a deprecated compatibility setting and is not the effective concurrency control. Use `MANGA_BOT_AI_WORKER_COUNT` and `MANGA_BOT_DELIVERY_WORKER_COUNT`.
6. SQLite stores API keys in the `api_keys` table as plaintext in the current schema. Restrict filesystem access to the database and backups. Encryption-at-rest/key-management should be a separately planned security change with a migration strategy.
7. The GitHub Actions workflow is a temporary runner workflow, not a persistent hosting solution. Its local database is ephemeral and is no longer uploaded as an artifact.
8. If any real credentials were included in earlier shared archives, rotate them. Never reuse credentials from an archive that may have been distributed.

## Deployment checklist

1. Copy `.env.example` to `.env` and set a fresh Telegram token and a valid Gemini API key.
2. Keep `.env`, `manga_bot.db`, and backups private; do not upload them to public repositories or CI artifacts.
3. Preserve the existing `manga_bot.db` when upgrading. Stop the old process before copying the database and any SQLite WAL sidecars.
4. Install dependencies using `python -m pip install -r requirements.txt`.
5. Run `python -m utils.healthcheck` before starting the bot.
6. Start exactly one polling process for the bot token with `python main.py`.
7. Confirm logs, Telegram delivery, Gemini responses, and memory use on the actual hosting plan before treating the deployment as production-validated.

## Release status

Source-level checks passed. This is a release candidate, not a claim of live production certification on the target host.
