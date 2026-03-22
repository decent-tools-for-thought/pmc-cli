from __future__ import annotations

from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmc_tool.config import DEFAULT_CONFIG, config_path, load_config, reset_config, save_config  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_save_and_load_config_follow_xdg_path(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmpdir}, clear=False):
                config = load_config()
                config["api"]["email"] = "tester@example.com"
                config["search"]["synonym_expansion"] = False
                save_config(config)

                path = config_path()
                self.assertTrue(path.exists())
                self.assertIn("tester@example.com", path.read_text(encoding="utf-8"))
                loaded = load_config()
                self.assertEqual(loaded["api"]["email"], "tester@example.com")
                self.assertFalse(loaded["search"]["synonym_expansion"])

    def test_load_config_merges_partial_override_with_defaults(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmpdir}, clear=False):
                path = config_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('[api]\nemail = "person@example.com"\n', encoding="utf-8")

                loaded = load_config()
                self.assertEqual(loaded["api"]["email"], "person@example.com")
                self.assertEqual(loaded["search"], DEFAULT_CONFIG["search"])
                self.assertEqual(loaded["output"], DEFAULT_CONFIG["output"])

    def test_reset_config_rewrites_defaults(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": tmpdir}, clear=False):
                config = reset_config()
                self.assertEqual(config, DEFAULT_CONFIG)
                self.assertEqual(load_config(), DEFAULT_CONFIG)


if __name__ == "__main__":
    unittest.main()
