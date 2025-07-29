import unittest
from unittest.mock import patch, MagicMock, call # Added call for checking multiple calls
from sciencemapping.core import ScienceMapper, DataSourceName, AnalysisTypeName

# Sample records to be returned by mocked data sources
MOCK_PUBMED_RECORDS = [{"title": "PubMed Paper", "source_type": "pubmed", "authors": ["P Author"], "keywords": ["pk1"], "year": 2020}]
MOCK_WOS_RECORDS = [{"title": "WoS Paper", "source_type": "wos", "authors": ["W Author"], "keywords": ["wk1"], "year": 2021}]
MOCK_SCOPUS_RECORDS = [{"title": "Scopus Paper", "source_type": "scopus_api", "authors": ["S Author"], "keywords": ["sk1"], "year": 2022}]
MOCK_DIMENSIONS_RECORDS = [{"title": "Dimensions Paper", "source_type": "dimensions_api", "authors": ["D Author"], "keywords": ["dk1"], "year": 2023}]
MOCK_OPENALEX_RECORDS = [{"title": "OpenAlex Paper", "source_type": "openalex_api", "authors": ["O Author"], "keywords": ["ok1"], "year": 2024}]
MOCK_GOOGLE_SCHOLAR_RECORDS = [{"title": "Google Scholar Paper", "source_type": "google_scholar", "authors": ["GS Author"], "keywords": [], "year": 2023, "times_cited_google_scholar": 5}]

# Sample analysis results to be returned by mocked PybibxAnalyzer
MOCK_COAUTH_RESULT = {"nodes": [{"id":"A1"}], "edges": [], "type": "co-authorship"}
MOCK_KW_RESULT = {"nodes": [{"id":"K1"}], "edges": [], "type": "keyword-cooccurrence"}
MOCK_CITATION_RESULT = {"most_cited_papers": [], "total_papers_with_citation_data": 0}


