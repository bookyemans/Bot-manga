# Void Translator — Phase 10 Security & Stability Report

## Scope
Review and targeted hardening of runtime file permissions, upstream error handling, and deployment configuration consistency. No database schema changes, dependency additions, or architecture changes were made.

## Changes
- Added `shared/file_security.py` with `create_private_file_if_missing()`. On POSIX, newly created runtime files receive mode `0600`; existing file permissions are intentionally not changed. Non-POSIX systems retain normal platform behavior.
- Updated `shared/database.py` to create a missing SQLite database file with owner-only permissions before opening it. Existing database permissions are preserved.
- Updated `utils/instance_lock.py` to apply owner-only (`0600`) permissions to the runtime lock file on POSIX.
- Updated `systems/ai_engine/gemini.py` so `_GeminiHTTPError` retains only the HTTP status in its message instead of retaining a truncated upstream response body that may contain sensitive provider details.
- Corrected image-limit examples in `.env.example` to match the current Settings defaults (10,000,000 pixels and 10,000,000 download bytes).
- Added tests for sanitized provider errors and POSIX file permissions.

## Verification
- Baseline before changes: `55 passed in 3.40s`.
- After changes: `58 passed in 3.45s`.
- `python -m compileall -q .`: passed (exit code 0).

## Verification limitations
- `aiosqlite` is not installed in this execution environment. The SQLite integration test module is dependency-gated, so the actual database connect/close path was not exercised here. The permission helper and lock permission behavior were tested independently.
- No live Telegram or Gemini requests were made.
- No production host permissions, backup procedures, or 512 MB RAM load tests were performed.
- API keys remain stored in the existing SQLite schema as plaintext. Encrypting or hashing them safely requires a separately designed migration and key-management strategy; this phase deliberately did not alter the schema or existing credentials.
- Existing database file permissions are not automatically tightened. Operators should review existing DB, WAL/SHM, `.env`, and backup file permissions on the deployment host.

## Compatibility
- No schema changes.
- No new packages.
- Existing database files and their permission modes are preserved.
- Gemini HTTP status handling and retry decisions are unchanged; only sensitive upstream body text is removed from exception messages.
