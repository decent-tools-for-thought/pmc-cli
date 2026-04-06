from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .articles_api import (
    BOOLEAN_TEXT_CHOICES,
    DATA_LINK_CATEGORY_CHOICES,
    DATABASE_CHOICES,
    ENDPOINT_DOCS as ARTICLE_ENDPOINT_DOCS,
    INLINE_IMAGE_CHOICES,
    JSON_XML_FORMATS,
    OBTAINED_BY_CHOICES,
    PROFILE_TYPES,
    QUERY_FORMATS,
    QUERY_RESULT_TYPES,
    RELATION_SOURCE_CHOICES,
    SOURCE_CHOICES,
    DEFAULT_JSON_FORMAT as ARTICLES_DEFAULT_FORMAT,
    EuropePmcArticlesApi,
    parse_status_update_body,
    render_doc as render_articles_doc,
)
from .config import load_config, reset_config, save_config
from .grants_api import (
    ENDPOINT_DOCS as GRANTS_ENDPOINT_DOCS,
    FORMATS as GRANT_FORMATS,
    RESULT_TYPES as GRANT_RESULT_TYPES,
    EuropePmcGrantsApi,
    render_doc as render_grants_doc,
)


Handler = Callable[[argparse.Namespace, dict], int]


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _resolve_query(args: argparse.Namespace) -> str | None:
    return _trim(getattr(args, "query_option", None)) or _trim(getattr(args, "query", None))


def _write_output(payload: bytes, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_bytes(payload)
    else:
        sys.stdout.buffer.write(payload)


def _render_http_response(response: Any) -> bytes:
    content_type = response.content_type.lower()
    if "json" in content_type:
        try:
            return (json.dumps(response.json(), indent=2, ensure_ascii=True) + "\n").encode("utf-8")
        except Exception:
            return response.body
    return response.body


def _emit_response(response: Any, output_path: str | None) -> int:
    _write_output(_render_http_response(response), output_path)
    return 0


def _set_config_value(config: dict, field: str, value: str) -> dict:
    if field == "email":
        config["api"]["email"] = value
    elif field == "base-url":
        config["api"]["base_url"] = value
    elif field == "default-result-type":
        config["api"]["default_result_type"] = value
    else:
        raise ValueError(f"Unsupported config field: {field}")
    return config


def _help_for(args: argparse.Namespace) -> argparse.ArgumentParser:
    return getattr(args, "_command_parser")


def _require(values: dict[str, Any], parser: argparse.ArgumentParser) -> bool:
    def present(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value != ""
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) > 0
        return True

    if all(present(value) for value in values.values()):
        return True
    parser.print_help()
    return False


def _articles_service(args: argparse.Namespace, config: dict) -> EuropePmcArticlesApi:
    return EuropePmcArticlesApi(config=config, release=args.release, base_url=_trim(args.base_url))


def _grants_service(args: argparse.Namespace, config: dict) -> EuropePmcGrantsApi:
    return EuropePmcGrantsApi(config=config, release=args.release, base_url=_trim(args.base_url))


def _article_query_handler(method_name: str) -> Handler:
    def handler(args: argparse.Namespace, config: dict) -> int:
        parser = _help_for(args)
        query = _resolve_query(args)
        if not _require({"query": query}, parser):
            return 0
        method = getattr(_articles_service(args, config), method_name)
        response = method(
            query=query,
            result_type=args.result_type,
            synonym=args.synonym,
            cursor_mark=args.cursor_mark,
            page_size=args.page_size,
            sort=args.sort,
            format_name=args.format,
            callback=args.callback,
            email=args.email,
        )
        return _emit_response(response, args.output)

    return handler


def _article_fields_handler(args: argparse.Namespace, config: dict) -> int:
    return _emit_response(
        _articles_service(args, config).fields(format_name=args.format, callback=args.callback),
        args.output,
    )


def _article_profile_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    query = _resolve_query(args)
    if not _require({"query": query}, parser):
        return 0
    response = _articles_service(args, config).profile(
        query=query,
        profile_type=args.profile_type,
        synonym=args.synonym,
        format_name=args.format,
        callback=args.callback,
        email=args.email,
    )
    return _emit_response(response, args.output)


def _article_fetch_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"source": args.source, "id": args.id}, parser):
        return 0
    response = _articles_service(args, config).article(
        source=args.source,
        article_id=args.id,
        result_type=args.result_type,
        format_name=args.format,
        callback=args.callback,
        email=args.email,
    )
    return _emit_response(response, args.output)


