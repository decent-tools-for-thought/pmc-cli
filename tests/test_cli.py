from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmc_tool import cli  # noqa: E402


class FakeService:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.calls: list[tuple[str, dict]] = []

    def fetch(self, **kwargs: dict) -> dict:
        self.calls.append(("fetch", kwargs))
        return {"title": "Fetched", "id": {"pmid": "123"}, "url": "https://example.test"}

    def related_records(self, **kwargs: dict) -> dict:
        self.calls.append(("related_records", kwargs))
        return {
            "items": [{"title": "Related", "id": {"raw": "PMC1"}}],
            "meta": {"identifier": "PMC1"},
        }

    def export(self, **kwargs: dict) -> dict:
        self.calls.append(("export", kwargs))
        return {
            "items": [
                {"title": "Exported", "id": {"doi": "10.1/example"}, "authors": [], "journal": {}}
            ],
            "meta": {},
        }

    def grants_search(self, **kwargs: dict) -> dict:
        self.calls.append(("grants_search", kwargs))
        return {"items": [{"title": "Grant", "id": {"grantId": "081052"}}], "meta": {}}

    def grants_fetch(self, **kwargs: dict) -> dict:
        self.calls.append(("grants_fetch", kwargs))
        return {"title": "Grant", "id": {"grantId": "081052"}}

    def preprint_stats(self) -> dict:
        self.calls.append(("preprint_stats", {}))
        return {"query": "SRC:PPR", "preprintCount": 10}

    def search(self, **kwargs: dict) -> dict:
        self.calls.append(("search", kwargs))
        return {"items": [{"title": "Preprint", "id": {"pprId": "PPR1"}}], "meta": {}}


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "api": {"base_url": "https://example.test", "default_result_type": "lite", "email": ""},
            "search": {
                "default_page_size": 1000,
                "default_preprints_only": False,
                "synonym_expansion": True,
            },
            "output": {"default_format": "jsonl"},
        }

    def _run_main(self, argv: list[str]) -> tuple[int, str, FakeService]:
        service = FakeService(self.config)
        stdout = StringIO()
        with (
            patch("pmc_tool.cli.load_config", return_value=self.config),
            patch("pmc_tool.cli.EuropePmcService", return_value=service),
            redirect_stdout(stdout),
        ):
            code = cli.main(argv)
        return code, stdout.getvalue(), service

    def test_resolve_identifier_argument_prefers_positional_detection(self) -> None:
        args = cli._parser().parse_args(["fetch", "PMC8860882"])
        self.assertEqual(cli._resolve_identifier_argument(args), (None, "PMC8860882", None, None))

        args = cli._parser().parse_args(["fetch", "10.1000/example"])
        self.assertEqual(
            cli._resolve_identifier_argument(args), (None, None, None, "10.1000/example")
        )

    def test_fetch_defaults_to_json_when_config_default_is_jsonl(self) -> None:
        code, output, service = self._run_main(["fetch", "--pmid", "123"])
        self.assertEqual(code, 0)
        self.assertEqual(service.calls[0][0], "fetch")
        self.assertEqual(json.loads(output)["title"], "Fetched")

    def test_related_source_is_inferred_from_identifier(self) -> None:
        code, _, service = self._run_main(["related", "citations", "PMC8860882"])
        self.assertEqual(code, 0)
        self.assertEqual(
            service.calls[0],
            (
                "related_records",
                {
                    "source": "PMC",
                    "identifier": "PMC8860882",
                    "relation": "citations",
                    "page": 1,
                    "page_size": 25,
                },
            ),
        )

    def test_export_maps_search_arguments_to_service(self) -> None:
        code, output, service = self._run_main(
            [
                "export",
                "machine learning",
                "--preprints-only",
                "--limit",
                "20",
                "--format",
                "ris",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("TY  - JOUR", output)
        _, kwargs = service.calls[0]
        self.assertEqual(kwargs["query"], "machine learning")
        self.assertTrue(kwargs["preprints_only"])
        self.assertEqual(kwargs["limit"], 20)
        self.assertEqual(kwargs["format_name"], "ris")

    def test_grants_search_passes_helper_flags(self) -> None:
        code, _, service = self._run_main(
            [
                "grants",
                "search",
                "malaria",
                "--agency",
                "Wellcome Trust",
                "--pi",
                "smith",
                "--limit",
                "2",
            ]
        )
        self.assertEqual(code, 0)
        _, kwargs = service.calls[0]
        self.assertEqual(kwargs["query"], "malaria")
        self.assertEqual(kwargs["agency"], "Wellcome Trust")
        self.assertEqual(kwargs["pi"], "smith")
        self.assertEqual(kwargs["limit"], 2)

    def test_preprints_by_date_range_forces_preprint_search_and_sort(self) -> None:
        code, _, service = self._run_main(
            ["preprints", "by-date-range", "2024-01-01", "2024-01-31"]
        )
        self.assertEqual(code, 0)
        _, kwargs = service.calls[0]
        self.assertTrue(kwargs["preprints_only"])
        self.assertEqual(kwargs["from_date"], "2024-01-01")
        self.assertEqual(kwargs["to_date"], "2024-01-31")
        self.assertEqual(kwargs["sort"], "sort_date:y")


if __name__ == "__main__":
    unittest.main()
