from typing import List, Dict, Any, Optional, Tuple

# Assume pybibx would be imported like this if installed and working.
# We will not actually import it here to avoid errors if it's not in the environment,
# but the functions will be structured as if it is.
# import pybibx

# Attempt to import pybibx, but allow failure for environments where it's not installed.
PYBIBX_AVAILABLE = False
try:
    import pybibx
    # Further check if it has expected top-level components, e.g. a Corpus class
    if hasattr(pybibx, 'Corpus') and hasattr(pybibx, 'analysis'):
        PYBIBX_AVAILABLE = True
except ImportError:
    pybibx = None # Assign to None if import fails
    print("PybibxAnalyzer: Warning - pybibx library not found. Analysis methods will use placeholder logic.")


class PybibxAnalyzer:
    """
    A class to perform bibliometric analysis using the pybibx library.
    If pybibx is not available, it falls back to placeholder logic.
    """

    def __init__(self, records: List[Dict[str, Any]]):
        """
        Initialize the analyzer with a list of publication records, preparing them for bibliometric analysis.
        
        If the `pybibx` library is available, attempts to map the input records to the format expected by `pybibx` and creates a `pybibx.Corpus` object for advanced analysis. If `pybibx` is unavailable or initialization fails, sets up the analyzer to use internal placeholder logic instead.
        
        Parameters:
            records (List[Dict[str, Any]]): List of publication records in the internal dictionary format.
        """
        self.records = records
        self.pybibx_corpus = None # This would be the pybibx Corpus object

        if PYBIBX_AVAILABLE and pybibx:
            try:
                # Conceptual: Map internal record format to what pybibx might expect
                # pybibx might expect specific field names (e.g., WoS tags like 'AU', 'DE', 'CR', 'PY', 'TI', 'SO')
                # For this example, we'll assume a simple mapping for key fields.
                # A real implementation would need to know pybibx's exact requirements.

                pybibx_input_records = []
                for rec in self.records:
                    mapped_rec = {
                        "TI": rec.get("title"),
                        "AU": rec.get("authors"), # Assumes pybibx can handle list of author strings
                        "DE": rec.get("keywords"),# Assumes pybibx can handle list of keyword strings for Author Keywords
                        "ID": [], # Placeholder for Keywords Plus, if pybibx distinguishes
                        "PY": rec.get("year"),
                        "SO": rec.get("journal"),
                        "DI": rec.get("doi"),
                        "AB": rec.get("abstract"),
                        # For citation analysis, pybibx might need structured cited references
                        # or rely on a pre-calculated 'TC' (Times Cited) field.
                        "TC": rec.get("times_cited_wos") or rec.get("times_cited_scopus") or \
                              rec.get("times_cited_openalex") or rec.get("cited_by_count"),
                        "CR": rec.get("cited_references") # New conceptual field
                    }
                    # Remove None values as some libraries prefer sparse dicts
                    pybibx_input_records.append({k: v for k, v in mapped_rec.items() if v is not None})

                self.pybibx_corpus = pybibx.Corpus(pybibx_input_records)
                print("PybibxAnalyzer: Successfully initialized and mapped records to pybibx.Corpus (conceptual).")
            except Exception as e:
                print(f"PybibxAnalyzer: Error initializing pybibx.Corpus - {e}. Will use placeholder logic.")
                self.pybibx_corpus = None
        else:
            print("PybibxAnalyzer: pybibx not fully available. Using placeholder logic for all analyses.")

    def _transform_pybibx_network_output(
        self,
        pybibx_nodes: Optional[List[Any]],
        pybibx_edges: Optional[List[tuple[Any, Any, int]]],
        network_type: str
        ) -> Dict[str, Any]:
        """
        Convert pybibx network output into a standardized dictionary format with stringified node and edge information.
        
        Parameters:
            pybibx_nodes: List of node identifiers, such as author names or keywords.
            pybibx_edges: List of edge tuples in the form (source, target, weight).
            network_type: Type of the network represented as a string.
        
        Returns:
            Dictionary containing "nodes" (list of dicts with "id"), "edges" (list of dicts with "source", "target", "weight"), and "type".
        """
        if pybibx_nodes is None: pybibx_nodes = []
        if pybibx_edges is None: pybibx_edges = []

        nodes_transformed = [{"id": str(node)} for node in pybibx_nodes]
        edges_transformed = [
            {"source": str(u), "target": str(v), "weight": int(w)}
            for u, v, w in pybibx_edges
        ]

        return {"nodes": nodes_transformed, "edges": edges_transformed, "type": network_type}

    def co_authorship_network(self, author_threshold: int = 1) -> Optional[Dict[str, Any]]:
        """
        Generate a co-authorship network from the publication records, optionally using the pybibx library if available.
        
        Parameters:
            author_threshold (int): Minimum number of co-authored papers required for an edge to be included in the network.
        
        Returns:
            dict or None: A dictionary representing the co-authorship network with "nodes", "edges", and "type" keys, or None if there are no records.
        """
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'coauthorship'):
            try:
                print(f"PybibxAnalyzer: Calling conceptual pybibx.analysis.coauthorship (threshold {author_threshold}).")
                # Hypothetical: pybibx.analysis.coauthorship returns (list_of_nodes, list_of_edge_tuples)
                # e.g., nodes = ["Author A", "Author B"], edges = [("Author A", "Author B", 2)]
                pybibx_nodes, pybibx_edges = pybibx.analysis.coauthorship(
                    self.pybibx_corpus,
                    threshold=author_threshold
                )
                return self._transform_pybibx_network_output(pybibx_nodes, pybibx_edges, "co-authorship")
            except Exception as e:
                print(f"PybibxAnalyzer: Error during conceptual pybibx co-authorship - {e}. Falling back to placeholder.")

        # --- Placeholder Logic ---
        print(f"PybibxAnalyzer: Using placeholder co-authorship network (threshold {author_threshold}).")
        nodes = set()
        edges = {}
        for record in self.records:
            authors = record.get("authors", [])
            if len(authors) > 1:
                for author in authors: nodes.add(author)
                for i in range(len(authors)):
                    for j in range(i + 1, len(authors)):
                        auth1, auth2 = tuple(sorted((authors[i], authors[j])))
                        edge = (auth1, auth2)
                        edges[edge] = edges.get(edge, 0) + 1

        final_edges = [{"source": u, "target": v, "weight": w} for (u,v), w in edges.items() if w >= author_threshold]
        final_nodes_set = set()
        for edge_data in final_edges:
            final_nodes_set.add(edge_data["source"])
            final_nodes_set.add(edge_data["target"])
        final_nodes = [{"id": node} for node in final_nodes_set]
        return {"nodes": final_nodes, "edges": final_edges, "type": "co-authorship"}


    def keyword_cooccurrence_network(self, keyword_threshold: int = 1) -> Optional[Dict[str, Any]]:
        """
        Generate a keyword co-occurrence network from publication records, optionally using pybibx if available.
        
        If the pybibx library and its keyword analysis method are available, this method uses them to compute the network; otherwise, it constructs the network by counting co-occurrences of keywords within each record. Edges are included only if their co-occurrence count meets or exceeds the specified threshold.
        
        Parameters:
            keyword_threshold (int): Minimum number of co-occurrences required for an edge to be included in the network.
        
        Returns:
            dict or None: A dictionary representing the keyword co-occurrence network with "nodes", "edges", and "type" keys, or None if there are no records.
        """
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'keywords'):
            try:
                print(f"PybibxAnalyzer: Calling conceptual pybibx.analysis.keywords (cooccurrence, threshold {keyword_threshold}).")
                # Hypothetical: pybibx.analysis.keywords returns (list_of_nodes, list_of_edge_tuples)
                # e.g., nodes = ["kw A", "kw B"], edges = [("kw A", "kw B", 5)]
                pybibx_nodes, pybibx_edges = pybibx.analysis.keywords(
                    self.pybibx_corpus,
                    method="cooccurrence",
                    threshold=keyword_threshold
                )
                return self._transform_pybibx_network_output(pybibx_nodes, pybibx_edges, "keyword-cooccurrence")
            except Exception as e:
                print(f"PybibxAnalyzer: Error during conceptual pybibx keyword co-occurrence - {e}. Falling back to placeholder.")

        # --- Placeholder Logic ---
        print(f"PybibxAnalyzer: Using placeholder keyword co-occurrence network (threshold {keyword_threshold}).")
        nodes = set()
        edges = {}
        for record in self.records:
            keywords = [kw.lower() for kw in record.get("keywords", []) if isinstance(kw, str)]
            if len(keywords) > 1:
                for kw in keywords: nodes.add(kw)
                for i in range(len(keywords)):
                    for j in range(i + 1, len(keywords)):
                        kw1, kw2 = tuple(sorted((keywords[i], keywords[j])))
                        if kw1 == kw2: continue
                        edge = (kw1, kw2)
                        edges[edge] = edges.get(edge, 0) + 1

        final_edges = [{"source": u, "target": v, "weight": w} for (u,v), w in edges.items() if w >= keyword_threshold]
        final_nodes_set = set()
        for edge_data in final_edges:
            final_nodes_set.add(edge_data["source"])
            final_nodes_set.add(edge_data["target"])
        final_nodes = [{"id": node} for node in final_nodes_set]
        return {"nodes": final_nodes, "edges": final_edges, "type": "keyword-cooccurrence"}


    def citation_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Performs citation analysis on the publication records and returns a summary of the most cited papers.
        
        If the `pybibx` library is available and supports citation analysis, this method uses it to generate a summary including the top cited documents and total papers with citation data. If `pybibx` is unavailable or an error occurs, it falls back to aggregating citation counts from available fields in the records and returns the top 10 most cited papers.
        
        Returns:
            A dictionary containing:
                - "most_cited_papers": List of the top cited papers with their titles, DOIs, and citation counts.
                - "total_papers_with_citation_data": Number of papers with available citation data.
                - "raw_pybibx_summary": (If `pybibx` is used) The raw summary output from `pybibx`.
            Returns None if there are no records to analyze.
        """
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'citation_summary'): # Renamed for clarity
            try:
                print("PybibxAnalyzer: Calling conceptual pybibx.analysis.citation_summary.")
                # Hypothetical: pybibx.analysis.citation_summary returns a dict like:
                # {
                #   "total_papers_analyzed": N,
                #   "papers_with_citations": M,
                #   "total_citations_in_corpus": C, (sum of TC fields it found)
                #   "top_cited_documents": [
                #       {"title": "P1", "doi": "d1", "pybibx_citations": c1, "original_record_index": i1}, ...
                #   ],
                #   "average_citations_per_paper": X.X
                # }
                # This assumes pybibx can use the 'TC' field we mapped or calculates its own.
                pybibx_summary_dict = pybibx.analysis.citation_summary(self.pybibx_corpus, top_n=10)

                # Transform this hypothetical pybibx_summary_dict to our expected output format
                transformed_results = {
                    "most_cited_papers": [],
                    "total_papers_with_citation_data": pybibx_summary_dict.get("papers_with_citations", 0),
                    "raw_pybibx_summary": pybibx_summary_dict # Include the raw output too
                }
                if "top_cited_documents" in pybibx_summary_dict:
                    for item in pybibx_summary_dict["top_cited_documents"]:
                        transformed_results["most_cited_papers"].append({
                            "title": item.get("title", "N/A"),
                            "doi": item.get("doi", "N/A"),
                            "citations": item.get("pybibx_citations") # Use the count from pybibx
                        })
                return transformed_results
            except Exception as e:
                print(f"PybibxAnalyzer: Error during conceptual pybibx citation_summary - {e}. Falling back to placeholder.")

        # --- Placeholder Logic ---
        print("PybibxAnalyzer: Using placeholder citation analysis (based on available 'times_cited_...' fields).")
        most_cited_papers = []
        for record in self.records:
            citations = record.get("times_cited_wos") or \
                        record.get("times_cited_scopus") or \
                        record.get("times_cited_openalex") or \
                        record.get("cited_by_count")
            if citations is not None:
                try:
                    citations = int(citations)
                    most_cited_papers.append({
                        "title": record.get("title", "N/A"),
                        "doi": record.get("doi", "N/A"),
                        "citations": citations})
                except ValueError: pass
        most_cited_papers.sort(key=lambda x: x["citations"], reverse=True)
        return {
            "most_cited_papers": most_cited_papers[:10],
            "total_papers_with_citation_data": len(most_cited_papers)
        }

if __name__ == "__main__":
    # Example Usage (simulated)
    sample_records_data = [
        {
            "title": "Paper A", "authors": ["Smith, J", "Doe, A"], "year": 2020,
            "keywords": ["ai", "ml", "data"], "doi": "10.1/a", "times_cited_wos": 10
        },
        {
            "title": "Paper B", "authors": ["Doe, A", "Lee, C"], "year": 2021,
            "keywords": ["ml", "nlp", "data"], "doi": "10.1/b", "times_cited_wos": 25
        },
        {
            "title": "Paper C", "authors": ["Smith, J", "Lee, C"], "year": 2020,
            "keywords": ["ai", "robotics"], "doi": "10.1/c", "times_cited_wos": 5
        },
        {
            "title": "Paper D", "authors": ["Solo, X"], "year": 2022,
            "keywords": ["quantom", "physics"], "doi": "10.1/d", "times_cited_wos": 100
        },
         {
            "title": "Paper E", "authors": ["Smith, J", "Doe, A", "Lee, C"], "year": 2023,
            "keywords": ["ai", "ethics", "data"], "doi": "10.1/e", "times_cited_wos": 1
        },
    ]

    analyzer = PybibxAnalyzer(sample_records_data)

    print("\n--- Co-authorship Network (threshold 1) ---")
    coauth_net = analyzer.co_authorship_network(author_threshold=1)
    if coauth_net:
        print(f"Nodes: {len(coauth_net['nodes'])}")
        for node in coauth_net['nodes'][:3]: print(f"  {node}") # Print first 3
        print(f"Edges: {len(coauth_net['edges'])}")
        for edge in coauth_net['edges'][:3]: print(f"  {edge}") # Print first 3

    print("\n--- Co-authorship Network (threshold 2) ---")
    coauth_net_t2 = analyzer.co_authorship_network(author_threshold=2)
    if coauth_net_t2:
        print(f"Nodes: {len(coauth_net_t2['nodes'])}")
        for node in coauth_net_t2['nodes'][:3]: print(f"  {node}")
        print(f"Edges: {len(coauth_net_t2['edges'])}") # Should be fewer or different
        for edge in coauth_net_t2['edges'][:3]: print(f"  {edge}")


    print("\n--- Keyword Co-occurrence Network (threshold 1) ---")
    kw_net = analyzer.keyword_cooccurrence_network(keyword_threshold=1)
    if kw_net:
        print(f"Nodes: {len(kw_net['nodes'])}")
        for node in kw_net['nodes'][:3]: print(f"  {node}")
        print(f"Edges: {len(kw_net['edges'])}")
        for edge in kw_net['edges'][:3]: print(f"  {edge}")

    print("\n--- Citation Analysis ---")
    citation_stats = analyzer.citation_analysis()
    if citation_stats:
        print(f"Total papers with citation data: {citation_stats['total_papers_with_citation_data']}")
        print("Most cited papers (top 10):")
        for paper in citation_stats['most_cited_papers']:
            print(f"  '{paper['title']}' - Citations: {paper['citations']}")
