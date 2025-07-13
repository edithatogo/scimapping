# To-Do List & Future Work

This document outlines known limitations, unimplemented features, and potential areas for future development in the `scimapper` library and its sub-modules.

## Refactoring and Project Restructure

*   [X] Rename `sciencemapping` to `scimapper`.
*   [X] Create `scisourcer`, `sciwrangler`, and `sciprocessor` sub-packages.
*   [X] Move data source modules to `scisourcer`.
*   [X] Move utility modules to `sciwrangler`.
*   [X] Move analysis modules to `sciprocessor`.
*   [X] Update `core.py` and all tests.
*   [ ] Update all documentation.

## Documentation and Protocol

*   [ ] Create `CHANGELOG.md`.
*   [ ] Create session log.
*   [ ] Develop and version a protocol for module creation, including an iterative academic review process.

## Research and Development

### `scisourcer` (Data Sourcing)

*   [ ] **Exhaustive Research:** Identify and evaluate additional data sources (e.g., Google Scholar, Semantic Scholar, patent databases).
*   [ ] **Robust Error Handling:** Improve error handling for all data sources.
*   [ ] **Configuration Management:** Implement a robust configuration system for API keys.
*   [ ] **Full Text Links/Access:** Explore options for linking to or fetching full text.

### `sciwrangler` (Data Pre-processing)

*   [ ] **Exhaustive Research:** Investigate best practices for data deduplication, citation parsing, and data cleaning.
*   [ ] **Deduplication:** Implement advanced deduplication strategies.
*   [ ] **Parsing:** Enhance parsing of author names, affiliations, and other metadata.
*   [ ] **Data Enrichment:** Improve and expand data enrichment capabilities (e.g., CrossRef, funding data).

### `sciprocessor` (Analysis)

*   [ ] **Exhaustive Research:** Explore advanced bibliometric and scientometric analysis techniques.
*   [ ] **`pybibx` Integration:** Complete the integration with the `pybibx` library.
*   [ ] **New Analysis Types:** Implement new analysis types (e.g., bibliographic coupling, co-citation analysis, topic modeling).
*   [ ] **Visualization:** Integrate with visualization libraries.

## Publication and Community

*   [ ] Create example use cases and tutorials.
*   [ ] Write and iteratively review a paper for "Systematic Reviews".
*   [ ] Develop contribution guidelines and community support channels.
