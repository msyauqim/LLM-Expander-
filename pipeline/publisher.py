"""Publisher: simpan game ke SQLite database."""
import json
import sqlite3
import datetime
from pipeline.config import DB_PATH
from pipeline.models import AssembledGame, GameSpec


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE,
            title TEXT,
            html_content TEXT,
            metadata_json TEXT,
            created_at TEXT,
            published INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    return conn


def publish(game: AssembledGame, spec: GameSpec) -> str:
    """Simpan game ke database. Return game_id."""
    conn = _init_db()
    game_id = spec.data.get("game_id", f"game_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
    title = spec.data.get("metadata", {}).get("title", "Game Edukasi")

    conn.execute(
        "INSERT OR REPLACE INTO games (game_id, title, html_content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (game_id, title, game.html, json.dumps(spec.data, ensure_ascii=False), datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    print(f"  Game '{title}' published (ID: {game_id})")
    return game_id
