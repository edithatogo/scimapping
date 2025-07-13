# Usage Guide

This guide provides detailed information on how to use the `sciencemapping` library, focusing on the `ScienceMapper` core API.

## `ScienceMapper` Class

The primary entry point for using the library is the `ScienceMapper` class from `sciencemapping.core`.

```python
from sciencemapping.core import ScienceMapper

# Initialize the mapper
# It's recommended to provide your email for API polite pools
mapper = ScienceMapper(
    pubmed_email="your_email@example.com",
    openalex_email="your_email@example.com"
    # crossref_mailto will also be available after update
)
```

The `ScienceMapper` orchestrates two main operations: fetching data and analyzing it.

## 1. Fetching Data

The `fetch_data()` method is used to retrieve records from various supported data sources. Fetched records are stored internally within the `ScienceMapper` instance, replacing any previously fetched data.

```python
mapper.fetch_data(
    source: DataSourceName,
    query: Optional[str] = None,
    file_path: Optional[str] = None,
    max_results: int = 100,
    # ... other source-specific arguments
)
```

The method returns the `ScienceMapper` instance itself, allowing for chained calls.

### Supported Data Sources (`DataSourceName`)

*   `"pubmed"`: Fetches data from PubMed using its API.
    *   Requires `query` (PubMed search string).
    *   `max_results` controls the number of records.
    *   Uses the `pubmed_email` provided during `ScienceMapper` initialization.
    ```python
    mapper.fetch_data(source="pubmed", query="bibliometrics AND \"open science\"", max_results=50)
    ```

*   `"wos_file"`: Parses Web of Science export files (e.g., plain text, BibTeX).
    *   Requires `file_path` (path to the WoS file).
    *   `wos_file_encoding` (default: `'utf-8'`) can be specified.
    ```python
    mapper.fetch_data(source="wos_file", file_path="data/wos_exports.txt", wos_file_encoding="latin-1")
    ```

*   `"scopus_api"`: Fetches data from Scopus API.
    *   Requires `query` (Scopus search string).
    *   `max_results` controls the number of records.
    *   `scopus_api_key` (optional): Can be provided directly if not configured globally for `pybliometrics`.
    *   *Note*: Test environment has shown issues with `pybliometrics`.
    ```python
    mapper.fetch_data(source="scopus_api", query='TITLE-ABS-KEY("science mapping")', scopus_api_key="YOUR_SCOPUS_KEY")
    ```

*   `"dimensions_api"`: Fetches data from Dimensions API using its DSL.
    *   Requires `query` (Dimensions DSL query string).
    *   `max_results` controls the number of records.
    *   `dimensions_dsl_instance` (optional): Allows passing a pre-configured `dimcli.Dsl` instance.
    *   *Note*: Test environment has shown issues with `dimcli` test execution.
    ```python
    dsl_query = 'search publications where title ~ "bibliometric analysis" return publications[basics]'
    mapper.fetch_data(source="dimensions_api", query=dsl_query, max_results=20)
    ```

*   `"openalex_api"`: Fetches data from OpenAlex API.
    *   Can use `query` (free-text search) and/or `openalex_filter_criteria` (dictionary of filters).
    *   `max_results` controls the number of records.
    *   Uses the `openalex_email` provided during `ScienceMapper` initialization.
    *   *Note*: Test environment has shown issues with test execution.
    ```python
    mapper.fetch_data(source="openalex_api", query="network analysis", openalex_filter_criteria={"publication_year": "2023"}, max_results=30)
    ```

### Accessing Fetched Records

After fetching, records can be accessed using:
```python
records = mapper.get_records()
print(f"Fetched {len(records)} records.")
for record in records:
    print(record.get('title'))
```

## 2. Analyzing Data

The `analyze()` method performs bibliometric analyses on the currently loaded set of records. It uses the `PybibxAnalyzer` internally, which currently contains placeholder logic.

```python
mapper.analyze(
    analysis_type: AnalysisTypeName,
    # ... analysis-specific arguments
)
```

### Supported Analysis Types (`AnalysisTypeName`)

*   `"co_authorship"`: Generates a co-authorship network.
    *   `coauth_threshold` (int, default: 1): Minimum collaborations for an edge/author (placeholder behavior).
    ```python
    coauth_net = mapper.analyze("co_authorship", coauth_threshold=2)
    if coauth_net:
        print(f"Nodes: {len(coauth_net['nodes'])}, Edges: {len(coauth_net['edges'])}")
    ```

*   `"keyword_cooccurrence"`: Generates a keyword co-occurrence network.
    *   `keyword_threshold` (int, default: 1): Minimum co-occurrences for an edge (placeholder behavior).
    ```python
    kw_net = mapper.analyze("keyword_cooccurrence", keyword_threshold=3)
    if kw_net:
        print(f"Nodes: {len(kw_net['nodes'])}, Edges: {len(kw_net['edges'])}")
    ```

