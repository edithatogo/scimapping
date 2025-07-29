import unittest
from unittest.mock import patch, MagicMock

from sciencemapping.analysis.pybibx_analyzer import PybibxAnalyzer

SAMPLE_RECORDS = [
    {"title": "Paper A", "authors": ["Smith, J", "Doe, A"], "year": 2020, "keywords": ["ai", "ml", "data"], "doi": "10.1/a", "times_cited_wos": 10},
    {"title": "Paper B", "authors": ["Doe, A", "Lee, C"], "year": 2021, "keywords": ["ml", "nlp", "data"], "doi": "10.1/b", "times_cited_wos": 25},
    {"title": "Paper C", "authors": ["Smith, J", "Lee, C"], "year": 2020, "keywords": ["ai", "robotics"], "doi": "10.1/c", "times_cited_wos": 5},
    {"title": "Paper D", "authors": ["Solo, X"], "year": 2022, "keywords": ["quantum", "physics"], "doi": "10.1/d", "times_cited_wos": 100},
    {"title": "Paper E", "authors": ["Smith, J", "Doe, A", "Lee, C"], "year": 2023, "keywords": ["ai", "ethics", "data"], "doi": "10.1/e", "times_cited_wos": 1},
    {"title": "Paper F", "authors": ["NoKw, Z"], "year": 2023, "keywords": [], "doi": "10.1/f", "times_cited_openalex": 3},
    {"title": "Paper G", "authors": [], "year": 2023, "keywords": ["lonely", "research"], "doi": "10.1/g", "cited_by_count": 7}
]