def _article_relation_handler(name: str) -> Handler:
    def handler(args: argparse.Namespace, config: dict) -> int:
        parser = _help_for(args)
        if not _require({"source": args.source, "id": args.id}, parser):
            return 0
        method = getattr(_articles_service(args, config), name)
        response = method(
            source=args.source,
            article_id=args.id,
            page=args.page,
            page_size=args.page_size,
            format_name=args.format,
            callback=args.callback,
        )
        return _emit_response(response, args.output)

    return handler


def _article_evaluations_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"source": args.source, "id": args.id}, parser):
        return 0
    response = _articles_service(args, config).evaluations(
        source=args.source,
        article_id=args.id,
        format_name=args.format,
    )
    return _emit_response(response, args.output)


def _article_database_links_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"source": args.source, "id": args.id}, parser):
        return 0
    response = _articles_service(args, config).database_links(
        source=args.source,
        article_id=args.id,
        database=args.database,
        page=args.page,
        page_size=args.page_size,
        format_name=args.format,
        callback=args.callback,
    )
    return _emit_response(response, args.output)


def _article_labs_links_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"source": args.source, "id": args.id}, parser):
        return 0
    response = _articles_service(args, config).labs_links(
        source=args.source,
        article_id=args.id,
        provider_ids=args.provider_id,
        page=args.page,
        page_size=args.page_size,
        format_name=args.format,
        callback=args.callback,
    )
    return _emit_response(response, args.output)


def _article_data_links_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"source": args.source, "id": args.id}, parser):
        return 0
    response = _articles_service(args, config).data_links(
        source=args.source,
        article_id=args.id,
        category=args.category,
        obtained_by=args.obtained_by,
        from_date=args.from_date,
        tags=args.tags,
        section_limit=args.section_limit,
        email=args.email,
        ref=args.ref,
        format_name=args.format,
    )
    return _emit_response(response, args.output)


def _article_xml_body_handler(name: str) -> Handler:
    def handler(args: argparse.Namespace, config: dict) -> int:
        parser = _help_for(args)
        if not _require({"id": args.id}, parser):
            return 0
        response = getattr(_articles_service(args, config), name)(article_id=args.id)
        return _emit_response(response, args.output)

    return handler


def _article_supplementary_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"id": args.id}, parser):
        return 0
    response = _articles_service(args, config).supplementary_files(
        article_id=args.id,
        include_inline_image=args.include_inline_image,
    )
    return _emit_response(response, args.output)


def _article_status_update_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    if not _require({"body-or-article": args.body or args.article}, parser):
        return 0
    response = _articles_service(args, config).status_update_search(
        body=parse_status_update_body(args.body, args.article),
        format_name=args.format,
    )
    return _emit_response(response, args.output)


def _grants_search_handler(args: argparse.Namespace, config: dict) -> int:
    parser = _help_for(args)
    query = _resolve_query(args)
    if not _require({"query": query}, parser):
        return 0
    response = _grants_service(args, config).search(
        query=query,
        result_type=args.result_type,
        page=args.page,
        format_name=args.format,
    )
    return _emit_response(response, args.output)


def _doc_handler(args: argparse.Namespace, config: dict) -> int:
    del config
    if args.surface is None:
        sys.stdout.write(
            "Europe PMC Developer APIs\n\n"
            "Surfaces\n"
            "- articles\n"
            "- grants\n\n"
            "Use `pmc doc articles [endpoint]` or `pmc doc grants [endpoint]`.\n"
        )
        return 0
    if args.surface == "articles":
        sys.stdout.write(render_articles_doc(args.topic))
        return 0
    if args.surface == "grants":
        sys.stdout.write(render_grants_doc(args.topic))
        return 0
    raise ValueError(f"Unsupported doc surface: {args.surface}")


def _config_handler(args: argparse.Namespace, config: dict) -> int:
    if args.config_command is None:
        _help_for(args).print_help()
        return 0
    if args.config_command == "show":
        print(json.dumps(config, indent=2, ensure_ascii=True))
        return 0
    if args.config_command == "reset":
        print(json.dumps(reset_config(), indent=2, ensure_ascii=True))
        return 0
    updated = _set_config_value(config, args.field, args.value)
    save_config(updated)
    print(json.dumps(updated, indent=2, ensure_ascii=True))
    return 0


def _endpoint_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str, help_text: str
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text, description=help_text)
    parser.add_argument("--output")
    return parser


