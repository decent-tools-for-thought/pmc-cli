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
- `pmc articles search`: search Europe PMC with free text or raw query syntax, with result-type, synonym-expansion, cursor-mark, page-size, sort, and format controls.
- `pmc articles search-post`: the same search over `POST`, for queries too long for a URL.
- `pmc articles fetch <source> <id>`: fetch a single record; `--doi` resolves a DOI instead.
- `pmc articles citations` / `pmc articles references`: traverse related records.
- `pmc articles fields`, `pmc articles profile`: inspect searchable fields and result profiles.

$$\color{#EAB308}Full \space Text \space and \space \color{#CA8A04}Supplementary \space Files$$
- `pmc articles fulltext-xml <pmcid>`: fetch open-access full text as XML; `--doi` accepted.
- `pmc articles book-xml <id>`: fetch bookshelf XML by NBK or PM id; `--doi` accepted.
- `pmc articles supplementary-files <pmcid>`: download supplementary files as a zip; `--doi` accepted.
- `pmc articles data-links`, `database-links`, `labs-links`: follow links to data deposited in external repositories.

$$\color{#EAB308}Grant \space \color{#CA8A04}Search$$
- `pmc grants search`: search grant data by PI, agency, grant ID, title, abstract, affiliation, active date, and category, using the GRIST query syntax.

$$\color{#EAB308}Endpoint \space \color{#CA8A04}Docs$$
- `pmc doc articles <endpoint>`: print the parameters and notes for one Europe PMC endpoint.
- `pmc doc grants search`: the same for the grants surface.

$$\color{#EAB308}Saved \space \color{#CA8A04}Defaults$$
- `pmc config show`: print the saved config.
- `pmc config reset`: restore defaults.
- `pmc config set email`: save an email value for the `User-Agent`.
- `pmc config set base-url` and `default-result-type`: tune default request behavior.

## Configuration
$$\color{#EAB308}Save \space \color{#CA8A04}Defaults$$

Europe PMC does not require an API key for the endpoints this CLI uses. The main optional setting is an email address added to the `User-Agent` string:

```bash
pmc config set email your-email@example.com    # add contact info to the User-Agent
pmc config show                                # inspect saved defaults
```

Config is stored at `$XDG_CONFIG_HOME/pmc-cli/config.toml` or `~/.config/pmc-cli/config.toml`.

## Quick Start
$$\color{#EAB308}Try \space \color{#CA8A04}Search$$

```bash
pmc articles search "single cell RNA sequencing" --page-size 5    # search the literature

pmc articles fetch MED 35092342                      # fetch one record by source and id
pmc articles fetch --doi 10.1111/brv.12453           # or resolve a DOI

pmc articles references MED 35092342 --page-size 25    # follow references
pmc articles citations PMC PMC8860882                  # follow citations
```

$$\color{#EAB308}Download \space \color{#CA8A04}Supplementary \space Files$$

Supplementary files are served as a zip, for **open-access PMC records only**:

```bash
pmc articles supplementary-files PMC6378602 --output suppl.zip    # by PMCID
pmc articles supplementary-files --doi 10.1111/brv.12453 --output suppl.zip    # by DOI
```

By default the zip also contains the article's inline figure images. Pass
`--include-inline-image no` to get only genuine supplementary files — for articles whose
only attachments are inline figures this returns a 404, which is a meaningful "no
supplements" answer rather than an error to work around:

```bash
pmc articles supplementary-files PMC6378602 --include-inline-image no --output suppl.zip
```

Requests for a non-open-access article fail with a non-zero exit status and leave no
output file behind, so a batch download will not silently fill up with error stubs.
Find candidates with the `HAS_SUPPL` and `OPEN_ACCESS` filters:

```bash
pmc articles search "OPEN_ACCESS:y AND HAS_SUPPL:Y AND HAS_DOI:Y" --page-size 10
```

Full text for open-access records comes back as JATS XML:

```bash
pmc articles fulltext-xml PMC6378602 --output article.xml
pmc articles fulltext-xml --doi 10.1111/brv.12453 --output article.xml
```

## Credits

This client is built for Europe PMC and is not affiliated with Europe PMC.

Credit goes to the Europe PMC project and its maintainers for the underlying literature service, identifiers, and API documentation this tool relies on.
