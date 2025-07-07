# Data Sources Guide

This document provides specific notes on each data source supported by the `sciencemapping` library and how to interact with them via `ScienceMapper.fetch_data()`.

## Common Internal Format

Data retrieved from all sources is parsed into a common internal format, which is a list of dictionaries. Each dictionary represents a publication record. Key fields typically include:

*   `title`: (str) Article title.
*   `authors`: (List[str]) List of author names.
*   `year`: (int) Publication year.
*   `journal`: (str, Optional) Name of the journal or publication venue.
*   `doi`: (str, Optional) Digital Object Identifier.
*   `abstract`: (str, Optional) Abstract of the publication.
*   `keywords`: (List[str]) List of keywords or concepts.
*   `document_type`: (str, Optional) Type of document (e.g., "article", "review").
*   `source_type`: (str) Identifier for the original data source (e.g., "pubmed", "wos").
*   Source-specific IDs (e.g., `pubmed_id`, `wos_id`, `scopus_id`, `dimensions_id`, `openalex_id`).
*   Source-specific citation counts (e.g., `times_cited_wos`, `times_cited_openalex`).
*   `cited_references`: (Optional[List[str]]) A list of identifiers (e.g., DOIs, WoS IDs) for documents cited by the record. This field is intended for advanced citation analysis and network building; its population depends on the data source and parser capabilities.
*   `raw_data`: (dict) The original data structure from the source library for more detailed inspection if needed.

The exact availability of these fields can vary by source and the specific record.

## 1. PubMed

*   **Source Name in `fetch_data`**: `"pubmed"`
*   **Library Used**: `pymed`
*   **Parameters**:
    *   `query` (str, **required**): A valid PubMed search query string.
    *   `max_results` (int, optional, default: 100): Maximum number of records to fetch.
    *   `pubmed_email` (str, optional, default in `ScienceMapper`): Your email for NCBI's polite API pool. It's highly recommended to set this either in `ScienceMapper` constructor or ensure the default is acceptable.
*   **Notes**:
    *   Makes live API calls to NCBI Entrez.
    *   The `sciencemapping.data_sources.pubmed` module handles parsing into the common format.

## 2. Web of Science (WoS)

*   **Source Name in `fetch_data`**: `"wos_file"`
*   **Library Used**: `metaknowledge`
*   **Parameters**:
    *   `file_path` (str, **required**): Path to the Web of Science export file. Common formats are plain text (`savedrecs.txt`) or BibTeX. `metaknowledge` attempts to auto-detect the format.
    *   `wos_file_encoding` (str, optional, default: `'utf-8'`): Encoding of the input file. Common alternatives include `'latin-1'` or `'cp1252'`.
*   **Notes**:
    *   This method parses local files exported from the Web of Science interface.
    *   The `sciencemapping.data_sources.wos` module uses `metaknowledge` for parsing and then maps fields to the common internal format.
    *   Ensure your WoS export includes fields like TI, AU, SO, PY, AB, DE, ID, DI, UT, TC for comprehensive parsing.

## 3. Scopus

*   **Source Name in `fetch_data`**: `"scopus_api"`
*   **Library Used**: `pybliometrics`
*   **Parameters**:
    *   `query` (str, **required**): A valid Scopus search query string (e.g., using Scopus advanced search syntax like `TITLE-ABS-KEY(...)`).
    *   `max_results` (int, optional, default: 100): Maximum number of records to aim for.
    *   `scopus_api_key` (str, optional): Your Scopus API key. If not provided, `pybliometrics` will attempt to use its global configuration (e.g., from a `config.ini` file or environment variables).
*   **Notes**:
    *   Requires a Scopus API key from Elsevier. You need to configure `pybliometrics` with this key. See [pybliometrics documentation](https://pybliometrics.readthedocs.io/en/stable/configuration.html).
    *   The `sciencemapping.data_sources.scopus` module handles API interaction and parsing.
    *   *Test Environment Status*: Unit tests for this module have encountered persistent issues related to `pybliometrics`'s behavior in the sandboxed test environment (specifically around error object types and configuration loading). The core logic is implemented, but full test validation is pending.

## 4. Dimensions

*   **Source Name in `fetch_data`**: `"dimensions_api"`
*   **Library Used**: `dimcli`
*   **Parameters**:
    *   `query` (str, **required**): A Dimensions DSL (Domain Specific Language) query string.
    *   `max_results` (int, optional, default: 100): Maximum number of records to retrieve.
    *   `dimensions_dsl_instance` (optional): Allows passing a pre-initialized and authenticated `dimcli.Dsl` object for more control.
*   **Notes**:
    *   Requires access to the Dimensions API, which is a subscription service. Credentials must be configured for `dimcli` to work (e.g., via `dimcli login` or environment variables). See [dimcli documentation](https://dimcli.readthedocs.io/en/latest/gettingstarted.html#authentication).
    *   The `sciencemapping.data_sources.dimensions` module handles API interaction. The structure of the returned data depends heavily on the `return` clause in your DSL query. The parser attempts to map common fields.
    *   *Test Environment Status*: Unit tests for this module could not be run due to `ModuleNotFoundError` for the main `sciencemapping.data_sources.dimensions` module within the test execution context. The code and tests are written but unverified.

## 5. OpenAlex

*   **Source Name in `fetch_data`**: `"openalex_api"`
*   **Library Used**: `openalex` (the official Python client)
*   **Parameters**:
    *   `query` (str, optional): A free-text search query.
    *   `openalex_filter_criteria` (Dict[str, Any], optional): A dictionary of filters to apply (e.g., `{"publication_year": "2023", "authorships.author.id": "A1234567"}`).
    *   Either `query` or `openalex_filter_criteria` (or both) must be provided.
    *   `max_results` (int, optional, default: 25): Maximum number of records to fetch.
    *   `openalex_email` (str, optional, default in `ScienceMapper`): Your email to use the OpenAlex polite API pool, which is recommended for better service.
*   **Notes**:
    *   OpenAlex provides a free and open API.
    *   The `sciencemapping.data_sources.openalex` module uses the `openalex` library.
    *   *Test Environment Status*: Unit tests for this module could not be run due to `ModuleNotFoundError` for the main `sciencemapping.data_sources.openalex` module within the test execution context. The code and tests are written but unverified.
    *   The parser handles common fields like `display_name` (for title), `authorships`, `host_venue`, `concepts` (as keywords), and `cited_by_count`. Abstract parsing from `abstract_inverted_index` is noted as a more complex task not fully implemented in the basic parser.
