from __future__ import annotations

from typing import Any


REFERENCE_CAPABLE_MODEL_NAMES = [
    "Veo 3.1 Fast",
    "Veo 3.1",
    "Sora 2",
    "Runway Gen-4 Turbo",
    "Kling I2V",
]


def supports_visual_references(capabilities: dict[str, Any] | None) -> bool:
    caps = capabilities or {}
    return bool(
        caps.get("video_reference_images")
        or caps.get("video_first_frame")
        or caps.get("video_multi_reference")
    )


def max_reference_images(capabilities: dict[str, Any] | None) -> int:
    caps = capabilities or {}
    if caps.get("video_multi_reference"):
        value = caps.get("video_max_reference_images")
        try:
            return max(1, int(value or 3))
        except (TypeError, ValueError):
            return 3
    if caps.get("video_reference_images"):
        return 1
    if caps.get("video_first_frame"):
        return 1
    return 0


def supported_reference_roles(capabilities: dict[str, Any] | None) -> set[str]:
    roles = (capabilities or {}).get("video_reference_roles") or []
    return {str(role) for role in roles if role}


def ordered_visual_references(
    visual_references: list[dict[str, Any]] | None,
    capabilities: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not supports_visual_references(capabilities):
        return []

    supported_roles = supported_reference_roles(capabilities)
    refs = [
        ref for ref in (visual_references or [])
        if isinstance(ref, dict)
        and ref.get("image_url")
        and (not supported_roles or ref.get("type") in supported_roles or ref.get("role") in supported_roles)
    ]

    priority = {
        "environment": 0,
        "scene": 0,
        "identity": 1,
        "character": 1,
        "composition": 2,
        "style": 3,
    }

    def score(ref: dict[str, Any]) -> tuple[int, str]:
        role = str(ref.get("role") or ref.get("type") or "")
        return priority.get(role, 9), str(ref.get("label") or ref.get("target") or "")

    return sorted(refs, key=score)[:max_reference_images(capabilities)]


def reference_image_payload(
    visual_references: list[dict[str, Any]] | None,
    capabilities: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = ordered_visual_references(visual_references, capabilities)
    if not refs:
        return {}

    urls = [str(ref["image_url"]) for ref in refs]
    if (capabilities or {}).get("video_multi_reference") or (capabilities or {}).get("video_reference_images"):
        return {"reference_images": urls}
    if (capabilities or {}).get("video_first_frame"):
        return {"first_frame": urls[0]}
    return {}


def append_reference_instructions(
    prompt: str,
    visual_references: list[dict[str, Any]] | None,
    capabilities: dict[str, Any] | None,
) -> str:
    refs = ordered_visual_references(visual_references, capabilities)
    if not refs:
        return prompt

    lines = ["", "Reference image instructions:"]
    for index, ref in enumerate(refs, start=1):
        label = ref.get("label") or ref.get("target") or ref.get("type") or f"reference {index}"
        role = ref.get("role") or ref.get("type") or "reference"
        placement = ref.get("placement") or "unspecified"
        scope = ref.get("scope") or "whole_shot"
        instruction = ref.get("instruction") or "Use this image as the visual reference for the named subject."
        lines.append(f"{index}. {label}: {role}, {placement}, {scope}. {instruction}")
    return f"{prompt.rstrip()}\n" + "\n".join(lines)
