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
