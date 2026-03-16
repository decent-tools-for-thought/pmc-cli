from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmc_tool.core import (  # noqa: E402
    EuropePmcService,
    build_query,
    build_grants_query,
    normalize_field_list,
    normalize_grant_record,
    normalize_record,
    render_output,
)


class DummyClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, url, params=None):
        self.calls.append((url, params))
        key = (url, tuple(sorted((params or {}).items())))
        if key not in self.responses:
            raise AssertionError(f"Unexpected request: {key}")
        return self.responses[key]


class PmcCoreTests(unittest.TestCase):
    def test_build_query_from_flags(self) -> None:
        query = build_query(
            None,
            None,
            "human cell",
            None,
            "Smith",
            "review",
            "2024-01-01",
            "2024-12-31",
            True,
            True,
            True,
            "MED",
            "sort_date:y",
        )
        self.assertEqual(
            query,
            'TITLE:"human cell" AND AUTH:"Smith" AND PUB_TYPE:"review" AND FIRST_PDATE:[2024-01-01 TO *] AND FIRST_PDATE:[* TO 2024-12-31] AND SRC:MED AND SRC:PPR AND HAS_FT:y AND OPEN_ACCESS:y AND sort_date:y',
        )

    def test_raw_query_conflicts_with_structured_flags(self) -> None:
        with self.assertRaises(ValueError):
            build_query("term", "TITLE:test", None, None, None, None, None, None, False, None, False, None, None)

    def test_build_grants_query_from_helpers(self) -> None:
        query = build_grants_query(
            None,
            None,
            "Smith",
            "Wellcome Trust",
            "081052",
            "cluster randomised",
            None,
            "University College London",
            "2010-01-01",
            "COVID-19",
            "ORCID/0000-0001-9691-9684",
            True,
        )
        self.assertEqual(
            query,
            'pi:Smith ga:"Wellcome Trust" gid:081052 title:"cluster randomised" aff:"University College London" date:2010-01-01 cat:COVID-19 pi_id:ORCID/0000-0001-9691-9684 epmc_funders:yes',
        )

    def test_grants_raw_query_conflicts_with_helpers(self) -> None:
        with self.assertRaises(ValueError):
            build_grants_query(None, "pi:smith", "Smith", None, None, None, None, None, None, None, None, None)

    def test_normalize_record_maps_ids_and_affiliations(self) -> None:
        record = {
            "source": "PPR",
            "id": "PPR123",
            "doi": "10.1/example",
            "title": "Example",
            "authorList": {
                "author": [
                    {
                        "fullName": "Doe J",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "initials": "J",
                        "authorId": {"type": "ORCID", "value": "0000-0001"},
                        "authorAffiliationDetailsList": {"authorAffiliation": [{"affiliation": "Inst A"}]},
                    }
                ]
            },
            "firstPublicationDate": "2024-01-02",
            "isOpenAccess": "Y",
            "hasPDF": "N",
            "inPMC": "N",
            "keywordList": {"keyword": ["single-cell"]},
            "meshHeadingList": {"meshHeading": [{"descriptorName": "Neoplasms"}]},
        }
        normalized = normalize_record(record, "lite", query_text="SRC:PPR", include_author_affiliations=True)
        self.assertEqual(normalized["id"]["pprId"], "PPR123")
        self.assertTrue(normalized["isOpenAccess"])
        self.assertFalse(normalized["hasFullText"])
        self.assertEqual(normalized["provenance"]["srcFilter"], "PPR")
        self.assertEqual(normalized["authors"][0]["affiliation"], "Inst A")
        self.assertEqual(normalized["authors"][0]["orcid"], "0000-0001")
        self.assertEqual(normalized["meshHeadingList"], ["Neoplasms"])

    def test_normalize_fields(self) -> None:
        payload = {"searchTermList": {"searchTerms": [{"term": "TITLE"}, {"term": "AUTH"}]}}
        normalized = normalize_field_list(payload)
        self.assertEqual(normalized["fields"], ["TITLE", "AUTH"])
        self.assertEqual(normalized["count"], 2)

    def test_normalize_grant_record(self) -> None:
        record = {
            "Person": {
                "FamilyName": "Osrin",
                "GivenName": "David",
                "Initials": "D",
                "Alias": [{"Source": "ORCID", "value": "0000-0001"}],
            },
            "Grant": {
                "Id": "081052",
                "Doi": "10.35802/081052",
                "Title": "Cluster randomised trial",
                "Type": "Research",
                "Stream": "Population",
                "StartDate": "2007-02-01",
                "EndDate": "2011-01-31",
                "Amount": {"value": 648257.0, "Currency": "GBP"},
                "Funder": {"Name": "Wellcome Trust", "FundRefID": "https://doi.org/10.13039/100010269"},
            },
            "Institution": {"Name": "University College London", "RORID": "ror.org/02jx3x895"},
        }
        normalized = normalize_grant_record(record, "core")
        self.assertEqual(normalized["id"]["grantId"], "081052")
        self.assertEqual(normalized["principalInvestigator"]["aliases"]["ORCID"], ["0000-0001"])
        self.assertEqual(normalized["amount"]["currency"], "GBP")
        self.assertEqual(normalized["institution"]["rorId"], "ror.org/02jx3x895")

    def test_search_uses_fields_and_limit(self) -> None:
        base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        params = {
            "query": '"cancer"',
            "format": "json",
            "resultType": "lite",
            "pageSize": 2,
            "cursorMark": "*",
            "synonym": "false",
            "fields": "doi,pmid",
        }
        client = DummyClient(
            {
                (
                    f"{base}/search",
                    tuple(sorted(params.items())),
                ): {
                    "version": "6.9",
                    "hitCount": 3,
                    "nextCursorMark": "abc",
                    "request": {"queryString": '"cancer"'},
                    "resultList": {
                        "result": [
                            {"source": "MED", "pmid": "1", "title": "A", "authorString": "Doe J.", "firstPublicationDate": "2024-01-01"},
                            {"source": "MED", "pmid": "2", "title": "B", "authorString": "Doe J.", "firstPublicationDate": "2024-01-02"},
                        ]
                    },
                }
            }
        )
        service = EuropePmcService(client=client)
        result = service.search(
            query="cancer",
            raw_query=None,
            title=None,
            abstract=None,
            author=None,
            category=None,
            from_date=None,
            to_date=None,
            preprints_only=False,
            has_fulltext=None,
            open_access_only=False,
            source=None,
            sort=None,
            page_size=2,
            cursor_mark=None,
            limit=1,
            result_type="lite",
            synonyms=False,
            fields="doi,pmid",
            include_author_affiliations=False,
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["meta"]["fieldsRequested"], ["doi", "pmid"])

    def test_related_records_uses_article_relations_endpoint(self) -> None:
        base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        client = DummyClient(
            {
                (
                    f"{base}/MED/35092342/references/1/25/json",
                    (),
                ): {
                    "hitCount": 1,
                    "referenceList": {
                        "reference": [
                            {"id": "123", "source": "MED", "title": "Referenced", "authorString": "Doe J.", "pubYear": 2024}
                        ]
                    },
                }
            }
        )
        service = EuropePmcService(client=client)
        result = service.related_records(source="MED", identifier="35092342", relation="references", page=1, page_size=25)
        self.assertEqual(result["items"][0]["title"], "Referenced")
        self.assertEqual(result["meta"]["identifier"], "35092342")

    def test_render_export_formats(self) -> None:
        items = [
            {
                "id": {"doi": "10.1/example", "pmid": None, "pmcid": None},
                "title": "Example",
                "authors": [{"fullName": "Doe J", "firstName": "Jane", "lastName": "Doe"}],
                "publishedDate": "2024-01-02",
                "url": "https://doi.org/10.1/example",
                "journal": {"title": "Journal"},
            }
        ]
        self.assertIn("@article", render_output(items, "bib"))
        self.assertIn("TY  - JOUR", render_output(items, "ris"))
        self.assertIn('"DOI": "10.1/example"', render_output(items, "csl-json"))

    def test_grants_search_uses_grist_endpoint(self) -> None:
        base = "https://www.ebi.ac.uk/europepmc/GristAPI/rest/get/query=gid:081052&format=json&resultType=core&page=1"
        client = DummyClient(
            {
                (
                    base,
                    (),
                ): {
                    "HitCount": "1",
                    "Request": {"Query": "gid:081052", "ResultType": "Core", "Page": "1"},
                    "RecordList": {
                        "Record": {
                            "Person": {"FamilyName": "Osrin"},
                            "Grant": {"Id": "081052", "Title": "Cluster randomised trial", "Funder": {"Name": "Wellcome Trust"}},
                        }
                    },
                }
            }
        )
        service = EuropePmcService(client=client)
        result = service.grants_fetch(grant_id="081052", result_type="core")
        self.assertEqual(result["id"]["grantId"], "081052")
        self.assertEqual(result["funder"]["name"], "Wellcome Trust")

    def test_grants_search_builds_helper_query_for_endpoint(self) -> None:
        base = "https://www.ebi.ac.uk/europepmc/GristAPI/rest/get/query=pi:Smith%20ga:%22Wellcome%20Trust%22%20date:2010&format=json&resultType=lite&page=1"
        client = DummyClient(
            {
                (
                    base,
                    (),
                ): {
                    "HitCount": "1",
                    "Request": {"Query": 'pi:Smith ga:"Wellcome Trust" date:2010', "ResultType": "Lite", "Page": "1"},
                    "RecordList": {
                        "Record": {
                            "Person": {"FamilyName": "Smith"},
                            "Grant": {"Id": "1", "Title": "Grant", "Funder": {"Name": "Wellcome Trust"}},
                        }
                    },
                }
            }
        )
        service = EuropePmcService(client=client)
        result = service.grants_search(
            query=None,
            raw_query=None,
            pi="Smith",
            agency="Wellcome Trust",
            grant_id=None,
            title=None,
            abstract=None,
            affiliation=None,
            active_date="2010",
            category=None,
            pi_id=None,
            epmc_funders=None,
            result_type="lite",
            page=1,
            limit=1,
        )
        self.assertEqual(result["items"][0]["funder"]["name"], "Wellcome Trust")


if __name__ == "__main__":
    unittest.main()
