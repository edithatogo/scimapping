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
    1.  **Primary: Parsed Structured Data**: The `FundingAnalyzer` now primarily consumes the `funding_entries` field from records. This field is expected to be populated by the individual data source parsers (`pubmed.py`, `wos.py`, etc.), which are responsible for extracting structured funding information (funder names, grant IDs, funder identifiers like ROR/CrossRef) from the raw source data.
    2.  **Enrichment via CrossRef**: The library also includes a utility (`sciencemapping.utils.enrichment.enrich_records_with_crossref_funding`) to augment records with funding data from CrossRef using DOIs. This can supplement the information from primary sources.
    3.  **Secondary: NLP on Acknowledgements**: If the `funding_entries` field is sparse or missing, and an acknowledgements text field (e.g., `acknowledgements_text`, `acknowledgements_text_fx`) is available, the `FundingAnalyzer` can use `spaCy` (if available) for NLP-based extraction of potential funders (as ORG entities) and regex for grant ID patterns.
*   **Current Implementation (`FundingAnalyzer`)**:
    *   **Input**: Expects records to potentially have a `funding_entries: List[Dict[str, Any]]` field (as defined in `docs/data_sources.md`).
    *   **NLP Capability (Conditional)**: Uses `spaCy` for NER on various forms of acknowledgement text if `funding_entries` is not sufficiently populated.
    *   **Regex for Grant IDs**: Applied during NLP on acknowledgements.
    *   **Prioritization**: The `extract_funding_data()` method now first processes `funding_entries`. If this is empty/missing, it then attempts NLP on available acknowledgement texts.
    *   **Normalization**: Includes basic funder name normalization.
*   **Key Methods**:
    *   `extract_funding_data()`: Returns a list, where each item links to an original record and contains extracted/normalized `funders` (List[str]) and `grant_ids` (List[str]), along with `source_of_funding_info` indicating if data came from "structured_from_parser" or "nlp_acknowledgements".
    *   `get_funding_summary_stats()`: Calculates statistics based on the output of `extract_funding_data`.
*   **Future Enhancements**:
    *   Continued refinement of data source parsers to maximize the quality of structured `funding_entries`.
    *   Deeper integration of CrossRef enrichment results into the `funding_entries` structure or a similar standardized field.
    *   More sophisticated NLP for acknowledgements (entity disambiguation, relation extraction).
