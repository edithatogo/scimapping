# Analysis Modules Guide

The `sciencemapping` library includes several modules for performing bibliometric and network analysis on the fetched data. These are primarily located under `sciencemapping.analysis/`.

## 1. `PybibxAnalyzer`

*   **Module**: `sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer`
*   **Purpose**: This class serves as an interface to a conceptual `pybibx` library for performing bibliometric analyses.
*   **`pybibx` Integration & Data Structures (Conceptual)**:
    *   The `PybibxAnalyzer` is designed to conceptually interact with a `pybibx` library.
    *   **Input Data Format (`PybibxRecordInput`)**: When initialized, `PybibxAnalyzer` conceptually transforms the input records (which are in the library's common internal format) into a list of records, where each record conforms to the `PybibxRecordInput` TypedDict. This structure includes fields like:
        *   `id: str` (e.g., DOI or a generated internal ID)
        *   `title: Optional[str]`
        *   `authors: Optional[List[str]]`
        *   `year: Optional[int]`
        *   `keywords: Optional[List[str]]`
        *   `references: Optional[List[str]]` (IDs of cited works)
        *   `source_journal: Optional[str]`
        *   `abstract: Optional[str]`
        This list of `PybibxRecordInput` dictionaries would then (conceptually) be used to initialize a `pybibx.Corpus`.
        ```python
        # Conceptual transformation to PybibxRecordInput:
        # for rec in self.records:
        #     mapped_rec: PybibxRecordInput = {
        #         "id": rec.get("doi") or f"internal_id_{...}",
        #         "title": rec.get("title"),
        #         # ... other fields ...
        #     }
        #     pybibx_input_records.append(mapped_rec)
        # self.pybibx_corpus = pybibx.Corpus(pybibx_input_records) # Conceptual
        ```
    *   **Output Data Formats (`TypedDict`s)**: The analysis methods are designed to return structured outputs defined by TypedDicts:
        *   `PybibxNetworkNode`: `{'id': str, 'label': str, 'size': int}`
        *   `PybibxNetworkEdge`: `{'source': str, 'target': str, 'weight': int}`
        *   `PybibxNetworkOutput`: `{'nodes': List[PybibxNetworkNode], 'edges': List[PybibxNetworkEdge], 'type': str}`
        *   `PybibxCitedPaper`: `{'id': str, 'title': Optional[str], 'citations': Optional[int]}`
        *   `PybibxCitationAnalysisOutput`: Contains fields like `total_citations_in_corpus`, `papers_with_citation_data`, `h_index_corpus`, `average_citations_per_paper`, and `top_cited_papers: List[PybibxCitedPaper]`.
    *   **Fallback Mechanism**: If the `pybibx` library is not found (as is currently the case since it's conceptual), or if any step in using it were to fail, the analyzer gracefully falls back to using **internal placeholder logic**. This placeholder logic also aims to return data in the defined `TypedDict` output structures.
*   **Key Analysis Methods**:
    *   **Co-authorship Network Analysis**:
        *   Method: `co_authorship_network(author_threshold: int = 1) -> Optional[PybibxNetworkOutput]`
        *   *Conceptual `pybibx` path*: Calls a hypothetical `pybibx.analysis.coauthorship` and transforms its output.
        *   *Output Structure*: Returns a `PybibxNetworkOutput` dictionary. Nodes represent authors (id/label: author name, size: publication count). Edges represent co-authorships with weights.
    *   **Keyword Co-occurrence Network Analysis**:
        *   Method: `keyword_cooccurrence_network(keyword_threshold: int = 1) -> Optional[PybibxNetworkOutput]`
        *   *Conceptual `pybibx` path*: Calls a hypothetical `pybibx.analysis.keywords` and transforms its output.
        *   *Output Structure*: Returns a `PybibxNetworkOutput` dictionary. Nodes represent keywords (id/label: keyword, size: occurrence frequency). Edges represent co-occurrences with weights.
    *   **Citation Analysis**:
        *   Method: `citation_analysis() -> Optional[PybibxCitationAnalysisOutput]`
        *   *Conceptual `pybibx` path*: Calls a hypothetical `pybibx.analysis.citation_summary`.
        *   *Output Structure*: Returns a `PybibxCitationAnalysisOutput` dictionary including metrics like total citations, paper counts, H-index (placeholder might be `None`), average citations, and a list of top-cited papers (each as `PybibxCitedPaper`).

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
*   **Purpose**: Provides tools for inferring gender from author names and calculating basic gender distribution statistics.
*   **Current Status & `gender-guesser` Integration**:
    *   The `GenderAnalyzer` integrates the `gender-guesser` Python library for name-based gender inference.
    *   **Initialization**:
        *   When `GenderAnalyzer` is initialized (`__init__(self, records, name_field="authors", custom_gender_map=None)`), it accepts an optional `custom_gender_map` (a dictionary mapping names to gender categories, e.g., `{"Firstname Lastname": "female", "AnotherFirstName": "nonbinary"}`).
        *   It attempts to initialize `gender_guesser.detector.Detector(case_sensitive=False)`.
    *   **Fallback Mechanism**: If `gender-guesser` is not installed/fails to initialize, a warning is issued, and it falls back to internal placeholder logic for names not in the custom map.
    *   Informative messages indicate the active gender inference method.
*   **Key Methods**:
    *   `_get_first_name(full_name: str)`: Helper to extract a potential first name.
    *   `infer_author_genders()`:
        *   **Priority for Custom Map**: First checks if the full author name, then the extracted first name (case-insensitively for first names), exists in the `custom_gender_map`. If so, the custom gender is used.
        *   **`gender-guesser` Usage**: If not found in the custom map and `gender-guesser` is available, it calls `gender_detector.get_gender(first_name)`. Direct output categories from `gender-guesser` are used (e.g., `female`, `male`, `andy`, `unknown`, `mostly_female`, `mostly_male`).
        *   **Error Handling**: Errors from `gender-guesser` calls result in `'error_in_guessing'`.
        *   **Placeholder Fallback**: If no custom map entry and `gender-guesser` is unavailable/fails, placeholder logic is used.
        *   **Output**: Returns a list of dictionaries: `{"name": str, "first_name_used_for_guess": Optional[str], "inferred_gender": str, "gender_source": str}`. The `gender_source` indicates the origin (e.g., "custom_map_full_name", "custom_map_first_name", "gender_guesser", "placeholder").
    *   `get_gender_distribution_stats()`: Calculates and returns a dictionary with counts for each `inferred_gender` category.

*   **Ethical Considerations & Limitations**:
    *   **Probabilistic Nature**: Name-based gender inference (including `gender-guesser`) is probabilistic and not deterministic. Accuracy varies significantly based on name origin, cultural context, and the coverage of the underlying name database.
    *   **Bias**: Name databases can have inherent biases (e.g., towards Western names).
    *   **Non-Binary Genders**: Most current tools, including `gender-guesser`, primarily operate on a binary (male/female) or limited categorical model (like `andy` for androgynous). They generally do not accurately represent or identify non-binary individuals.
    *   **Misgendering**: There's a risk of misgendering individuals.
    *   **Usage Recommendation**: Results from this type of analysis should **always be reported with strong caveats** regarding these limitations. They are best suited for aggregate statistical analysis of large datasets to identify potential trends or disparities, **not for making assumptions or decisions about any specific individual's gender.** User discretion and awareness of the limitations are crucial.
*   **Dependencies**: Requires the `gender-guesser` library (`pip install gender-guesser`).

## 3. `FundingAnalyzer`

*   **Module**: `sciencemapping.analysis.funding_analyzer.FundingAnalyzer`
*   **Purpose**: Provides tools for extracting and analyzing research funding information from publication records.
*   **Strategy for Funding Data**:
    1.  **Primary Source: Parsed `funding_entries`**: The `FundingAnalyzer`'s `extract_funding_data()` method now primarily consumes the `funding_entries` field from input records. This field is expected to be populated by the individual data source parsers (`pubmed.py`, `wos.py`, etc.), which are responsible for extracting structured funding information (funder names, grant IDs, specific funder identifiers like ROR/CrossRef) directly from the raw source data. Funder names within `funding_entries` are then normalized by `FundingAnalyzer`.
    2.  **Enrichment via CrossRef**: Separately, the library provides `sciencemapping.utils.enrichment.enrich_records_with_crossref_funding` (accessible via `ScienceMapper.enrich_with_crossref()`) to augment records with funding data from CrossRef. This enriched data would also ideally be structured into a similar `funding_entries` format or a distinct `crossref_funding` field.
    3.  **Secondary Source: NLP on Acknowledgements**: If a record's `funding_entries` field is sparse or missing, *and* an acknowledgements text field (e.g., `acknowledgements_text` from record, or source-specific ones like `acknowledgements_text_fx`, `acknowledgements_text_scopus`) is available, the `FundingAnalyzer` will then attempt NLP.
*   **Current Implementation (`FundingAnalyzer`)**:
    *   **Input Processing**: The `extract_funding_data()` method iterates through records. For each record:
        *   It first processes any data found in `record.get("funding_entries", [])`.
        *   If no substantial funding information is derived from `funding_entries`, and `spaCy` is available and relevant acknowledgement text exists, it applies NLP (NER for organizations, regex for grant IDs) to that text.
    *   **NLP Capability (Conditional)**: Uses `spaCy` (if available and `en_core_web_sm` model is downloaded) for NER.
    *   **Regex for Grant IDs**: Applied during the NLP step on acknowledgements.
    *   **Normalization**: Includes basic funder name normalization.
*   **Key Methods**:
    *   `extract_funding_data()`: Returns a list, where each item links to an original record and contains extracted/normalized `funders` (List[str]) and `grant_ids` (List[str]), along with `source_of_funding_info` indicating if data came from "structured_from_parser" or "nlp_acknowledgements".
    *   `get_funding_summary_stats()`: Calculates statistics based on the output of `extract_funding_data`.
*   **Future Enhancements**:
    *   Continued refinement of data source parsers to maximize the quality of structured `funding_entries`.
    *   Deeper integration of CrossRef enrichment results into the `funding_entries` structure or a similar standardized field.
    *   More sophisticated NLP for acknowledgements (entity disambiguation, relation extraction).
