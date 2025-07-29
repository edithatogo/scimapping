from typing import List, Dict, Any, Optional, Tuple # Added Tuple
from typing_extensions import TypedDict # For TypedDict

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

# --- TypedDict Definitions for Conceptual pybibx Data Structures ---

class PybibxRecordInput(TypedDict, total=False):
    """
    Represents the conceptual structure of a single record passed to pybibx.
    Fields are optional as not all records might have all information.
    """
    id: str # Unique identifier for the record (e.g., DOI or internal ID)
    title: str
    authors: List[str]
    year: int
    keywords: List[str]
    references: List[str] # List of IDs of cited works (e.g., DOIs)
    source_journal: str
    abstract: str
    # Potentially other fields pybibx might use, like 'document_type', 'language', 'times_cited'


# --- TypedDicts for Conceptual pybibx Analysis Outputs ---

# For Network outputs (Co-authorship, Keyword Co-occurrence)
class PybibxNetworkNode(TypedDict):
    id: str     # Node identifier (e.g., author name, keyword)
    label: str  # Display label for the node
    size: int   # e.g., publication count for authors, occurrence count for keywords

class PybibxNetworkEdge(TypedDict):
    source: str  # ID of the source node
    target: str  # ID of the target node
    weight: int  # e.g., co-authorship count, co-occurrence frequency

class PybibxNetworkOutput(TypedDict):
    nodes: List[PybibxNetworkNode]
    edges: List[PybibxNetworkEdge]
    type: str # e.g., "co-authorship", "keyword-cooccurrence"

# For Citation Analysis Output
class PybibxCitedPaper(TypedDict, total=False):
    id: str # DOI or other ID of the cited paper
    title: str
    citations: int # Number of citations it received (within the corpus or globally, depending on pybibx)