class TestScienceMapper(unittest.TestCase):

    def setUp(self):
        self.mapper = ScienceMapper(pubmed_email="test@example.com", openalex_email="test@example.com")

    @patch('sciencemapping.data_sources.pubmed.search_pubmed', return_value=MOCK_PUBMED_RECORDS)
    def test_fetch_data_pubmed(self, mock_search_pubmed):
        self.mapper.fetch_data(source="pubmed", query="cancer", max_results=10)
        mock_search_pubmed.assert_called_once_with(
            "cancer",
            max_results=10,
            email="test@example.com"
        )
        self.assertEqual(self.mapper.get_records(), MOCK_PUBMED_RECORDS)
        self.assertEqual(self.mapper._source_of_records, "pubmed")

    @patch('sciencemapping.data_sources.wos.parse_wos_file', return_value=MOCK_WOS_RECORDS)
    def test_fetch_data_wos(self, mock_parse_wos):
        self.mapper.fetch_data(source="wos_file", file_path="wos.txt", wos_file_encoding="latin-1")
        mock_parse_wos.assert_called_once_with("wos.txt", encoding="latin-1")
        self.assertEqual(self.mapper.get_records(), MOCK_WOS_RECORDS)

    @patch('sciencemapping.data_sources.scopus.search_scopus', return_value=MOCK_SCOPUS_RECORDS)
    def test_fetch_data_scopus(self, mock_search_scopus):
        self.mapper.fetch_data(source="scopus_api", query="bibliometrics", scopus_api_key="testkey")
        mock_search_scopus.assert_called_once_with("bibliometrics", max_results=100, api_key="testkey")
        self.assertEqual(self.mapper.get_records(), MOCK_SCOPUS_RECORDS)

    @patch('sciencemapping.data_sources.dimensions.search_dimensions_api', return_value=MOCK_DIMENSIONS_RECORDS)
    def test_fetch_data_dimensions(self, mock_search_dimensions):
        dsl_query = "search publications for \"test\""
        self.mapper.fetch_data(source="dimensions_api", query=dsl_query)
        mock_search_dimensions.assert_called_once_with(
            dsl_query=dsl_query,
            max_results=100,
            dsl_instance=None
        )
        self.assertEqual(self.mapper.get_records(), MOCK_DIMENSIONS_RECORDS)

    @patch('sciencemapping.data_sources.openalex.search_openalex_works', return_value=MOCK_OPENALEX_RECORDS)
    def test_fetch_data_openalex(self, mock_search_openalex):
        filters = {"publication_year": "2023"}
        self.mapper.fetch_data(source="openalex_api", query="science", openalex_filter_criteria=filters)
        mock_search_openalex.assert_called_once_with(
            search_query="science",
            filter_criteria=filters,
            max_results=100,
            user_email="test@example.com"
        )
        self.assertEqual(self.mapper.get_records(), MOCK_OPENALEX_RECORDS)

    @patch('sciencemapping.data_sources.google_scholar.search_google_scholar', return_value=MOCK_GOOGLE_SCHOLAR_RECORDS)
    def test_fetch_data_google_scholar(self, mock_search_gs):
        self.mapper.fetch_data(source="google_scholar", query="machine learning", max_results=50)
        mock_search_gs.assert_called_once_with(
            query="machine learning",
            max_results=50
        )
        self.assertEqual(self.mapper.get_records(), MOCK_GOOGLE_SCHOLAR_RECORDS)
        self.assertEqual(self.mapper._source_of_records, "google_scholar")

    def test_fetch_data_invalid_source(self):
        with self.assertRaises(ValueError) as context:
            self.mapper.fetch_data(source="invalid_source_name") # type: ignore
        self.assertIn("Unknown data source: invalid_source_name", str(context.exception))

    def test_fetch_data_missing_params(self):
        with self.assertRaises(ValueError):
            self.mapper.fetch_data(source="pubmed") # Missing query
        with self.assertRaises(ValueError):
            self.mapper.fetch_data(source="wos_file") # Missing file_path


    @patch('sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_co_authorship(self, MockPybibxAnalyzer):
        # Setup mock analyzer instance and its method
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.co_authorship_network.return_value = MOCK_COAUTH_RESULT

        # First, fetch some data to load into the mapper
        self.mapper._records = MOCK_PUBMED_RECORDS # Manually set records for this test

        result = self.mapper.analyze("co_authorship", coauth_threshold=2)

        MockPybibxAnalyzer.assert_called_once_with(MOCK_PUBMED_RECORDS)
        mock_analyzer_instance.co_authorship_network.assert_called_once_with(author_threshold=2)
        self.assertEqual(result, MOCK_COAUTH_RESULT)

    @patch('sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_keyword_cooccurrence(self, MockPybibxAnalyzer):
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.keyword_cooccurrence_network.return_value = MOCK_KW_RESULT
        self.mapper._records = MOCK_WOS_RECORDS

        result = self.mapper.analyze("keyword_cooccurrence", keyword_threshold=5)

        MockPybibxAnalyzer.assert_called_once_with(MOCK_WOS_RECORDS)
        mock_analyzer_instance.keyword_cooccurrence_network.assert_called_once_with(keyword_threshold=5)
        self.assertEqual(result, MOCK_KW_RESULT)

    @patch('sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_citation(self, MockPybibxAnalyzer):
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.citation_analysis.return_value = MOCK_CITATION_RESULT
        self.mapper._records = MOCK_OPENALEX_RECORDS

        result = self.mapper.analyze("citation_analysis")

        MockPybibxAnalyzer.assert_called_once_with(MOCK_OPENALEX_RECORDS)
        mock_analyzer_instance.citation_analysis.assert_called_once_with()
        self.assertEqual(result, MOCK_CITATION_RESULT)

    def test_analyze_no_records(self):
        # Ensure PybibxAnalyzer is NOT called if no records
        with patch('sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer') as MockPybibxAnalyzer_norec:
            with patch('builtins.print') as mock_print: # To check warning
                result = self.mapper.analyze("co_authorship")
                self.assertIsNone(result)
                MockPybibxAnalyzer_norec.assert_not_called()
                mock_print.assert_any_call("Warning: No records loaded to analyze. Returning None.")


    def test_analyze_invalid_type(self):
        self.mapper._records = MOCK_PUBMED_RECORDS # Load some data
        with self.assertRaises(ValueError) as context:
            self.mapper.analyze("unknown_analysis") # type: ignore
        self.assertIn("Unknown analysis type: unknown_analysis", str(context.exception))

    def test_get_records_empty_initially(self):
        self.assertEqual(self.mapper.get_records(), [])

    @patch('sciencemapping.data_sources.pubmed.search_pubmed', return_value=MOCK_PUBMED_RECORDS)
    def test_chaining_fetch_and_analyze(self, mock_search_pubmed):
         with patch('sciencemapping.analysis.pybibx_analyzer.PybibxAnalyzer') as MockPybibxAnalyzer:
            mock_analyzer_instance = MockPybibxAnalyzer.return_value
            mock_analyzer_instance.citation_analysis.return_value = MOCK_CITATION_RESULT

            analysis_result = self.mapper.fetch_data(source="pubmed", query="test").analyze("citation_analysis")

            mock_search_pubmed.assert_called_once()
            MockPybibxAnalyzer.assert_called_once_with(MOCK_PUBMED_RECORDS)
            mock_analyzer_instance.citation_analysis.assert_called_once()
            self.assertEqual(analysis_result, MOCK_CITATION_RESULT)


if __name__ == '__main__':
    unittest.main()
