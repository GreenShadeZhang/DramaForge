"""arq worker tasks for storyboard generation."""

from __future__ import annotations

from arq.connections import RedisSettings, create_pool

from app.core.config import settings
from app.services.storyboard_generation_service import run_storyboard_generation


async def run_storyboard_generation_job(
    ctx: dict,
    project_id: int,
    episode_id: int,
    user_id: int,
    shots_per_segment: int,
) -> dict[str, object]:
    return await run_storyboard_generation(
        project_id=project_id,
        episode_id=episode_id,
        user_id=user_id,
        shots_per_segment=shots_per_segment,
    )


async def enqueue_storyboard_generation_job(
    *,
    project_id: int,
    episode_id: int,
    user_id: int,
    shots_per_segment: int,
) -> str:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        queued = await redis.enqueue_job(
            "run_storyboard_generation_job",
            project_id,
            episode_id,
            user_id,
            shots_per_segment,
        )
        if queued is None:
            raise RuntimeError("arq rejected storyboard generation job")
        return queued.job_id
    finally:
        await redis.close()
