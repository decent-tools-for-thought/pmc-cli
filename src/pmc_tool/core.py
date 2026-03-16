from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

from .config import load_config
from .http import HttpClient


VALID_RESULT_TYPES = {"idlist", "lite", "core"}
ARTICLE_FORMATS = {"json", "xml"}
EXPORT_FORMATS = {"jsonl", "bib", "ris", "csl-json"}
GRANTS_RESULT_TYPES = {"lite", "core"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _bool_flag(value: Any) -> bool:
    return str(value).upper() in {"Y", "TRUE", "1"}


def _quoted(text: str) -> str:
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_fields(value: str | None) -> list[str]:
    fields = _split_csv(value)
    return list(dict.fromkeys(fields))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _format_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value}. Expected YYYY-MM-DD") from exc


def build_query(
    query: str | None,
    raw_query: str | None,
    title: str | None,
    abstract: str | None,
    author: str | None,
    category: str | None,
    from_date: str | None,
    to_date: str | None,
    preprints_only: bool,
    has_fulltext: bool | None,
    open_access_only: bool,
    source: str | None,
    sort: str | None,
    extra_filters: list[str] | None = None,
) -> str:
    structured_values = [
        query,
        title,
        abstract,
        author,
        category,
        from_date,
        to_date,
        source,
        sort,
        *(extra_filters or []),
    ]
    if raw_query and (any(value for value in structured_values) or preprints_only or has_fulltext is not None or open_access_only):
        raise ValueError("--raw-query cannot be combined with structured query flags")
    if raw_query:
        return raw_query

    clauses = []
    if query:
        clauses.append(_quoted(query))
    if title:
        clauses.append(f"TITLE:{_quoted(title)}")
    if abstract:
        clauses.append(f"ABSTRACT:{_quoted(abstract)}")
    if author:
        clauses.append(f"AUTH:{_quoted(author)}")
    if category:
        clauses.append(f"PUB_TYPE:{_quoted(category)}")
    if from_date:
        clauses.append(f"FIRST_PDATE:[{_format_date(from_date)} TO *]")
    if to_date:
        clauses.append(f"FIRST_PDATE:[* TO {_format_date(to_date)}]")
    if source:
        clauses.append(f"SRC:{source.upper()}")
    if preprints_only:
        clauses.append("SRC:PPR")
    if has_fulltext is True:
        clauses.append("HAS_FT:y")
    elif has_fulltext is False:
        clauses.append("HAS_FT:n")
    if open_access_only:
        clauses.append("OPEN_ACCESS:y")
    if extra_filters:
        clauses.extend(extra_filters)
    if sort:
        clauses.append(sort)
    if not clauses:
        raise ValueError(
            "A query or one of --raw-query/--title/--abstract/--author/--category/--from-date/--to-date is required"
        )
    return " AND ".join(clauses)


def build_grants_query(
    query: str | None,
    raw_query: str | None,
    pi: str | None,
    agency: str | None,
    grant_id: str | None,
    title: str | None,
    abstract: str | None,
    affiliation: str | None,
    active_date: str | None,
    category: str | None,
    pi_id: str | None,
    epmc_funders: bool | None,
) -> str:
    structured_values = [query, pi, agency, grant_id, title, abstract, affiliation, active_date, category, pi_id]
    if raw_query and (any(value for value in structured_values) or epmc_funders is not None):
        raise ValueError("--raw-query cannot be combined with structured grants query flags")
    if raw_query:
        return raw_query

    clauses = []
    if query:
        clauses.append(query)
    if pi:
        clauses.append(f"pi:{_quoted(pi) if ' ' in pi else pi}")
    if agency:
        clauses.append(f"ga:{_quoted(agency) if ' ' in agency else agency}")
    if grant_id:
        clauses.append(f"gid:{grant_id}")
    if title:
        clauses.append(f"title:{_quoted(title) if ' ' in title else title}")
    if abstract:
        clauses.append(f"abstract:{_quoted(abstract) if ' ' in abstract else abstract}")
    if affiliation:
        clauses.append(f"aff:{_quoted(affiliation) if ' ' in affiliation else affiliation}")
    if active_date:
        clauses.append(f"date:{active_date}")
    if category:
        clauses.append(f"cat:{_quoted(category) if ' ' in category else category}")
    if pi_id:
        clauses.append(f"pi_id:{pi_id}")
    if epmc_funders is True:
        clauses.append("epmc_funders:yes")
    elif epmc_funders is False:
        clauses.append("epmc_funders:no")

    if not clauses:
        raise ValueError(
            "A grants query or one of --raw-query/--pi/--agency/--grant-id/--title/--abstract/--affiliation/--active-date is required"
        )
    return " ".join(clauses)


