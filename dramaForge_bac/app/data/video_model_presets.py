"""Known video model presets and capability merging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VIDEO_PRESET_ID_KEY = "video_preset_id"


@dataclass(frozen=True)
class VideoModelPreset:
    preset_id: str
    display_name: str
    provider_types: tuple[str, ...]
    model_ids: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    default_model_id: str | None = None
    default_params_json: dict[str, Any] = field(default_factory=dict)
    capabilities_json: dict[str, Any] = field(default_factory=dict)
    match_policy: str = "exact_or_alias"

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "display_name": self.display_name,
            "provider_types": list(self.provider_types),
            "model_ids": list(self.model_ids),
            "aliases": list(self.aliases),
            "default_model_id": self.default_model_id or (self.model_ids[0] if self.model_ids else ""),
            "default_params_json": dict(self.default_params_json),
            "capabilities_json": dict(self.capabilities_json),
            "match_policy": self.match_policy,
        }


SORA_DURATIONS = ["4", "8", "12", "16", "20"]
SORA_2_SIZES = ["720x1280", "1280x720"]
SORA_2_PRO_SIZES = [
    "720x1280",
    "1280x720",
    "1024x1792",
    "1792x1024",
    "1080x1920",
    "1920x1080",
]


VIDEO_MODEL_PRESETS: tuple[VideoModelPreset, ...] = (
    VideoModelPreset(
        preset_id="openai/sora-2",
        display_name="OpenAI Sora 2",
        provider_types=("openai_native", "openai_compatible"),
        model_ids=("sora-2",),
        aliases=("OpenAI Sora 2", "Sora 2"),
        default_model_id="sora-2",
        default_params_json={"seconds": "8", "size": "720x1280"},
        capabilities_json={
            "video_size": True,
            "video_supported_sizes": SORA_2_SIZES,
            "video_size_param": "size",
            "video_duration": True,
            "video_supported_durations": SORA_DURATIONS,
            "video_duration_param": "seconds",
            "video_first_frame": True,
            "video_reference_roles": ["character", "scene", "style"],
        },
    ),
    VideoModelPreset(
        preset_id="openai/sora-2-pro",
        display_name="OpenAI Sora 2 Pro",
        provider_types=("openai_native", "openai_compatible"),
        model_ids=("sora-2-pro",),
        aliases=("OpenAI Sora 2 Pro", "Sora 2 Pro"),
        default_model_id="sora-2-pro",
        default_params_json={"seconds": "8", "size": "1280x720"},
        capabilities_json={
            "video_size": True,
            "video_supported_sizes": SORA_2_PRO_SIZES,
            "video_size_param": "size",
            "video_duration": True,
            "video_supported_durations": SORA_DURATIONS,
            "video_duration_param": "seconds",
            "video_first_frame": True,
            "video_reference_roles": ["character", "scene", "style"],
        },
    ),
    VideoModelPreset(
        preset_id="laozhang/veo-3.1-fast",
        display_name="Veo 3.1 Fast",
        provider_types=("openai_compatible",),
        model_ids=("veo-3.1-fast",),
        aliases=("veo3.1-fast", "veo-3.1 fast"),
        default_model_id="veo-3.1-fast",
        capabilities_json={
            "video_reference_images": True,
            "video_first_frame": True,
            "video_multi_reference": True,
            "video_max_reference_images": 3,
            "video_reference_roles": ["character", "scene", "style"],
        },
    ),
    VideoModelPreset(
        preset_id="fal/kling-i2v",
        display_name="Kling I2V (fal.ai)",
        provider_types=("fal", "fal_ai"),
        model_ids=("fal-ai/kling-video/v1.6/standard/image-to-video",),
        aliases=("kling-i2v", "kling image-to-video"),
        default_model_id="fal-ai/kling-video/v1.6/standard/image-to-video",
        capabilities_json={
            "video_first_frame": True,
            "video_reference_roles": ["character", "scene"],
        },
    ),
    VideoModelPreset(
        preset_id="runway/gen4_turbo",
        display_name="Runway Gen-4 Turbo",
        provider_types=("runway",),
        model_ids=("gen4_turbo",),
        aliases=("runway gen4 turbo", "gen-4 turbo"),
        default_model_id="gen4_turbo",
        capabilities_json={
            "video_first_frame": True,
            "video_reference_roles": ["character", "scene", "style"],
        },
    ),
    VideoModelPreset(
        preset_id="seedance-2.0",
        display_name="SeeDance 2.0",
        provider_types=("openai_compatible",),
        model_ids=("seedance-2.0",),
        aliases=("seedance 2.0",),
        default_model_id="seedance-2.0",
    ),
    VideoModelPreset(
        preset_id="seedance-1-0-pro",
        display_name="Seedance 1.0 Pro",
        provider_types=("volcengine_ark", "volces"),
        model_ids=("seedance-1-0-pro",),
        aliases=("seedance 1.0 pro",),
        default_model_id="seedance-1-0-pro",
    ),
    VideoModelPreset(
        preset_id="replicate/kling-standard",
        display_name="Kling Standard (Replicate)",
        provider_types=("replicate",),
        model_ids=("kwaivgi/kling-v1.6-standard",),
        aliases=("kling standard", "kling-v1.6-standard"),
        default_model_id="kwaivgi/kling-v1.6-standard",
    ),
    VideoModelPreset(
        preset_id="luma/ray-2",
        display_name="Luma Ray 2",
        provider_types=("luma",),
        model_ids=("ray-2",),
        aliases=("ray 2", "luma ray 2"),
        default_model_id="ray-2",
    ),
    VideoModelPreset(
        preset_id="dashscope/wan2.1-t2v-turbo",
        display_name="Wan 2.1 T2V Turbo",
        provider_types=("dashscope",),
        model_ids=("wan2.1-t2v-turbo",),
        aliases=("wan 2.1 t2v turbo",),
        default_model_id="wan2.1-t2v-turbo",
    ),
    VideoModelPreset(
        preset_id="google/veo-3.0-generate-preview",
        display_name="Google Veo 3 Preview",
        provider_types=("google_vertex", "vertex"),
        model_ids=("veo-3.0-generate-preview",),
        aliases=("veo 3 preview", "google veo 3"),
        default_model_id="veo-3.0-generate-preview",
    ),
)


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def list_video_model_presets() -> list[dict[str, Any]]:
    return [preset.to_dict() for preset in VIDEO_MODEL_PRESETS]


def get_video_model_preset(preset_id: str | None) -> VideoModelPreset | None:
    normalized = _norm(preset_id)
    if not normalized:
        return None
    for preset in VIDEO_MODEL_PRESETS:
        if _norm(preset.preset_id) == normalized:
            return preset
    return None


def match_video_model_preset(
    model_id: str | None,
    provider_type: str | None = None,
    preset_id: str | None = None,
) -> VideoModelPreset | None:
    explicit = get_video_model_preset(preset_id)
    if explicit:
        return explicit

    normalized_model = _norm(model_id)
    normalized_provider = _norm(provider_type)
    if not normalized_model:
        return None

    for preset in VIDEO_MODEL_PRESETS:
        provider_matches = (
            not normalized_provider
            or not preset.provider_types
            or normalized_provider in {_norm(item) for item in preset.provider_types}
        )
        if not provider_matches:
            continue
        candidates = {_norm(item) for item in (*preset.model_ids, *preset.aliases)}
        if normalized_model in candidates:
            return preset
    return None


def video_preset_id_from_schema(param_schema_json: dict[str, Any] | None) -> str | None:
    if not isinstance(param_schema_json, dict):
        return None
    value = param_schema_json.get(VIDEO_PRESET_ID_KEY)
    return str(value).strip() if value else None


def effective_video_model_config(
    *,
    model_id: str | None,
    provider_type: str | None = None,
    default_params_json: dict[str, Any] | None = None,
    capabilities_json: dict[str, Any] | None = None,
    param_schema_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_default_params = dict(default_params_json or {})
    user_capabilities = dict(capabilities_json or {})
    preset = match_video_model_preset(
        model_id,
        provider_type,
        video_preset_id_from_schema(param_schema_json),
    )
    effective_default_params = {}
    effective_capabilities = {}
    if preset:
        effective_default_params.update(preset.default_params_json)
        effective_capabilities.update(preset.capabilities_json)
    effective_default_params.update(user_default_params)
    effective_capabilities.update(user_capabilities)
    return {
        "preset_id": preset.preset_id if preset else None,
        "effective_default_params_json": effective_default_params,
        "effective_capabilities_json": effective_capabilities,
    }


def preset_model_schema(preset_id: str | None) -> dict[str, Any]:
    return {VIDEO_PRESET_ID_KEY: preset_id} if preset_id else {}


def catalog_video_model(
    preset_id: str,
    *,
    display_name: str | None = None,
    model_id: str | None = None,
    is_default: bool = False,
) -> dict[str, Any]:
    preset = get_video_model_preset(preset_id)
    if not preset:
        raise ValueError(f"Unknown video model preset: {preset_id}")
    return {
        "model_id": model_id or preset.default_model_id or preset.model_ids[0],
        "display_name": display_name or preset.display_name,
        "capability": "video",
        "is_default": is_default,
        "default_params_json": {},
        "param_schema_json": preset_model_schema(preset.preset_id),
        "capabilities_json": {},
    }
