from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmc_tool.articles_api import (  # noqa: E402
    EuropePmcApiError,
    EuropePmcArticlesApi,
)
from pmc_tool.http import HttpResponse  # noqa: E402


ERROR_BEAN = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><errorBean><errCode>0</errCode>'
    b"<errMsg>Article with id PMC8860882 is not open access one</errMsg></errorBean>"
)

FULLTEXT_ERROR_BEAN = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><fullTextXMLBean><fullTextXML>'
    b"<pmId>NBK000000</pmId><message>Article is not either Open Access article or a valid "
    b"NBK/PM ID</message><isOpenAccess>N</isOpenAccess></fullTextXML></fullTextXMLBean>"
)


class RecordingClient:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    def request(self, **kwargs) -> HttpResponse:
        self.requests.append(kwargs)
        return self.responses.pop(0)


def _response(content_type: str, body: bytes) -> HttpResponse:
    return HttpResponse(
        url="https://example.test/endpoint",
        status=200,
        headers={"Content-Type": content_type},
        body=body,
    )


def _service(responses: list[HttpResponse]) -> tuple[EuropePmcArticlesApi, RecordingClient]:
    client = RecordingClient(responses)
    config = {"api": {"base_url": "https://example.test", "default_result_type": "lite"}}
    return EuropePmcArticlesApi(config=config, client=client), client


def _search_payload(results: list[dict]) -> bytes:
    return json.dumps({"resultList": {"result": results}}).encode("utf-8")


class ErrorPayloadTests(unittest.TestCase):
    def test_error_bean_on_http_200_raises(self) -> None:
        service, _ = _service([_response("application/xml", ERROR_BEAN)])
        with self.assertRaises(EuropePmcApiError) as caught:
            service.supplementary_files(article_id="PMC8860882")
        self.assertIn("is not open access one", str(caught.exception))

    def test_fulltext_error_bean_on_http_200_raises(self) -> None:
        service, _ = _service([_response("application/xml", FULLTEXT_ERROR_BEAN)])
        with self.assertRaises(EuropePmcApiError) as caught:
            service.book_xml(article_id="NBK000000")
        self.assertIn("valid NBK/PM ID", str(caught.exception))

    def test_successful_zip_is_returned_untouched(self) -> None:
        body = b"PK\x03\x04payload"
        service, _ = _service([_response("application/zip", body)])
        self.assertEqual(service.supplementary_files(article_id="PMC1").body, body)

    def test_article_xml_is_not_mistaken_for_an_error(self) -> None:
        body = b'<?xml version="1.0"?><article><front/></article>'
        service, _ = _service([_response("application/xml", body)])
        self.assertEqual(service.fulltext_xml(article_id="PMC1").body, body)


class ResolveDoiTests(unittest.TestCase):
    def test_resolves_single_match(self) -> None:
        payload = _search_payload([{"source": "PMC", "id": "PMC6378602", "pmcid": "PMC6378602"}])
        service, client = _service([_response("application/json", payload)])
        record = service.resolve_doi("10.1111/brv.12453")
        self.assertEqual(record["pmcid"], "PMC6378602")
        self.assertEqual(client.requests[0]["params"]["query"], 'DOI:"10.1111/brv.12453"')

    def test_strips_doi_url_and_scheme_prefixes(self) -> None:
        payload = _search_payload([{"source": "PMC", "id": "PMC1", "pmcid": "PMC1"}])
        service, client = _service([_response("application/json", payload)])
        service.resolve_doi("https://doi.org/10.1/abc")
        self.assertEqual(client.requests[0]["params"]["query"], 'DOI:"10.1/abc"')

    def test_unknown_doi_raises(self) -> None:
        service, _ = _service([_response("application/json", _search_payload([]))])
        with self.assertRaises(EuropePmcApiError) as caught:
            service.resolve_doi("10.9999/nope")
        self.assertIn("No Europe PMC record found", str(caught.exception))

    def test_ambiguous_doi_raises(self) -> None:
        payload = _search_payload([{"source": "MED", "id": "1"}, {"source": "PPR", "id": "2"}])
        service, _ = _service([_response("application/json", payload)])
        with self.assertRaises(EuropePmcApiError) as caught:
            service.resolve_doi("10.1/dup")
        self.assertIn("matches 2 Europe PMC records", str(caught.exception))

    def test_record_without_pmcid_raises_for_pmc_only_endpoints(self) -> None:
        payload = _search_payload([{"source": "MED", "id": "41995635", "pmid": "41995635"}])
        service, _ = _service([_response("application/json", payload)])
        with self.assertRaises(EuropePmcApiError) as caught:
            service.resolve_doi_to_pmcid("10.1/med-only")
        self.assertIn("has no PMCID", str(caught.exception))

    def test_book_id_falls_back_to_record_id(self) -> None:
        payload = _search_payload([{"source": "NBK", "id": "NBK1116"}])
        service, _ = _service([_response("application/json", payload)])
        self.assertEqual(service.resolve_doi_to_book_id("10.1/book"), "NBK1116")


if __name__ == "__main__":
    unittest.main()
