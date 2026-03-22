from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, reset_config, save_config
from .core import EuropePmcService, render_output


DEFAULT_OUTPUT_FORMATS = {
    "search": "jsonl",
    "fetch": "json",
    "related": "json",
    "fields": "json",
    "export": "bib",
    "grants": "json",
    "preprints": "jsonl",
}

COMMAND_OUTPUT_CHOICES = {
    "search": {"jsonl", "json", "text"},
    "fetch": {"json", "text"},
    "related": {"json", "jsonl", "text"},
    "fields": {"json", "text"},
    "export": {"jsonl", "bib", "ris", "csl-json", "json", "text"},
    "grants:search": {"jsonl", "json", "text"},
    "grants:fetch": {"json", "text"},
    "preprints:search": {"jsonl", "json", "text"},
    "preprints:by-category": {"jsonl", "json", "text"},
    "preprints:by-date-range": {"jsonl", "json", "text"},
    "preprints:stats": {"json", "text"},
}


def _add_search_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_preprints_only: bool = False,
    format_choices: list[str] | None = None,
) -> None:
    parser.add_argument("query", nargs="?")
    parser.add_argument("--raw-query")
    parser.add_argument("--title")
    parser.add_argument("--abstract")
    parser.add_argument("--author")
    parser.add_argument("--category")
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--preprints-only", action="store_true", default=default_preprints_only)
    parser.add_argument("--has-fulltext", dest="has_fulltext", action="store_true")
    parser.add_argument("--no-fulltext", dest="has_fulltext", action="store_false")
    parser.set_defaults(has_fulltext=None)
    parser.add_argument("--open-access-only", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--sort")
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--cursor-mark")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--result-type", choices=["idlist", "lite", "core"])
    parser.add_argument("--synonyms", dest="synonyms", action="store_true")
    parser.add_argument("--no-synonyms", dest="synonyms", action="store_false")
    parser.set_defaults(synonyms=None)
    parser.add_argument("--fields")
    parser.add_argument("--include-author-affiliations", action="store_true")
    if format_choices is not None:
        parser.add_argument("--format", choices=format_choices)


def _resolve_identifier_argument(
    args: argparse.Namespace,
) -> tuple[str | None, str | None, str | None, str | None]:
    positional = getattr(args, "identifier", None)
    pmid = args.pmid
    pmcid = args.pmcid
    ppr = args.ppr
    doi = args.doi
    if positional:
        upper = positional.upper()
        if upper.startswith("PMC"):
            pmcid = positional
        elif upper.startswith("PPR") or upper.startswith("PMR"):
            ppr = positional
        elif positional.isdigit():
            pmid = positional
        else:
            doi = positional
    return pmid, pmcid, ppr, doi