def _author_affiliations(author: dict[str, Any]) -> list[str]:
    details = author.get("authorAffiliationDetailsList", {}).get("authorAffiliation", [])
    values = [detail.get("affiliation") for detail in details if detail.get("affiliation")]
    if not values and author.get("affiliation"):
        values.append(author["affiliation"])
    return values


def _author_objects(record: dict[str, Any], include_affiliations: bool) -> list[dict[str, Any]]:
    author_list = record.get("authorList", {}).get("author", [])
    if author_list:
        return [
            {
                "firstName": author.get("firstName"),
                "lastName": author.get("lastName"),
                "initials": author.get("initials"),
                "fullName": author.get("fullName"),
                "affiliation": _author_affiliations(author)[0] if include_affiliations and _author_affiliations(author) else None,
                "affiliations": _author_affiliations(author) if include_affiliations else [],
                "orcid": ((author.get("authorId") or {}).get("value") if (author.get("authorId") or {}).get("type") == "ORCID" else None),
            }
            for author in author_list
        ]

    author_string = record.get("authorString")
    if not author_string:
        return []
    authors = []
    for chunk in [part.strip().rstrip(".") for part in author_string.split(",") if part.strip()]:
        authors.append(
            {
                "firstName": None,
                "lastName": chunk,
                "initials": None,
                "fullName": chunk,
                "affiliation": None,
                "affiliations": [],
                "orcid": None,
            }
        )
    return authors


def _source_name(source: str | None) -> str | None:
    mapping = {"MED": "pubmed", "PMC": "pmc", "PPR": "ppr"}
    return mapping.get((source or "").upper(), (source or "").lower() or None)


def _record_url(record: dict[str, Any]) -> str | None:
    source = record.get("source") or record.get("sourceType")
    pmcid = record.get("pmcid")
    pmid = record.get("pmid")
    doi = record.get("doi")
    ppr_id = record.get("id") if (source or "").upper() == "PPR" else None
    if pmcid:
        return f"https://europepmc.org/article/PMC/{pmcid.removeprefix('PMC')}"
    if pmid:
        return f"https://europepmc.org/article/MED/{pmid}"
    if doi:
        return f"https://doi.org/{doi}"
    if ppr_id:
        return f"https://europepmc.org/article/PPR/{ppr_id}"
    return None


def _rights(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "license": record.get("license"),
        "embargoDate": record.get("embargoDate"),
        "copyright": record.get("copyrightStatement"),
    }


