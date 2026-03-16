# PMC (Europe PMC) Tool - Project Outline

## Overview
Command-line interface for the Europe PMC REST API, optimized for preprint discovery and fielded literature search. Europe PMC provides the closest experience to PubMed's E-utilities for preprint search, with explicit preprint filtering and fielded queries.

## Core Strengths
- Preprint-specific search with `SRC:PPR` filter
- True fielded search operators: `TITLE:`, `ABSTRACT:`, `AUTH:`
- Cursor-based deep pagination for large result sets
- Stable RESTful API under EBI infrastructure
- Explicit preprint ingestion pipeline and daily updates

## API Characteristics

### Base Endpoint
- REST API: `https://www.ebi.ac.uk/europepmc/webservices/rest/search`

### Query Language
- Solr-powered search platform
- Native query syntax with field operators
- Boolean combinations supported
- Preprint filtering via `SRC:PPR`
- Synonym expansion via `synonym` parameter

### Pagination Model
- Cursor-based pagination using `cursorMark` and `pageSize`
- Recommended for deep pagination: cursorMark + pageSize=1000
- 10 requests/sec throttling, 500 requests/min limits
- More data-efficient than offset-based pagination

### Rate Limiting
- Throttling: 10 requests/sec, 500 requests/min
- No explicit authentication required
- Uses EBI infrastructure standards

## Command Surface

### Core Commands

#### `search` - Primary discovery interface
```bash
pmc search <query> [options]
```

**Native Mode (passthrough):**
- `--raw-query <string>` - Pass through full Europe PMC query syntax
- Supports complex boolean with all Solr operators
- Direct access to `SRC:PPR`, `TITLE:`, `ABSTRACT:`, `AUTH:` etc.

**Opinionated Mode (flag-based):**
- `--title <text>` - Search in title field
- `--abstract <text>` - Search in abstract field
- `--author <name>` - Search by author name
- `--category <code>` - Filter by subject category
- `--preprints-only, --no-preprints` - Explicit preprint control
- `--from-date <YYYY-MM-DD>` - Lower bound filter
- `--to-date <YYYY-MM-DD>` - Upper bound filter
- `--has-fulltext/--no-fulltext` - Filter by full-text availability
- `--open-access-only` - Filter by OA status

**Common Options:**
- `--page-size <int>` - Default 1000 for cursor pagination
- `--cursor-mark <string>` - Resume pagination cursor
- `--result-type <lite|core>` - Payload depth selection
- `--format <jsonl|json|text>` - Output format
- `--limit <int>` - Maximum number of results
- `--synonyms/--no-synonyms` - MeSH/synonym expansion
- `--fields <list>` - Specific fields to retrieve

#### `fetch` - Retrieve full records
```bash
pmc fetch <source_id> [options]
```

**ID Types:**
- `--pmid <id>` - PubMed ID
- `--pmcid <id>` - PubMed Central ID
- `--ppr <id>` - Preprint specific ID (PMR format)
- `--doi <id>` - DOI resolution

**Options:**
- `--result-type <lite|core>`
- `--format <json|text>`
- `--include-references` - Fetch citation metadata
- `--include-author-affiliations` - Expanded author data
- `--fulltext/--no-fulltext` - Include full text when available

#### `preprints` - Preprint-specific wrapper
```bash
pmc preprints <subcommand> [options]
```

**Subcommands:**
- `search <query>` - Same as search but forces `SRC:PPR`
- `by-category <category>` - Browse preprint collections
- `by-date-range <from> <to>` - Harvest preprint metadata
- `stats` - Preprint ingestion statistics (uses /sum endpoints)

#### `export` - Metadata export
```bash
pmc export <query> [options]
```

**Options:**
- `--format <bib|ris|csl-json|jsonl>`
- `--style <citation-style>` - CSL style for formatted output
- `--limit <int>`
- `--output <file>`

#### `config` - Configuration management
```bash
pmc config <subcommand>
```

**Subcommands:**
- `set email <address>` - Set contact email for EBI usage tracking
- `set default-result-type <lite|core>`
- `show` - Display current configuration
- `reset` - Restore defaults

