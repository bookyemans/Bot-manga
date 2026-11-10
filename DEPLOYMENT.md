# Void Translator — Deployment Guide

## Supported runtime

- Python 3.11 or newer.
- One polling process per Telegram bot token.
- A persistent, writable local directory for SQLite and the instance lock.
- Outbound network access to Telegram and the configured Gemini API endpoint.

This application is a polling worker, not an HTTP web server. Do not configure an HTTP port probe as its liveness check.

## Install on a Python host

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env; set a fresh Telegram token and required AI API key.
python -m utils.healthcheck
python main.py
```

Keep `.env` readable only by the service account (for example, `chmod 600 .env` on Linux). Do not paste credentials into source files or commit `.env`.

## Upgrade without losing data

1. Stop the old bot process cleanly.
2. Back up the existing database before changing files. If SQLite WAL mode is active, stop the process first and preserve the database plus `-wal`/`-shm` sidecars if present, or use SQLite's online backup API while the database is open.
3. Extract the new release into a separate directory.
4. Copy the existing database to the configured persistent path. The historical default remains `manga_bot.db` in the working directory unless `MANGA_BOT_DATABASE_PATH` is set.
5. Create `.env` from the new `.env.example`, then restore the deployment's required settings using fresh/valid credentials. Never overwrite a working `.env` blindly.
6. Install the release dependencies in its virtual environment and run `python -m utils.healthcheck`.
7. Start exactly one polling process and inspect logs, Telegram delivery, and AI responses.
8. Keep the backup until the upgraded bot has been verified.

Never start with an empty database if the deployment is expected to retain existing users, access rules, settings, or API keys.

## Docker Compose

```bash
cp .env.example .env
# Edit .env before starting.
docker compose up -d --build
docker compose logs -f void-translator
```

Compose mounts named volumes for `/app/data` and `/app/.runtime`. The database path is `/app/data/manga_bot.db`. For migration, stop the old service and copy the old database into the `void_translator_data` volume before starting the container. Do not assume Compose migrates a host database automatically.

To stop: `docker compose down` (named volumes are retained). To remove persistent data, `docker compose down -v` — this is destructive and should not be used for routine upgrades.

## systemd

Review `systemd/void-translator.service.example`, create the `bot` service account, adjust paths and permissions, then install the unit as `/etc/systemd/system/void-translator.service`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now void-translator
sudo systemctl status void-translator
journalctl -u void-translator -f
```

Ensure the service account can read `.env` and write the database and lock directories.

## Health, logs, and safeguards

- `python -m utils.healthcheck` checks required token configuration and SQLite accessibility/integrity. It intentionally does not call Telegram or Gemini.
- Logs are written to stdout/stderr; route them through the host's log collector and restrict access because operational logs may contain user-related context.
- The advisory instance lock prevents duplicate local polling processes sharing the same lock path. Keep the lock on a local filesystem that supports OS file locking.
- Shutdown attempts to stop workers and close provider/database resources.
- Keep `.env`, databases, SQLite sidecars, backups, and runtime lock files out of source-control and public archives.

## Backup and restore

Back up the SQLite database regularly using a SQLite-aware method. For a simple stopped-service backup, copy the database file after the process has exited cleanly. Store backups encrypted and access-controlled. Test restoration periodically into a separate directory before relying on a backup. Never upload production databases as public CI artifacts.

## Resource and durability limitations

The defaults are conservative, but this release has not been benchmarked on the target 0.5 CPU / 512 MB host. Measure real RSS and latency under representative image sizes and user concurrency before setting production capacity.

Queued jobs, the job registry, and active sessions remain in memory. A restart or crash can lose queued/in-progress work and active session state. This release does not provide durable job recovery or multi-instance coordination beyond the local process lock. SQLite API keys remain plaintext in the current schema; protect the database and backups at the filesystem/storage layer.
