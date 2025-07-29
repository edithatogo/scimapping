from typing import List, Dict, Any, Optional, Literal

# Import data sourcing functions
from .data_sources import pubmed, scopus, wos, dimensions, openalex, google_scholar

# Import the analyzer
from .analysis.pybibx_analyzer import PybibxAnalyzer

# Import enrichment utilities
from .utils.enrichment import enrich_records_with_crossref_funding, HABANERO_AVAILABLE as CROSSREF_CLIENT_AVAILABLE

# Define types for clarity
DataSourceName = Literal["pubmed", "scopus_api", "wos_file", "dimensions_api", "openalex_api", "google_scholar"]
AnalysisTypeName = Literal["co_authorship", "keyword_cooccurrence", "citation_analysis"]

# --- Default configurations or constants ---
DEFAULT_PUBMED_EMAIL = "sciencemappinglib_user@example.com"
DEFAULT_OPENALEX_EMAIL = "sciencemappinglib_user@example.com"
DEFAULT_CROSSREF_MAILTO = "sciencemappinglib_user@example.com"

class ScienceMapper:
    """
    High-level API for the science mapping library.
    Orchestrates data fetching, enrichment, and analysis.
    """

    def __init__(self,
                 pubmed_email: Optional[str] = DEFAULT_PUBMED_EMAIL,
                 openalex_email: Optional[str] = DEFAULT_OPENALEX_EMAIL,
                 crossref_mailto: Optional[str] = DEFAULT_CROSSREF_MAILTO
                 ):
        """
        Initializes the ScienceMapper.

        Args:
            pubmed_email: Email for PubMed API polite pool.
            openalex_email: Email for OpenAlex API polite pool.
            crossref_mailto: Email for CrossRef API polite pool (used by enrichment).
        """
        self.pubmed_email = pubmed_email
        self.openalex_email = openalex_email
        self.crossref_mailto = crossref_mailto
        self._records: List[Dict[str, Any]] = []
        self._source_of_records: Optional[DataSourceName] = None

    def fetch_data(
        self,
        source: DataSourceName,
        query: Optional[str] = None,
        file_path: Optional[str] = None,
        max_results: int = 100,
        wos_file_encoding: str = 'utf-8',
        dimensions_dsl_instance: Optional[Any] = None,
        scopus_api_key: Optional[str] = None,
        openalex_filter_criteria: Optional[Dict[str, Any]] = None,
        gs_fill_publications: bool = False # For Google Scholar
    ) -> 'ScienceMapper':
        """
        Fetches data from the specified source. Stores records internally.
        Returns the ScienceMapper instance for chaining.
        Raises ValueError for unknown source or missing parameters.
        """
        self._records = []
        self._source_of_records = source
        print(f"Core: Fetching data from {source}...")

        if source == "pubmed":
            if not query: raise ValueError("Query is required for PubMed search.")
            self._records = pubmed.search_pubmed(query, max_results=max_results, email=self.pubmed_email)

        elif source == "scopus_api":
            if not query: raise ValueError("Query is required for Scopus API search.")
            self._records = scopus.search_scopus(query, max_results=max_results, api_key=scopus_api_key)
            # print(f"Core: (Placeholder) Scopus API fetch. Test environment may have issues.")

        elif source == "wos_file":
            if not file_path: raise ValueError("File path is required for WoS file parsing.")
            self._records = wos.parse_wos_file(file_path, encoding=wos_file_encoding)

        elif source == "dimensions_api":
            if not query: raise ValueError("DSL query is required for Dimensions API search.")
            self._records = dimensions.search_dimensions_api(
                dsl_query=query, max_results=max_results, dsl_instance=dimensions_dsl_instance)
            # print(f"Core: (Placeholder) Dimensions API fetch. Test environment may have issues.")

        elif source == "openalex_api":
            if not query and not openalex_filter_criteria:
                 raise ValueError("Either search_query or filter_criteria is required for OpenAlex.")
            self._records = openalex.search_openalex_works(
                search_query=query, filter_criteria=openalex_filter_criteria,
                max_results=max_results, user_email=self.openalex_email)
            # print(f"Core: (Placeholder) OpenAlex API fetch. Test environment may have issues.")

        elif source == "google_scholar":
            if not query:
                raise ValueError("Query is required for Google Scholar search.")
            self._records = google_scholar.search_google_scholar(
                query,
                max_results=max_results,
                fill_publications=gs_fill_publications
            )
            # Warnings about reliability are handled within the google_scholar module itself.

        else:
            raise ValueError(f"Unknown data source: {source}")

        print(f"Core: Fetched {len(self._records)} records from {source}.")
        return self

    def get_records(self) -> List[Dict[str, Any]]:
        """Returns the currently loaded records."""
        return self._records

    def analyze(
        self,
        analysis_type: AnalysisTypeName,
        coauth_threshold: int = 1,
        keyword_threshold: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Performs the specified analysis on the currently loaded records.
        Raises ValueError if no records are loaded or analysis type is unknown.
        """
        if not self._records:
            print("Warning: No records loaded to analyze. Returning None.")
            return None

        analyzer = PybibxAnalyzer(self._records)
        results: Optional[Dict[str, Any]] = None
        print(f"Core: Performing analysis: {analysis_type}...")

        if analysis_type == "co_authorship":
            results = analyzer.co_authorship_network(author_threshold=coauth_threshold)
        elif analysis_type == "keyword_cooccurrence":
            results = analyzer.keyword_cooccurrence_network(keyword_threshold=keyword_threshold)
        elif analysis_type == "citation_analysis":
            results = analyzer.citation_analysis()
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        if results is None:
            print(f"Core: Analysis '{analysis_type}' yielded no results or failed.")
        else:
            print(f"Core: Analysis '{analysis_type}' complete.")

        return results

    def enrich_with_crossref(self, use_configured_mailto: bool = True) -> 'ScienceMapper':
        """
        Enriches the currently loaded records with funding information from CrossRef.
        This method requires the 'habanero' library to be installed.

        Args:
            use_configured_mailto: If True (default), uses the mailto email provided
                                   during ScienceMapper initialization. If False, the default
                                   in enrichment.py (or None if that's also None) will be used.

        Returns:
            The ScienceMapper instance for chaining.
        """
        if not self._records:
            print("Warning: No records loaded. Please fetch data before attempting CrossRef enrichment.")
            return self

        if not CROSSREF_CLIENT_AVAILABLE:
            print("Warning: 'habanero' library (for CrossRef) not available. Skipping enrichment.")
            return self

        print("Core: Enriching records with CrossRef funding data...")
        mailto_to_use = self.crossref_mailto if use_configured_mailto else None

        self._records = enrich_records_with_crossref_funding(self._records, mailto=mailto_to_use)

        print(f"Core: CrossRef enrichment process completed. {len(self._records)} records processed.")
        return self


# Example Usage (from when core.py was first created)
if __name__ == "__main__":
    print("ScienceMapper Core - Example Usage")
    mapper = ScienceMapper(
        pubmed_email="mytest@example.com",
        openalex_email="mytest_oa@example.com",
        crossref_mailto="mytest_cr@example.com" # Provide CrossRef mailto
    )
    try:
        # Fetch some data
        mapper.fetch_data(source="pubmed", query='("Nature Methods"[Journal]) AND ("2023"[Date - Publication]) AND cancer', max_results=2)

        # Enrich with CrossRef
        if mapper.get_records():
            print(f"\nRecords before CrossRef enrichment (sample DOI): {mapper.get_records()[0].get('doi')}")
            mapper.enrich_with_crossref()
            print(f"Records after CrossRef enrichment (first record):")
            if mapper.get_records()[0].get("crossref_funding"):
                 print(f"  CrossRef Funding: {mapper.get_records()[0]['crossref_funding']}")
            else:
                 print(f"  No CrossRef funding found for first record or DOI missing.")

        # Analyze
        if mapper.get_records():
            coauth_results = mapper.analyze("co_authorship")
            if coauth_results: print("\nCo-authorship nodes (sample):", coauth_results.get("nodes", [])[:1])

    except Exception as e: print(f"Error in example: {e}")
    print("\nScienceMapper Core example finished.")
