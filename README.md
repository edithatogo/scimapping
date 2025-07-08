# Science Mapping Library

This project is a Python library for science mapping, bringing together various data sources and analysis tools.

## Overview

The primary goal of this library is to provide a comprehensive toolkit for:

*   **Sourcing Data:** Fetching bibliographic data from multiple academic databases including:
    *   PubMed
    *   Scopus
    *   Web of Science
    *   Dimensions
    *   OpenAlex
*   **Analyzing Data:** Utilizing tools like `pybibx` to perform various bibliometric and science mapping analyses.

## Features (Planned)

*   Modular data source connectors.
*   A common internal data format for seamless integration between sources and analysis.
*   Analysis capabilities leveraging `pybibx`.
*   Investigation into gender and research funding analysis.
*   Comprehensive documentation and examples.

## Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd sciencemapping
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the package and its dependencies:**
    To install the `sciencemapping` library and its core dependencies, navigate to the project root directory (where `pyproject.toml` is located) and run:
    ```bash
    pip install .
    ```
    For development, you can install it in editable mode:
    ```bash
    pip install -e .
    ```
    This uses the `pyproject.toml` file to build and install the package. Dependencies listed in `pyproject.toml` will be installed automatically.

    Alternatively, core runtime dependencies are also listed in `requirements.txt` for reference or for environments where a PEP 517 build is not used:
    ```bash
    pip install -r requirements.txt
    # Followed by pip install -e . if you also want the sciencemapping package itself installed from local source
    ```

    **Important Notes on Dependencies:**
    *   **`pybibx`**: This library is intended for core analysis. It's listed as a dependency, but its direct integration is currently conceptual. The `PybibxAnalyzer` module uses placeholder logic.
    *   **`pybliometrics` (for Scopus)**: A key dependency for Scopus. Commented out in `pyproject.toml` due to prior runtime issues. Add it if using Scopus and ensure it's configured with your API key.
    *   **API Clients (`dimcli`, `openalex`)**: These will be installed. Configure your API keys/credentials for these services per their documentation.
    *   **`spacy` (for NLP in Funding Analysis)**: If using NLP features for funding analysis, `spacy` will be installed. You also need to download a language model:
        ```bash
        python -m spacy download en_core_web_sm
        ```
    *   **`gender-guesser` (for Gender Analysis)**: Used by `GenderAnalyzer`. It will be installed as a dependency.

## Getting Started

(Instructions will be added as the library develops, likely pointing to the `docs/` directory and `examples/`)

## Contributing

(Guidelines for contributing will be added here)

## License

(License information will be added here)
