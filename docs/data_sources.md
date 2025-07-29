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
*   `keywords`: (List[str]) A sorted list of unique, lowercased, and stripped keywords or concepts associated with the work. Populated by combining and cleaning relevant fields from the source data (e.g., author keywords, index terms, concepts).
*   `document_type`: (str, Optional) Type of document (e.g., "article", "review").
*   `source_type`: (str) Identifier for the original data source (e.g., "pubmed", "wos").
*   Source-specific IDs (e.g., `pubmed_id`, `wos_id`, `scopus_id`, `dimensions_id`, `openalex_id`).
*   Source-specific citation counts (e.g., `times_cited_wos`, `times_cited_openalex`, `times_cited_google_scholar`).
*   `cited_references`: (Optional[List[str]]) A list of identifiers for documents cited *by* the current record. The content and availability of these identifiers vary by data source:
    *   **Preferred Identifier**: Parsers prioritize extracting Digital Object Identifiers (DOIs) for cited references when the source provides them directly or they can be reliably parsed from reference strings.
    *   **Fallback Identifiers**: If a DOI is not available for a cited reference, parsers attempt to extract a source-specific identifier. Examples include:
        *   PubMed: PubMed IDs (PMIDs).
        *   Web of Science: WoS Accession Numbers (e.g., `WOS:000...`).
        *   Scopus: Scopus EIDs.
        *   Dimensions: Dimensions Publication IDs (e.g., `pub.123...`).
        *   OpenAlex: OpenAlex Work IDs (e.g., `W123...`).
    *   **Format**: The field stores a sorted list of unique string identifiers.
    *   **Availability**: Some data sources (e.g., Google Scholar) do not provide lists of cited references, in which case this field will be `None`. For other sources, it depends on the data returned by their APIs or included in their export files (e.g., PubMed requires `references_loaded`; Scopus requires fetching full details).
*   `funding_entries`: (Optional[List[Dict[str, Any]]]) A list of dictionaries, each representing a distinct funding acknowledgement. Standard keys within each dictionary include:
    *   `funder_name` (Optional[str]): The name of the funding organization. Parsers attempt to extract the most complete name available.
    *   `grant_ids` (Optional[List[str]]): A list of grant identification codes or numbers.
    *   `funder_ror_id` (Optional[str]): The ROR (Research Organization Registry) ID of the funder, if available.
    *   `funder_crossref_id` (Optional[str]): The CrossRef Funder ID (a DOI like "10.13039/...") for the funder, if available.
    *   `dimensions_funder_id` (Optional[str]): The Dimensions Funder ID, if data is from Dimensions.
    *   `openalex_funder_id` (Optional[str]): The OpenAlex Funder ID (e.g., "F123..."), if data is from OpenAlex.
    *   `raw_funding_text` (Optional[str]): The original, unprocessed funding string from the source, if applicable (e.g., from PubMed GR tags or WoS FU/FX fields).
    *   `source_of_info` (str): Indicates the origin of this specific funding entry. Examples:
        *   `"pubmed_GR_tag"`: From PubMed's grant information.
        *   `"wos_FU_field"`: From Web of Science 'FU' (Funding Agency and Grant Number) field.
        *   `"wos_FX_field_as_primary"`: From Web of Science 'FX' (Funding Text) field, used when FU was empty.
        *   `"scopus_api_structured_funding"`: From structured funding data via Scopus API.
        *   `"dimensions_api_funders_field"`: From the 'funders' block in Dimensions API results.
        *   `"dimensions_api_grant_ids_field"`: From the top-level 'supporting_grant_ids' in Dimensions API results.
        *   `"openalex_api_funders"`: From the 'funders' block in OpenAlex API results.
        *   `"crossref_api"`: For a new funding entry added entirely from CrossRef enrichment.
        *   `"original_source; crossref_api_augmentation"`: If an existing entry (e.g., from `pubmed_GR_tag`) was augmented with details (like a ROR ID or additional grant IDs) from CrossRef.
    This field is populated by data source parsers and can be further augmented by the CrossRef enrichment utility, which attempts to merge data intelligently based on funder identifiers and names.
