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

        mock_pybibx_result = {"nodes": [{"id":"pybibx_author1"}], "edges": [{"source":"pybibx_author1", "target":"pybibx_author2", "weight":1}]}
        mock_pybibx_module.analysis = MagicMock() # Ensure 'analysis' attribute exists
        mock_pybibx_module.analysis.coauthorship.return_value = mock_pybibx_result

        analyzer_with_pybibx = PybibxAnalyzer(SAMPLE_RECORDS) # PYBIBX_AVAILABLE=True will be seen by this instance

        network = analyzer_with_pybibx.co_authorship_network(author_threshold=1)

        mock_pybibx_module.Corpus.assert_called_with(SAMPLE_RECORDS)
        mock_pybibx_module.analysis.coauthorship.assert_called_once_with(mock_corpus_instance, threshold=1)
        self.assertEqual(network["nodes"], mock_pybibx_result["nodes"])
        self.assertEqual(network["edges"], mock_pybibx_result["edges"])
        self.assertEqual(network["type"], "co-authorship")

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
        mock_corpus = MagicMock()
        mock_pybibx_module.Corpus.return_value = mock_corpus
        mock_pybibx_result = {"nodes": [{"id":"kw1_pybibx"}], "edges": []}
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.keywords.return_value = mock_pybibx_result

        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        result = analyzer.keyword_cooccurrence_network()

        mock_pybibx_module.analysis.keywords.assert_called_once_with(mock_corpus, method="cooccurrence", threshold=1)
        self.assertEqual(result["nodes"], mock_pybibx_result["nodes"])
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
        mock_corpus = MagicMock()
        mock_pybibx_module.Corpus.return_value = mock_corpus
        mock_pybibx_result = {"most_cited_papers": [{"title":"Top Paper"}], "total_papers_with_citation_data": 1}
        mock_pybibx_module.analysis = MagicMock()
        mock_pybibx_module.analysis.citations.return_value = mock_pybibx_result

        analyzer = PybibxAnalyzer(SAMPLE_RECORDS)
        result = analyzer.citation_analysis()

        mock_pybibx_module.analysis.citations.assert_called_once_with(mock_corpus)
        self.assertEqual(result, mock_pybibx_result)

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
