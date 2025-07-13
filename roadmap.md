# scimapper Library Roadmap

This document outlines the strategic roadmap for the development of the `scimapper` Python library and its conceptual sub-modules: `scisourcer`, `sciwrangler`, and `sciprocessor`.

## Project Vision

To create a modular, comprehensive, user-friendly, and extensible Python ecosystem for conducting bibliometric analysis and science mapping. This modularity will allow researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components (`scisourcer`, `sciwrangler`, `sciprocessor`) into other projects.

## Key Development Phases

### Phase 1: Refactoring and Project Restructure (In Progress)

*   **Goal:** Refactor the existing `sciencemapping` library into the new `scimapper` project structure with three distinct sub-modules.
*   **Key Deliverables:**
    *   [X] Rename the project to `scimapper`.
    *   [X] Create the `scisourcer` sub-package for data sourcing.
    *   [X] Create the `sciwrangler` sub-package for data parsing and pre-processing.
    *   [X] Create the `sciprocessor` sub-package for bibliometric analysis.
    *   [X] Update the `core.py` module and all tests to reflect the new structure.
    *   [ ] Update all documentation to reflect the new structure and vision.
    *   [ ] Investigate EndNote parsing.
*   **Status:** In Progress.

### Phase 2: Documentation, Protocol, and Research (Next)

*   **Goal:** Establish a robust documentation and development protocol, and conduct exhaustive research for each module.
*   **Key Deliverables:**
    *   [ ] Create and maintain a `CHANGELOG.md` and a session log.
    *   [ ] Develop a detailed protocol for the creation, review, and improvement of each module, following an academic review cycle.
    *   [ ] Conduct exhaustive research to identify additional data sources for `scisourcer`.
    *   [ ] Research best practices for data pre-processing, deduplication, and parsing for `sciwrangler`.
    *   [ ] Research advanced bibliometric and scientometric analysis techniques for `sciprocessor`.
*   **Status:** Planned.

### Phase 3: Advanced Analysis, Visualization, and Usability

*   **Goal:** Implement advanced features, visualization, and improve usability.
*   **Key Deliverables (Examples):**
    *   [ ] Implement advanced analysis types (e.g., bibliographic coupling, co-citation analysis, topic modeling).
    *   [ ] Integrate with visualization libraries (e.g., `Matplotlib`, `Plotly`, `NetworkX`).
    *   [ ] Add data export functions (e.g., CSV, Excel, JSON, GEXF).
    *   [ ] Develop comprehensive API documentation and tutorials.
*   **Status:** Planned.

### Phase 4: Publication and Community Engagement

*   **Goal:** Prepare for publication and foster a community around the `scimapper` ecosystem.
*   **Key Deliverables:**
    *   [ ] Create example use cases and tutorials.
    *   [ ] Write a paper for submission to the journal "Systematic Reviews".
    *   [ ] Go through an iterative internal review process for the paper.
    *   [ ] Establish clear contribution guidelines and community support channels.
*   **Status:** Planned.

---
**Legend:**
*   [X] Complete
*   [ ] To Do / Planned
---

This roadmap is a living document and will be updated as the project progresses and priorities evolve.