class TestPybibxAnalyzer(unittest.TestCase):

    def setUp(self):
        # This analyzer might see the actual PYBIBX_AVAILABLE state at import time of its module
        self.analyzer_placeholder_default = PybibxAnalyzer(SAMPLE_RECORDS)
        self.empty_analyzer = PybibxAnalyzer([])

    @patch('sciencemapping.analysis.pybibx_analyzer.pybibx')
    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', True)
    def test_co_authorship_network_with_pybibx_success(self, mock_pybibx_module): # Only one mock arg expected
        """Test co-authorship network when pybibx is available and call succeeds."""
        mock_corpus_instance = MagicMock(name="MockPybibxCorpus")
        mock_pybibx_module.Corpus.return_value = mock_corpus_instance

        # Define mock raw output from pybibx.analysis.coauthorship
        mock_raw_pybibx_nodes = ["Author A", "Author B"]
        mock_raw_pybibx_edges = [("Author A", "Author B", 2)]
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.coauthorship.return_value = (mock_raw_pybibx_nodes, mock_raw_pybibx_edges)

        analyzer_with_pybibx = PybibxAnalyzer(SAMPLE_RECORDS)
        network = analyzer_with_pybibx.co_authorship_network(author_threshold=1) # Threshold is used by pybibx call

        # Verify Corpus was called with mapped records (harder to check precisely without deep_equals on complex list of dicts)
        # For now, just check it was called. A more detailed check would compare the mapped structure.
        mock_pybibx_module.Corpus.assert_called()
        # Check that the first record passed to Corpus has at least one expected mapped key (e.g., 'AU' for authors)
        call_args_list = mock_pybibx_module.Corpus.call_args_list
        self.assertTrue(len(call_args_list) > 0)
        first_call_args = call_args_list[0][0][0] # First arg of first call
        self.assertTrue(len(first_call_args) > 0) # Records list not empty
        # Check if a sample mapped record has expected structure (e.g., 'AU' key if authors were mapped to 'AU')
        # Check if a sample mapped record has expected PybibxRecordInput structure
        self.assertIn("authors", first_call_args[0])
        self.assertEqual(first_call_args[0]["authors"], SAMPLE_RECORDS[0]["authors"])
        self.assertIn("id", first_call_args[0]) # DOI or generated ID

        # Mock output from pybibx.analysis.coauthorship, assuming it can also provide node sizes
        # For simplicity, let's say it returns nodes and edges, and _transform can use a default size.
        # Or, we can mock that pybibx.analysis.coauthorship returns a structure that includes sizes.
        # The _transform_pybibx_network_output takes an optional node_sizes_map.
        # We'll assume pybibx.analysis.coauthorship provides raw nodes, and the transformer uses default size for this mock.
        mock_pybibx_module.analysis.coauthorship.assert_called_once_with(mock_corpus_instance, threshold=1)

        # Verify transformed output (PybibxNetworkOutput)
        expected_nodes: List[PybibxNetworkNode] = [ # type: ignore
            {"id": "Author A", "label": "Author A", "size": 1}, # Default size
            {"id": "Author B", "label": "Author B", "size": 1}  # Default size
        ]
        expected_edges: List[PybibxNetworkEdge] = [ # type: ignore
            {"source": "Author A", "target": "Author B", "weight": 2}
        ]

        self.assertIsNotNone(network)
        self.assertEqual(network["type"], "co-authorship")
        # Sort nodes and edges by 'id' or 'source' for consistent comparison if order not guaranteed
        self.assertCountEqual(network["nodes"], expected_nodes) # Use assertCountEqual for lists of dicts
        self.assertCountEqual(network["edges"], expected_edges)

    @patch('sciencemapping.analysis.pybibx_analyzer.pybibx')
    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', True)
    def test_co_authorship_network_with_pybibx_api_error(self, mock_pybibx_module):
        """Test co-authorship network when pybibx call fails, falling back to placeholder."""
        mock_corpus_instance = MagicMock(name="MockPybibxCorpus")
        mock_pybibx_module.Corpus.return_value = mock_corpus_instance
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.coauthorship.side_effect = Exception("Simulated pybibx API error")

        analyzer_with_pybibx_error = PybibxAnalyzer(SAMPLE_RECORDS)

        with patch('builtins.print') as mock_print:
            network = analyzer_with_pybibx_error.co_authorship_network(author_threshold=1)
            mock_print.assert_any_call("PybibxAnalyzer: Error during conceptual pybibx co-authorship - Simulated pybibx API error. Falling back to placeholder.")
            mock_print.assert_any_call("PybibxAnalyzer: Using placeholder co-authorship network (threshold 1).")

        # Check placeholder results (structure should now match PybibxNetworkOutput)
        self.assertIsNotNone(network)
        self.assertTrue(all("id" in node and "label" in node and "size" in node for node in network["nodes"]))
        self.assertEqual(len(network["nodes"]), 4) # "Smith, J", "Doe, A", "Lee, C", "Solo, X" (NoKw, Z is isolated)
                                                 # Actually, placeholder only includes nodes in filtered edges.
                                                 # For threshold 1, Smith J, Doe A, Lee C are connected. Solo X is not.
                                                 # Smith,J - Doe,A (2); Smith,J - Lee,C (2); Doe,A - Lee,C (2)
                                                 # Nodes involved: Smith,J; Doe,A; Lee,C. So 3 nodes.
        self.assertEqual(len(network["nodes"]), 3)
        node_ids_t1 = {node["id"] for node in network["nodes"]}
        self.assertIn("Smith, J", node_ids_t1)
        self.assertEqual(len(network["edges"]), 3)
        # Example check for node size (Smith, J appears in 3 papers in SAMPLE_RECORDS)
        smith_node = next(n for n in network["nodes"] if n["id"] == "Smith, J")
        self.assertEqual(smith_node["size"], 3)


    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_co_authorship_network_fallback_placeholder(self):
        """Test co-authorship network uses placeholder when pybibx is initially unavailable."""
        analyzer_no_pybibx = PybibxAnalyzer(SAMPLE_RECORDS) # PYBIBX_AVAILABLE=False will be seen
        network_t1 = analyzer_no_pybibx.co_authorship_network(author_threshold=1)

        # Validating placeholder logic output (should conform to PybibxNetworkOutput)
        self.assertIsNotNone(network_t1)
        self.assertEqual(network_t1["type"], "co-authorship")
        self.assertTrue(all("id" in n and "label" in n and "size" in n for n in network_t1["nodes"]))

        self.assertEqual(len(network_t1["nodes"]), 3) # Smith, J; Doe, A; Lee, C
        node_ids_t1 = {node["id"] for node in network_t1["nodes"]}
        self.assertIn("Smith, J", node_ids_t1)
        self.assertIn("Doe, A", node_ids_t1)
        self.assertIn("Lee, C", node_ids_t1)

        # Check size for a specific author (Smith, J is in 3 papers)
        smith_node_t1 = next(n for n in network_t1["nodes"] if n["id"] == "Smith, J")
        self.assertEqual(smith_node_t1["size"], 3)

        self.assertEqual(len(network_t1["edges"]), 3) # (Smith,Doe), (Smith,Lee), (Doe,Lee) all with weight 2 or more

        network_t3 = analyzer_no_pybibx.co_authorship_network(author_threshold=3) # Paper E has all 3 authors
        # Smith,J - Doe,A (occurs in A, E) -> weight 2
        # Doe,A - Lee,C (occurs in B, E) -> weight 2
        # Smith,J - Lee,C (occurs in C, E) -> weight 2
        # So for threshold=3, no edges should remain.
        self.assertIsNotNone(network_t3)
        self.assertEqual(len(network_t3["nodes"]), 0) # No edges means no nodes in current placeholder logic
        self.assertEqual(len(network_t3["edges"]), 0)

    def test_co_authorship_network_empty_input_placeholder(self):
        """Test co-authorship with no records (uses placeholder)."""
        # This test uses self.empty_analyzer which would have seen original PYBIBX_AVAILABLE state
        # If original PYBIBX_AVAILABLE was True but Corpus init failed, it would print error then use placeholder
        # If original PYBIBX_AVAILABLE was False, it uses placeholder.
        # Placeholder returns None if self.records is empty.
        network = self.empty_analyzer.co_authorship_network()
        self.assertIsNone(network)


    @patch('sciencemapping.analysis.pybibx_analyzer.pybibx')
    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', True)
    def test_keyword_cooccurrence_with_pybibx_success(self, mock_pybibx_module): # mock_pybibx_available removed
        mock_corpus = MagicMock(name="MockPybibxCorpus_KW")
        mock_pybibx_module.Corpus.return_value = mock_corpus

        mock_raw_pybibx_nodes = ["ml", "ai"]
        mock_raw_pybibx_edges = [("ml", "ai", 5)]
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.keywords.return_value = (mock_raw_pybibx_nodes, mock_raw_pybibx_edges)

        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        result = analyzer.keyword_cooccurrence_network(keyword_threshold=2) # Example threshold

        mock_pybibx_module.Corpus.assert_called() # Check that Corpus was initialized
        mock_pybibx_module.analysis.keywords.assert_called_once_with(
            mock_corpus,
            method="cooccurrence",
            threshold=2
        )

        expected_nodes: List[PybibxNetworkNode] = [ # type: ignore
            {"id": "ml", "label": "ml", "size": 1}, # Default size from _transform
            {"id": "ai", "label": "ai", "size": 1}  # Default size from _transform
        ]
        expected_edges: List[PybibxNetworkEdge] = [ # type: ignore
            {"source": "ml", "target": "ai", "weight": 5}
        ]
        self.assertCountEqual(result["nodes"], expected_nodes)
        self.assertCountEqual(result["edges"], expected_edges)
        self.assertEqual(result["type"], "keyword-cooccurrence")

    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_keyword_cooccurrence_fallback_placeholder(self): # Removed mock_pybibx_unavailable
        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        network_t1 = analyzer.keyword_cooccurrence_network(keyword_threshold=1)
        self.assertIsNotNone(network_t1)
        self.assertEqual(network_t1["type"], "keyword-cooccurrence")
        self.assertTrue(all("id" in n and "label" in n and "size" in n for n in network_t1["nodes"]))

        # Example check for a specific keyword's size (e.g., 'data' appears in 3 papers)
        data_node = next((n for n in network_t1["nodes"] if n["id"] == "data"), None)
        self.assertIsNotNone(data_node)
        self.assertEqual(data_node["size"], 3)

        # Check number of edges based on SAMPLE_RECORDS and threshold 1
        # ai-ml (A), ai-data (A), ml-data (A)
        # ml-nlp (B), ml-data (B), nlp-data (B)
        # ai-robotics (C)
        # quantum-physics (D)
        # ai-ethics (E), ai-data (E), ethics-data (E)
        # lonely-research (G)
        # Unique edges: (ai,data), (ai,ethics), (ai,ml), (ai,robotics), (data,ethics), (data,ml), (data,nlp)
        # (lonely,research), (ml,nlp), (physics,quantum) -> 10 edges
        self.assertEqual(len(network_t1["edges"]), 10)

        network_t2 = analyzer.keyword_cooccurrence_network(keyword_threshold=2)
        # Edges with weight >= 2:
        # (ai,data) from A, E -> weight 2
        # (ml,data) from A, B -> weight 2
        self.assertIsNotNone(network_t2)
        self.assertEqual(len(network_t2["edges"]), 2)
        # Nodes involved in edges with weight >= 2: ai, data, ml
        self.assertEqual(len(network_t2["nodes"]), 3)
        self.assertTrue(all("id" in n and "label" in n and "size" in n for n in network_t2["nodes"]))


    def test_keyword_cooccurrence_empty_input_placeholder(self):
        network = self.empty_analyzer.keyword_cooccurrence_network()
        self.assertIsNone(network)


    @patch('sciencemapping.analysis.pybibx_analyzer.pybibx')
    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', True)
    def test_citation_analysis_with_pybibx_success(self, mock_pybibx_module): # mock_pybibx_available removed
        mock_corpus = MagicMock(name="MockPybibxCorpus_Cite")
        mock_pybibx_module.Corpus.return_value = mock_corpus

        # Hypothetical raw output from pybibx.analysis.citation_summary
        mock_raw_pybibx_citation_summary = {
            "total_papers_analyzed": len(SAMPLE_RECORDS),
            "papers_with_citations": 1,
            "total_citations_in_corpus": 50,
            "top_cited_documents": [
                {"title": "Pybibx Top Paper", "doi": "pd1", "pybibx_citations": 50, "original_record_index": 0},
            ],
            "average_citations_per_paper": 25.0 # Example
        }
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.citation_summary.return_value = mock_raw_pybibx_citation_summary

        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        result = analyzer.citation_analysis()

        mock_pybibx_module.Corpus.assert_called()
        mock_pybibx_module.analysis.citation_summary.assert_called_once_with(mock_corpus, top_n=10)

        # Verify transformed output (PybibxCitationAnalysisOutput)
        expected_output: PybibxCitationAnalysisOutput = { # type: ignore
            "total_citations_in_corpus": 50, # From mock_raw_pybibx_citation_summary
            "papers_with_citation_data": 1,    # From mock_raw_pybibx_citation_summary
            "h_index_corpus": None,  # Assuming pybibx mock doesn't provide it or it's None
            "average_citations_per_paper": 25.0, # From mock_raw_pybibx_citation_summary
            "top_cited_papers": [{
                "id": "pd1", # Assuming 'doi' is used as 'id' in transformation
                "title": "Pybibx Top Paper",
                "citations": 50
            }]
            # "raw_pybibx_summary" is no longer part of the defined TypedDict,
            # but the conceptual pybibx call could still return it inside its dict.
            # For strict TypedDict adherence, it should be removed or added to TypedDict if desired.
            # Let's assume it's not part of the strict output for now.
        }

        self.assertIsNotNone(result)
        self.assertEqual(result.get("total_citations_in_corpus"), expected_output.get("total_citations_in_corpus"))
        self.assertEqual(result.get("papers_with_citation_data"), expected_output.get("papers_with_citation_data"))
        self.assertEqual(result.get("h_index_corpus"), expected_output.get("h_index_corpus"))
        self.assertEqual(result.get("average_citations_per_paper"), expected_output.get("average_citations_per_paper"))
        self.assertCountEqual(result.get("top_cited_papers", []), expected_output.get("top_cited_papers", []))

    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_citation_analysis_fallback_placeholder(self): # Removed mock_pybibx_unavailable argument
        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        stats = analyzer.citation_analysis()

        self.assertIsNotNone(stats)
        self.assertIn("total_citations_in_corpus", stats)
        self.assertIn("papers_with_citation_data", stats)
        self.assertIn("h_index_corpus", stats) # Should be None from placeholder
        self.assertIn("average_citations_per_paper", stats)
        self.assertIn("top_cited_papers", stats)

        self.assertEqual(stats["papers_with_citation_data"], 7) # All sample records have some citation count
        self.assertEqual(stats["most_cited_papers"][0]["title"], "Paper D") # Paper D has 100 citations
        self.assertEqual(stats["most_cited_papers"][0]["id"], "10.1/d") # Check ID
        self.assertTrue(all("id" in p and "title" in p and "citations" in p for p in stats["top_cited_papers"]))

        # Calculate expected total and average for placeholder
        expected_total_citations = 10 + 25 + 5 + 100 + 1 + 3 + 7 # 151
        expected_avg_citations = expected_total_citations / 7
        self.assertEqual(stats["total_citations_in_corpus"], expected_total_citations)
        self.assertAlmostEqual(stats["average_citations_per_paper"], expected_avg_citations)
        self.assertIsNone(stats["h_index_corpus"]) # Placeholder returns None for h-index

    def test_citation_analysis_empty_input_placeholder(self):
        stats = self.empty_analyzer.citation_analysis()
        self.assertIsNone(stats)

if __name__ == '__main__':
    unittest.main()
