# scimapper

`scimapper` is a Python library for modular bibliometric analysis. It is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. This modular design allows researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components into other projects.

## Overview

The primary goal of this library is to provide a comprehensive toolkit for:

*   **Sourcing Data:** Fetching bibliographic data from multiple academic databases including:
    *   PubMed
    *   Scopus
    *   Web of Science
    *   Dimensions
    *   OpenAlex
*   **Wrangling Data:** Cleaning, normalizing, and deduplicating data from different sources.
*   **Processing Data:** Utilizing tools like `pybibx` to perform various bibliometric and science mapping analyses.

## Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd scimapper
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the package and its dependencies:**
    To install the `scimapper` library and its core dependencies, navigate to the project root directory (where `pyproject.toml` is located) and run:
    ```bash
    pip install .
    ```
    For development, you can install it in editable mode:
    ```bash
    pip install -e .
    ```

## Getting Started

A simple example of how to use the `scimapper` library is provided in the `examples/simple_workflow.ipynb` notebook. A more advanced example is provided in the `examples/advanced_workflow.ipynb` notebook.

## Contributing

Contributions are welcome! Please see the `CONTRIBUTING.md` file for more information.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more information.
