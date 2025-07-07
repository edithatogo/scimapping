# Analysis Modules Guide

The `sciencemapping` library includes several modules for performing bibliometric and network analysis on the fetched data. These are primarily located under `sciencemapping.analysis/`.

## 1. `PybibxAnalyzer`

*   **Module**: `sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer`
*   **Purpose**: This class serves as an interface to the `pybibx` library for performing bibliometric analyses.
*   **Current Status & `pybibx` Integration (Conceptual)**:
    *   The `PybibxAnalyzer` is designed to use `pybibx` if the library is installed and available.
    *   **Corpus Initialization**: When initialized, `PybibxAnalyzer` attempts to convert the input records (in the library's common internal format) into a format suitable for `pybibx.Corpus`. This involves conceptual mapping of field names (e.g., `title` to `TI`, `authors` to `AU`, `keywords` to `DE`, `year` to `PY`, coalesced citation counts to `TC`, and `cited_references` to `CR`).
        ```python
        # Conceptual mapping within PybibxAnalyzer for pybibx.Corpus
        # mapped_rec = {
        #     "TI": record.get("title"), "AU": record.get("authors"),
        #     "DE": record.get("keywords"), "PY": record.get("year"),
        #     "TC": record.get("times_cited_..."), # Coalesced
        #     "CR": record.get("cited_references")
        #     # ... other relevant WoS-like tags pybibx might expect
        # }
        # self.pybibx_corpus = pybibx.Corpus(mapped_pybibx_records)
        ```
    *   **Fallback Mechanism**: If `pybibx` is not found, or if any step in initializing or using `pybibx` fails (e.g., `pybibx.Corpus()` instantiation, or an analysis call like `pybibx.analysis.coauthorship()`), the analyzer gracefully falls back to using **internal placeholder logic** for the requested analysis. It will print informative messages indicating whether `pybibx` (conceptual) or placeholder logic was used.
*   **Key Analysis Methods (Conceptual `pybibx` API Usage & Placeholders)**:
    *   **Co-authorship Network Analysis**:
        *   Method: `co_authorship_network(author_threshold: int = 1)`
        *   *Conceptual `pybibx` path*:
            *   Calls `pybibx.analysis.coauthorship(self.pybibx_corpus, threshold=author_threshold)`.
            *   Assumes this returns a tuple: `(nodes, edges)`, where `nodes` is a list of author names, and `edges` is a list of tuples like `(author1, author2, weight)`.
            *   These raw results are transformed by `_transform_pybibx_network_output` into the standard `{"nodes": [{"id": ...}], "edges": [{"source": ..., "target": ..., "weight": ...}], "type": "co-authorship"}` format.
        *   *Fallback*: Generates a basic co-authorship network using internal logic.
    *   **Keyword Co-occurrence Network Analysis**:
        *   Method: `keyword_cooccurrence_network(keyword_threshold: int = 1)`
        *   *Conceptual `pybibx` path*:
            *   Calls `pybibx.analysis.keywords(self.pybibx_corpus, method="cooccurrence", threshold=keyword_threshold)`.
            *   Assumes this returns `(nodes, edges)` similar to co-authorship, but with keywords.
            *   Results are transformed by `_transform_pybibx_network_output`.
        *   *Fallback*: Generates a basic keyword co-occurrence network.
    *   **Citation Analysis**:
        *   Method: `citation_analysis()`
        *   *Conceptual `pybibx` path*:
            *   Calls `pybibx.analysis.citation_summary(self.pybibx_corpus, top_n=10)`.
            *   Assumes this returns a dictionary with keys like `total_papers_analyzed`, `papers_with_citations`, `top_cited_documents` (a list of dicts, each with `title`, `doi`, `pybibx_citations`).
            *   These raw results are transformed into the library's standard format: `{"most_cited_papers": [{"title": ..., "doi": ..., "citations": ...}], "total_papers_with_citation_data": ..., "raw_pybibx_summary": ...}`.
        *   *Fallback*: Calculates basic citation statistics from available `times_cited_...` fields in the input records.
*   **Usage**:
    ```python
    from sciencemapping.analysis.pybibx_analyzer import PybibxAnalyzer

    # Assuming 'records' is a list of dicts from ScienceMapper.get_records()
    analyzer = PybibxAnalyzer(records)
    # Analyzer prints messages about pybibx initialization or fallback.

    coauth_net = analyzer.co_authorship_network() # Will try pybibx, then fallback
    # ... other analysis calls
    ```
*   **Note**: This integration is **conceptual and not yet tested with an actual `pybibx` library**. The successful execution of real `pybibx` functions depends on its proper installation, API matching these assumptions, and compatibility. The placeholder logic ensures `PybibxAnalyzer` remains functional.

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
*   **Purpose**: Provides tools for extracting and analyzing research funding information from publication records.
*   **Strategy for Funding Data**:
    1.  **Primary: Structured Data from Sources**: The most reliable approach is to utilize structured funding information directly provided by the data sources. Individual data source parsers (`pubmed.py`, `wos.py`, `scopus.py`, `dimensions.py`, `openalex.py`) should be enhanced to extract fields like funder names, grant IDs, and funding agency acronyms, populating standardized fields in the common internal record format (e.g., a dedicated `structured_funding` list of dicts).
    2.  **Enrichment via CrossRef**: CrossRef is a valuable source for funding metadata, often including Funder Registry IDs. Future work should include a mechanism to query CrossRef (using DOIs) to augment records with this structured funding information.
    3.  **Secondary: NLP on Acknowledgements**: When structured data is sparse or unavailable, `FundingAnalyzer` can process free-text "acknowledgements" sections (if present in the records) using NLP techniques.
*   **Current Implementation (`FundingAnalyzer`)**:
    *   **NLP Capability (Conditional)**: Uses `spaCy` (if available and `en_core_web_sm` model is downloaded) for Named Entity Recognition (NER) to identify potential funding organizations (`ORG` entities) from acknowledgement text.
    *   **Regex for Grant IDs**: Employs regular expressions to find common grant ID patterns within acknowledgement text or other free-text funding fields.
    *   **Prioritization**: The `extract_funding_data()` method attempts to use any pre-existing structured funding fields (e.g., `funding_details` from Scopus, `funders` list from OpenAlex, WoS `FU` field) first. It then applies NLP and regex to `acknowledgements` or `FX` (WoS Funding Text) fields as a supplementary step.
    *   **Normalization**: Includes basic funder name normalization (e.g., "NSF" to "National Science Foundation").
*   **Key Methods**:
    *   `extract_funding_data()`: Processes records and returns a list, where each item contains the original record's index/identifier and extracted `funders` (List[str]) and `grant_ids` (List[str]). It also indicates the primary `source_of_funding_info` (e.g., "structured", "nlp_acknowledgements").
    *   `get_funding_summary_stats()`: Calculates statistics like the number of records with funding information and lists top funders (normalized).
*   **Future Enhancements (for `FundingAnalyzer` and data parsers)**:
    *   Improve data source parsers to robustly extract and standardize structured funding information.
    *   Implement CrossRef integration for funding data enrichment.
    *   Enhance NLP capabilities (e.g., more sophisticated entity disambiguation for funders, better grant ID patterns, relation extraction between funders and grants).
    *   Develop a more comprehensive internal model for storing detailed structured funding data (e.g., funder IDs, grant amounts if available).
