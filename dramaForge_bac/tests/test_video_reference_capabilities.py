import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "video_reference_capabilities.py"
)
SPEC = spec_from_file_location("video_reference_capabilities", MODULE_PATH)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

append_reference_instructions = MODULE.append_reference_instructions
reference_image_payload = MODULE.reference_image_payload
supports_visual_references = MODULE.supports_visual_references


class VideoReferenceCapabilitiesTest(unittest.TestCase):
    def test_empty_capabilities_do_not_support_references(self):
        self.assertFalse(supports_visual_references({}))
        self.assertEqual(reference_image_payload([], {}), {})

    def test_multi_reference_payload_uses_ordered_urls(self):
        refs = [
            {"type": "character", "role": "identity", "image_url": "char.png", "label": "Hero"},
            {"type": "scene", "role": "environment", "image_url": "scene.png", "label": "Temple"},
            {"type": "style", "role": "style", "image_url": "style.png", "label": "Ink"},
        ]
        caps = {
            "video_reference_images": True,
            "video_multi_reference": True,
            "video_max_reference_images": 2,
            "video_reference_roles": ["character", "scene", "style"],
        }

        self.assertEqual(
            reference_image_payload(refs, caps),
            {"reference_images": ["scene.png", "char.png"]},
        )

    def test_first_frame_payload_uses_single_url(self):
        refs = [{"type": "scene", "role": "environment", "image_url": "scene.png", "label": "Temple"}]
        caps = {"video_first_frame": True}

        self.assertEqual(reference_image_payload(refs, caps), {"first_frame": "scene.png"})

    def test_prompt_instructions_include_reference_semantics(self):
        refs = [
            {
                "type": "scene",
                "role": "environment",
                "image_url": "scene.png",
                "label": "Temple",
                "placement": "background",
                "scope": "whole_shot",
                "instruction": "Keep the hall layout.",
            }
        ]
        prompt = append_reference_instructions("A slow push-in.", refs, {"video_first_frame": True})

        self.assertIn("Reference image instructions:", prompt)
        self.assertIn("Temple: environment, background, whole_shot. Keep the hall layout.", prompt)


if __name__ == "__main__":
    unittest.main()