class PybibxCitationAnalysisOutput(TypedDict, total=False):
    total_citations_in_corpus: int # Sum of citations for all papers in the input set
    papers_with_citation_data: int # Count of papers that had citation information
    h_index_corpus: Optional[int] # h-index calculated for the input set of papers
    average_citations_per_paper: Optional[float]
    top_cited_papers: List[PybibxCitedPaper] # List of top N cited papers from the input set


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
        self.pybibx_corpus = None # This would be the pybibx Corpus object

        if PYBIBX_AVAILABLE and pybibx:
            try:
                # Conceptual: Map internal record format to what pybibx might expect
                # pybibx might expect specific field names (e.g., WoS tags like 'AU', 'DE', 'CR', 'PY', 'TI', 'SO')
                # Conceptual: Map internal record format to PybibxRecordInput
                # This is a placeholder for the actual transformation logic.
                # A real implementation would carefully map fields and handle missing data.

                pybibx_input_records: List[PybibxRecordInput] = []
                for i, rec in enumerate(self.records):
                    # Use DOI as primary ID, fallback to a generated one if DOI is missing for pybibx.
                    record_id = rec.get("doi") or f"internal_id_{i}"

                    # Ensure all fields are of the correct type or None for PybibxRecordInput
                    # (which has total=False, so missing keys are okay)
                    mapped_rec: PybibxRecordInput = {
                        "id": record_id,
                        "title": rec.get("title"),
                        "authors": rec.get("authors"),
                        "year": rec.get("year"),
                        "keywords": rec.get("keywords"),
                        "references": rec.get("cited_references"), # List of cited DOIs/IDs
                        "source_journal": rec.get("journal"),
                        "abstract": rec.get("abstract")
                        # 'times_cited' could be another field if pybibx uses it directly
                    }
                    # Filter out None values to create a sparse dictionary, as pybibx might prefer this.
                    # PybibxRecordInput(total=False) handles missing keys gracefully.
                    pybibx_input_records.append({k: v for k, v in mapped_rec.items() if v is not None}) # type: ignore

                # self.pybibx_corpus = pybibx.Corpus(pybibx_input_records) # Conceptual instantiation
                # For actual pybibx, the input might be a list of objects or a specific file format.
                # For now, we store the conceptually transformed records if needed by placeholder logic.
                self.conceptual_pybibx_input_records = pybibx_input_records
                # If pybibx.Corpus expects a list of dicts directly:
                self.pybibx_corpus = pybibx.Corpus(self.conceptual_pybibx_input_records)
                print("PybibxAnalyzer: Successfully initialized and mapped records to pybibx.Corpus (conceptual).")
            except Exception as e:
                print(f"PybibxAnalyzer: Error initializing pybibx.Corpus - {e}. Will use placeholder logic.")
                self.pybibx_corpus = None
        else:
            print("PybibxAnalyzer: pybibx not fully available. Using placeholder logic for all analyses.")

    def _transform_pybibx_network_output(
        self,
        pybibx_nodes: Optional[List[Any]],  # pybibx might return list of node names/IDs
        pybibx_edges: Optional[List[Tuple[Any, Any, int]]], # pybibx might return list of (u,v,w) tuples
        network_type: str,
        # Conceptual: pybibx might provide node attributes like size separately or not at all
        # For this transformation, we'll assume node_sizes_map is {node_id: size} if available
        node_sizes_map: Optional[Dict[str, int]] = None
        ) -> PybibxNetworkOutput:
        """
        Transforms hypothetical pybibx network output into our PybibxNetworkOutput TypedDict.

        Args:
            pybibx_nodes: List of node identifiers (e.g., author names, keywords).
            pybibx_edges: List of edge tuples (e.g., (item1, item2, weight)).
            network_type: String identifier for the network type.
            node_sizes_map: Optional dictionary mapping node ID to its size.
        """
        if pybibx_nodes is None: pybibx_nodes = []
        if pybibx_edges is None: pybibx_edges = []
        if node_sizes_map is None: node_sizes_map = {}

        nodes_transformed: List[PybibxNetworkNode] = []
        for node_id_any in pybibx_nodes:
            node_id = str(node_id_any)
            nodes_transformed.append({
                "id": node_id,
                "label": node_id, # Default label to id
                "size": node_sizes_map.get(node_id, 1) # Default size to 1 if not provided
            })

        edges_transformed: List[PybibxNetworkEdge] = []
        for u_any, v_any, w_any in pybibx_edges:
            edges_transformed.append({
                "source": str(u_any),
                "target": str(v_any),
                "weight": int(w_any)
            })

        return {"nodes": nodes_transformed, "edges": edges_transformed, "type": network_type}

    def co_authorship_network(self, author_threshold: int = 1) -> Optional[PybibxNetworkOutput]:
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
        author_counts: Dict[str, int] = {}
        edges_dict: Dict[Tuple[str, str], int] = {}

        for record in self.records:
            authors = record.get("authors", [])
            if not authors or not isinstance(authors, list):
                continue

            unique_authors_in_record = sorted(list(set(str(auth) for auth in authors if auth and isinstance(auth, str))))

            for author in unique_authors_in_record:
                author_counts[author] = author_counts.get(author, 0) + 1

            if len(unique_authors_in_record) > 1:
                for i in range(len(unique_authors_in_record)):
                    for j in range(i + 1, len(unique_authors_in_record)):
                        # Authors already sorted within unique_authors_in_record, direct tuple is fine
                        auth1, auth2 = unique_authors_in_record[i], unique_authors_in_record[j]
                        edge = (auth1, auth2) # Tuple will be sorted by Python if elements are comparable
                        edges_dict[edge] = edges_dict.get(edge, 0) + 1

        final_edges: List[PybibxNetworkEdge] = []
        for (u,v), w in edges_dict.items():
            if w >= author_threshold:
                final_edges.append({"source": u, "target": v, "weight": w})

        # Determine nodes that are part of the filtered edges
        nodes_in_filtered_edges: set[str] = set()
        for edge_data in final_edges:
            nodes_in_filtered_edges.add(edge_data["source"])
            nodes_in_filtered_edges.add(edge_data["target"])

        final_nodes: List[PybibxNetworkNode] = []
        for author_name in nodes_in_filtered_edges:
            final_nodes.append({
                "id": author_name,
                "label": author_name,
                "size": author_counts.get(author_name, 0) # Get actual count
            })

        return {"nodes": final_nodes, "edges": final_edges, "type": "co-authorship"}


    def keyword_cooccurrence_network(self, keyword_threshold: int = 1) -> Optional[PybibxNetworkOutput]:
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
        keyword_counts: Dict[str, int] = {}
        edges_dict: Dict[Tuple[str, str], int] = {}

        for record in self.records:
            keywords_raw = record.get("keywords", [])
            if not keywords_raw or not isinstance(keywords_raw, list):
                continue

            # Normalize keywords (e.g., lowercase, strip) and get unique keywords per record
            unique_keywords_in_record = sorted(list(set(
                str(kw).lower().strip() for kw in keywords_raw if kw and isinstance(kw, str) and str(kw).strip()
            )))

            for kw in unique_keywords_in_record:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            if len(unique_keywords_in_record) > 1:
                for i in range(len(unique_keywords_in_record)):
                    for j in range(i + 1, len(unique_keywords_in_record)):
                        # Keywords already sorted in unique_keywords_in_record
                        kw1, kw2 = unique_keywords_in_record[i], unique_keywords_in_record[j]
                        # No need to check kw1 == kw2 as they are from a set initially
                        edge = (kw1, kw2)
                        edges_dict[edge] = edges_dict.get(edge, 0) + 1

        final_edges: List[PybibxNetworkEdge] = []
        for (u,v), w in edges_dict.items():
            if w >= keyword_threshold:
                final_edges.append({"source": u, "target": v, "weight": w})

        nodes_in_filtered_edges: set[str] = set()
        for edge_data in final_edges:
            nodes_in_filtered_edges.add(edge_data["source"])
            nodes_in_filtered_edges.add(edge_data["target"])

        final_nodes: List[PybibxNetworkNode] = []
        for kw_name in nodes_in_filtered_edges:
            final_nodes.append({
                "id": kw_name,
                "label": kw_name,
                "size": keyword_counts.get(kw_name, 0) # Get actual frequency
            })

        return {"nodes": final_nodes, "edges": final_edges, "type": "keyword-cooccurrence"}


    def citation_analysis(self) -> Optional[PybibxCitationAnalysisOutput]:
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
                # This assumes pybibx can use a 'times_cited' field we might map into PybibxRecordInput,
                # or it calculates citations from the 'references' field.
                pybibx_summary_dict: Dict[str, Any] = pybibx.analysis.citation_summary(self.pybibx_corpus, top_n=10)

                # Transform this hypothetical pybibx_summary_dict to PybibxCitationAnalysisOutput
                # This is still conceptual as pybibx_summary_dict structure is hypothetical.
                top_papers_transformed: List[PybibxCitedPaper] = []
                if "top_cited_documents" in pybibx_summary_dict and isinstance(pybibx_summary_dict["top_cited_documents"], list):
                    for item in pybibx_summary_dict["top_cited_documents"]:
                        if isinstance(item, dict):
                            top_papers_transformed.append({
                                "id": item.get("id", item.get("doi", "N/A")), # Prefer 'id' from pybibx record
                                "title": item.get("title", "N/A"),
                                "citations": item.get("pybibx_citations", item.get("citations", 0))
                            })

                # Ensure all keys of PybibxCitationAnalysisOutput are present, even if as None/default
                output: PybibxCitationAnalysisOutput = {
                    "total_citations_in_corpus": pybibx_summary_dict.get("total_citations_in_corpus", 0),
                    "papers_with_citation_data": pybibx_summary_dict.get("papers_with_citations", 0),
                    "h_index_corpus": pybibx_summary_dict.get("h_index_corpus"), # Optional, so get() is fine
                    "average_citations_per_paper": pybibx_summary_dict.get("average_citations_per_paper"), # Optional
                    "top_cited_papers": top_papers_transformed
                    # "raw_pybibx_summary": pybibx_summary_dict # Optionally include raw output
                }
                return output
            except Exception as e:
                print(f"PybibxAnalyzer: Error during conceptual pybibx citation_summary - {e}. Falling back to placeholder.")

        # --- Placeholder Logic ---
        print("PybibxAnalyzer: Using placeholder citation analysis (based on available 'times_cited_...' fields).")
        placeholder_top_cited: List[PybibxCitedPaper] = []
        total_citations = 0
        papers_with_citations = 0

        for i, record in enumerate(self.records):
            citations_val = record.get("times_cited_wos") or \
                            record.get("times_cited_scopus") or \
                            record.get("times_cited_openalex") or \
                            record.get("cited_by_count") # This is OpenAlex specific, consider a generic internal name?

            citations_int: Optional[int] = None
            if citations_val is not None:
                try:
                    citations_int = int(citations_val)
                    papers_with_citations += 1
                    total_citations += citations_int
                except ValueError:
                    pass # Could not convert to int

            if citations_int is not None: # Add to list only if citations could be parsed as int
                placeholder_top_cited.append({
                    "id": record.get("doi") or f"internal_id_{i}", # Use DOI or internal ID
                    "title": record.get("title", "N/A"),
                    "citations": citations_int
                })

        placeholder_top_cited.sort(key=lambda x: x.get("citations", 0), reverse=True)

        avg_citations: Optional[float] = None
        if papers_with_citations > 0:
            avg_citations = total_citations / papers_with_citations

        # Placeholder h-index (very naive, actual h-index needs sorted list of citations)
        # For a proper placeholder, one might sort all citation counts and calculate it.
        # For now, just a None.
        h_index_placeholder: Optional[int] = None

        return {
            "total_citations_in_corpus": total_citations,
            "papers_with_citation_data": papers_with_citations,
            "h_index_corpus": h_index_placeholder,
            "average_citations_per_paper": avg_citations,
            "top_cited_papers": placeholder_top_cited[:10]
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
