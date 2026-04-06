from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from .config import load_config
from .http import HttpClient, HttpResponse


PRODUCTION_BASE_URL = "https://www.ebi.ac.uk/europepmc/GristAPI/rest"
TEST_BASE_URL = "https://www.ebi.ac.uk/europepmc/GristAPI/test/rest"
API_VERSION = "current docs page"
DEFAULT_RESULT_TYPE = "lite"
DEFAULT_FORMAT = "json"
RESULT_TYPES = ["lite", "core"]
FORMATS = ["xml", "json", "cerif"]


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
        "/get/query={query}",
        "Search the GRIST grants database.",
        "xml, json, cerif",
        ["query", "resultType", "page", "format"],
        [
            "API default format is xml; this CLI defaults to json.",
            "API default resultType is lite.",
            "Pages are 1-based and default to 25 results per page.",
            "CERIF pagination metadata is carried in HTTP headers.",
        ],
    )
]

QUERY_FIELD_DOCS = [
    ("ga, grant_agency", "Search funder names, abbreviations, and FundRef IDs.", 'ga:"Wellcome Trust"'),
    ("gid, gr, grant_id", "Search grant IDs.", "gid:083611"),
    ("title, ti", "Search grant titles.", 'ti:"kidney cancer"'),
    ("abstract, abs", "Search grant abstracts.", 'abstract:"diverse functions"'),
    ("date, active_date", "Search grants active on a given date. Format yyyy-mm-dd with optional month/day.", "active_date:2010"),
    ("kw", "Keyword search across titles, abstracts, streams, and grant types.", 'kw:"Physiological Sciences"'),
    ("pi", "Search PI last name with optional initials.", 'pi:"Hubbard S"'),
    ("pi_id, author_id", "Search PI alternate identifiers such as ORCID. Format {type}/{value}.", "pi_id:ORCID/0000-0001-2345-6789"),
    ("aff", "Search institution names and departments.", 'aff:"University of Manchester"'),
    ("cat", "Search grant category groupings.", 'cat:"COVID-19"'),
    ("epmc_funders", "Restrict to Europe PMC funders. Accepted values yes|no, y|n, true|false.", "epmc_funders:yes"),
]


class EuropePmcGrantsApi:
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
        self.base_url = base_url or (TEST_BASE_URL if release == "test" else PRODUCTION_BASE_URL)
        self.client = client or HttpClient(user_agent="pmc-cli/0.1.0")

    def search(
        self,
        *,
        query: str,
        result_type: str | None = None,
        page: int | None = None,
        format_name: str | None = None,
    ) -> HttpResponse:
        segments = [f"query={quote(query, safe=':/\\\"')}"]
        if result_type or DEFAULT_RESULT_TYPE:
            segments.append(f"resultType={quote(result_type or DEFAULT_RESULT_TYPE, safe='')}")
        if page is not None:
            segments.append(f"page={page}")
        if format_name or DEFAULT_FORMAT:
            segments.append(f"format={quote(format_name or DEFAULT_FORMAT, safe='')}")
        return self.client.request(
            method="GET",
            url=f"{self.base_url}/get/" + "&".join(segments),
        )


def render_doc(topic: str | None = None) -> str:
    lines = [
        "Grants RESTful API",
        "",
        "Web Service Releases",
        f"- Production base URL: {PRODUCTION_BASE_URL}",
        f"- Test base URL: {TEST_BASE_URL}",
        "",
        "Result Types",
        "- lite: key metadata",
        "- core: full metadata including abstracts, start/end dates, and institution details",
        "",
        "Format Rules",
        "- The HTTP API defaults to XML when format is omitted.",
        "- This CLI defaults to JSON.",
        "- CERIF responses are XML and carry pagination metadata in HTTP headers.",
        "",
    ]
    if topic is None:
        lines.append("Endpoints")
        for endpoint in ENDPOINT_DOCS:
            lines.append(f"- {endpoint.command}: {endpoint.method} {endpoint.path} [{endpoint.formats}]")
            lines.append(f"  {endpoint.summary}")
        lines.append("")
        lines.append("GRIST Query Fields")
        for syntax, description, example in QUERY_FIELD_DOCS:
            lines.append(f"- {syntax}: {description} Example: `{example}`")
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
    lines.append("")
    lines.append("Notes")
    for note in matched.notes:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("GRIST Query Fields")
    for syntax, description, example in QUERY_FIELD_DOCS:
        lines.append(f"- {syntax}: {description} Example: `{example}`")
    return "\n".join(lines) + "\n"
