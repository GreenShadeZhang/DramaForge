from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.v2 import scripts
from app.core.database import Base
from app.models.project import DramaGenre, Project, VideoStyle
from app.models.script import Script
from app.models.user import User
from app.schemas.script import (
    ScriptGenerateRequest,
    StoryBibleDraftRequest,
    StoryBibleUpdate,
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _user_project(db_session):
    user = User(id=1, username="creator", email="creator@example.com")
    project = Project(
        id=1,
        user_id=1,
        title="职场反击",
        description="女主被陷害后用证据反击。",
        genre=DramaGenre.URBAN,
        style=VideoStyle.REALISTIC,
    )
    db_session.add_all([user, project])
    await db_session.flush()
    return user, project


def _model_resolution():
    return SimpleNamespace(
        model_id="test-model",
        api_key="test-key",
        base_url="https://example.test",
        raw_params={},
    )


def _generated_script_result():
    return {
        "script": {
            "protagonist": "林夏",
            "genre": "都市情感",
            "synopsis": "林夏在公司会议上反击陷害。",
            "background": "现代都市公司。",
            "setting": "职场陷害与证据反转。",
            "one_liner": "被陷害的女主用证据完成反击。",
            "raw_content": "{}",
            "premise": "AI 生成的命题",
            "world_rules": "AI 生成的世界规则",
            "character_relationships": "AI 生成的人物关系",
            "timeline": "AI 生成的时间线",
            "episode_arc": "AI 生成的分集节奏",
            "visual_style_rules": "AI 生成的视觉规则",
            "continuity_notes": "AI 生成的连续性备注",
        },
        "episodes": [
            {"number": 1, "title": "会议反击", "content": "△ 公司会议室。"},
        ],
        "characters": [
            {"name": "林夏", "role": "protagonist", "description": "冷静坚韧"},
        ],
        "scenes": [
            {"name": "公司会议室", "description": "高压会议现场", "time_of_day": "day", "interior": True},
        ],
    }


@pytest.mark.asyncio
async def test_get_story_bible_creates_draft_script(db_session):
    user, project = await _user_project(db_session)

    bible = await scripts.get_story_bible(project.id, user, db_session)
    result = await db_session.execute(select(Script).where(Script.project_id == project.id))
    script = result.scalar_one()

    assert bible.premise == ""
    assert script.project_id == project.id
    assert script.episodes == []


@pytest.mark.asyncio
async def test_update_story_bible_before_generation(db_session):
    user, project = await _user_project(db_session)

    bible = await scripts.update_story_bible(
        project.id,
        StoryBibleUpdate(premise="女主被陷害后完成反击。"),
        user,
        db_session,
    )

    assert bible.premise == "女主被陷害后完成反击。"


@pytest.mark.asyncio
async def test_draft_story_bible_fills_empty_fields_without_overwriting(monkeypatch, db_session):
    user, project = await _user_project(db_session)
    db_session.add(Script(project_id=project.id, premise="用户手写命题"))
    await db_session.flush()

    async def resolve(db, user_id, capability):
        return _model_resolution()

    async def draft_story_bible(**kwargs):
        return {
            "premise": "AI 命题",
            "world_rules": "AI 世界规则",
            "character_relationships": "AI 人物关系",
            "timeline": "AI 时间线",
            "episode_arc": "AI 分集节奏",
            "visual_style_rules": "AI 视觉规则",
            "continuity_notes": "AI 连续性备注",
        }

    monkeypatch.setattr(scripts.user_model_resolver, "resolve", resolve)
    monkeypatch.setattr(scripts.script_engine, "draft_story_bible", draft_story_bible)

    bible = await scripts.draft_story_bible(
        project.id,
        StoryBibleDraftRequest(user_input="职场反击", total_episodes=3),
        user,
        db_session,
    )

    assert bible.premise == "用户手写命题"
    assert bible.world_rules == "AI 世界规则"


@pytest.mark.asyncio
async def test_draft_story_bible_preview_without_project(monkeypatch, db_session):
    user = User(id=1, username="creator", email="creator@example.com")
    db_session.add(user)
    await db_session.flush()
    captured = {}

    async def resolve(db, user_id, capability):
        return _model_resolution()

    async def draft_story_bible(**kwargs):
        captured.update(kwargs)
        return {
            "premise": "AI 命题",
            "world_rules": "AI 世界规则",
            "character_relationships": "AI 人物关系",
            "timeline": "AI 时间线",
            "episode_arc": "AI 分集节奏",
            "visual_style_rules": "AI 视觉规则",
            "continuity_notes": "AI 连续性备注",
        }

    monkeypatch.setattr(scripts.user_model_resolver, "resolve", resolve)
    monkeypatch.setattr(scripts.script_engine, "draft_story_bible", draft_story_bible)

    bible = await scripts.draft_story_bible_preview(
        StoryBibleDraftRequest(user_input="职场反击", genre="urban", total_episodes=5),
        user,
        db_session,
    )

    assert captured["project"] is None
    assert captured["user_input"] == "职场反击"
    assert captured["genre"] == "urban"
    assert captured["total_episodes"] == 5
    assert bible.premise == "AI 命题"


@pytest.mark.asyncio
async def test_generate_script_uses_and_preserves_existing_story_bible(monkeypatch, db_session):
    user, project = await _user_project(db_session)
    db_session.add(Script(project_id=project.id, premise="用户手写命题"))
    await db_session.flush()
    captured = {}

    async def resolve(db, user_id, capability):
        return _model_resolution()

    async def create_from_text(**kwargs):
        captured["story_bible"] = kwargs.get("story_bible")
        return _generated_script_result()

    monkeypatch.setattr(scripts.user_model_resolver, "resolve", resolve)
    monkeypatch.setattr(scripts.script_engine, "create_from_text", create_from_text)

    generated = await scripts.generate_script(
        project.id,
        ScriptGenerateRequest(user_input="职场反击", total_episodes=1),
        user,
        db_session,
    )

    assert captured["story_bible"] == {"premise": "用户手写命题"}
    assert generated.premise == "用户手写命题"


@pytest.mark.asyncio
async def test_save_script_result_preserves_story_bible_override(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(scripts, "_AsyncSessionLocal", session_factory)
    async with session_factory() as session:
        session.add(Project(id=1, user_id=1, title="职场反击"))
        session.add(Script(project_id=1, premise="旧命题"))
        await session.commit()

    await scripts._save_script_result(
        1,
        _generated_script_result(),
        False,
        {"premise": "用户手写命题"},
    )

    async with session_factory() as session:
        result = await session.execute(select(Script).where(Script.project_id == 1))
        script = result.scalar_one()

    await engine.dispose()

    assert script.premise == "用户手写命题"
    assert script.world_rules == "AI 生成的世界规则"
