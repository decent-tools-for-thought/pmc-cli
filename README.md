# pmc-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/pmc-cli?sort=semver)](https://github.com/decent-tools-for-thought/pmc-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-0BSD-green)

Command-line access to the Europe PMC APIs for literature search, record fetch, citation traversal, and export.

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Why This Exists

- Search Europe PMC quickly from a terminal.
- Fetch records by PMID, PMCID, DOI, or preprint identifier.
- Export results in JSONL, BibTeX, RIS, or CSL-JSON.

## Install

```bash
uv tool install .
pmc --help
```

For local development:

```bash
uv sync
uv run pmc --help
```

## Quick Start

Search:

```bash
pmc search "single cell RNA sequencing" --limit 5 --format text
```

Fetch one paper:

```bash
pmc fetch --pmid 35092342 --format text
```

Follow references or citations:

```bash
pmc related references 35092342 --source MED --page-size 25 --format text
pmc related citations PMC8860882 --source PMC --format json
```

Export citations:

```bash
pmc export "machine learning" --limit 20 --format bib --output citations.bib
```

## Configuration

Europe PMC does not require an API key for the endpoints this CLI uses. The main optional setting is an email address added to the `User-Agent` string:

```bash
pmc config set email your-email@example.com
pmc config show
```

Config is stored at `$XDG_CONFIG_HOME/pmc-tool/config.toml` or `~/.config/pmc-tool/config.toml`.

## Development

```bash
uv run ruff check src
uv run mypy
```

## Credits

This client is built on Europe PMC and its public APIs. Credit goes to the Europe PMC project and its maintainers for the underlying data service and documentation.