*   `"citation_analysis"`: Performs basic citation analysis (e.g., lists most cited papers based on available data).
    ```python
    citation_stats = mapper.analyze("citation_analysis")
    if citation_stats:
        print(citation_stats.get("most_cited_papers"))
    ```

### Conceptual Gender and Funding Analysis

While not directly invoked via `mapper.analyze()` with a specific `AnalysisTypeName` yet, the library includes conceptual modules:
*   `sciencemapping.analysis.gender_analyzer.GenderAnalyzer`
*   `sciencemapping.analysis.funding_analyzer.FundingAnalyzer`

These can be used by passing the records from `mapper.get_records()`:
```python
from sciencemapping.analysis.gender_analyzer import GenderAnalyzer
from sciencemapping.analysis.funding_analyzer import FundingAnalyzer

current_records = mapper.get_records()
if current_records:
    gender_analyzer = GenderAnalyzer(current_records)
    gender_stats = gender_analyzer.get_gender_distribution_stats() # Uses placeholder logic
    print("Gender Stats (placeholder):", gender_stats)

    funding_analyzer = FundingAnalyzer(current_records)
    funding_summary = funding_analyzer.get_funding_summary_stats() # Uses placeholder logic
    print("Funding Summary (placeholder):", funding_summary)
```
Refer to `docs/analysis_modules.md` for more on their placeholder nature.

## 3. Enriching Data with CrossRef Funding Information

After fetching records from a primary source, you can enrich them with funding information from CrossRef using their DOIs. This feature uses the `habanero` library to interact with the CrossRef REST API.

```python
# Assuming 'mapper' is an initialized ScienceMapper instance with records loaded
# For example, after:
# mapper.fetch_data(source="pubmed", query="your query", max_results=10)

if mapper.get_records():
    print(f"Records before CrossRef enrichment: {len(mapper.get_records())}")
    # The mailto email used will be the one set during ScienceMapper initialization
    # (self.crossref_mailto).
    mapper.enrich_with_crossref()

    print(f"Records after CrossRef enrichment: {len(mapper.get_records())}")
    for record in mapper.get_records():
        if "crossref_funding" in record:
            print(f"Title: {record.get('title')}")
            print(f"  CrossRef Funding: {record['crossref_funding']}")
```

### `enrich_with_crossref()` Method

*   **Purpose**: Iterates through currently loaded records in the `ScienceMapper` instance. For each record with a DOI, it queries the CrossRef API to retrieve metadata and extracts funding information.
*   **Data Integration**: Funding information retrieved from CrossRef is merged into the existing `funding_entries` list within each record. If a record does not have a `funding_entries` list, it will be created.
    *   Each funding item from CrossRef is added as a new dictionary to the `funding_entries` list.
    *   These new entries will have their `source_of_info` field set to `"crossref_api"`.
    *   The structure of each added entry follows the standard `funding_entries` item format:
        ```
        {
            "funder_name": "Funder Name from CrossRef",
            "funder_crossref_id": "10.13039/xxxx" (Funder Registry ID, if available),
            "grant_ids": ["Grant ID1", "Grant ID2"],
            "source_of_info": "crossref_api"
            // other fields like funder_ror_id might be absent if not in CrossRef data
        }
        ```
    *   A basic de-duplication check is performed: if an identical funder name and set of grant IDs already exists in `funding_entries`, the CrossRef entry might update the existing one with a `funder_crossref_id` rather than adding a full duplicate.
*   **Dependencies**: Requires the `habanero` library to be installed (`pip install habanero`).
*   **API Etiquette**: It's highly recommended to provide a `mailto` email address when initializing `ScienceMapper` (via the `crossref_mailto` parameter). This email is used for CrossRef's polite API pool.
    ```python
    mapper = ScienceMapper(
        # ... other emails ...
        crossref_mailto="your_polite_email@example.com"
    )
    ```
*   **Error Handling**: If `habanero` is not installed, a warning will be issued, and enrichment will be skipped. Errors during API calls to CrossRef are also handled with warnings, and enrichment for the problematic DOIs/batches may be skipped.

## Error Handling

*   `fetch_data()` will raise a `ValueError` if an unknown `source` is provided or if required parameters for a source (like `query` for PubMed or `file_path` for WoS) are missing.
*   `analyze()` will print a warning and return `None` if no records have been loaded. It will raise a `ValueError` for an unknown `analysis_type`.
*   `enrich_with_crossref()` will print warnings if `habanero` is missing or if CrossRef API calls fail.

## Chaining Operations

Methods `fetch_data()` and `enrich_with_crossref()` return the `ScienceMapper` instance, allowing for chaining:
```python
analysis_results = (mapper.fetch_data(source="pubmed", query="test", max_results=5)
                          .enrich_with_crossref()
                          .analyze("co_authorship"))
```
This makes `ScienceMapper().fetch_data(...)` return the instance, which is then enriched, and finally, the `analyze` method is called on the enriched records.
