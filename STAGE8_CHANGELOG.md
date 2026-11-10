# Stage 8 — Deployment & Portability

- Added configurable database and instance-lock paths while retaining the historical `manga_bot.db` default.
- Added a cross-platform OS advisory lock to prevent duplicate polling processes in one deployment directory.
- Added a local health-check command that validates required token configuration and SQLite accessibility/integrity without exposing credentials or making external API calls.
- Hardened shutdown so job workers, Gemini resources, and SQLite each get a cleanup attempt even if another cleanup step fails.
- Added Dockerfile, Docker Compose persistent volumes, Procfile worker declaration, systemd service example, `.dockerignore`, and deployment/migration instructions.
- Added explicit `python-dotenv` dependency for `.env` loading via pydantic-settings.
- Kept `.env` and database artifacts excluded from archives/source control.
