from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmc_tool import cli  # noqa: E402
from pmc_tool.http import HttpResponse  # noqa: E402


class StdoutCapture:
    def __init__(self) -> None:
        self.buffer = BytesIO()

    def write(self, text: str) -> int:
        self.buffer.write(text.encode("utf-8"))
        return len(text)

    def flush(self) -> None:
        return None

    def getvalue(self) -> str:
        return self.buffer.getvalue().decode("utf-8")


class FakeArticlesApi:
    def __init__(self, config: dict, release: str = "production", base_url: str | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []

    def _response(self, content_type: str, body: bytes) -> HttpResponse:
        return HttpResponse(url="https://example.test", status=200, headers={"Content-Type": content_type}, body=body)

    def search(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("search", kwargs))
        return self._response("application/json", b'{"mode":"articles-search"}')

    def search_post(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("search_post", kwargs))
        return self._response("application/json", b'{"mode":"articles-search-post"}')

    def fields(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("fields", kwargs))
        return self._response("application/json", b'{"fields":[]}')

    def profile(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("profile", kwargs))
        return self._response("application/json", b'{"profile":"ok"}')

    def article(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("article", kwargs))
        return self._response("application/json", b'{"id":"123"}')

    def citations(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("citations", kwargs))
        return self._response("application/json", b'{"citationList":[]}')

    def references(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("references", kwargs))
        return self._response("application/json", b'{"referenceList":[]}')

    def evaluations(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("evaluations", kwargs))
        return self._response("application/json", b'{"evaluationList":[]}')

    def database_links(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("database_links", kwargs))
        return self._response("application/json", b'{"request":{}}')

    def labs_links(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("labs_links", kwargs))
        return self._response("application/json", b'{"providers":[]}')

    def data_links(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("data_links", kwargs))
        return self._response("application/json", b'{"dataLinkList":[]}')

    def fulltext_xml(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("fulltext_xml", kwargs))
        return self._response("application/xml", b"<article/>")

    def book_xml(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("book_xml", kwargs))
        return self._response("application/xml", b"<book/>")

    def supplementary_files(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("supplementary_files", kwargs))
        return self._response("application/zip", b"PK\x03\x04")

    def status_update_search(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("status_update_search", kwargs))
        return self._response("application/json", b'{"articlesWithStatusUpdate":[]}')


class FakeGrantsApi:
    def __init__(self, config: dict, release: str = "production", base_url: str | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []

    def search(self, **kwargs: dict) -> HttpResponse:
        self.calls.append(("search", kwargs))
        return HttpResponse(
            url="https://example.test",
            status=200,
            headers={"Content-Type": "application/json"},
            body=b'{"mode":"grants-search"}',
        )


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "api": {
                "base_url": "https://www.ebi.ac.uk/europepmc/webservices/rest",
                "default_result_type": "lite",
                "email": "",
            },
            "search": {"default_page_size": 1000, "default_preprints_only": False, "synonym_expansion": True},
            "output": {"default_format": "jsonl"},
        }

    def _run_main(self, argv: list[str]) -> tuple[int, str, str, list[FakeArticlesApi], list[FakeGrantsApi]]:
        stdout = StdoutCapture()
        stderr = StringIO()
        articles_holder: list[FakeArticlesApi] = []
        grants_holder: list[FakeGrantsApi] = []

        def build_articles(*, config: dict, release: str = "production", base_url: str | None = None) -> FakeArticlesApi:
            service = FakeArticlesApi(config, release=release, base_url=base_url)
            articles_holder.append(service)
            return service

        def build_grants(*, config: dict, release: str = "production", base_url: str | None = None) -> FakeGrantsApi:
            service = FakeGrantsApi(config, release=release, base_url=base_url)
            grants_holder.append(service)
            return service

        with (
            patch("pmc_tool.cli.load_config", return_value=self.config),
            patch("pmc_tool.cli.EuropePmcArticlesApi", side_effect=build_articles),
            patch("pmc_tool.cli.EuropePmcGrantsApi", side_effect=build_grants),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue(), articles_holder, grants_holder

    def test_articles_search_is_namespaced(self) -> None:
        code, output, _, articles, grants = self._run_main(["articles", "search", "p53"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["mode"], "articles-search")
        self.assertEqual(articles[0].calls[0][0], "search")
        self.assertEqual(articles[0].calls[0][1]["query"], "p53")
        self.assertEqual(grants, [])

    def test_articles_fetch_is_namespaced(self) -> None:
        code, output, _, articles, _ = self._run_main(["articles", "fetch", "MED", "123", "--format", "dc"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["id"], "123")
        self.assertEqual(articles[0].calls[0][1]["source"], "MED")
        self.assertEqual(articles[0].calls[0][1]["format_name"], "dc")

    def test_articles_surface_without_endpoint_shows_help(self) -> None:
        code, output, _, articles, grants = self._run_main(["articles"])
        self.assertEqual(code, 0)
        self.assertIn("Europe PMC Articles RESTful API", output)
        self.assertEqual(articles, [])
        self.assertEqual(grants, [])

    def test_articles_missing_identifier_shows_contextual_help(self) -> None:
        code, output, _, articles, _ = self._run_main(["articles", "fetch", "MED"])
        self.assertEqual(code, 0)
        self.assertIn("GET /article/{source}/{id}", output)
        self.assertEqual(articles, [])

    def test_grants_search_routes_to_grants_api(self) -> None:
        code, output, _, articles, grants = self._run_main(["grants", "search", "pi:smith", "--format", "cerif"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["mode"], "grants-search")
        self.assertEqual(articles, [])
        self.assertEqual(grants[0].calls[0][0], "search")
        self.assertEqual(grants[0].calls[0][1]["query"], "pi:smith")
        self.assertEqual(grants[0].calls[0][1]["format_name"], "cerif")

    def test_grants_surface_without_endpoint_shows_help(self) -> None:
        code, output, _, articles, grants = self._run_main(["grants"])
        self.assertEqual(code, 0)
        self.assertIn("Europe PMC Grants RESTful API", output)
        self.assertEqual(articles, [])
        self.assertEqual(grants, [])

    def test_doc_is_hierarchical(self) -> None:
        code, output, _, articles, grants = self._run_main(["doc", "grants", "search"])
        self.assertEqual(code, 0)
        self.assertIn("Grants RESTful API", output)
        self.assertIn("GRIST Query Fields", output)
        self.assertEqual(articles, [])
        self.assertEqual(grants, [])

    def test_doc_root_lists_surfaces(self) -> None:
        code, output, _, _, _ = self._run_main(["doc"])
        self.assertEqual(code, 0)
        self.assertIn("articles", output)
        self.assertIn("grants", output)

    def test_fulltext_xml_still_returns_raw_xml(self) -> None:
        code, output, _, articles, _ = self._run_main(["articles", "fulltext-xml", "PMC123"])
        self.assertEqual(code, 0)
        self.assertEqual(output, "<article/>")
        self.assertEqual(articles[0].calls[0][0], "fulltext_xml")

    def test_status_update_search_accepts_articles(self) -> None:
        code, output, _, articles, _ = self._run_main(
            ["articles", "status-update-search", "--article", "MED", "1"]
        )
        self.assertEqual(code, 0)
        self.assertIn("articlesWithStatusUpdate", output)
        self.assertEqual(
            articles[0].calls[0][1]["body"],
            {"ids": [{"src": "MED", "extId": "1"}]},
        )


if __name__ == "__main__":
    unittest.main()