*   `acknowledgements_text` / `acknowledgements_text_fx` / `acknowledgements_text_scopus_funding`: (Optional[str]) Raw acknowledgement or funding text fields from the source, used by `FundingAnalyzer` for NLP if `funding_entries` is sparse.
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
    *   **Keyword Data**: Populated from the `keywords` list provided by `pymed`. The list is normalized (lowercased, stripped, unique, sorted).
    *   **Funding Data**: Parses MEDLINE `GR` tags. Entries in `funding_entries` will have `source_of_info: "pubmed_GR_tag"`, `raw_funding_text` (the original GR string), and parsed `funder_name` and `grant_ids` based on the GR string structure.
    *   **Cited References**: If available in the PubMed data (`references_loaded` is true), `pymed` provides a list of cited PubMed IDs, which are stored in the `cited_references` field.

## 2. Web of Science (WoS)

*   **Source Name in `fetch_data`**: `"wos_file"`
*   **Library Used**: `metaknowledge`
*   **Parameters**:
    *   `file_path` (str, **required**): Path to the Web of Science export file. Common formats are plain text (`savedrecs.txt`) or BibTeX. `metaknowledge` attempts to auto-detect the format.
    *   `wos_file_encoding` (str, optional, default: `'utf-8'`): Encoding of the input file. Common alternatives include `'latin-1'` or `'cp1252'`.
*   **Notes**:
    *   This method parses local files exported from the Web of Science interface.
    *   The `sciencemapping.data_sources.wos` module uses `metaknowledge` for parsing and then maps fields to the common internal format.
    *   Ensure your WoS export includes fields like TI, AU, SO, PY, AB, DE, ID, DI, UT, TC, FU, FX for comprehensive parsing.
    *   **Keyword Data**: Populated by merging the `DE` (Author Keywords) and `ID` (Keywords Plus) fields from the export file. The combined list is normalized.
    *   **Funding Data**: Parses the `FU` (Funding Agency and Grant Number) field and, if `FU` is empty, the `FX` (Funding Text) field. Entries from `FU` have `source_of_info: "wos_FU_field"`, `raw_funding_text`, and parsed `funder_name` and `grant_ids`. Entries from `FX` (used as primary) have `source_of_info: "wos_FX_field_as_primary"` and `raw_funding_text`. The full `FX` text is also stored in `acknowledgements_text_fx`.
    *   **Cited References**: Parses the `CR` (Cited References) field from WoS export files. For each cited reference string, it first attempts to extract a DOI using regular expressions. If a DOI is not found, it then attempts to extract a WoS Accession Number (e.g., `WOS:000...`). Extracted identifiers (preferring DOIs) are cleaned, de-duplicated, sorted, and stored in the `cited_references` list.

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
    *   **Keyword Data**: If fetching full details, keywords are populated by merging the `authkeywords` and `idxterms` fields. For basic search results, only `authkeywords` (from the pipe-separated string) are used. The combined list is normalized.
    *   **Funding Data**: Extracts from the structured `funding` attribute of `pybliometrics.scopus.AbstractRetrieval` objects (when full details are fetched). Entries in `funding_entries` will have `source_of_info: "scopus_api_structured_funding"`, and include `funder_name` (prioritizing full agency name over acronym) and `grant_ids` (handling semicolon-separated IDs). The full `funding_text` from the API is stored in `acknowledgements_text_scopus`. Basic search results (without detail fetching) will have `funding_entries` as `None`.
    *   **Cited References**: Extracted via `fetch_scopus_abstract_details` from the `references` attribute of the `AbstractRetrieval` object. It prioritizes DOIs if available for each reference, otherwise uses the Scopus EID. These are stored in the `cited_references` list. Basic search results initialize `cited_references` to `None`.
    *   *Test Environment Status*: Unit tests for this module have encountered persistent issues related to `pybliometrics`'s behavior in the sandboxed test environment. The core logic is implemented, but full test validation is pending.

## 4. Dimensions

*   **Source Name in `fetch_data`**: `"dimensions_api"`
*   **Library Used**: `dimcli`
*   **Parameters**:
    *   `query` (str, **required**): A Dimensions DSL (Domain Specific Language) query string.
    *   `max_results` (int, optional, default: 100): Maximum number of records to retrieve.
    *   `dimensions_dsl_instance` (optional): Allows passing a pre-initialized and authenticated `dimcli.Dsl` object for more control.
