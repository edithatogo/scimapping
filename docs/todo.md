# To-Do List & Future Work

This document outlines known limitations, unimplemented features, and potential areas for future development in the `sciencemapping` library.

## Known Issues & Limitations

1.  **Scopus Module Testing (`pybliometrics`)**:
    *   Unit tests for `sciencemapping.data_sources.scopus` are currently incomplete/failing due to persistent issues with how `pybliometrics.scopus.errors` (and potentially `pybliometrics.scopus.CONFIG`) behaves within the sandboxed test environment. It appears as a `dict` at runtime in critical exception handling blocks, leading to `AttributeError`.
    *   **Action**: Needs deeper investigation into `pybliometrics`'s internal structure or more advanced mocking techniques that don't trigger this behavior. Alternatively, tests might need to be adapted to work with `errors` as a dictionary if that's its consistent state in this environment.

2.  **Dimensions Module Testing (`dimcli`)**:
    *   Unit tests for `sciencemapping.data_sources.dimensions` could not be run due to `ModuleNotFoundError` for the module itself (`sciencemapping.data_sources.dimensions`) during test execution. This points to a Python path or test discovery issue in the sandbox.
    *   **Action**: Resolve test discovery/execution path issues.

3.  **OpenAlex Module Testing (`openalex`)**:
    *   Similar to Dimensions, unit tests for `sciencemapping.data_sources.openalex` could not be run due to `ModuleNotFoundError` for `sciencemapping.data_sources.openalex`.
    *   **Action**: Resolve test discovery/execution path issues.

4.  **`pybibx` Integration**:
    *   The `PybibxAnalyzer` has been updated to conceptually support `pybibx`:
        *   It attempts to initialize `pybibx.Corpus`.
        *   Analysis methods include conceptual calls to `pybibx.analysis` functions.
        *   It falls back to placeholder logic if `pybibx` is unavailable or calls fail.
    *   **Next Steps for Full Integration**:
        *   Successfully install `pybibx` in a target environment.
        *   Verify/correct the assumed `pybibx` API calls and data transformations in `PybibxAnalyzer`.
        *   Implement any necessary field name mapping if the library's common internal format differs significantly from `pybibx`'s expected input for its `Corpus`.
        *   Ensure unit tests for `PybibxAnalyzer` accurately mock the verified `pybibx` API.

5.  **Common Data Format - `cited_references`**:
    *   Conceptually added `cited_references: Optional[List[str]]` to the common internal data format to support advanced citation analyses.
    *   **Action**: Update individual data source parsers (`pubmed.py`, `wos.py`, `scopus.py`, etc.) to populate this field if the source data provides cited reference information.

6.  **Abstract Parsing (OpenAlex)**:
    *   The OpenAlex parser currently notes the presence of `abstract_inverted_index` but does not reconstruct the full abstract.
    *   **Action**: Implement abstract reconstruction if the `openalex` library doesn't provide a direct way or if a more custom approach is needed.

## Planned Features & Enhancements

### Data Sources
1.  **Robust Error Handling**: Further improve error handling for API limits, network issues, and unexpected data formats for all sources.
2.  **Configuration Management**: Implement a more robust way for users to provide API keys and other configurations (e.g., via a config file for the library itself, or environment variables clearly documented).
3.  **Full Text Links/Access**: For sources like PubMed, explore options to link to or (where permissible) fetch full text for more detailed analysis (e.g., for acknowledgements).
4.  **Additional Data Sources**: Consider adding support for:
    *   Google Scholar (requires careful handling due to scraping limitations; `scholarly` library).
    *   CrossRef or Semantic Scholar for more open metadata.
    *   Patent databases.

### Analysis Modules
1.  **Full `pybibx` Integration**: Complete the integration as noted above.
2.  **Gender Analysis**:
    *   Integrate `gender-guesser` or a similar library.
    *   Provide options for users to supply their own name-gender lists.
    *   Expand statistical reporting (e.g., gender by year, by journal, by field).
    *   Strengthen documentation on ethical use and limitations.
3.  **Funding Analysis**:
    *   Implement NLP techniques (e.g., using spaCy or NLTK for NER) to extract funders and grant details from acknowledgement texts.
    *   Develop methods to normalize funder names.
    *   Allow analysis of funding trends (e.g., top funders by field/year).
4.  **New Analysis Types**:
    *   Bibliographic coupling analysis.
    *   Collaboration network analysis between institutions or countries.
    *   Thematic evolution / trend analysis of keywords or topics.
    *   Burst detection for emerging topics.
5.  **Visualization**:
    *   Integrate with libraries like `Matplotlib`, `Seaborn`, `Plotly`, or `NetworkX` (with graphviz) to generate basic plots and network visualizations from analysis results.

### Core & Usability
1.  **Data Export**: Add functionality to export processed records and analysis results in common formats (CSV, Excel, JSON, GEXF for networks).
2.  **Caching**: Implement caching for API calls to reduce redundant requests and respect API limits.
3.  **Logging**: Add more comprehensive logging throughout the library.
4.  **Command-Line Interface (CLI)**: Develop a CLI for common workflows.
5.  **Asynchronous Operations**: For fetching data from multiple APIs, consider using `asyncio` for improved performance.

## Documentation & Examples
1.  **More Examples**: Add more complex example workflows, potentially as Jupyter notebooks.
2.  **Complete API Reference**: Generate a full API reference using tools like Sphinx.
3.  **Tutorials**: Write step-by-step tutorials for common use cases.