## Output Schema

### Record Envelope (stable format)
```json
{
  "backend": "europepmc",
  "id": {
    "source": "pmc" | "ppr" | "pubmed",
    "pmid": "string | null",
    "pmcid": "string | null",
    "pprId": "string | null",
    "doi": "string | null"
  },
  "title": "string",
  "authors": [
    {
      "firstName": "string",
      "lastName": "string",
      "initials": "string",
      "affiliation": "string | null"
    }
  ],
  "publishedDate": "YYYY-MM-DD | null",
  "abstract": "string | null",
  "url": "string",
  "source": "string",
  "isOpenAccess": boolean,
  "hasFullText": boolean,
  "category": "string | null",
  "rights": {
    "license": "string | null",
    "embargoDate": "string | null"
  },
  "provenance": {
    "retrievedAt": "ISO8601 timestamp",
    "resultType": "lite | core",
    "srcFilter": "PPR | MED | ..."
  }
}
```

### Search Results (JSONL)
- One line per hit
- Same record envelope structure
- Minimal payload by default (lite result-type)
- Pagination metadata in header line (for cursor continuation)

## Configuration

### Global Config (~/.config/pmc-tool/config.toml)
```toml
[api]
base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"
default_result_type = "lite"
email = "user@example.com"  # For EBI goodwill tracking

[search]
default_page_size = 1000
default_preprints_only = false
synonym_expansion = true

[output]
default_format = "jsonl"
include_references = false
```

### Rate Limiting Strategy
- Request pool with max 10 req/s concurrency
- Built-in exponential backoff on HTTP 503
- Cursor checkpointing for resumable large searches
- ETag/Last-Modified caching for repeat fetches

## Key Constraint: Preprint Versioning
- Europe PMC only indexes latest preprint version when multiple exist
- Some DOI versioning may not be captured in version chains
- CLI should expose `--include-versions` flag where backend supports it
- Output provenance should clearly indicate version coverage

## Operational Notes

### Strengths for BioRxiv Discovery
1. Explicit preprint pipeline with daily ingest from Crossref
2. Solr query language gives PubMed-style fielded search
3. Crossref integration means broad bioRxiv coverage
4. EBI infrastructure provides reliability and stability

### Known Limitations
1. Versioning: Only latest preprint version searchable
2. Preprint coverage limited to ingested preprint platforms (32 as of April 2024)
3. Rate-limited, though generous (10 rps)
4. Full-text availability depends on OA policy and PMC deposit

### Design Philosophy
- Europe PMC is "the cleanest" preprint discovery backend
- Prioritize `SRC:PPR` as first-class capability
- Maintain dual interface: native query language + flag-based convenience
- Cursor pagination is the canonical deep-paginate pattern
- EMBL-EBI training materials guide supported query syntax

## Testing Strategy

### Unit Tests
- Query builder for flag-based → Europe PMC syntax translation
- Record envelope normalization logic
- Pagination cursor management
- Rate limiter backoff behavior

### Integration Tests
- Live API calls against Europe PMC test endpoints
- Preprint filter validation (`SRC:PPR`)
- Fielded query accuracy (`TITLE:`, `ABSTRACT:`, `AUTH:`)
- Cursor pagination across large result sets

### Contract Tests
- Verify output schema stability
- Test that provenance metadata is always present
- Validate retry/backoff under throttling

## Future Extensions (Non-Initial)

### Advanced Features
- `pmc harvest` - Bulk export for offline indexing
- `pmc similar` - Related papers via Europe PMC link endpoints
- `pmc mesh` - MeSH term exploration
- `pmc citations` - Citation graph via Europe PMC reference links
- `pmc bulk-download` - XML bulk integration support

### Backend Integration
- Direct PMC FTP bulk download access for local indexing
- Europe PMC RESTful GraphQL endpoint (when available)

## Dependencies (Projected)
- CLI framework: `click` or `clap` (language TBD)
- HTTP client: `requests`/`httpx` or similar with connection pooling
- Configuration: `toml` or `JSON` for structured config
- Rate limiting: Custom implementation with token bucket
- Logging: Structured logging (JSON format) for operations