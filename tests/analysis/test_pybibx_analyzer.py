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
        # This depends on the exact mapping logic in PybibxAnalyzer.__init__
        # For example, if authors are mapped to 'AU':
        self.assertIn("AU", first_call_args[0])
        self.assertEqual(first_call_args[0]["AU"], SAMPLE_RECORDS[0]["authors"])


        mock_pybibx_module.analysis.coauthorship.assert_called_once_with(mock_corpus_instance, threshold=1)

        # Verify transformed output
        expected_transformed_nodes = [{"id": "Author A"}, {"id": "Author B"}]
        expected_transformed_edges = [{"source": "Author A", "target": "Author B", "weight": 2}]

        self.assertIsNotNone(network)
        self.assertEqual(network["type"], "co-authorship")
        self.assertListEqual(network["nodes"], expected_transformed_nodes)
        self.assertListEqual(network["edges"], expected_transformed_edges)

    @patch('sciencemapping.analysis.pybibx_analyzer.pybibx')
    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', True)
    def test_co_authorship_network_with_pybibx_api_error(self, mock_pybibx_module): # Only one mock arg expected
        """Test co-authorship network when pybibx call fails, falling back to placeholder."""
        mock_corpus_instance = MagicMock(name="MockPybibxCorpus")
        mock_pybibx_module.Corpus.return_value = mock_corpus_instance
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.coauthorship.side_effect = Exception("Simulated pybibx API error")

        analyzer_with_pybibx_error = PybibxAnalyzer(SAMPLE_RECORDS)

        with patch('builtins.print') as mock_print: # To check error messages
            network = analyzer_with_pybibx_error.co_authorship_network(author_threshold=1)
            mock_print.assert_any_call("PybibxAnalyzer: Error during pybibx co-authorship analysis - Simulated pybibx API error. Falling back to placeholder.")
            mock_print.assert_any_call("PybibxAnalyzer: Using placeholder co-authorship network generation (threshold 1).")

        # Check placeholder results (copied from existing placeholder test)
        self.assertEqual(len(network["nodes"]), 3)
        node_ids_t1 = {node["id"] for node in network["nodes"]}
        self.assertIn("Smith, J", node_ids_t1)
        self.assertEqual(len(network["edges"]), 3)

    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_co_authorship_network_fallback_placeholder(self): # Removed mock_pybibx_unavailable
        """Test co-authorship network uses placeholder when pybibx is initially unavailable."""
        analyzer_no_pybibx = PybibxAnalyzer(SAMPLE_RECORDS) # PYBIBX_AVAILABLE=False will be seen
        network_t1 = analyzer_no_pybibx.co_authorship_network(author_threshold=1)

        # Validating placeholder logic output
        self.assertIsNotNone(network_t1)
        self.assertEqual(network_t1["type"], "co-authorship")
        self.assertEqual(len(network_t1["nodes"]), 3)
        node_ids_t1 = {node["id"] for node in network_t1["nodes"]}
        self.assertIn("Smith, J", node_ids_t1)
        self.assertIn("Doe, A", node_ids_t1)
        self.assertIn("Lee, C", node_ids_t1)
        self.assertEqual(len(network_t1["edges"]), 3)

        network_t3 = analyzer_no_pybibx.co_authorship_network(author_threshold=3)
        self.assertEqual(len(network_t3["nodes"]), 0)
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

        expected_nodes = [{"id": "ml"}, {"id": "ai"}]
        expected_edges = [{"source": "ml", "target": "ai", "weight": 5}]
        self.assertEqual(result["nodes"], expected_nodes)
        self.assertListEqual(result["edges"], expected_edges)
        self.assertEqual(result["type"], "keyword-cooccurrence")

    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_keyword_cooccurrence_fallback_placeholder(self): # Removed mock_pybibx_unavailable
        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        network_t1 = analyzer.keyword_cooccurrence_network(keyword_threshold=1)
        self.assertIsNotNone(network_t1)
        self.assertEqual(network_t1["type"], "keyword-cooccurrence")
        self.assertEqual(len(network_t1["edges"]), 10) # From previous placeholder logic

        network_t2 = analyzer.keyword_cooccurrence_network(keyword_threshold=2)
        self.assertEqual(len(network_t2["edges"]), 2)

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

        # Verify transformed output
        expected_transformed_result = {
            "most_cited_papers": [{
                "title": "Pybibx Top Paper", "doi": "pd1", "citations": 50
            }],
            "total_papers_with_citation_data": 1,
            "raw_pybibx_summary": mock_raw_pybibx_citation_summary
        }
        self.assertEqual(result, expected_transformed_result)

    @patch('sciencemapping.analysis.pybibx_analyzer.PYBIBX_AVAILABLE', False)
    def test_citation_analysis_fallback_placeholder(self): # Removed mock_pybibx_unavailable argument
        analyzer = PybibxAnalyzer(SAMPLE_RECORDS) # Uses SAMPLE_RECORDS from global scope
        stats = analyzer.citation_analysis()
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_papers_with_citation_data"], 7)
        self.assertEqual(stats["most_cited_papers"][0]["title"], "Paper D")

    def test_citation_analysis_empty_input_placeholder(self):
        stats = self.empty_analyzer.citation_analysis()
        self.assertIsNone(stats)

if __name__ == '__main__':
    unittest.main()
