<div align="center">

# pmc-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/pmc-cli?sort=semver&color=facc15)](https://github.com/decent-tools-for-thought/pmc-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-eab308)
![License](https://img.shields.io/badge/license-0BSD-ca8a04)

Command-line client for Europe PMC search, fetch, related-record traversal, grants, preprints, and citation export workflows.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#EAB308}Install \space \color{#CA8A04}Tool$$

```bash
uv tool install .    # install the CLI
pmc --help           # inspect the command surface
```

## Functionality
$$\color{#EAB308}Paper \space \color{#CA8A04}Search$$
- `pmc search`: search Europe PMC with free text, raw query syntax, title, abstract, author, category, date bounds, source filters, page size, cursor marks, limits, synonym-expansion control, result-type control, and `jsonl`/`json`/`text` output.
- `pmc search`: supports `--preprints-only`, full-text filtering, open-access-only filtering, explicit field selection, and author-affiliation inclusion.
- `pmc fetch`: fetch a single record by positional identifier, `--pmid`, `--pmcid`, `--ppr`, or `--doi`.
- `pmc fetch`: optionally include references, citations, and author affiliations.
- `pmc related references <identifier>`: fetch references for a MED, PMC, or PPR record.
- `pmc related citations <identifier>`: fetch citations for a MED, PMC, or PPR record.
- `pmc fields`: list the searchable fields exposed by the client.

$$\color{#EAB308}Citation \space \color{#CA8A04}Export$$
- `pmc export`: run a search and export results as `bib`, `ris`, `csl-json`, `jsonl`, `json`, or `text`.
- `pmc export --output <path>`: write export output directly to a file.

$$\color{#EAB308}Grant \space \color{#CA8A04}Search$$
- `pmc grants search`: search grant data by free text, raw query, PI, agency, grant ID, title, abstract, affiliation, active date, category, PI ID, and Europe PMC funder participation.
- `pmc grants fetch <grant-id>`: fetch one grant record.

$$\color{#EAB308}Preprint \space \color{#CA8A04}Search$$
- `pmc preprints search`: search only preprint records with the same fielded controls as general literature search.
- `pmc preprints by-category <category>`: browse preprints by category with date and paging controls.
- `pmc preprints by-date-range <from> <to>`: browse preprints within a date range.
- `pmc preprints stats`: fetch aggregate preprint statistics.

$$\color{#EAB308}Saved \space \color{#CA8A04}Defaults$$
- `pmc config show`: print the saved config.
- `pmc config reset`: restore defaults.
- `pmc config set email`: save an email value for the `User-Agent`.
- `pmc config set default-result-type`, `default-page-size`, `default-format`, `default-preprints-only`, and `synonym-expansion`: tune default request behavior.

## Configuration
$$\color{#EAB308}Save \space \color{#CA8A04}Defaults$$

Europe PMC does not require an API key for the endpoints this CLI uses. The main optional setting is an email address added to the `User-Agent` string:

```bash
pmc config set email your-email@example.com    # add contact info to the User-Agent
pmc config show                                # inspect saved defaults
```

Config is stored at `$XDG_CONFIG_HOME/pmc-tool/config.toml` or `~/.config/pmc-tool/config.toml`.

## Quick Start
$$\color{#EAB308}Try \space \color{#CA8A04}Search$$

```bash
pmc search "single cell RNA sequencing" --limit 5 --format text    # search the literature

pmc fetch --pmid 35092342 --format text    # fetch one record by PMID

pmc related references 35092342 --source MED --page-size 25 --format text    # follow references
pmc related citations PMC8860882 --source PMC --format json                   # follow citations

pmc export "machine learning" --limit 20 --format bib --output citations.bib    # export citations to BibTeX
```

## Credits

This client is built for Europe PMC and is not affiliated with Europe PMC.

Credit goes to the Europe PMC project and its maintainers for the underlying literature service, identifiers, and API documentation this tool relies on.