def normalize_record(
    record: dict[str, Any],
    result_type: str,
    *,
    query_text: str | None = None,
    include_author_affiliations: bool = False,
) -> dict[str, Any]:
    source = record.get("source") or record.get("sourceType")
    pmcid = record.get("pmcid")
    pmid = record.get("pmid")
    doi = record.get("doi")
    ppr_id = record.get("id") if (source or "").upper() == "PPR" else None
    full_text_urls = record.get("fullTextUrlList", {}).get("fullTextUrl", [])
    mesh_headings = record.get("meshHeadingList", {}).get("meshHeading", [])
    keywords = record.get("keywordList", {}).get("keyword", [])

    return {
        "backend": "europepmc",
        "id": {
            "source": _source_name(source),
            "pmid": pmid,
            "pmcid": pmcid,
            "pprId": ppr_id,
            "doi": doi,
        },
        "title": record.get("title"),
        "authors": _author_objects(record, include_author_affiliations),
        "publishedDate": record.get("firstPublicationDate"),
        "abstract": record.get("abstractText"),
        "url": _record_url(record),
        "source": source,
        "journal": {
            "title": record.get("journalTitle") or (record.get("journalInfo") or {}).get("journal", {}).get("title"),
            "abbreviation": (record.get("journalInfo") or {}).get("journal", {}).get("medlineAbbreviation"),
            "volume": record.get("journalVolume") or (record.get("journalInfo") or {}).get("volume"),
            "issue": record.get("issue") or (record.get("journalInfo") or {}).get("issue"),
            "pages": record.get("pageInfo"),
        },
        "isOpenAccess": _bool_flag(record.get("isOpenAccess")),
        "hasFullText": any(_bool_flag(record.get(flag)) for flag in ["hasPDF", "hasBook", "hasSuppl", "inPMC", "inEPMC"]),
        "category": record.get("pubType") or (record.get("pubTypeList") or {}).get("pubType"),
        "keywordList": keywords,
        "meshHeadingList": [heading.get("descriptorName") for heading in mesh_headings if heading.get("descriptorName")],
        "citationCount": record.get("citedByCount"),
        "referencesCount": record.get("hasReferences"),
        "fullTextUrls": [
            {
                "url": item.get("url"),
                "site": item.get("site"),
                "availability": item.get("availability"),
                "documentStyle": item.get("documentStyle"),
            }
            for item in full_text_urls
        ],
        "rights": _rights(record),
        "provenance": {
            "retrievedAt": _now(),
            "resultType": result_type,
            "srcFilter": "PPR" if query_text and "SRC:PPR" in query_text else source,
        },
    }


def normalize_article_payload(
    payload: dict[str, Any],
    result_type: str,
    *,
    include_author_affiliations: bool = False,
) -> dict[str, Any]:
    result_payload = payload.get("result")
    record = result_payload if isinstance(result_payload, dict) else payload
    return normalize_record(record, result_type, include_author_affiliations=include_author_affiliations)


def normalize_citation_record(record: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "backend": "europepmc",
        "kind": kind,
        "id": {
            "source": _source_name(record.get("source")),
            "pmid": record.get("id") if record.get("source") == "MED" else None,
            "pmcid": record.get("id") if record.get("source") == "PMC" else None,
            "pprId": record.get("id") if record.get("source") == "PPR" else None,
            "doi": record.get("doi"),
            "raw": record.get("id"),
        },
        "title": record.get("title"),
        "authors": record.get("authorString"),
        "journal": record.get("journalAbbreviation"),
        "year": record.get("pubYear"),
        "volume": record.get("volume"),
        "issue": record.get("issue"),
        "pages": record.get("pageInfo"),
        "citationType": record.get("citationType"),
        "order": record.get("citedOrder"),
        "match": _bool_flag(record.get("match")),
        "citationCount": record.get("citedByCount"),
        "provenance": {"retrievedAt": _now()},
    }


def normalize_field_list(payload: dict[str, Any]) -> dict[str, Any]:
    terms = payload.get("searchTermList", {}).get("searchTerms", [])
    fields = [item.get("term") for item in terms if item.get("term")]
    return {"backend": "europepmc", "fields": fields, "count": len(fields), "provenance": {"retrievedAt": _now()}}