def _write_output_if_needed(text: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
    else:
        print(text)


def _resolve_related_source(source: str | None, identifier: str) -> str:
    if source is not None:
        return source
    upper = identifier.upper()
    if upper.startswith("PMC"):
        return "PMC"
    if upper.startswith("PPR") or upper.startswith("PMR"):
        return "PPR"
    return "MED"


def _output_format_key(args: argparse.Namespace) -> str:
    if args.command == "grants":
        return f"grants:{args.grants_command}"
    if args.command == "preprints":
        return f"preprints:{args.preprints_command}"
    return str(args.command)


def _resolve_output_format(args: argparse.Namespace, config: dict) -> str:
    explicit = getattr(args, "format", None)
    if explicit:
        return explicit
    key = _output_format_key(args)
    supported = COMMAND_OUTPUT_CHOICES.get(key, set())
    configured = config["output"]["default_format"]
    if configured in supported:
        return configured
    return DEFAULT_OUTPUT_FORMATS[args.command]


def _add_grants_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", nargs="?")
    parser.add_argument("--raw-query")
    parser.add_argument("--pi")
    parser.add_argument("--agency")
    parser.add_argument("--grant-id")
    parser.add_argument("--title")
    parser.add_argument("--abstract")
    parser.add_argument("--affiliation")
    parser.add_argument("--active-date")
    parser.add_argument("--category")
    parser.add_argument("--pi-id")
    parser.add_argument("--epmc-funders", dest="epmc_funders", action="store_true")
    parser.add_argument("--not-epmc-funders", dest="epmc_funders", action="store_false")
    parser.set_defaults(epmc_funders=None)
    parser.add_argument("--result-type", choices=["lite", "core"])
    parser.add_argument("--page", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--format", choices=["jsonl", "json", "text"])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmc")
    subparsers = parser.add_subparsers(dest="command")

    search = subparsers.add_parser("search")
    _add_search_arguments(search, format_choices=["jsonl", "json", "text"])

    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("identifier", nargs="?")
    fetch.add_argument("--pmid")
    fetch.add_argument("--pmcid")
    fetch.add_argument("--ppr")
    fetch.add_argument("--doi")
    fetch.add_argument("--result-type", choices=["lite", "core"])
    fetch.add_argument("--include-references", action="store_true")
    fetch.add_argument("--include-citations", action="store_true")
    fetch.add_argument("--include-author-affiliations", action="store_true")
    fetch.add_argument("--format", choices=["json", "text"])

    related = subparsers.add_parser("related")
    related_sub = related.add_subparsers(dest="related_command")
    for name in ["references", "citations"]:
        relation = related_sub.add_parser(name)
        relation.add_argument("identifier")
        relation.add_argument("--source", choices=["MED", "PMC", "PPR"])
        relation.add_argument("--page", type=int, default=1)
        relation.add_argument("--page-size", type=int, default=25)
        relation.add_argument("--format", choices=["json", "jsonl", "text"])

    fields = subparsers.add_parser("fields")
    fields.add_argument("--format", choices=["json", "text"], default="json")

    export = subparsers.add_parser("export")
    _add_search_arguments(export, format_choices=None)
    export.add_argument("--output")
    export.add_argument(
        "--format", choices=["jsonl", "bib", "ris", "csl-json", "json", "text"], default="bib"
    )

    grants = subparsers.add_parser("grants")
    grants_sub = grants.add_subparsers(dest="grants_command")

    grants_search = grants_sub.add_parser("search")
    _add_grants_search_arguments(grants_search)

    grants_fetch = grants_sub.add_parser("fetch")
    grants_fetch.add_argument("grant_id")
    grants_fetch.add_argument("--result-type", choices=["lite", "core"], default="core")
    grants_fetch.add_argument("--format", choices=["json", "text"])

    preprints = subparsers.add_parser("preprints")
    preprints_sub = preprints.add_subparsers(dest="preprints_command")

    preprint_search = preprints_sub.add_parser("search")
    _add_search_arguments(
        preprint_search, default_preprints_only=True, format_choices=["jsonl", "json", "text"]
    )

    by_category = preprints_sub.add_parser("by-category")
    by_category.add_argument("category")
    by_category.add_argument("--from-date")
    by_category.add_argument("--to-date")
    by_category.add_argument("--page-size", type=int)
    by_category.add_argument("--cursor-mark")
    by_category.add_argument("--limit", type=int)
    by_category.add_argument("--result-type", choices=["idlist", "lite", "core"])
    by_category.add_argument("--format", choices=["jsonl", "json", "text"])

    by_date_range = preprints_sub.add_parser("by-date-range")
    by_date_range.add_argument("from_date")
    by_date_range.add_argument("to_date")
    by_date_range.add_argument("--page-size", type=int)
    by_date_range.add_argument("--cursor-mark")
    by_date_range.add_argument("--limit", type=int)
    by_date_range.add_argument("--result-type", choices=["idlist", "lite", "core"])
    by_date_range.add_argument("--format", choices=["jsonl", "json", "text"])

    preprints_sub.add_parser("stats").add_argument(
        "--format", choices=["json", "text"], default="json"
    )

    config = subparsers.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command")
    config_sub.add_parser("show")
    config_sub.add_parser("reset")
    config_set = config_sub.add_parser("set")
    config_set.add_argument(
        "field",
        choices=[
            "email",
            "default-result-type",
            "default-page-size",
            "default-format",
            "default-preprints-only",
            "synonym-expansion",
        ],
    )
    config_set.add_argument("value")

    return parser


def _set_config_value(config: dict, field: str, value: str) -> dict:
    if field == "email":
        config["api"]["email"] = value
    elif field == "default-result-type":
        config["api"]["default_result_type"] = value
    elif field == "default-page-size":
        config["search"]["default_page_size"] = int(value)
    elif field == "default-format":
        config["output"]["default_format"] = value
    elif field == "default-preprints-only":
        config["search"]["default_preprints_only"] = value.lower() in {"1", "true", "yes", "y"}
    elif field == "synonym-expansion":
        config["search"]["synonym_expansion"] = value.lower() in {"1", "true", "yes", "y"}
    else:
        raise ValueError(f"Unsupported config field: {field}")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    help_attr_by_command = {
        "related": "related_command",
        "grants": "grants_command",
        "preprints": "preprints_command",
        "config": "config_command",
    }
    help_attr = help_attr_by_command.get(args.command)
    if help_attr and getattr(args, help_attr) is None:
        next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ).choices[args.command].print_help()
        return 0
    config = load_config()

    if args.command == "config":
        if args.config_command == "show":
            print(json.dumps(config, indent=2, ensure_ascii=True))
            return 0
        if args.config_command == "reset":
            print(json.dumps(reset_config(), indent=2, ensure_ascii=True))
            return 0
        config = _set_config_value(config, args.field, args.value)
        save_config(config)
        print(json.dumps(config, indent=2, ensure_ascii=True))
        return 0

    service = EuropePmcService(config=config)
    output_format = _resolve_output_format(args, config)

    try:
        if args.command == "search":
            result = service.search(
                query=args.query,
                raw_query=args.raw_query,
                title=args.title,
                abstract=args.abstract,
                author=args.author,
                category=args.category,
                from_date=args.from_date,
                to_date=args.to_date,
                preprints_only=args.preprints_only,
                has_fulltext=args.has_fulltext,
                open_access_only=args.open_access_only,
                source=args.source,
                sort=args.sort,
                page_size=args.page_size,
                cursor_mark=args.cursor_mark,
                limit=args.limit,
                result_type=args.result_type,
                synonyms=args.synonyms,
                fields=args.fields,
                include_author_affiliations=args.include_author_affiliations,
            )
            payload = result if output_format == "json" else result["items"]
            print(render_output(payload, output_format))
            return 0

        if args.command == "fetch":
            pmid, pmcid, ppr, doi = _resolve_identifier_argument(args)
            payload = service.fetch(
                pmid=pmid,
                pmcid=pmcid,
                ppr=ppr,
                doi=doi,
                result_type=args.result_type,
                include_references=args.include_references,
                include_citations=args.include_citations,
                include_author_affiliations=args.include_author_affiliations,
            )
            print(render_output(payload, output_format))
            return 0

        if args.command == "related":
            identifier = args.identifier
            source = _resolve_related_source(args.source, identifier)
            result = service.related_records(
                source=source,
                identifier=identifier,
                relation=args.related_command,
                page=args.page,
                page_size=args.page_size,
            )
            payload = result if output_format == "json" else result["items"]
            print(render_output(payload, output_format))
            return 0

        if args.command == "fields":
            payload = service.fields()
            if output_format == "text":
                print("\n".join(payload["fields"]))
            else:
                print(render_output(payload, "json"))
            return 0

        if args.command == "export":
            result = service.export(
                query=args.query,
                raw_query=args.raw_query,
                title=args.title,
                abstract=args.abstract,
                author=args.author,
                category=args.category,
                from_date=args.from_date,
                to_date=args.to_date,
                preprints_only=args.preprints_only,
                has_fulltext=args.has_fulltext,
                open_access_only=args.open_access_only,
                source=args.source,
                sort=args.sort,
                limit=args.limit,
                result_type=args.result_type,
                synonyms=args.synonyms,
                format_name=output_format,
            )
            payload = result if output_format == "json" else result["items"]
            rendered = render_output(payload, output_format)
            _write_output_if_needed(rendered, args.output)
            return 0

        if args.command == "grants":
            if args.grants_command == "search":
                result = service.grants_search(
                    query=args.query,
                    raw_query=args.raw_query,
                    pi=args.pi,
                    agency=args.agency,
                    grant_id=args.grant_id,
                    title=args.title,
                    abstract=args.abstract,
                    affiliation=args.affiliation,
                    active_date=args.active_date,
                    category=args.category,
                    pi_id=args.pi_id,
                    epmc_funders=args.epmc_funders,
                    result_type=args.result_type,
                    page=args.page,
                    limit=args.limit,
                )
                payload = result if output_format == "json" else result["items"]
                print(render_output(payload, output_format))
                return 0

            payload = service.grants_fetch(
                grant_id=args.grant_id,
                result_type=args.result_type,
            )
            print(render_output(payload, output_format))
            return 0

        if args.command == "preprints":
            if args.preprints_command == "stats":
                print(render_output(service.preprint_stats(), output_format))
                return 0

            if args.preprints_command == "by-category":
                result = service.search(
                    query=None,
                    raw_query=None,
                    title=None,
                    abstract=None,
                    author=None,
                    category=args.category,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    preprints_only=True,
                    has_fulltext=None,
                    open_access_only=False,
                    source=None,
                    sort=None,
                    page_size=args.page_size,
                    cursor_mark=args.cursor_mark,
                    limit=args.limit,
                    result_type=args.result_type,
                    synonyms=False,
                    fields=None,
                    include_author_affiliations=False,
                )
            elif args.preprints_command == "by-date-range":
                result = service.search(
                    query=None,
                    raw_query=None,
                    title=None,
                    abstract=None,
                    author=None,
                    category=None,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    preprints_only=True,
                    has_fulltext=None,
                    open_access_only=False,
                    source=None,
                    sort="sort_date:y",
                    page_size=args.page_size,
                    cursor_mark=args.cursor_mark,
                    limit=args.limit,
                    result_type=args.result_type,
                    synonyms=False,
                    fields=None,
                    include_author_affiliations=False,
                )
            else:
                result = service.search(
                    query=args.query,
                    raw_query=args.raw_query,
                    title=args.title,
                    abstract=args.abstract,
                    author=args.author,
                    category=args.category,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    preprints_only=True,
                    has_fulltext=args.has_fulltext,
                    open_access_only=args.open_access_only,
                    source=args.source,
                    sort=args.sort,
                    page_size=args.page_size,
                    cursor_mark=args.cursor_mark,
                    limit=args.limit,
                    result_type=args.result_type,
                    synonyms=args.synonyms,
                    fields=args.fields,
                    include_author_affiliations=args.include_author_affiliations,
                )
            payload = result if output_format == "json" else result["items"]
            print(render_output(payload, output_format))
            return 0

        raise ValueError(f"Unsupported command: {args.command}")
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
