"""SQLite schema and query invariants (uses stdlib sqlite3 for portability)."""
import sqlite3


def _initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS users_access (user_id INTEGER PRIMARY KEY, role TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, persona TEXT, mode TEXT, output_method TEXT, file_format TEXT)")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(settings)").fetchall()}
    for column in ("session_mode", "use_glossary"):
        if column not in columns:
            conn.execute(f"ALTER TABLE settings ADD COLUMN {column} TEXT")
    conn.execute("CREATE TABLE IF NOT EXISTS api_keys (key_value TEXT PRIMARY KEY, user_id INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_access_role ON users_access(role)")
    conn.commit()


def test_schema_migration_is_idempotent_and_preserves_existing_rows():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE settings (user_id INTEGER PRIMARY KEY, persona TEXT)")
    conn.execute("INSERT INTO settings(user_id, persona) VALUES (7, 'Nabil')")
    _initialize(conn)
    _initialize(conn)
    row = conn.execute("SELECT persona, session_mode, use_glossary FROM settings WHERE user_id=7").fetchone()
    assert row == ("Nabil", None, None)


def test_settings_upsert_uses_one_statement_and_preserves_other_columns():
    conn = sqlite3.connect(":memory:")
    _initialize(conn)
    conn.execute("INSERT INTO settings(user_id, persona) VALUES (?, ?)", (7, "Nabil"))
    conn.execute(
        "INSERT INTO settings (user_id, mode) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET mode = excluded.mode",
        (7, "bubble"),
    )
    assert conn.execute("SELECT persona, mode FROM settings WHERE user_id=7").fetchone() == ("Nabil", "bubble")


def test_access_and_api_key_mutations_are_atomic_and_report_row_counts():
    conn = sqlite3.connect(":memory:")
    _initialize(conn)
    first = conn.execute("INSERT OR IGNORE INTO users_access(user_id, role) VALUES (?, 'user')", (12,)).rowcount
    duplicate = conn.execute("INSERT OR IGNORE INTO users_access(user_id, role) VALUES (?, 'user')", (12,)).rowcount
    removed = conn.execute("DELETE FROM users_access WHERE user_id=? AND role='user'", (12,)).rowcount
    assert (first, duplicate, removed) == (1, 0, 1)
    inserted = conn.execute("INSERT OR IGNORE INTO api_keys(key_value, user_id) VALUES (?, NULL)", ("test-key",)).rowcount
    duplicate_key = conn.execute("INSERT OR IGNORE INTO api_keys(key_value, user_id) VALUES (?, NULL)", ("test-key",)).rowcount
    assert (inserted, duplicate_key) == (1, 0)


def test_query_indexes_exist_for_role_and_user_key_lookups():
    conn = sqlite3.connect(":memory:")
    _initialize(conn)
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(users_access)")} | {
        row[1] for row in conn.execute("PRAGMA index_list(api_keys)")
    }
    assert "idx_users_access_role" in indexes
    assert "idx_api_keys_user_id" in indexes
