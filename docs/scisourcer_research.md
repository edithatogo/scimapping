# scisourcer Research

This document outlines the research conducted for the `scisourcer` module.

## Data Sources

The following data sources have been identified as potential candidates for inclusion in the `scisourcer` module:

*   **PubMed:** A free resource supporting the search and retrieval of biomedical and life sciences literature.
    *   **API:** [E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
    *   **Python Library:** `pymed`
*   **Web of Science:** A paid-access platform that provides access to multiple databases that provide reference and citation data from academic journals, conference proceedings, and other documents in various academic disciplines.
    *   **API:** [Web of Science API](https://developer.clarivate.com/apis/wos)
    *   **Python Library:** `wos`
*   **Scopus:** A bibliographic database containing abstracts and citations for academic journal articles.
    *   **API:** [Scopus API](https://dev.elsevier.com/sc_apis.html)
    *   **Python Library:** `pybliometrics`
*   **Dimensions:** A research information database that covers grants, publications, citations, alternative metrics, clinical trials, patents and policy documents.
    *   **API:** [Dimensions API](https://www.dimensions.ai/dimensions-api/)
    *   **Python Library:** `dimcli`
*   **OpenAlex:** A free and open catalog of the global research system.
    *   **API:** [OpenAlex API](https://docs.openalex.org/)
    *   **Python Library:** `openalex`
*   **Google Scholar:** A freely accessible web search engine that indexes the full text or metadata of scholarly literature across an array of publishing formats and disciplines.
    *   **API:** No official API.
    *   **Python Library:** `scholarly` (unofficial)
*   **Semantic Scholar:** A project developed at the Allen Institute for AI, it is a large-scale, AI-powered research tool for scientific literature.
    *   **API:** [Semantic Scholar API](https://www.semanticscholar.org/product/api)
    *   **Python Library:** `semanticscholar`
*   **Patent Databases:** Such as the USPTO, EPO, and WIPO databases.
    *   **API:** Each database has its own API.
    *   **Python Library:** `patstat` (for EPO), `uspto` (for USPTO)

## Full Text Access

The following are potential ways to get the full text of articles:

*   **Unpaywall:** A database of millions of free-to-read scholarly articles.
    *   **API:** [Unpaywall API](https://unpaywall.org/products/api)
    *   **Python Library:** `unpywall`
*   **CORE:** A database of millions of open access research papers.
    *   **API:** [CORE API](https://core.ac.uk/services/api)
    *   **Python Library:** `core-sdk`
*   **Publisher APIs:** Many publishers provide APIs that can be used to access the full text of their articles.
*   **Web Scraping:** The full text of articles can be scraped from publisher websites. This should be done with caution, as it may violate the terms of service of the website.

## CrossRef API

The [CrossRef API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) provides access to a wealth of metadata about scholarly articles. The following are some of the features that could be added to the `scisourcer` module using the CrossRef API:

*   **Citation Counts:** The CrossRef API can be used to get the number of times an article has been cited.
*   **Funder Information:** The CrossRef API can be used to get information about the funding sources for an article.
*   **License Information:** The CrossRef API can be used to get information about the license under which an article is published.
*   **Full Text Links:** The CrossRef API can be used to get links to the full text of an article.
*   **Event Data:** The CrossRef API can be used to get information about events that are related to an article, such as news articles, blog posts, and social media mentions.
*   **Affiliation Data:** The CrossRef API can be used to get information about the affiliations of the authors of an article. This can be used to identify the institutions that are most active in a particular research field.
