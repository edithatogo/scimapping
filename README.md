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
    *   **`pybibx`**: This library is intended for core analysis. It's listed as a dependency, but its direct integration and testing are currently ongoing. The `PybibxAnalyzer` module currently uses placeholder logic.
    *   **`pybliometrics` (for Scopus)**: This is a key dependency for Scopus access. It's currently commented out in `pyproject.toml` due to runtime issues encountered in the development environment. If you plan to use Scopus features, you'll need to add it to the dependencies in `pyproject.toml` (or install it separately) and ensure it works in your environment with proper API key configuration.
    *   **API Clients (`dimcli`, `openalex`)**: For data sources like Dimensions and OpenAlex, their respective client libraries (`dimcli`, `openalex`) will be installed. You will need to configure your API keys/credentials for these services as per their documentation for live API calls.

## Getting Started

(Instructions will be added as the library develops, likely pointing to the `docs/` directory and `examples/`)

## Contributing

(Guidelines for contributing will be added here)

## License

(License information will be added here)
