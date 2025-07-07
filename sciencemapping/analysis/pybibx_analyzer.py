from typing import List, Dict, Any, Optional

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
        Initializes the analyzer with a list of records in the common internal format.

        Args:
            records: A list of publication records.
        """
        self.records = records
        self.pybibx_corpus = None

        if PYBIBX_AVAILABLE and pybibx:
            try:
                # This assumes pybibx.Corpus can take a list of dicts.
                # Field name mapping might be needed here if our internal format
                # doesn't match pybibx's expectations perfectly.
                # For now, assume direct compatibility or that pybibx is flexible.
                self.pybibx_corpus = pybibx.Corpus(self.records)
                print("PybibxAnalyzer: Successfully initialized pybibx.Corpus.")
            except Exception as e:
                print(f"PybibxAnalyzer: Error initializing pybibx.Corpus - {e}. Will use placeholder logic.")
                self.pybibx_corpus = None # Ensure fallback
        else:
            print("PybibxAnalyzer: pybibx not fully available. Using placeholder logic for all analyses.")


    def _transform_pybibx_network_output(self, pybibx_network_result: Any, network_type: str) -> Dict[str, Any]:
        """
        Transforms hypothetical pybibx network output into our standard dict format.
        This is a placeholder for actual transformation logic.
        Assumes pybibx_network_result might be an object with .nodes() and .edges(data=True)
        similar to NetworkX, or a dict already.
        """
        if not pybibx_network_result:
            return {"nodes": [], "edges": [], "type": network_type}

        # Placeholder: Assume pybibx_network_result is already in a compatible dict format
        # or has methods to export to it.
        if isinstance(pybibx_network_result, dict) and "nodes" in pybibx_network_result and "edges" in pybibx_network_result:
            return {**pybibx_network_result, "type": network_type}

        # If pybibx_network_result is like a NetworkX graph G:
        # nodes = [{"id": str(node), **data} for node, data in getattr(pybibx_network_result, 'nodes', lambda data=True: [] )(data=True)]
        # edges = [{"source": str(u), "target": str(v), **data} for u, v, data in getattr(pybibx_network_result, 'edges', lambda data=True: [])(data=True)]
        # return {"nodes": nodes, "edges": edges, "type": network_type}

        # Fallback if transformation is unknown for this placeholder
        print(f"PybibxAnalyzer: Warning - Could not transform pybibx '{network_type}' network output of type {type(pybibx_network_result)}. Returning raw or empty.")
        if isinstance(pybibx_network_result, dict): # If it's a dict but not matching, return as is
            return {**pybibx_network_result, "type": network_type}
        return {"nodes": [], "edges": [], "type": network_type, "raw_pybibx_output": str(pybibx_network_result)}


    def co_authorship_network(self, author_threshold: int = 1) -> Optional[Dict[str, Any]]:
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'coauthorship'):
            try:
                print(f"PybibxAnalyzer: Calling pybibx.analysis.coauthorship with threshold {author_threshold}.")
                # Hypothetical actual pybibx call structure
                # This assumes pybibx.analysis.coauthorship exists and takes corpus and threshold
                raw_network = pybibx.analysis.coauthorship(self.pybibx_corpus, threshold=author_threshold)
                return self._transform_pybibx_network_output(raw_network, "co-authorship")
            except Exception as e:
                print(f"PybibxAnalyzer: Error during pybibx co-authorship analysis - {e}. Falling back to placeholder.")
                # Fall through to placeholder if pybibx call fails

        # --- Placeholder Logic (if pybibx not available or call failed) ---
        print(f"PybibxAnalyzer: Using placeholder co-authorship network generation (threshold {author_threshold}).")
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
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'keywords'):
            try:
                print(f"PybibxAnalyzer: Calling pybibx.analysis.keywords (cooccurrence) with threshold {keyword_threshold}.")
                # Hypothetical actual pybibx call structure
                # This assumes pybibx.analysis.keywords exists and can do co-occurrence
                raw_network = pybibx.analysis.keywords(self.pybibx_corpus, method="cooccurrence", threshold=keyword_threshold)
                return self._transform_pybibx_network_output(raw_network, "keyword-cooccurrence")
            except Exception as e:
                print(f"PybibxAnalyzer: Error during pybibx keyword co-occurrence analysis - {e}. Falling back to placeholder.")
                # Fall through to placeholder

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
        if not self.records: return None

        if self.pybibx_corpus and PYBIBX_AVAILABLE and pybibx and hasattr(pybibx, 'analysis') and hasattr(pybibx.analysis, 'citations'):
            try:
                print("PybibxAnalyzer: Calling pybibx.analysis.citations.")
                # Hypothetical actual pybibx call
                citation_stats_raw = pybibx.analysis.citations(self.pybibx_corpus)
                # Assume citation_stats_raw needs transformation
                # This is highly speculative as pybibx citation output is unknown
                # For placeholder, assume it might return a list of records with a 'pybibx_citations' field
                # or a dict with 'most_cited_papers', 'h_index_authors' etc.
                # For now, let's assume a simple dict structure is returned by pybibx:
                if isinstance(citation_stats_raw, dict) and "most_cited_papers" in citation_stats_raw:
                    return citation_stats_raw
                else: # Fallback to our placeholder if pybibx output is not as expected or needs complex parsing
                    print("PybibxAnalyzer: pybibx citation output format not recognized or needs parsing. Falling back to placeholder.")
            except Exception as e:
                print(f"PybibxAnalyzer: Error during pybibx citation analysis - {e}. Falling back to placeholder.")
                # Fall through to placeholder

        # --- Placeholder Logic ---
        print("PybibxAnalyzer: Using placeholder citation analysis.")
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
