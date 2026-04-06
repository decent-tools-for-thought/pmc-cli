from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .config import load_config
from .http import HttpClient, HttpResponse


PRODUCTION_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
TEST_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/test/rest"
API_VERSION = "6.9"
DEFAULT_RESULT_TYPE = "lite"
DEFAULT_JSON_FORMAT = "json"
BOOLEAN_TEXT_CHOICES = ["TRUE", "Y", "YES", "FALSE", "N", "NO"]
INLINE_IMAGE_CHOICES = ["y", "yes", "true", "n", "no", "false"]
QUERY_RESULT_TYPES = ["idlist", "lite", "core"]
QUERY_FORMATS = ["xml", "json", "dc"]
JSON_XML_FORMATS = ["xml", "json"]
SOURCE_CHOICES = ["AGR", "CBA", "CIT", "CTX", "ETH", "HIR", "MED", "NBK", "PAT", "PMC", "PPR"]
RELATION_SOURCE_CHOICES = ["AGR", "CBA", "CTX", "ETH", "HIR", "MED", "PAT", "PMC", "PPR"]
DATABASE_CHOICES = [
    "ARXPR",
    "CHEBI",
    "CHEMBL",
    "EMBL",
    "INTACT",
    "INTERPRO",
    "OMIM",
    "PDB",
    "PRIDE",
    "UNIPROT",
]
PROFILE_TYPES = ["pub_type", "source", "all"]
OBTAINED_BY_CHOICES = ["tm_accession", "tm_term", "ext_links", "submission"]
DATA_LINK_CATEGORY_CHOICES = [
    "Access to Understanding",
    "Altmetric",
    "Arthritis Research UK",
    "Bibliomics and Text Mining Group (BiTeM)",
    "BioModels",
    "BioSamples",
    "BioStudies",
    "Cellosaurus",
    "Centre for Reviews and Dissemination (UK)",
    "Chemicals",
    "Clinical Trials",
    "COSMIC",
    "Data Citations",
    "DEPOD",
    "Diseases",
    "DisGeNET",
    "DisProt",
    "Dryad Digital Repository",
    "EBI Metagenomics",
    "EBI Train Online",
    "Electron Microscopy Data Bank",
    "EMBL Press Releases",
    "EMPIAR",
    "ENCODE: Encyclopedia of DNA Elements",
    "EuroFIR Document Repository",
    "European Genome-Phenome Archive",
    "F1000Prime",
    "FlyBase",
    "Functional Genomics Experiments",
    "Gene Ontology (GO) Terms",
    "Genes & Proteins",
    "GenomeRNAi",
    "GOA Project",
    "HAL Open Archive",
    "IntAct",
    "iPTMnet",
    "IUPHAR/BPS Guide to Pharmacology",
    "Kudos",
    "Linkoping University Digital Archive",
    "Marie Curie Press Releases",
    "Medical Research Council",
    "MetaboLights",
    "MGnify",
    "ModelArchive",
    "Mouse Genome Informatics (MGI)",
    "National Centre for Text Mining (NaCTeM)",
    "Neuroscience Information Framework",
    "NHGRI-EBI GWAS Catalog",
    "NTNU/BSC",
    "Nucleotide Sequences",
    "Open Access at Bielefeld University",
    "Open Access at Lund University",
    "Open Targets Platform",
    "OpenAIRE",
    "PANGAEA",
    "Pfam",
    "PhenoMiner",
    "PomBase, University of Cambridge",
    "preLights",
    "Protein Families",
    "Protein Interactions",
    "Protein Structures",
    "ProteomeXchange",
    "Proteomics Data",
    "protocols.io",
    "Publons",
    "PubTator (NCBI)",
    "Reactome",
    "Related Immune Epitope Information - Immune Epitope Database and Analysis Resource",
    "Reuse Recipe Document",
    "SABIO-RK",
    "Saccharomyces Genome Database",
    "SIGNOR",
    "STORRE: University of Stirling repository",
    "STRENDA DB",
    "Versus Arthritis",
    "Wellcome Trust",
    "WikiPathways",
    "Wikipedia",
    "Worldwide Cancer Research",
    "WormBase",
    "Ximbio",
    "ZFIN",
]


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _read_body_argument(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


@dataclass(frozen=True)
class EndpointDoc:
    command: str
    method: str
    path: str
    summary: str
    formats: str
    params: list[str]
    notes: list[str]


ENDPOINT_DOCS = [
    EndpointDoc(
        "search",
        "GET",
        "/search",
        "Search articles and preprints.",
        "xml, json, dc",
        ["query", "resultType", "synonym", "cursorMark", "pageSize", "sort", "format", "callback", "email"],
        ["API default format is xml; this CLI defaults to json.", "DC output ignores resultType and always behaves as core."],
    ),
    EndpointDoc(
        "search-post",
        "POST",
        "/searchPOST",
        "POST form-encoded search with the same parameters as /search.",
        "xml, json, dc",
        ["query", "resultType", "synonym", "cursorMark", "pageSize", "sort", "format", "callback", "email"],
        ["Request body must be application/x-www-form-urlencoded.", "Useful for long queries."],
    ),
    EndpointDoc(
        "fields",
        "GET",
        "/fields",
        "List indexed search fields.",
        "xml, json",
        ["format", "callback"],
        ["Production and test releases both expose this endpoint."],
    ),
    EndpointDoc(
        "profile",
        "GET",
        "/profile",
        "Return hit-count profiles by publication type or source.",
        "xml, json",
        ["query", "profiletype", "synonym", "format", "callback", "email"],
        [],
    ),
    EndpointDoc(
        "article",
        "GET",
        "/article/{source}/{id}",
        "Fetch a specific record by source and identifier.",
        "xml, json, dc",
        ["source", "id", "resultType", "format", "callback", "email"],
        ["API doc says this endpoint also accepts debug, but the current Swagger schema does not publish that parameter."],
    ),
    EndpointDoc(
        "citations",
        "GET",
        "/{source}/{id}/citations",
        "Fetch publications citing a given record.",
        "xml, json",
        ["source", "id", "page", "pageSize", "format", "callback"],
        [],
    ),
    EndpointDoc(
        "references",
        "GET",
        "/{source}/{id}/references",
        "Fetch publications referenced by a given record.",
        "xml, json",
        ["source", "id", "page", "pageSize", "format", "callback"],
        [],
    ),
    EndpointDoc(
        "evaluations",
        "GET",
        "/evaluations/{source}/{id}",
        "Fetch evaluations for a record.",
        "xml, json",
        ["source", "id", "format"],
        [],
    ),
    EndpointDoc(
        "database-links",
        "GET",
        "/{source}/{id}/databaseLinks",
        "Fetch biological database cross-references for a record.",
        "xml, json",
        ["source", "id", "database", "page", "pageSize", "format", "callback"],
        [],
    ),
    EndpointDoc(
        "labs-links",
        "GET",
        "/{source}/{id}/labsLinks",
        "Fetch third-party External Links for a record.",
        "xml, json",
        ["source", "id", "providerIds", "page", "pageSize", "format", "callback"],
        ["Repeat --provider-id to send multiple providerIds values."],
    ),
    EndpointDoc(
        "data-links",
        "GET",
        "/{source}/{id}/datalinks",
        "Fetch consolidated Scholix-format data-literature links.",
        "xml, json",
        ["source", "id", "category", "obtainedBy", "fromDate", "tags", "sectionLimit", "email", "ref", "format"],
        ["The API documents fromDate as DD-MM-YYYY.", "Use comma-separated values for tags when sending multiple tags."],
    ),
    EndpointDoc(
        "fulltext-xml",
        "GET",
        "/{id}/fullTextXML",
        "Fetch Open Access article full text as XML.",
        "xml",
        ["id"],
        ["No format parameter; XML is the endpoint payload."],
    ),
    EndpointDoc(
        "book-xml",
        "GET",
        "/{id}/bookXML",
        "Fetch Open Access bookshelf/book XML.",
        "xml",
        ["id"],
        ["Accepts either a PMID or NBK identifier."],
    ),
    EndpointDoc(
        "supplementary-files",
        "GET",
        "/{id}/supplementaryFiles",
        "Download supplementary files as a zip archive.",
        "zip",
        ["id", "includeInlineImage"],
        ["No json/xml switch; this endpoint downloads a zip when files exist."],
    ),
    EndpointDoc(
        "status-update-search",
        "POST",
        "/status-update-search",
        "Fetch article status updates for one or more source/id pairs.",
        "json, xml",
        ["format", "body(ids:[{src, extId}])"],
        ["Request body must be application/json."],
    ),
]


class EuropePmcArticlesApi:
    def __init__(
        self,
        *,
        config: dict | None = None,
        client: HttpClient | None = None,
        release: str = "production",
        base_url: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.release = release
        self.base_url = base_url or (
            TEST_BASE_URL if release == "test" else self.config["api"].get("base_url", PRODUCTION_BASE_URL)
        )
        self.client = client or HttpClient(user_agent="pmc-cli/0.1.0")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> HttpResponse:
        return self.client.request(
            method=method,
            url=f"{self.base_url}{path}",
            params=params,
            form=form,
            json_body=json_body,
        )

    def _email_or_default(self, email: str | None) -> str | None:
        explicit = _trim(email)
        if explicit is not None:
            return explicit
        configured = _trim(self.config["api"].get("email"))
        return configured

    def search(
        self,
        *,
        query: str,
        result_type: str | None = None,
        synonym: str | None = None,
        cursor_mark: str | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        format_name: str | None = None,
        callback: str | None = None,
        email: str | None = None,
    ) -> HttpResponse:
        params = {
            "query": query,
            "resultType": result_type or self.config["api"].get("default_result_type", DEFAULT_RESULT_TYPE),
            "synonym": synonym,
            "cursorMark": cursor_mark,
            "pageSize": page_size,
            "sort": sort,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
            "email": self._email_or_default(email),
        }
        return self._request("GET", "/search", params=params)

    def search_post(
        self,
        *,
        query: str,
        result_type: str | None = None,
        synonym: str | None = None,
        cursor_mark: str | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        format_name: str | None = None,
        callback: str | None = None,
        email: str | None = None,
    ) -> HttpResponse:
        form = {
            "query": query,
            "resultType": result_type or self.config["api"].get("default_result_type", DEFAULT_RESULT_TYPE),
            "synonym": synonym,
            "cursorMark": cursor_mark,
            "pageSize": page_size,
            "sort": sort,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
            "email": self._email_or_default(email),
        }
        return self._request("POST", "/searchPOST", form=form)

    def fields(self, *, format_name: str | None = None, callback: str | None = None) -> HttpResponse:
        return self._request(
            "GET",
            "/fields",
            params={"format": format_name or DEFAULT_JSON_FORMAT, "callback": callback},
        )

    def profile(
        self,
        *,
        query: str,
        profile_type: str | None = None,
        synonym: str | None = None,
        format_name: str | None = None,
        callback: str | None = None,
        email: str | None = None,
    ) -> HttpResponse:
        params = {
            "query": query,
            "profiletype": profile_type,
            "synonym": synonym,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
            "email": self._email_or_default(email),
        }
        return self._request("GET", "/profile", params=params)

    def article(
        self,
        *,
        source: str,
        article_id: str,
        result_type: str | None = None,
        format_name: str | None = None,
        callback: str | None = None,
        email: str | None = None,
    ) -> HttpResponse:
        params = {
            "resultType": result_type or self.config["api"].get("default_result_type", DEFAULT_RESULT_TYPE),
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
            "email": self._email_or_default(email),
        }
        return self._request(
            "GET",
            f"/article/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}",
            params=params,
        )

    def citations(
        self,
        *,
        source: str,
        article_id: str,
        page: int | None = None,
        page_size: int | None = None,
        format_name: str | None = None,
        callback: str | None = None,
    ) -> HttpResponse:
        params = {
            "page": page,
            "pageSize": page_size,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
        }
        return self._request(
            "GET",
            f"/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}/citations",
            params=params,
        )

    def references(
        self,
        *,
        source: str,
        article_id: str,
        page: int | None = None,
        page_size: int | None = None,
        format_name: str | None = None,
        callback: str | None = None,
    ) -> HttpResponse:
        params = {
            "page": page,
            "pageSize": page_size,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
        }
        return self._request(
            "GET",
            f"/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}/references",
            params=params,
        )

    def evaluations(self, *, source: str, article_id: str, format_name: str | None = None) -> HttpResponse:
        return self._request(
            "GET",
            f"/evaluations/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}",
            params={"format": format_name or DEFAULT_JSON_FORMAT},
        )

    def database_links(
        self,
        *,
        source: str,
        article_id: str,
        database: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        format_name: str | None = None,
        callback: str | None = None,
    ) -> HttpResponse:
        params = {
            "database": database,
            "page": page,
            "pageSize": page_size,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
        }
        return self._request(
            "GET",
            f"/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}/databaseLinks",
            params=params,
        )

    def labs_links(
        self,
        *,
        source: str,
        article_id: str,
        provider_ids: list[int] | None = None,
        page: int | None = None,
        page_size: int | None = None,
        format_name: str | None = None,
        callback: str | None = None,
    ) -> HttpResponse:
        params = {
            "providerIds": provider_ids,
            "page": page,
            "pageSize": page_size,
            "format": format_name or DEFAULT_JSON_FORMAT,
            "callback": callback,
        }
        return self._request(
            "GET",
            f"/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}/labsLinks",
            params=params,
        )

    def data_links(
        self,
        *,
        source: str,
        article_id: str,
        category: str | None = None,
        obtained_by: str | None = None,
        from_date: str | None = None,
        tags: str | None = None,
        section_limit: str | None = None,
        email: str | None = None,
        ref: str | None = None,
        format_name: str | None = None,
    ) -> HttpResponse:
        params = {
            "category": category,
            "obtainedBy": obtained_by,
            "fromDate": from_date,
            "tags": tags,
            "sectionLimit": section_limit,
            "email": self._email_or_default(email),
            "ref": ref,
            "format": format_name or DEFAULT_JSON_FORMAT,
        }
        return self._request(
            "GET",
            f"/{quote(source.upper(), safe='')}/{quote(article_id, safe='')}/datalinks",
            params=params,
        )

    def fulltext_xml(self, *, article_id: str) -> HttpResponse:
        return self._request("GET", f"/{quote(article_id, safe='')}/fullTextXML")

    def book_xml(self, *, article_id: str) -> HttpResponse:
        return self._request("GET", f"/{quote(article_id, safe='')}/bookXML")

    def supplementary_files(
        self,
        *,
        article_id: str,
        include_inline_image: str | None = None,
    ) -> HttpResponse:
        return self._request(
            "GET",
            f"/{quote(article_id, safe='')}/supplementaryFiles",
            params={"includeInlineImage": include_inline_image},
        )

    def status_update_search(
        self,
        *,
        ids: list[dict[str, str]] | None = None,
        body: Any | None = None,
        format_name: str | None = None,
    ) -> HttpResponse:
        payload = body if body is not None else {"ids": ids or []}
        return self._request(
            "POST",
            "/status-update-search",
            params={"format": format_name or DEFAULT_JSON_FORMAT},
            json_body=payload,
        )


def render_doc(topic: str | None = None) -> str:
    lines = [
        "Europe PMC Articles RESTful API",
        "",
        f"CLI doc set targets API version {API_VERSION}.",
        "",
        "Web Service Releases",
        f"- Production base URL: {PRODUCTION_BASE_URL}",
        f"- Test base URL: {TEST_BASE_URL}",
        "- Europe PMC publishes production and test releases side by side.",
        "",
        "Result Types",
        "- idlist: IDs and sources only",
        "- lite: key metadata, default result type",
        "- core: full metadata including abstract, full text links, and MeSH terms",
        "",
        "Format Rules",
        "- The HTTP API defaults to XML when format is omitted.",
        "- This CLI defaults to JSON for endpoints that publish JSON.",
        "- search, search-post, and article also support dc (Dublin Core).",
        "- DC output effectively behaves as core regardless of resultType.",
        "",
    ]
    if topic is None:
        lines.append("Endpoints")
        for endpoint in ENDPOINT_DOCS:
            lines.append(f"- {endpoint.command}: {endpoint.method} {endpoint.path} [{endpoint.formats}]")
            lines.append(f"  {endpoint.summary}")
        lines.append("")
        lines.append("Use `pmc doc <command>` for full parameter detail.")
        return "\n".join(lines) + "\n"

    matched = next((doc for doc in ENDPOINT_DOCS if doc.command == topic), None)
    if matched is None:
        lines.append("Known endpoint topics:")
        for endpoint in ENDPOINT_DOCS:
            lines.append(f"- {endpoint.command}")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"Endpoint: {matched.command}",
            f"Method: {matched.method}",
            f"Path: {matched.path}",
            f"Formats: {matched.formats}",
            f"Summary: {matched.summary}",
            "",
            "Parameters",
        ]
    )
    for parameter in matched.params:
        lines.append(f"- {parameter}")
    if matched.notes:
        lines.append("")
        lines.append("Notes")
        for note in matched.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def parse_status_update_body(body: str | None, articles: list[list[str]] | None) -> Any:
    if body:
        return _read_body_argument(body)
    return {"ids": [{"src": src, "extId": ext_id} for src, ext_id in (articles or [])]}
