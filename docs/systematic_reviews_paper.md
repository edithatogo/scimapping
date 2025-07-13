# scimapper: A Python Library for Modular Bibliometric Analysis

**Authors:** Jules

**Affiliations:** Agent

**Abstract:**

Bibliometric analysis is a powerful tool for understanding the structure and evolution of scientific research. However, existing tools for bibliometric analysis are often monolithic and difficult to extend. In this paper, we present `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. This modular design allows researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components into other projects. We believe that `scimapper` will be a valuable tool for the bibliometric research community.

**Keywords:** bibliometrics, scientometrics, science mapping, Python, open source software

## 1. Introduction

Bibliometric analysis is a quantitative approach to studying the scientific literature. It can be used to identify trends in research, to map the intellectual structure of a field, and to assess the impact of research. The field of bibliometrics has a long history, dating back to the early 20th century. In recent years, the field has been revolutionized by the availability of large-scale bibliographic databases and the development of powerful new software tools.

Despite the advances in the field, there are still a number of challenges that are associated with bibliometric analysis. One of the biggest challenges is the lack of standardization in the data. Bibliographic data is often messy and inconsistent, which can make it difficult to compare results across different studies. Another challenge is the lack of transparency in the methods that are used to conduct bibliometric analysis. Many of the existing tools for bibliometric analysis are black boxes, which makes it difficult to understand how they work and to reproduce their results.

In this paper, we present `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to address the challenges of standardization and transparency by providing a modular and extensible framework for bibliometric analysis. The library is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. This modular design allows researchers to use the entire `scimapper` library for end-to-end workflows or to incorporate individual components into other projects.

## 2. The scimapper Library

The `scimapper` library is composed of three sub-packages:

*   **`scisourcer`:** This sub-package is responsible for sourcing data from a variety of bibliographic databases, including PubMed, Web of Science, Scopus, Dimensions, and OpenAlex. The `scisourcer` sub-package provides a consistent API for accessing these different data sources, which makes it easy to switch between them.
*   **`sciwrangler`:** This sub-package is responsible for pre-processing the data, including cleaning, normalizing, and deduplicating the data. The `sciwrangler` sub-package provides a flexible data model that can be used to represent the data in a consistent way, regardless of the original data source. The data model is based on a simple dictionary, which makes it easy to use and to extend.
*   **`sciprocessor`:** This sub-package is responsible for analyzing the data, including performing co-authorship analysis, keyword co-occurrence analysis, and citation analysis. The `sciprocessor` sub-package provides a number of different analysis methods, which can be easily extended with new methods.

## 3. Example Workflow

In this section, we present a more comprehensive example of how to use the `scimapper` library to perform a co-authorship analysis of a set of PubMed records.

```python
# Import the necessary classes and functions
from scimapper.core import ScienceMapper
from scimapper.sciwrangler.deduplication import deduplicate_by_title
from scimapper.sciprocessor.network_analysis import calculate_network_metrics

# Create a ScienceMapper instance
# This object will orchestrate the entire workflow, from fetching data to analyzing it.
mapper = ScienceMapper()

# Fetch data from PubMed
# We will search for 100 articles with the query "bibliometrics".
mapper.fetch_data(source="pubmed", query="bibliometrics", max_results=100)

# Enrich the data with CrossRef funding information
# This will add funding information from CrossRef to the records.
mapper.enrich_with_crossref()

# Get the records
# The records are stored in a list of dictionaries.
records = mapper.get_records()

# Remove duplicate records
# We will use the `deduplicate_by_title` function to remove duplicate records based on their title.
records = deduplicate_by_title(records)

# Analyze the co-authorship network
# We will use the `analyze` method to perform a co-authorship analysis.
coauth_net = mapper.analyze("co_authorship")

# Calculate network metrics
# We will use the `calculate_network_metrics` function to calculate network metrics.
network_metrics = calculate_network_metrics(coauth_net)

# Print the results
# The results are a dictionary containing the network metrics.
print(network_metrics)
```

## 4. Conclusion

In this paper, we have presented `scimapper`, a Python library for modular bibliometric analysis. `scimapper` is designed to be extensible and easy to use, and it is composed of three distinct sub-packages: `scisourcer`, for sourcing data; `sciwrangler`, for pre-processing data; and `sciprocessor`, for analyzing data. We believe that `scimapper` will be a valuable tool for the bibliometric research community, and that it will help to address some of the challenges that are associated with bibliometric analysis.

### 4.1. Limitations

The `scimapper` library is still under development, and there are a number of limitations that should be aware of. First, the library does not yet support all of the features that are available in other bibliometric analysis tools. For example, it does not yet support all of the data sources that are available in other tools, and it does not yet support all of the analysis methods that are available in other tools. Second, the library has not yet been tested on a wide range of datasets. Third, the library does not yet have a graphical user interface.

### 4.2. Future Work

We are actively working to address the limitations of the `scimapper` library. We plan to add support for more data sources, including Google Scholar, Semantic Scholar, and patent databases. We also plan to add support for more analysis methods, including bibliographic coupling, co-citation analysis, topic modeling, and burst detection. Finally, we plan to develop a graphical user interface for the library. We welcome contributions from the community, and we hope that `scimapper` will become a valuable resource for the bibliometric research community. We believe that `scimapper` has the potential to make a significant contribution to the field of bibliometric analysis, and we look forward to seeing how it is used by the community.