def _grant_aliases(person: dict[str, Any], grant: dict[str, Any]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for alias in _as_list(person.get("Alias")):
        if isinstance(alias, dict) and alias.get("Source") and alias.get("value"):
            aliases.setdefault(str(alias["Source"]), []).append(str(alias["value"]))
    if grant.get("Alias"):
        aliases.setdefault("grant", []).append(str(grant["Alias"]))
    return aliases


def normalize_grant_record(record: dict[str, Any], result_type: str) -> dict[str, Any]:
    person = record.get("Person") or {}
    grant = record.get("Grant") or {}
    funder = grant.get("Funder") or {}
    institution = record.get("Institution") or {}
    amount = grant.get("Amount") or {}
    return {
        "backend": "europepmc-grants",
        "id": {
            "grantId": grant.get("Id"),
            "doi": grant.get("Doi"),
        },
        "title": grant.get("Title"),
        "abstract": grant.get("Abstract"),
        "principalInvestigator": {
            "givenName": person.get("GivenName"),
            "familyName": person.get("FamilyName"),
            "initials": person.get("Initials"),
            "title": person.get("Title"),
            "aliases": _grant_aliases(person, grant),
        },
        "funder": {
            "name": funder.get("Name"),
            "searchTerm": funder.get("pubMedSearchTerm"),
            "fundRefId": funder.get("FundRefID"),
        },
        "institution": {
            "name": institution.get("Name"),
            "department": institution.get("Department"),
            "rorId": institution.get("RORID"),
        },
        "type": grant.get("Type"),
        "stream": grant.get("Stream"),
        "startDate": grant.get("StartDate"),
        "endDate": grant.get("EndDate"),
        "amount": {
            "value": amount.get("value"),
            "currency": amount.get("Currency"),
        },
        "url": f"https://doi.org/{grant['Doi']}" if grant.get("Doi") else None,
        "provenance": {
            "retrievedAt": _now(),
            "resultType": result_type,
        },
    }


def normalize_grants_response(payload: dict[str, Any], result_type: str) -> dict[str, Any]:
    records = _as_list((payload.get("RecordList") or {}).get("Record"))
    request = payload.get("Request") or {}
    return {
        "items": [normalize_grant_record(record, result_type) for record in records],
        "meta": {
            "hitCount": int(payload["HitCount"]) if payload.get("HitCount") is not None else None,
            "page": int(request["Page"]) if request.get("Page") is not None else None,
            "query": request.get("Query"),
            "resultType": (request.get("ResultType") or result_type).lower(),
        },
    }


def normalize_search_response(
    payload: dict[str, Any],
    *,
    result_type: str,
    query_text: str,
    include_author_affiliations: bool,
    fields_requested: list[str],
) -> dict[str, Any]:
    batch = payload.get("resultList", {}).get("result", [])
    request = payload.get("request") or {}
    return {
        "items": [
            normalize_record(
                item,
                result_type,
                query_text=query_text,
                include_author_affiliations=include_author_affiliations,
            )
            for item in batch
        ],
        "meta": {
            "version": payload.get("version"),
            "hitCount": payload.get("hitCount"),
            "nextCursorMark": payload.get("nextCursorMark"),
            "request": request,
            "fieldsRequested": fields_requested,
            "query": query_text,
        },
    }


def _pick_identifier(pmid: str | None, pmcid: str | None, ppr: str | None, doi: str | None) -> tuple[str, str]:
    ids = [bool(pmid), bool(pmcid), bool(ppr), bool(doi)]
    if sum(ids) != 1:
        raise ValueError("Exactly one of --pmid/--pmcid/--ppr/--doi is required")
    if pmid:
        return "MED", pmid
    if pmcid:
        return "PMC", pmcid
    if ppr:
        return "PPR", ppr
    return "DOI", str(doi)


def _render_bibtex_entry(item: dict[str, Any], index: int) -> str:
    identifier = item["id"].get("doi") or item["id"].get("pmid") or item["id"].get("pmcid") or f"epmc{index}"
    authors = " and ".join(author.get("fullName") or author.get("lastName") or "Unknown" for author in item.get("authors", []))
    year = (item.get("publishedDate") or "").split("-", 1)[0] or "????"
    journal = (item.get("journal") or {}).get("title")
    title = item.get("title") or ""
    lines = [f"@article{{{identifier},", f"  title = {{{title}}},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    if journal:
        lines.append(f"  journal = {{{journal}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if item["id"].get("doi"):
        lines.append(f"  doi = {{{item['id']['doi']}}},")
    if item.get("url"):
        lines.append(f"  url = {{{item['url']}}},")
    lines.append("}")
    return "\n".join(lines)


def _render_ris_entry(item: dict[str, Any]) -> str:
    lines = ["TY  - JOUR"]
    for author in item.get("authors", []):
        name = author.get("fullName") or author.get("lastName")
        if name:
            lines.append(f"AU  - {name}")
    if item.get("title"):
        lines.append(f"TI  - {item['title']}")
    journal = (item.get("journal") or {}).get("title")
    if journal:
        lines.append(f"JO  - {journal}")
    if item.get("publishedDate"):
        lines.append(f"PY  - {item['publishedDate']}")
    if item["id"].get("doi"):
        lines.append(f"DO  - {item['id']['doi']}")
    if item.get("url"):
        lines.append(f"UR  - {item['url']}")
    lines.append("ER  -")
    return "\n".join(lines)


def _render_csl_json(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for item in items:
        issued_parts = [int(part) for part in (item.get("publishedDate") or "").split("-") if part.isdigit()]
        output.append(
            {
                "id": item["id"].get("doi") or item["id"].get("pmid") or item["id"].get("pmcid"),
                "type": "article-journal",
                "title": item.get("title"),
                "author": [
                    {"given": author.get("firstName"), "family": author.get("lastName") or author.get("fullName")}
                    for author in item.get("authors", [])
                ],
                "DOI": item["id"].get("doi"),
                "URL": item.get("url"),
                "container-title": (item.get("journal") or {}).get("title"),
                "issued": {"date-parts": [issued_parts]} if issued_parts else None,
            }
        )
    return output


class EuropePmcService:
    def __init__(self, config: dict | None = None, client: HttpClient | None = None) -> None:
        self.config = config or load_config()
        email = self.config["api"].get("email")
        user_agent = "pmc-tool/0.1.0"
        if email:
            user_agent = f"{user_agent} ({email})"
        self.client = client or HttpClient(user_agent=user_agent)
        self.base_url = self.config["api"]["base_url"].rstrip("/")

    def search(
        self,
        *,
        query: str | None,
        raw_query: str | None,
        title: str | None,
        abstract: str | None,
        author: str | None,
        category: str | None,
        from_date: str | None,
        to_date: str | None,
        preprints_only: bool,
        has_fulltext: bool | None,
        open_access_only: bool,
        source: str | None,
        sort: str | None,
        page_size: int | None,
        cursor_mark: str | None,
        limit: int | None,
        result_type: str | None,
        synonyms: bool | None,
        fields: str | None,
        include_author_affiliations: bool,
    ) -> dict[str, Any]:
        query_text = build_query(
            query,
            raw_query,
            title,
            abstract,
            author,
            category,
            from_date,
            to_date,
            preprints_only,
            has_fulltext,
            open_access_only,
            source,
            sort,
        )
        resolved_result_type = (result_type or self.config["api"]["default_result_type"]).lower()
        if resolved_result_type not in VALID_RESULT_TYPES:
            raise ValueError(f"Unsupported result type: {resolved_result_type}")
        resolved_page_size = page_size or self.config["search"]["default_page_size"]
        if synonyms is None:
            synonyms = bool(self.config["search"]["synonym_expansion"])
        selected_fields = _normalize_fields(fields)

        params = {
            "query": query_text,
            "format": "json",
            "resultType": resolved_result_type,
            "pageSize": resolved_page_size,
            "cursorMark": cursor_mark or "*",
            "synonym": "true" if synonyms else "false",
            "fields": ",".join(selected_fields) if selected_fields else None,
        }

        items = []
        last_meta: dict[str, Any] = {}
        while True:
            payload = self.client.get_json(f"{self.base_url}/search", params)
            normalized = normalize_search_response(
                payload,
                result_type=resolved_result_type,
                query_text=query_text,
                include_author_affiliations=include_author_affiliations,
                fields_requested=selected_fields,
            )
            batch = normalized["items"]
            items.extend(batch)
            last_meta = normalized["meta"]
            if limit is not None and len(items) >= limit:
                return {"items": items[:limit], "meta": last_meta}
            next_cursor = payload.get("nextCursorMark")
            raw_batch = payload.get("resultList", {}).get("result", [])
            if not raw_batch or limit is None or len(raw_batch) < resolved_page_size or next_cursor == params["cursorMark"]:
                break
            params["cursorMark"] = next_cursor
        return {"items": items, "meta": last_meta}

    def fetch(
        self,
        *,
        pmid: str | None,
        pmcid: str | None,
        ppr: str | None,
        doi: str | None,
        result_type: str | None,
        include_references: bool,
        include_citations: bool,
        include_author_affiliations: bool,
    ) -> dict[str, Any]:
        resolved_result_type = (result_type or self.config["api"]["default_result_type"]).lower()
        source, identifier = _pick_identifier(pmid, pmcid, ppr, doi)

        if source == "DOI":
            result = self.search(
                query=None,
                raw_query=f'DOI:{_quoted(identifier)}',
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
                limit=2,
                result_type=resolved_result_type,
                synonyms=False,
                fields=None,
                include_author_affiliations=include_author_affiliations,
            )
            if len(result["items"]) != 1:
                raise RuntimeError(f"Expected exactly one DOI match, found {len(result['items'])}")
            payload = result["items"][0]
        else:
            raw_payload = self.client.get_json(
                f"{self.base_url}/article/{source}/{quote(str(identifier), safe='')}",
                {"format": "json", "resultType": resolved_result_type},
            )
            payload = normalize_article_payload(
                raw_payload,
                resolved_result_type,
                include_author_affiliations=include_author_affiliations,
            )

        if include_references:
            payload["references"] = self.related_records(
                source=source if source != "DOI" else payload["source"],
                identifier=identifier if source != "DOI" else (payload["id"].get("pmid") or payload["id"].get("pmcid") or payload["id"].get("pprId")),
                relation="references",
                page=1,
                page_size=100,
            )
        if include_citations:
            payload["citations"] = self.related_records(
                source=source if source != "DOI" else payload["source"],
                identifier=identifier if source != "DOI" else (payload["id"].get("pmid") or payload["id"].get("pmcid") or payload["id"].get("pprId")),
                relation="citations",
                page=1,
                page_size=100,
            )
        return payload

    def related_records(self, *, source: str | None, identifier: str | None, relation: str, page: int, page_size: int) -> dict[str, Any]:
        if relation not in {"references", "citations"}:
            raise ValueError(f"Unsupported relation: {relation}")
        if not source or not identifier:
            raise ValueError("Source and identifier are required for relation lookups")
        endpoint = f"{self.base_url}/{source.upper()}/{quote(str(identifier), safe='')}/{relation}/{page}/{page_size}/json"
        payload = self.client.get_json(endpoint)
        list_key = "referenceList" if relation == "references" else "citationList"
        item_key = "reference" if relation == "references" else "citation"
        items = payload.get(list_key, {}).get(item_key, [])
        return {
            "items": [normalize_citation_record(item, relation[:-1]) for item in items],
            "meta": {
                "hitCount": payload.get("hitCount"),
                "page": page,
                "pageSize": page_size,
                "source": source.upper(),
                "identifier": identifier,
            },
        }

    def fields(self) -> dict[str, Any]:
        payload = self.client.get_json(f"{self.base_url}/fields", {"format": "json"})
        return normalize_field_list(payload)

    def preprint_stats(self) -> dict[str, Any]:
        payload = self.client.get_json(
            f"{self.base_url}/search",
            {"query": "SRC:PPR", "resultType": "idlist", "format": "json", "pageSize": 1},
        )
        return {
            "backend": "europepmc",
            "query": "SRC:PPR",
            "preprintCount": payload.get("hitCount"),
            "version": payload.get("version"),
            "provenance": {"retrievedAt": _now()},
        }

    def grants_search(
        self,
        *,
        query: str | None,
        raw_query: str | None,
        pi: str | None,
        agency: str | None,
        grant_id: str | None,
        title: str | None,
        abstract: str | None,
        affiliation: str | None,
        active_date: str | None,
        category: str | None,
        pi_id: str | None,
        epmc_funders: bool | None,
        result_type: str | None,
        page: int | None,
        limit: int | None,
    ) -> dict[str, Any]:
        resolved_result_type = (result_type or "lite").lower()
        if resolved_result_type not in GRANTS_RESULT_TYPES:
            raise ValueError(f"Unsupported grants result type: {resolved_result_type}")
        query_text = build_grants_query(
            query,
            raw_query,
            pi,
            agency,
            grant_id,
            title,
            abstract,
            affiliation,
            active_date,
            category,
            pi_id,
            epmc_funders,
        )
        current_page = page or 1
        items: list[dict[str, Any]] = []
        last_meta: dict[str, Any] = {}
        while True:
            payload = self.client.get_json(
                f"https://www.ebi.ac.uk/europepmc/GristAPI/rest/get/query={quote(query_text, safe=':')}&format=json&resultType={resolved_result_type}&page={current_page}"
            )
            normalized = normalize_grants_response(payload, resolved_result_type)
            batch = normalized["items"]
            items.extend(batch)
            last_meta = normalized["meta"]
            if limit is not None and len(items) >= limit:
                return {"items": items[:limit], "meta": last_meta}
            if not batch or limit is None or len(batch) < 25:
                break
            current_page += 1
        return {"items": items, "meta": last_meta}

    def grants_fetch(self, *, grant_id: str, result_type: str | None) -> dict[str, Any]:
        result = self.grants_search(
            query=None,
            raw_query=None,
            pi=None,
            agency=None,
            grant_id=grant_id,
            title=None,
            abstract=None,
            affiliation=None,
            active_date=None,
            category=None,
            pi_id=None,
            epmc_funders=None,
            result_type=result_type or "core",
            page=1,
            limit=2,
        )
        if len(result["items"]) != 1:
            raise RuntimeError(f"Expected exactly one grant match, found {len(result['items'])}")
        return result["items"][0]

    def export(
        self,
        *,
        query: str | None,
        raw_query: str | None,
        title: str | None,
        abstract: str | None,
        author: str | None,
        category: str | None,
        from_date: str | None,
        to_date: str | None,
        preprints_only: bool,
        has_fulltext: bool | None,
        open_access_only: bool,
        source: str | None,
        sort: str | None,
        limit: int | None,
        result_type: str | None,
        synonyms: bool | None,
        format_name: str,
    ) -> dict[str, Any]:
        result = self.search(
            query=query,
            raw_query=raw_query,
            title=title,
            abstract=abstract,
            author=author,
            category=category,
            from_date=from_date,
            to_date=to_date,
            preprints_only=preprints_only,
            has_fulltext=has_fulltext,
            open_access_only=open_access_only,
            source=source,
            sort=sort,
            page_size=min(limit or self.config["search"]["default_page_size"], self.config["search"]["default_page_size"]),
            cursor_mark=None,
            limit=limit,
            result_type=result_type,
            synonyms=synonyms,
            fields=None,
            include_author_affiliations=False,
        )
        if format_name not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format: {format_name}")
        return result


def render_output(data: dict[str, Any] | list[dict[str, Any]], fmt: str) -> str:
    import json

    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=True)
    if fmt == "jsonl":
        if not isinstance(data, list):
            raise ValueError("jsonl output requires a list of records")
        return "\n".join(json.dumps(item, ensure_ascii=True) for item in data)
    if fmt == "text":
        if isinstance(data, list):
            return "\n".join(
                f"{item.get('title') or item.get('kind') or item.get('query')} [{(item.get('id') or {}).get('doi') or (item.get('id') or {}).get('pmid') or (item.get('id') or {}).get('pmcid') or (item.get('id') or {}).get('raw') or ''}]"
                for item in data
            )
        primary = data.get("title") or data.get("query") or data.get("backend")
        secondary = data.get("url") or json.dumps(data.get("meta") or {}, ensure_ascii=True)
        return f"{primary}\n{secondary}".rstrip()
    if fmt == "bib":
        if not isinstance(data, list):
            raise ValueError("bib output requires a list of records")
        return "\n\n".join(_render_bibtex_entry(item, index) for index, item in enumerate(data, start=1))
    if fmt == "ris":
        if not isinstance(data, list):
            raise ValueError("ris output requires a list of records")
        return "\n\n".join(_render_ris_entry(item) for item in data)
    if fmt == "csl-json":
        if not isinstance(data, list):
            raise ValueError("csl-json output requires a list of records")
        return json.dumps(_render_csl_json(data), indent=2, ensure_ascii=True)
    raise ValueError(f"Unsupported format: {fmt}")
