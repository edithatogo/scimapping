# Sciencemapping Library Documentation

Welcome to the documentation for the `sciencemapping` library!

## Overview

The `sciencemapping` library aims to provide a comprehensive toolkit for researchers and analysts to perform science mapping and bibliometric analysis. It facilitates fetching bibliographic data from various academic sources and analyzing it to uncover insights, trends, and structures within scientific literature.

**Key Features (Implemented & Planned):**

*   **Multiple Data Sources:**
    *   PubMed (API via `pymed`)
    *   Web of Science (WoS) (File parsing via `metaknowledge`)
    *   Scopus (API via `pybliometrics` - *currently with test environment issues*)
    *   Dimensions (API via `dimcli` - *currently with test environment issues*)
    *   OpenAlex (API via `openalex` - *currently with test environment issues*)
*   **Core `ScienceMapper` API:** A high-level interface to orchestrate data fetching and analysis.
*   **Analysis Modules:**
    *   `PybibxAnalyzer`: Interface for analyses like co-authorship, keyword co-occurrence, citation analysis (currently using placeholder logic pending full `pybibx` integration and testing).
    *   `GenderAnalyzer`: Conceptual module for gender-related analysis (uses placeholder logic).
    *   `FundingAnalyzer`: Conceptual module for funding-related analysis (uses placeholder logic).
*   **Common Data Format:** Aims to parse data from different sources into a consistent internal representation for easier analysis.

## Installation

1.  **Clone the repository (if not already done):**
    ```bash
    git clone <repository_url>
    cd sciencemapping
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    The library relies on several external packages. Install them using the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    This will install core dependencies such as `requests`, `pymed`, `metaknowledge`, `dimcli`, `openalex`, `spacy`, `gender-guesser`, `habanero`, etc.

    **Additionally for NLP features:**
    *   The `FundingAnalyzer` uses `spaCy` for NLP. You'll need to download a spaCy language model:
        ```bash
        python -m spacy download en_core_web_sm
        ```

    *Note on `pybibx`*: `pybibx` is listed as a dependency but its direct integration is conceptual at this stage. The `PybibxAnalyzer` uses placeholder logic.
    *Note on API clients*: For Scopus (`pybliometrics`), Dimensions (`dimcli`), you will need to configure your API keys/credentials as per their respective documentation for live API calls. Ensure `pybliometrics` is added to requirements if Scopus functionality is critical and environment issues are resolved.

## Quick Start

The following example demonstrates a basic workflow using the `ScienceMapper`.

```python
from sciencemapping.core import ScienceMapper
import os

# --- Prepare a sample WoS file for the example ---
def create_sample_wos_file(filepath="quick_start_wos.txt"):
    content = """PT J
AU Einstein, Albert; Podolsky, Boris; Rosen, Nathan
TI Can Quantum-Mechanical Description of Physical Reality Be Considered Complete?
SO Physical Review
PY 1935
DE EPR paradox; quantum mechanics; entanglement
UT WOS:000123456
ER
PT J
AU Crick, Francis; Watson, James D
TI Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid
SO Nature
PY 1953
DE DNA structure; double helix
UT WOS:000789012
ER
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

# --- Main workflow ---
if __name__ == "__main__":
    mapper = ScienceMapper(
        pubmed_email="your_actual_email@example.com", # Important for PubMed API
        openalex_email="your_actual_email@example.com" # Good practice for OpenAlex API
    )

    # 1. Fetch data from a WoS file
    wos_file = create_sample_wos_file()
    try:
        mapper.fetch_data(source="wos_file", file_path=wos_file)
        print(f"Fetched {len(mapper.get_records())} records from WoS file.")
        if mapper.get_records():
            print(f"First WoS record title: {mapper.get_records()[0].get('title')}")
    finally:
        if os.path.exists(wos_file):
            os.remove(wos_file)

    # 2. Fetch data from PubMed (replace with a relevant query for your needs)
    # Note: This makes a live API call.
    print("\\nFetching from PubMed...")
    try:
        mapper.fetch_data(source="pubmed", query='("Nature"[Journal]) AND (" CRISPR"[Title/Abstract]) AND ("2023"[Date - Publication])', max_results=2)
        print(f"Fetched {len(mapper.get_records())} records from PubMed.")
        if mapper.get_records():
            print(f"First PubMed record title: {mapper.get_records()[0].get('title')}")
    except Exception as e:
        print(f"PubMed fetch error: {e}")


    # 3. Perform analysis (using placeholder logic for pybibx)
    if mapper.get_records():
        print("\\nPerforming co-authorship analysis...")
        coauth_results = mapper.analyze("co_authorship")
        if coauth_results:
            print(f"Co-authorship nodes: {len(coauth_results.get('nodes', []))}, Edges: {len(coauth_results.get('edges', []))}")

        print("\\nPerforming keyword co-occurrence analysis...")
        keyword_results = mapper.analyze("keyword_cooccurrence")
        if keyword_results:
            print(f"Keyword co-occurrence nodes: {len(keyword_results.get('nodes', []))}, Edges: {len(keyword_results.get('edges', []))}")
    else:
        print("\\nNo records loaded for analysis.")
```

See `examples/basic_workflow.py` for a more detailed script.

## Next Steps

*   Explore `docs/usage.md` for detailed API information.
*   Check `docs/data_sources.md` for notes on specific data sources.
*   Learn about the analysis modules in `docs/analysis_modules.md`.

---

*This documentation is currently under development.*
