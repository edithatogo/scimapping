# sciwrangler Research

This document outlines the research conducted for the `sciwrangler` module.

## Best Practices

The following are best practices for data pre-processing, deduplication, and parsing:

### Data Pre-processing

*   **Normalization:** Normalize funder names, author names, and other metadata to ensure consistency. This can be done using a combination of rule-based and machine learning-based approaches.
    *   **Rule-based:** Use a predefined mapping of common name variants to a canonical form.
    *   **Machine learning-based:** Train a model to identify and normalize name variants.
*   **Cleaning:** Remove irrelevant characters and formatting from the data. This can be done using regular expressions and other string manipulation techniques.
*   **Imputation:** Impute missing values where possible. This can be done using a variety of statistical and machine learning techniques, such as mean/median/mode imputation, regression imputation, and k-nearest neighbors imputation.

### Deduplication

*   **Exact Matching:** Identify and remove duplicate records based on exact matches of all fields. This is a simple and effective way to remove duplicate records, but it may not be sufficient for all datasets.
*   **Fuzzy Matching:** Identify and remove duplicate records based on fuzzy matching of key fields, such as title and author names. This is a more sophisticated approach that can identify duplicate records that have minor variations in their metadata.
    *   **String similarity metrics:** Use string similarity metrics, such as Levenshtein distance and Jaro-Winkler distance, to identify similar strings.
    *   **Blocking:** Use blocking techniques to reduce the number of pairwise comparisons that need to be made.

### Parsing

*   **Citation Parsing:** Parse citation strings to extract individual citation components, such as author names, year, and journal. This can be done using a variety of rule-based and machine learning-based approaches.
    *   **Rule-based:** Use regular expressions to identify and extract the different components of a citation.
    *   **Machine learning-based:** Train a model to identify and extract the different components of a citation.
*   **Abstract Parsing:** Parse abstracts to extract key information, such as the research question, methods, and results. This can be done using natural language processing (NLP) techniques, such as named entity recognition and relation extraction.
