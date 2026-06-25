import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.services.storage import storage


class StorageCleanupTest(unittest.TestCase):
    def test_delete_project_tree_removes_only_project_directory(self):
        original_storage_dir = settings.storage_dir
        with tempfile.TemporaryDirectory() as tmp:
            settings.storage_dir = tmp
            try:
                project_dir = settings.projects_path / "42"
                nested_file = project_dir / "ep001" / "segments" / "segment_0001.mp4"
                nested_file.parent.mkdir(parents=True)
                nested_file.write_text("video", encoding="utf-8")

                self.assertTrue(storage.delete_project_tree(42))
                self.assertFalse(project_dir.exists())
                self.assertTrue((Path(tmp) / "projects").exists())
            finally:
                settings.storage_dir = original_storage_dir


if __name__ == "__main__":
    unittest.main()
