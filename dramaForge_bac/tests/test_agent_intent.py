import unittest

from app.api.v2.chat import _classify_agent_intent
from app.services.agent_intent import AgentIntent, agent_intent_classifier


class AgentIntentClassifierTests(unittest.TestCase):
    def test_classifies_image_generation_request(self):
        result = agent_intent_classifier.classify("帮我生成一张竖屏赛博朋克短剧海报")

        self.assertEqual(result.intent, AgentIntent.IMAGE)
        self.assertEqual(result.slots["aspect_ratio"], "9:16")
        self.assertEqual(result.slots["image_size"], "1024x1792")

    def test_classifies_video_generation_request(self):
        result = agent_intent_classifier.classify("生成一个8秒横屏悬疑短视频，雨夜追车")

        self.assertEqual(result.intent, AgentIntent.VIDEO)
        self.assertEqual(result.slots["duration"], "8")
        self.assertEqual(result.slots["aspect_ratio"], "16:9")
        self.assertEqual(result.slots["video_resolution"], "1280x720")

    def test_image_to_video_prefers_video(self):
        result = agent_intent_classifier.classify("把这张角色图做成图生视频")

        self.assertEqual(result.intent, AgentIntent.VIDEO)

    def test_scriptwriting_stays_chat(self):
        result = agent_intent_classifier.classify("帮我写一个短剧脚本，主题是职场逆袭")

        self.assertEqual(result.intent, AgentIntent.CHAT)

    def test_selected_model_capability_forces_media_intent(self):
        result = _classify_agent_intent(
            content="帮我写一个短剧脚本，主题是职场逆袭",
            mode="general",
            model_capability="image",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.intent, AgentIntent.IMAGE)
        self.assertEqual(result.matched_by, "selected_model")

    def test_non_general_mode_does_not_route_media(self):
        result = _classify_agent_intent(
            content="生成一张竖屏海报",
            mode="scriptwriter",
            model_capability="image",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