*   **Notes**:
    *   Requires access to the Dimensions API, which is a subscription service. Credentials must be configured for `dimcli` to work (e.g., via `dimcli login` or environment variables). See [dimcli documentation](https://dimcli.readthedocs.io/en/latest/gettingstarted.html#authentication).
    *   The `sciencemapping.data_sources.dimensions` module handles API interaction. The structure of the returned data depends heavily on the `return` clause in your DSL query.
    *   **Keyword Data**: Populated by merging the `keywords` and `concepts` fields from the API response. The combined list is normalized.
    *   **Funding Data**: Parses the `funders` list and `supporting_grant_ids` from the API response. Entries from the `funders` list populate `funder_name` (prioritizing name/organization over acronym), `grant_ids` (from `grant_ids` and `grants` sub-fields), `dimensions_funder_id` (from the funder's `id` field), and `funder_ror_id`. These entries have `source_of_info: "dimensions_api_funders_field"`. Grant IDs from the top-level `supporting_grant_ids` field that are not associated with a specific funder in the `funders` block create separate entries with `grant_ids` and `source_of_info: "dimensions_api_grant_ids_field"`.
    *   **Cited References**: If the Dimensions DSL query requests `references` for a publication, the API typically returns a list of Dimensions publication IDs (either as flat list or list of dicts with an `id` key). These IDs are extracted and stored in the `cited_references` field.
    *   *Test Environment Status*: Unit tests for this module could not be run due to `ModuleNotFoundError`. Code and tests are written but unverified.

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
    *   **Keyword Data**: Populated from the `display_name` of each item in the `concepts` list from the API response. The list is normalized.
    *   **Funding Data**: Processes the `funders` list from the API response. Entries in `funding_entries` will have `source_of_info: "openalex_api_funders"` and can include `funder_name` (from `display_name`), `grant_ids` (from `award_id` in the `grants` sub-list), `funder_ror_id` (from `ror`), `openalex_funder_id` (extracted from the funder's `id` URL, e.g., "F123..."), and `funder_crossref_id` (from the funder's `doi` field).
    *   **Cited References**: Parses the `referenced_works` list (which contains OpenAlex work URLs) from the API response. It extracts the OpenAlex Work ID (e.g., "W123...") from each URL (case-insensitive for the "W") and stores these in the `cited_references` field.
    *   *Test Environment Status*: Unit tests for this module could not be run due to `ModuleNotFoundError`. Code and tests are written but unverified.
    *   The parser handles common fields like `display_name` (for title), `authorships`, `host_venue`, and `cited_by_count`. Abstracts are reconstructed from the `abstract_inverted_index` field provided by the API; if this field is missing or cannot be parsed, the `abstract` in the record will be `None`.

## 6. Google Scholar

*   **Source Name in `fetch_data`**: `"google_scholar"`
*   **Library Used**: `scholarly`
*   **Parameters**:
    *   `query` (str, **required**): A search query string for Google Scholar.
    *   `max_results` (int, optional, default: 20): Maximum number of publications to retrieve. Note that `scholarly` fetches results in batches, and this limits the total.
*   **Notes**:
    *   **Important Caveats**:
        *   Google Scholar does **not** have an official API. `scholarly` works by scraping the Google Scholar website.
        *   This is **unreliable** and prone to breaking if Google changes its website structure.
        *   Excessive use can lead to your IP address being temporarily or permanently **blocked** by Google. Use with extreme caution and at your own risk.
        *   Data quality and field availability can be inconsistent.
    *   The `sciencemapping.data_sources.google_scholar` module uses `scholarly` for fetching and parsing.
    *   **Keyword Data**: Google Scholar does not provide a reliable keyword field. This is initialized to an empty list.
    *   **Funding Data**: Google Scholar does not provide structured funding information. The `funding_entries` field in records from this source will be initialized to `None`.
    *   **Cited References**: Google Scholar does not provide a list of cited references for each paper. The `cited_references` field will be `None`.
    *   **Citation Counts**: The parser extracts the "Cited by" count provided by Google Scholar and stores it as `times_cited_google_scholar`.
    *   Fields parsed include title, authors (as a string), publication venue, year, and number of citations. Abstract and keywords are often not available or reliably parsed.
    *   *Test Environment Status*: Unit tests for this module are written and expected to pass, but depend on the external `scholarly` library's behavior.
