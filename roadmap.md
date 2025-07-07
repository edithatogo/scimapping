# Sciencemapping Library Roadmap

This document outlines the strategic roadmap for the development of the `sciencemapping` Python library. It complements the more granular tasks listed in `docs/todo.md`.

## Project Vision

To create a comprehensive, user-friendly, and extensible Python library for conducting bibliometric analysis and science mapping, enabling researchers to easily gather, analyze, and visualize scientific literature data from diverse sources.

## Key Development Phases

### Phase 1: Core Foundation & Data Sourcing (Partially Complete)

*   **Goal:** Establish the basic project structure, core API, and implement data sourcing from key bibliographic databases.
*   **Key Deliverables:**
    *   [X] Initial project structure (`sciencemapping` package, `tests`, `docs`, `examples`).
    *   [X] `ScienceMapper` core class for orchestrating workflows.
    *   [X] Data sourcing modules for:
        *   [X] PubMed (API) - *Tests Passing*
        *   [X] Web of Science (File Parsing) - *Tests Passing*
        *   [C] Scopus (API via `pybliometrics`) - *Core logic implemented; tests blocked by environment/dependency issues.*
        *   [C] Dimensions (API via `dimcli`) - *Core logic and tests written; tests blocked by environment/ModuleNotFoundError.*
        *   [C] OpenAlex (API via `openalex`) - *Core logic and tests written; tests blocked by environment/ModuleNotFoundError.*
    *   [X] Initial common internal data format for records.
    *   [X] Basic documentation (README, initial docs structure).
    *   [X] Packaging setup (`pyproject.toml`).
*   **Status:** Substantially complete, with noted issues in testing for some data source modules due to sandbox environment constraints.

### Phase 2: Core Analysis Engine & Initial Enhancements (Current Focus)

*   **Goal:** Integrate a core bibliometric analysis engine (`pybibx`) and begin implementing specialized analysis modules for identified gaps (funding, gender). Enhance data quality through enrichment (CrossRef).
*   **Key Deliverables:**
    *   [P] **Full `pybibx` Integration:** (Currently conceptual)
        *   [P] Refine `PybibxAnalyzer` with concrete (mocked) `pybibx` API calls and data transformations. - *Done conceptually*
        *   [_] Actual `pybibx` library testing, installation, and direct integration (environment permitting).
    *   [P] **Robust Funding Data:**
        *   [P] Enhance `FundingAnalyzer` with NLP (`spaCy`) for extracting from acknowledgements. - *Initial NLP version done*
        *   [P] **CrossRef Integration for Funding Data Enrichment.**
            *   [X] Initial enrichment service implemented.
            *   [X] Refined to merge data into common `funding_entries` field.
        *   [P] Enhance data source parsers for better structured funding data extraction. - *Initial pass completed; further refinement & testing needed.*
    *   [X] **Gender Analysis Module:**
        *   [P] Conceptual `GenderAnalyzer` with placeholder logic. - *Done*
        *   [X] Integrate `gender-guesser` or similar library. - *Done with `gender-guesser`*
        *   [P] Conceptual `GenderAnalyzer` with placeholder logic. - *Done*
        *   [ ] Integrate `gender-guesser` or similar library.
    *   [ ] Refine common data format (e.g., for `cited_references`, structured funding).
    *   [ ] Expand unit test coverage and address existing test execution blockers if environment allows.
*   **Status:** In Progress. Conceptual `pybibx` integration is done. Initial NLP for funding is done. CrossRef integration is next.

### Phase 3: Advanced Analysis & Visualization

*   **Goal:** Implement more advanced bibliometric analysis techniques and provide basic visualization capabilities.
*   **Key Deliverables (Examples):**
    *   [ ] Bibliographic coupling analysis.
    *   [ ] Co-citation analysis (requires `cited_references` data).
    *   [ ] Thematic analysis / Topic modeling on abstracts/keywords.
    *   [ ] Burst detection for trends.
    *   [ ] Basic network visualization (e.g., using NetworkX with Matplotlib, or wrappers for tools like Gephi).
    *   [ ] Basic chart generation for statistical summaries.
    *   [ ] Further development of Gender and Funding analysis modules with more sophisticated techniques.

### Phase 4: Usability, Export, and Robustness

*   **Goal:** Improve the overall usability of the library, add data export features, and enhance robustness.
*   **Key Deliverables (Examples):**
    *   [ ] Data export functions (CSV, Excel, JSON, GEXF for networks).
    *   [ ] Comprehensive API documentation (e.g., Sphinx-generated).
    *   [ ] More example workflows and tutorials (Jupyter notebooks).
    *   [ ] Robust configuration management for API keys and settings.
    *   [ ] Caching mechanisms for API calls.
    *   [ ] Enhanced logging throughout the library.
    *   [ ] Potential Command-Line Interface (CLI).

### Phase 5: Community & Ecosystem

*   **Goal:** Foster community engagement and explore integrations with other relevant tools.
*   **Key Deliverables (Examples):**
    *   [ ] Clear contribution guidelines and community support channels.
    *   [ ] Publication / Dissemination (e.g., JOSS paper, conference presentation).
    *   [ ] Exploration of integration with workflow tools or data visualization platforms.

---
**Legend:**
*   [X] Complete
*   [P] Partially Complete / In Progress (foundational work done)
*   [C] Conceptual Implementation / Code Written (testing blocked/incomplete)
*   [ ] To Do / Planned
---

This roadmap is a living document and will be updated as the project progresses and priorities evolve.
