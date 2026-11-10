# Void Translator

A modular-monolith Telegram translation bot for manga/manhwa images. The application keeps a single deployable process and uses bounded in-process job queues with SQLite persistence for application data.

## Quick start

1. Use Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `python -m pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set a fresh Telegram bot token and the required AI provider key.
5. Run `python -m utils.healthcheck`.
6. Start one polling process with `python main.py`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker, systemd, upgrade, backup, and recovery instructions. See [RELEASE_NOTES.md](RELEASE_NOTES.md) and `docs/refactoring/` for scope and engineering notes.

## Important operational notes

- Run only one polling process per bot token.
- Keep `.env`, SQLite databases, backups, and logs private.
- Preserve the existing `manga_bot.db` when upgrading; do not assume a fresh database contains old user data.
- Jobs and active sessions are currently in memory and are not recovered after a process restart.
- `python -m utils.healthcheck` checks local configuration/storage only; it does not test Telegram or Gemini connectivity.
- This release candidate has not been certified on the target 0.5 CPU / 512 MB host.