def _add_article_query_parameters(
    parser: argparse.ArgumentParser, *, default_format: str = ARTICLES_DEFAULT_FORMAT
) -> None:
    parser.add_argument("query", nargs="?")
    parser.add_argument("--query", dest="query_option")
    parser.add_argument("--result-type", choices=QUERY_RESULT_TYPES)
    parser.add_argument("--synonym", choices=BOOLEAN_TEXT_CHOICES)
    parser.add_argument("--cursor-mark")
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--sort")
    parser.add_argument("--format", choices=QUERY_FORMATS, default=default_format)
    parser.add_argument("--callback")
    parser.add_argument("--email")


def _add_article_relation_parameters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", nargs="?", choices=RELATION_SOURCE_CHOICES)
    parser.add_argument("id", nargs="?")
    parser.add_argument("--page", type=int)
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    parser.add_argument("--callback")


def _add_articles_surface(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    articles = subparsers.add_parser(
        "articles",
        help="Europe PMC Articles RESTful API",
        description="Europe PMC Articles RESTful API",
    )
    articles_sub = articles.add_subparsers(dest="articles_command")

    search = _endpoint_parser(articles_sub, "search", "GET /search")
    _add_article_query_parameters(search)
    search.set_defaults(_handler=_article_query_handler("search"), _command_parser=search)

    search_post = _endpoint_parser(articles_sub, "search-post", "POST /searchPOST")
    _add_article_query_parameters(search_post)
    search_post.set_defaults(
        _handler=_article_query_handler("search_post"), _command_parser=search_post
    )

    fields = _endpoint_parser(articles_sub, "fields", "GET /fields")
    fields.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    fields.add_argument("--callback")
    fields.set_defaults(_handler=_article_fields_handler, _command_parser=fields)

    profile = _endpoint_parser(articles_sub, "profile", "GET /profile")
    profile.add_argument("query", nargs="?")
    profile.add_argument("--query", dest="query_option")
    profile.add_argument("--profile-type", choices=PROFILE_TYPES)
    profile.add_argument("--synonym", choices=BOOLEAN_TEXT_CHOICES)
    profile.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    profile.add_argument("--callback")
    profile.add_argument("--email")
    profile.set_defaults(_handler=_article_profile_handler, _command_parser=profile)

    article = _endpoint_parser(articles_sub, "fetch", "GET /article/{source}/{id}")
    article.add_argument("source", nargs="?", choices=SOURCE_CHOICES)
    article.add_argument("id", nargs="?")
    article.add_argument("--result-type", choices=QUERY_RESULT_TYPES)
    article.add_argument("--format", choices=QUERY_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    article.add_argument("--callback")
    article.add_argument("--email")
    article.set_defaults(_handler=_article_fetch_handler, _command_parser=article)

    citations = _endpoint_parser(articles_sub, "citations", "GET /{source}/{id}/citations")
    _add_article_relation_parameters(citations)
    citations.set_defaults(
        _handler=_article_relation_handler("citations"), _command_parser=citations
    )

    references = _endpoint_parser(articles_sub, "references", "GET /{source}/{id}/references")
    _add_article_relation_parameters(references)
    references.set_defaults(
        _handler=_article_relation_handler("references"), _command_parser=references
    )

    evaluations = _endpoint_parser(articles_sub, "evaluations", "GET /evaluations/{source}/{id}")
    evaluations.add_argument("source", nargs="?", choices=RELATION_SOURCE_CHOICES)
    evaluations.add_argument("id", nargs="?")
    evaluations.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    evaluations.set_defaults(_handler=_article_evaluations_handler, _command_parser=evaluations)

    database_links = _endpoint_parser(
        articles_sub, "database-links", "GET /{source}/{id}/databaseLinks"
    )
    database_links.add_argument("source", nargs="?", choices=RELATION_SOURCE_CHOICES)
    database_links.add_argument("id", nargs="?")
    database_links.add_argument("--database", choices=DATABASE_CHOICES)
    database_links.add_argument("--page", type=int)
    database_links.add_argument("--page-size", type=int)
    database_links.add_argument(
        "--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT
    )
    database_links.add_argument("--callback")
    database_links.set_defaults(
        _handler=_article_database_links_handler, _command_parser=database_links
    )

    labs_links = _endpoint_parser(articles_sub, "labs-links", "GET /{source}/{id}/labsLinks")
    labs_links.add_argument("source", nargs="?", choices=RELATION_SOURCE_CHOICES)
    labs_links.add_argument("id", nargs="?")
    labs_links.add_argument("--provider-id", type=int, action="append")
    labs_links.add_argument("--page", type=int)
    labs_links.add_argument("--page-size", type=int)
    labs_links.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    labs_links.add_argument("--callback")
    labs_links.set_defaults(_handler=_article_labs_links_handler, _command_parser=labs_links)

    data_links = _endpoint_parser(articles_sub, "data-links", "GET /{source}/{id}/datalinks")
    data_links.add_argument("source", nargs="?", choices=RELATION_SOURCE_CHOICES)
    data_links.add_argument("id", nargs="?")
    data_links.add_argument("--category", choices=DATA_LINK_CATEGORY_CHOICES)
    data_links.add_argument("--obtained-by", choices=OBTAINED_BY_CHOICES)
    data_links.add_argument("--from-date")
    data_links.add_argument("--tags")
    data_links.add_argument("--section-limit")
    data_links.add_argument("--email")
    data_links.add_argument("--ref")
    data_links.add_argument("--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT)
    data_links.set_defaults(_handler=_article_data_links_handler, _command_parser=data_links)

    fulltext_xml = _endpoint_parser(articles_sub, "fulltext-xml", "GET /{id}/fullTextXML")
    fulltext_xml.add_argument("id", nargs="?")
    fulltext_xml.set_defaults(
        _handler=_article_xml_body_handler("fulltext_xml"), _command_parser=fulltext_xml
    )

    book_xml = _endpoint_parser(articles_sub, "book-xml", "GET /{id}/bookXML")
    book_xml.add_argument("id", nargs="?")
    book_xml.set_defaults(_handler=_article_xml_body_handler("book_xml"), _command_parser=book_xml)

    supplementary = _endpoint_parser(
        articles_sub, "supplementary-files", "GET /{id}/supplementaryFiles"
    )
    supplementary.add_argument("id", nargs="?")
    supplementary.add_argument("--include-inline-image", choices=INLINE_IMAGE_CHOICES)
    supplementary.set_defaults(
        _handler=_article_supplementary_handler, _command_parser=supplementary
    )

    status_update = _endpoint_parser(
        articles_sub, "status-update-search", "POST /status-update-search"
    )
    status_update.add_argument(
        "--format", choices=JSON_XML_FORMATS, default=ARTICLES_DEFAULT_FORMAT
    )
    status_update.add_argument("--article", nargs=2, action="append", metavar=("SRC", "EXT_ID"))
    status_update.add_argument("--body")
    status_update.set_defaults(
        _handler=_article_status_update_handler, _command_parser=status_update
    )


def _add_grants_surface(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    grants = subparsers.add_parser(
        "grants",
        help="Europe PMC Grants RESTful API",
        description="Europe PMC Grants RESTful API",
    )
    grants_sub = grants.add_subparsers(dest="grants_command")

    search = _endpoint_parser(grants_sub, "search", "GET /get/query={query}")
    search.add_argument("query", nargs="?")
    search.add_argument("--query", dest="query_option")
    search.add_argument("--result-type", choices=GRANT_RESULT_TYPES)
    search.add_argument("--page", type=int)
    search.add_argument("--format", choices=GRANT_FORMATS, default="json")
    search.set_defaults(_handler=_grants_search_handler, _command_parser=search)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmc")
    parser.add_argument("--release", choices=["production", "test"], default="production")
    parser.add_argument("--base-url")
    subparsers = parser.add_subparsers(dest="command")

    _add_articles_surface(subparsers)
    _add_grants_surface(subparsers)

    doc = subparsers.add_parser(
        "doc", help="Explain API surfaces, endpoints, releases, and result types"
    )
    doc.add_argument("surface", nargs="?", choices=["articles", "grants"])
    doc.add_argument(
        "topic",
        nargs="?",
        choices=[endpoint.command for endpoint in ARTICLE_ENDPOINT_DOCS + GRANTS_ENDPOINT_DOCS],
    )
    doc.set_defaults(_handler=_doc_handler, _command_parser=doc)

    config = subparsers.add_parser("config", help="Show or modify CLI config")
    config_sub = config.add_subparsers(dest="config_command")
    config_sub.add_parser("show")
    config_sub.add_parser("reset")
    config_set = config_sub.add_parser("set")
    config_set.add_argument("field", choices=["email", "base-url", "default-result-type"])
    config_set.add_argument("value")
    config.set_defaults(_handler=_config_handler, _command_parser=config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    # Print contextual help for API surfaces without endpoint selection.
    if args.command in {"articles", "grants"} and getattr(args, f"{args.command}_command") is None:
        parser._subparsers._group_actions[0].choices[args.command].print_help()  # type: ignore[attr-defined]
        return 0

    config = load_config()
    try:
        return args._handler(args, config)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
