"""Unit tests for Metabase embed signing helpers."""

from __future__ import annotations

import os
import time
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "dash" / "tools" / "metabase_embed.py"
)
MODULE_SPEC = spec_from_file_location("dash_tools_metabase_embed", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Failed to load dash/tools/metabase_embed.py for tests.")
MODULE = module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(MODULE)

build_metabase_question_embed = MODULE.build_metabase_question_embed
is_metabase_embedding_configured = MODULE.is_metabase_embedding_configured


class TestMetabaseEmbedHelpers(unittest.TestCase):
    def test_build_embed_returns_signed_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
                "METABASE_EMBED_TTL_SECONDS": "900",
            },
            clear=False,
        ):
            embed = build_metabase_question_embed(question_id=42, title="Sales trend")

        self.assertEqual(embed["kind"], "metabase_question")
        self.assertEqual(embed["question_id"], 42)
        self.assertEqual(embed["title"], "Sales trend")
        self.assertTrue(
            embed["iframe_url"].startswith("https://metabase.example.com/embed/question/")
        )
        self.assertEqual(embed["open_url"], "https://metabase.example.com/question/42")
        ttl = embed["expires_at"] - int(time.time())
        self.assertGreaterEqual(ttl, 1)
        self.assertLessEqual(ttl, 900)

    def test_ttl_is_clamped_to_safe_upper_bound(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
                "METABASE_EMBED_TTL_SECONDS": "99999",
            },
            clear=False,
        ):
            embed = build_metabase_question_embed(question_id=9)

        ttl = embed["expires_at"] - int(time.time())
        self.assertGreaterEqual(ttl, 1)
        self.assertLessEqual(ttl, 3600)

    def test_allowlist_blocks_unknown_question(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
                "METABASE_ALLOWED_QUESTION_IDS": "1,2,3",
            },
            clear=False,
        ):
            with self.assertRaises(PermissionError):
                build_metabase_question_embed(question_id=42)

    def test_ttl_is_clamped_to_safe_lower_bound(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
                "METABASE_EMBED_TTL_SECONDS": "1",
            },
            clear=False,
        ):
            embed = build_metabase_question_embed(question_id=5)

        ttl = embed["expires_at"] - int(time.time())
        self.assertGreaterEqual(ttl, 59)  # clamped to MIN=60

    def test_missing_embed_secret_raises(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                build_metabase_question_embed(question_id=1)

    def test_invalid_site_url_raises(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "metabase.example.com",  # missing scheme
                "METABASE_EMBED_SECRET": "test-secret",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                build_metabase_question_embed(question_id=1)

    def test_invalid_allowlist_format_raises(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
                "METABASE_ALLOWED_QUESTION_IDS": "1,abc,3",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                build_metabase_question_embed(question_id=1)

    def test_embedding_config_detects_required_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "test-secret",
            },
            clear=False,
        ):
            self.assertTrue(is_metabase_embedding_configured())

        with patch.dict(
            os.environ,
            {
                "METABASE_URL": "https://metabase.example.com",
                "METABASE_EMBED_SECRET": "",
            },
            clear=False,
        ):
            self.assertFalse(is_metabase_embedding_configured())


if __name__ == "__main__":
    unittest.main()
