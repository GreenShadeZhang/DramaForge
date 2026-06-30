import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import database
import app.models  # noqa: F401


@pytest.mark.asyncio
async def test_init_db_adds_story_bible_columns_to_existing_sqlite_scripts(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, future=True)
    monkeypatch.setattr(database, "async_engine", engine)
    monkeypatch.setattr(database.settings, "database_url", database_url)

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE scripts (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                protagonist VARCHAR(100),
                genre VARCHAR(50),
                synopsis TEXT,
                background TEXT,
                setting TEXT,
                one_liner VARCHAR(200),
                raw_content TEXT,
                is_approved BOOLEAN DEFAULT 0,
                created_at DATETIME
            )
        """))

    await database.init_db()

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(scripts)"))
        columns = {row[1] for row in result.fetchall()}

    assert {
        "premise",
        "world_rules",
        "character_relationships",
        "timeline",
        "episode_arc",
        "visual_style_rules",
        "continuity_notes",
    }.issubset(columns)

    await engine.dispose()
