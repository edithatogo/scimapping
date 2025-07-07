# Analysis Modules Guide

The `sciencemapping` library includes several modules for performing bibliometric and network analysis on the fetched data. These are primarily located under `sciencemapping.analysis/`.

## 1. `PybibxAnalyzer`

*   **Module**: `sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer`
*   **Purpose**: This class serves as an interface to the `pybibx` library for performing bibliometric analyses.
*   **Current Status & `pybibx` Integration**:
    *   The `PybibxAnalyzer` is designed to use `pybibx` if the library is installed and available in the Python environment. It attempts to initialize a `pybibx.Corpus` with the provided records.
    *   If `pybibx` is not found, or if initializing its components or performing an analysis fails, the analyzer gracefully falls back to using **internal placeholder logic**.
    *   This dual approach allows the `sciencemapping` library to function and demonstrate its intended analytical capabilities even if `pybibx` itself cannot be run (e.g., due to environment restrictions or installation issues).
    *   Actual calls to `pybibx` functions (e.g., `pybibx.analysis.coauthorship`) are structured within the analyzer but are contingent on `pybibx` being usable. The transformation of `pybibx` results into the library's standard dictionary format is also conceptually handled.
*   **Key Analysis Methods (Conceptual `pybibx` Usage & Placeholders)**:
    *   **Co-authorship Network Analysis**:
        *   Method: `co_authorship_network(author_threshold: int = 1)`
        *   *If `pybibx` available*: Conceptually calls `pybibx.analysis.coauthorship(corpus, threshold=...)`.
        *   *Fallback*: Generates a basic co-authorship network.
        *   Returns: A dictionary `{"nodes": [...], "edges": [...], "type": "co-authorship"}`.
    *   **Keyword Co-occurrence Network Analysis**:
        *   Method: `keyword_cooccurrence_network(keyword_threshold: int = 1)`
        *   *If `pybibx` available*: Conceptually calls `pybibx.analysis.keywords(corpus, method="cooccurrence", threshold=...)`.
        *   *Fallback*: Generates a basic keyword co-occurrence network.
        *   Returns: A dictionary `{"nodes": [...], "edges": [...], "type": "keyword-cooccurrence"}`.
    *   **Citation Analysis**:
        *   Method: `citation_analysis()`
        *   *If `pybibx` available*: Conceptually calls `pybibx.analysis.citations(corpus)`.
        *   *Fallback*: Calculates basic citation statistics (e.g., most cited papers) based on available `times_cited_...` fields in the input records.
        *   Returns: A dictionary like `{"most_cited_papers": [...], "total_papers_with_citation_data": ...}`.
*   **Usage**:
    ```python
    from sciencemapping.analysis.pybibx_analyzer import PybibxAnalyzer

    # Assuming 'records' is a list of dicts from ScienceMapper.get_records()
    analyzer = PybibxAnalyzer(records)
    # The analyzer will print messages indicating if pybibx was initialized or if it's using placeholders.

    coauth_net = analyzer.co_authorship_network()
    keyword_net = analyzer.keyword_cooccurrence_network()
    citation_stats = analyzer.citation_analysis()
    ```
*   **Note**: The successful execution of actual `pybibx` functions depends on its proper installation and compatibility with the runtime environment. The placeholder logic ensures the `PybibxAnalyzer` remains functional for demonstration and testing of the overall library structure.

## 2. `GenderAnalyzer`

*   **Module**: `sciencemapping.analysis.gender_analyzer.GenderAnalyzer`
*   **Purpose**: Addresses the potential analysis gap related to author gender. This module provides conceptual tools for inferring gender from author names and calculating basic gender distribution statistics.
*   **Current Status**: **Placeholder Logic / Conceptual**.
    *   The `infer_author_genders()` method demonstrates how first names could be extracted and passed to a gender guessing tool (like `gender-guesser`, which is commented out). The current placeholder uses a very simplistic rule for demonstration.
    *   The `get_gender_distribution_stats()` method uses the output of the placeholder inference.
*   **Key Methods**:
    *   `_get_first_name(full_name: str)`: Helper to extract a potential first name.
    *   `infer_author_genders()`: Returns a list of authors with an `inferred_gender` field (placeholder logic).
    *   `get_gender_distribution_stats()`: Returns a dictionary with counts for each inferred gender category.
*   **Ethical Considerations**:
    *   Gender inference is probabilistic, can be inaccurate, and may misgender individuals.
    *   It often relies on cultural and regional name-gender associations which may not be universally applicable.
    *   It typically operates on a binary gender assumption, excluding non-binary individuals.
    *   **Results from this type of analysis should always be reported with strong caveats and used for aggregate statistical insights, not for individual assessment.**
*   **Future**: Could be enhanced by integrating `gender-guesser` or other more sophisticated name-based inference tools, along with clear documentation on their limitations and biases.

## 3. `FundingAnalyzer`

*   **Module**: `sciencemapping.analysis.funding_analyzer.FundingAnalyzer`
*   **Purpose**: Addresses the potential analysis gap related to research funding. This module provides conceptual tools for extracting funding information (agencies, grant IDs) from publication records and calculating summary statistics.
*   **Current Status**: **Placeholder Logic / Conceptual**.
    *   The `extract_funding_data()` method demonstrates a tiered approach:
        1.  Prioritizes structured funding fields if available in records (e.g., from Scopus, Dimensions, OpenAlex).
        2.  Uses basic regular expressions to find grant IDs in funding text fields (like WoS `FU` or Scopus `funding_text`).
        3.  Conceptually includes parsing free-text "Acknowledgements" sections (currently with very basic regex for common funders/grant patterns as a placeholder for more advanced NLP).
    *   The `get_funding_summary_stats()` method calculates statistics like the number of records with funding info and top funders based on the extracted data.
*   **Key Methods**:
    *   `extract_funding_data()`: Returns a list of records, each augmented with identified `funders` (List[str]) and `grant_ids` (List[str]).
    *   `get_funding_summary_stats()`: Returns a dictionary with funding statistics.
*   **Future**:
    *   Could be significantly enhanced with robust NLP techniques (e.g., Named Entity Recognition using spaCy or NLTK) for processing acknowledgement texts.
    *   Integration with external databases of grant information (if available and accessible) could enrich the analysis.
    *   Development of a more standardized internal representation for funding data across different sources.
