# PMC Tool - Europe PMC CLI

Command-line access to the Europe PMC REST API with support for search, fetch, related-record traversal, field discovery, preprint workflows, and citation export.

## Install

```bash
uv tool install .
```

For local execution without installation:

```bash
uv sync
uv run pmc --help
```

Tagged GitHub releases publish Python distribution artifacts built from the tagged commit.

## Commands

### Search

```bash
pmc search "single cell RNA sequencing" \
  --title human \
  --author Smith \
  --from-date 2024-01-01 \
  --to-date 2024-12-31 \
  --has-fulltext \
  --open-access-only \
  --fields doi,pmid \
  --format json
```

Supported search features:

- raw or structured query mode
- fielded search terms: `--title`, `--abstract`, `--author`
- filters: `--category`, `--from-date`, `--to-date`, `--source`
- availability filters: `--has-fulltext`, `--no-fulltext`, `--open-access-only`
- result controls: `--result-type idlist|lite|core`, `--page-size`, `--cursor-mark`, `--limit`
- API controls: `--fields`, `--synonyms`, `--no-synonyms`, `--sort`

### Fetch

```bash
pmc fetch --pmid 35092342 --include-references --include-citations --format json
pmc fetch --doi 10.1002/pbc.29588 --include-author-affiliations
```

Supported identifiers:

- positional identifier with auto-detection
- `--pmid`
- `--pmcid`
- `--ppr`
- `--doi`

### Related Records

```bash
pmc related references 35092342 --source MED --page-size 25 --format text
pmc related citations PMC8860882 --source PMC --format json
```

### Fields

```bash
pmc fields --format text
```

Lists the searchable Europe PMC fields from the live `/fields` endpoint.

### Preprints

```bash
pmc preprints search "single cell" --limit 20
pmc preprints by-category review --from-date 2024-01-01 --limit 20
pmc preprints by-date-range 2024-01-01 2024-01-31 --format json
pmc preprints stats
```

`preprints search` is the normal search command with `SRC:PPR` enforced.

### Export

```bash
pmc export "machine learning" --preprints-only --limit 20 --format bib --output citations.bib
pmc export "single cell" --format ris --output citations.ris
pmc export "cancer" --format csl-json --output citations.json
```

Supported export formats:

- `jsonl`
- `bib`
- `ris`
- `csl-json`

### Grants

```bash
pmc grants search malaria --limit 20 --format json
pmc grants search --agency "Wellcome Trust" --pi smith --active-date 2010 --result-type core
pmc grants search 'ga:"Wellcome Trust" pi:smith' --raw-query --result-type core
pmc grants fetch 081052 --format json
```

Supported grants features:

- `grants search <query>` against the Europe PMC Grist API
- `grants fetch <grant-id>` via `gid:<id>` lookup
- helper flags on top of Grist syntax: `--pi`, `--agency`, `--grant-id`, `--title`, `--abstract`, `--affiliation`, `--active-date`, `--category`, `--pi-id`, `--epmc-funders`
- `--raw-query` passthrough for native Grist queries
- `--result-type lite|core`
- page-based traversal with `--page`
- normalized grant envelopes including PI, funder, institution, dates, and amount when present

### Config

```bash
pmc config show
pmc config set email your-email@example.com
pmc config set default-result-type core
pmc config set default-page-size 1000
pmc config set synonym-expansion true
```

## Output

The CLI normalizes Europe PMC responses into a stable JSON shape for search and fetch operations, while relation and field commands expose structured command-specific payloads.

## Coverage

Implemented Europe PMC article-service coverage in this tool:

- `/search`
- `/article/{source}/{id}`
- `/{source}/{id}/references/{page}/{pageSize}/json`
- `/{source}/{id}/citations/{page}/{pageSize}/json`
- `/fields`

Implemented Europe PMC grants coverage in this tool:

- `https://www.ebi.ac.uk/europepmc/GristAPI/rest/get/query={query}`

This tool does not yet implement other Europe PMC APIs such as annotations, SOAP, OAI, or bulk-download workflows.
