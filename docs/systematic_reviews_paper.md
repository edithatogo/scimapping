# scimapper: A Python Library for Modular Bibliometric Analysis

**Authors:** Jules

**Affiliations:** Agent

**Abstract:**

Bibliometric analysis is a powerful tool for understanding the structure and evolution of scientific research. However, existing tools for bibliometric analysis are often monolithic and difficult to extend. In this paper, we present `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. This modular design allows researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components into other projects. We believe that `scimapper` will be a valuable tool for the bibliometric research community.

**Keywords:** bibliometrics, scientometrics, science mapping, Python, open source software

## 1. Introduction

Bibliometric analysis is a quantitative approach to studying the scientific literature. It can be used to identify trends in research, to map the intellectual structure of a field, and to assess the impact of research. There are a number of software tools available for bibliometric analysis, but many of them are monolithic and difficult to extend. This can make it difficult for researchers to customize the tools to their specific needs.

In this paper, we present `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. This modular design allows researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components into other projects.

## 2. The scimapper Library

The `scimapper` library is composed of three sub-packages:

*   **`scisourcer`:** This sub-package is responsible for sourcing data from a variety of bibliographic databases, including PubMed, Web of Science, Scopus, Dimensions, and OpenAlex.
*   **`sciwrangler`:** This sub-package is responsible for pre-processing the data, including cleaning, normalizing, and deduplicating the data.
*   **`sciprocessor`:** This sub-package is responsible for analyzing the data, including performing co-authorship analysis, keyword co-occurrence analysis, and citation analysis.

## 3. Example Workflow

In this section, we present a simple example of how to use the `scimapper` library to perform a co-authorship analysis of a set of PubMed records.

```python
from scimapper.core import ScienceMapper

# Create a ScienceMapper instance
mapper = ScienceMapper()

# Fetch data from PubMed
mapper.fetch_data(source="pubmed", query="bibliometrics", max_results=10)

# Enrich the data with CrossRef funding information
mapper.enrich_with_crossref()

# Analyze the co-authorship network
coauth_net = mapper.analyze("co_authorship")

# Print the results
print(coauth_net)
```

## 4. Conclusion

In this paper, we have presented `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. We believe that `scimapper` will be a valuable tool for the bibliometric research community.
