## Agent Instructions for `sciencemapping` Repository

Welcome, AI Agent! This document provides guidelines for contributing to the `sciencemapping` library.

### Project Goal

The primary goal is to create a Python library for science mapping. This involves:
1.  **Sourcing Data:** Fetching bibliographic data from PubMed, Scopus, Web of Science, Dimensions, and OpenAlex.
2.  **Analyzing Data:** Primarily using `pybibx` for analysis, but also exploring custom solutions for gaps like gender and research funding analysis.

### Coding Conventions

*   **Style:** Follow PEP 8 Python style guidelines. Use a linter like Flake8 or a formatter like Black if possible.
*   **Type Hinting:** Use type hints for all function signatures and important variables.
*   **Docstrings:** Write clear and concise docstrings for all modules, classes, and functions, following Google Python Style Guide for docstrings.
*   **Modularity:** Design components to be modular and reusable. Data source connectors should be independent, and analysis functions should operate on a common internal data representation.
*   **Common Data Format:** Strive to convert data from all sources into a consistent internal format before passing it to analysis functions. This will likely be a list of dictionaries or a custom `Publication` class.

### Directory Structure

*   `sciencemapping/`: Main library code.
    *   `data_sources/`: Modules for each data source (e.g., `pubmed.py`, `scopus.py`).
    *   `analysis/`: Modules for analysis (e.g., `pybibx_analyzer.py`, `gender_analyzer.py`).
    *   `core.py` (or similar): High-level API for users.
*   `tests/`: Unit and integration tests. Maintain a parallel structure to the `sciencemapping` directory where possible.
*   `examples/`: Jupyter notebooks or Python scripts demonstrating library usage.
*   `docs/`: Project documentation.

### Testing

*   Write unit tests for all new functionality.
*   Aim for high test coverage.
*   Tests should be placed in the `tests/` directory, mirroring the structure of the `sciencemapping` package.
*   Use a testing framework like `pytest`.

### Dependencies

*   Manage dependencies in `requirements.txt`.
*   For data sources, prefer established Python client libraries if they exist and are well-maintained (e.g., `pymed` for PubMed, `pybliometrics` for Scopus, `openalex-py` for OpenAlex). Otherwise, use `requests` for direct API interaction.

### API Design for Data Sources

*   Each data source module (e.g., `sciencemapping/data_sources/pubmed.py`) should ideally provide:
    *   A function to search and retrieve records based on a query (e.g., `search_pubmed(query: str, max_results: int = 100) -> list[dict]`).
    *   Functions to parse the raw API response into the common internal data format.
    *   Clear error handling for API issues (e.g., connection errors, rate limits, invalid queries).

### Analysis Modules

*   Analysis functions should accept data in the common internal format.
*   Clearly document the expected input format and the structure of the output.

### Gender and Research Funding Analysis

*   This is a key area for exploration.
*   Investigate if data sources provide relevant fields (e.g., author's first names for gender inference, funding information in acknowledgements).
*   If `pybibx` cannot directly handle this, new modules or functions will need to be developed. This might involve:
    *   Gender inference libraries or techniques.
    *   Text processing to extract funding details.

### Workflow

1.  **Understand the Task:** Ensure you understand the specific feature or bug fix requested.
2.  **Plan:** If it's a significant change, update the main plan or create a sub-plan.
3.  **Implement:** Write code following the conventions above.
4.  **Test:** Write and run tests.
5.  **Document:** Update or add documentation as needed.
6.  **Submit:** Commit changes with a clear message.

### Communication

*   If instructions are unclear or you encounter a significant blocker, use `request_user_input`.
*   Provide updates on your progress, especially for multi-step tasks.

Good luck, and thank you for your contribution!
