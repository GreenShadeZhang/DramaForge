"""Agent intent routing for chat, image, and video generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentIntent(str, Enum):
    CHAT = "chat"
    IMAGE = "image"
    VIDEO = "video"


@dataclass
class AgentIntentResult:
    intent: AgentIntent
    confidence: float
    prompt: str
    matched_by: str
    slots: dict[str, Any] = field(default_factory=dict)

    @property
    def is_media(self) -> bool:
        return self.intent in {AgentIntent.IMAGE, AgentIntent.VIDEO}

    def to_meta(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "matched_by": self.matched_by,
            "prompt": self.prompt,
            "slots": self.slots,
        }


_GENERATION_ACTIONS = (
    "生成",
    "创建",
    "制作",
    "做一个",
    "做一段",
    "做张",
    "出一张",
    "出图",
    "生图",
    "画一张",
    "绘制",
    "设计一张",
    "来一张",
    "来一段",
)

_IMAGE_TERMS = (
    "图片",
    "图像",
    "配图",
    "海报",
    "封面",
    "插画",
    "角色图",
    "场景图",
    "分镜图",
    "概念图",
    "宣传图",
    "剧照",
    "头像",
    "壁纸",
)

_VIDEO_TERMS = (
    "视频",
    "短视频",
    "短片",
    "长视频",
    "影片",
    "成片",
    "镜头",
    "动画",
    "动态画面",
    "转场",
    "运镜",
)

_VIDEO_PHRASES = (
    "图生视频",
    "图转视频",
    "图片转视频",
    "文生视频",
    "一键成片",
    "生成短片",
    "生成视频",
    "生成长视频",
    "做短片",
    "做视频",
)

_PLANNING_TERMS = (
    "脚本",
    "剧本",
    "文案",
    "大纲",
    "策划",
    "方案",
    "建议",
    "分析",
    "优化",
    "改写",
    "润色",
    "解释",
    "怎么",
    "如何",
    "为什么",
)

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:秒|s|S)")
_RATIO_RE = re.compile(r"(\d{1,2})\s*[:：]\s*(\d{1,2})")


class AgentIntentClassifier:
    """Small deterministic classifier for Agent mode media routing."""

    def classify(self, query: str) -> AgentIntentResult:
        text = (query or "").strip()
        lowered = text.lower()

        slots = self._extract_slots(text)
        if self._is_video_request(text, lowered):
            return AgentIntentResult(
                intent=AgentIntent.VIDEO,
                confidence=0.92,
                prompt=text,
                matched_by="rule",
                slots=slots,
            )

        if self._is_image_request(text, lowered):
            return AgentIntentResult(
                intent=AgentIntent.IMAGE,
                confidence=0.9,
                prompt=text,
                matched_by="rule",
                slots=slots,
            )

        return AgentIntentResult(
            intent=AgentIntent.CHAT,
            confidence=0.72,
            prompt=text,
            matched_by="fallback",
            slots=slots,
        )

    def _is_video_request(self, text: str, lowered: str) -> bool:
        if any(phrase in text for phrase in _VIDEO_PHRASES):
            return True

        has_action = any(action in text for action in _GENERATION_ACTIONS)
        has_video_term = any(term in text for term in _VIDEO_TERMS)
        if has_action and has_video_term:
            return True

        if has_video_term and not any(term in text for term in _PLANNING_TERMS):
            return any(word in text for word in ("我要", "帮我", "来个", "来一段"))

        if "video" in lowered and any(word in lowered for word in ("generate", "create", "make")):
            return True

        return False

    def _is_image_request(self, text: str, lowered: str) -> bool:
        if "图生视频" in text or "图片转视频" in text or "图转视频" in text:
            return False

        if any(action in text for action in ("出图", "生图", "画一张", "绘制")):
            return True

        has_action = any(action in text for action in _GENERATION_ACTIONS)
        has_image_term = any(term in text for term in _IMAGE_TERMS)
        if has_action and has_image_term:
            return True

        if has_image_term and not any(term in text for term in _PLANNING_TERMS):
            return any(word in text for word in ("我要", "帮我", "来个", "来一张"))

        if "image" in lowered and any(word in lowered for word in ("generate", "create", "make")):
            return True

        return False

    def _extract_slots(self, text: str) -> dict[str, Any]:
        slots: dict[str, Any] = {}

        duration = _DURATION_RE.search(text)
        if duration:
            slots["duration"] = duration.group(1)

        ratio = _RATIO_RE.search(text)
        if ratio:
            slots["aspect_ratio"] = f"{ratio.group(1)}:{ratio.group(2)}"

        if any(word in text for word in ("竖屏", "竖版", "手机屏", "9:16", "9：16")):
            slots["aspect_ratio"] = "9:16"
            slots["image_size"] = "1024x1792"
            slots["video_resolution"] = "720x1280"
        elif any(word in text for word in ("横屏", "横版", "16:9", "16：9")):
            slots["aspect_ratio"] = "16:9"
            slots["image_size"] = "1792x1024"
            slots["video_resolution"] = "1280x720"
        elif any(word in text for word in ("方图", "正方形", "1:1", "1：1")):
            slots["aspect_ratio"] = "1:1"
            slots["image_size"] = "1024x1024"

        return slots


agent_intent_classifier = AgentIntentClassifier()
