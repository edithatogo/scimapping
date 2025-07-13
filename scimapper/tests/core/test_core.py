import unittest
from unittest.mock import patch, MagicMock, call # Added call for checking multiple calls
from scimapper.core import ScienceMapper, DataSourceName, AnalysisTypeName

# Sample records to be returned by mocked data sources
MOCK_PUBMED_RECORDS = [{"title": "PubMed Paper", "source_type": "pubmed", "authors": ["P Author"], "keywords": ["pk1"], "year": 2020}]
MOCK_WOS_RECORDS = [{"title": "WoS Paper", "source_type": "wos", "authors": ["W Author"], "keywords": ["wk1"], "year": 2021}]
MOCK_SCOPUS_RECORDS = [{"title": "Scopus Paper", "source_type": "scopus_api", "authors": ["S Author"], "keywords": ["sk1"], "year": 2022}]
MOCK_DIMENSIONS_RECORDS = [{"title": "Dimensions Paper", "source_type": "dimensions_api", "authors": ["D Author"], "keywords": ["dk1"], "year": 2023}]
MOCK_OPENALEX_RECORDS = [{"title": "OpenAlex Paper", "source_type": "openalex_api", "authors": ["O Author"], "keywords": ["ok1"], "year": 2024}]

# Sample analysis results to be returned by mocked PybibxAnalyzer
MOCK_COAUTH_RESULT = {"nodes": [{"id":"A1"}], "edges": [], "type": "co-authorship"}
MOCK_KW_RESULT = {"nodes": [{"id":"K1"}], "edges": [], "type": "keyword-cooccurrence"}
MOCK_CITATION_RESULT = {"most_cited_papers": [], "total_papers_with_citation_data": 0}


class TestScienceMapper(unittest.TestCase):

    def setUp(self):
        """
        Set up a new ScienceMapper instance with test email addresses before each test.
        """
        self.mapper = ScienceMapper(pubmed_email="test@example.com", openalex_email="test@example.com")

    @patch('scimapper.scisourcer.pubmed.search_pubmed', return_value=MOCK_PUBMED_RECORDS)
    def test_fetch_data_pubmed(self, mock_search_pubmed):
        """
        Tests fetching data from the PubMed source using the ScienceMapper, verifying correct API call parameters, record storage, and source labeling.
        """
        self.mapper.fetch_data(source="pubmed", query="cancer", max_results=10)
        mock_search_pubmed.assert_called_once_with(
            "cancer",
            max_results=10,
            email="test@example.com"
        )
        self.assertEqual(self.mapper.get_records(), MOCK_PUBMED_RECORDS)
        self.assertEqual(self.mapper._source_of_records, "pubmed")

    @patch('scimapper.scisourcer.wos.parse_wos_file', return_value=MOCK_WOS_RECORDS)
    def test_fetch_data_wos(self, mock_parse_wos):
        """
        Tests that fetching data from a WoS file correctly calls the parser with the provided file path and encoding, and stores the resulting records.
        """
        self.mapper.fetch_data(source="wos_file", file_path="wos.txt", wos_file_encoding="latin-1")
        mock_parse_wos.assert_called_once_with("wos.txt", encoding="latin-1")
        self.assertEqual(self.mapper.get_records(), MOCK_WOS_RECORDS)

    @patch('scimapper.scisourcer.scopus.search_scopus', return_value=MOCK_SCOPUS_RECORDS)
    def test_fetch_data_scopus(self, mock_search_scopus):
        """
        Test that fetching data from the Scopus API correctly calls the search function and stores the returned records.
        """
        self.mapper.fetch_data(source="scopus_api", query="bibliometrics", scopus_api_key="testkey")
        mock_search_scopus.assert_called_once_with("bibliometrics", max_results=100, api_key="testkey")
        self.assertEqual(self.mapper.get_records(), MOCK_SCOPUS_RECORDS)

    @patch('scimapper.scisourcer.dimensions.search_dimensions_api', return_value=MOCK_DIMENSIONS_RECORDS)
    def test_fetch_data_dimensions(self, mock_search_dimensions):
        """
        Tests that fetching data from the Dimensions API correctly calls the search function with the expected parameters and stores the returned records.
        """
        dsl_query = "search publications for \"test\""
        self.mapper.fetch_data(source="dimensions_api", query=dsl_query)
        mock_search_dimensions.assert_called_once_with(
            dsl_query=dsl_query,
            max_results=100,
            dsl_instance=None
        )
        self.assertEqual(self.mapper.get_records(), MOCK_DIMENSIONS_RECORDS)

    @patch('scimapper.scisourcer.openalex.search_openalex_works', return_value=MOCK_OPENALEX_RECORDS)
    def test_fetch_data_openalex(self, mock_search_openalex):
        """
        Test that `fetch_data` correctly retrieves and stores records from the OpenAlex API using the provided query and filter criteria.
        
        Verifies that the OpenAlex search function is called with the expected parameters and that the fetched records are stored in the mapper.
        """
        filters = {"publication_year": "2023"}
        self.mapper.fetch_data(source="openalex_api", query="science", openalex_filter_criteria=filters)
        mock_search_openalex.assert_called_once_with(
            search_query="science",
            filter_criteria=filters,
            max_results=100,
            user_email="test@example.com"
        )
        self.assertEqual(self.mapper.get_records(), MOCK_OPENALEX_RECORDS)

    def test_fetch_data_invalid_source(self):
        """
        Test that fetching data with an invalid source raises a ValueError with the expected message.
        """
        with self.assertRaises(ValueError) as context:
            self.mapper.fetch_data(source="invalid_source_name") # type: ignore
        self.assertIn("Unknown data source: invalid_source_name", str(context.exception))

    def test_fetch_data_missing_params(self):
        """
        Test that fetch_data raises ValueError when required parameters are missing for specific sources.
        """
        with self.assertRaises(ValueError):
            self.mapper.fetch_data(source="pubmed") # Missing query
        with self.assertRaises(ValueError):
            self.mapper.fetch_data(source="wos_file") # Missing file_path


    @patch('scimapper.sciprocessor.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_co_authorship(self, MockPybibxAnalyzer):
        # Setup mock analyzer instance and its method
        """
        Tests that the co-authorship network analysis is performed correctly using the mocked PybibxAnalyzer, with the expected threshold and records.
        """
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.co_authorship_network.return_value = MOCK_COAUTH_RESULT

        # First, fetch some data to load into the mapper
        self.mapper._records = MOCK_PUBMED_RECORDS # Manually set records for this test

        result = self.mapper.analyze("co_authorship", coauth_threshold=2)

        MockPybibxAnalyzer.assert_called_once_with(MOCK_PUBMED_RECORDS)
        mock_analyzer_instance.co_authorship_network.assert_called_once_with(author_threshold=2)
        self.assertEqual(result, MOCK_COAUTH_RESULT)

    @patch('scimapper.sciprocessor.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_keyword_cooccurrence(self, MockPybibxAnalyzer):
        """
        Tests that the 'analyze' method correctly performs keyword co-occurrence analysis using the PybibxAnalyzer mock, passing the appropriate threshold and returning the expected result.
        """
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.keyword_cooccurrence_network.return_value = MOCK_KW_RESULT
        self.mapper._records = MOCK_WOS_RECORDS

        result = self.mapper.analyze("keyword_cooccurrence", keyword_threshold=5)

        MockPybibxAnalyzer.assert_called_once_with(MOCK_WOS_RECORDS)
        mock_analyzer_instance.keyword_cooccurrence_network.assert_called_once_with(keyword_threshold=5)
        self.assertEqual(result, MOCK_KW_RESULT)

    @patch('scimapper.sciprocessor.pybibx_analyzer.PybibxAnalyzer')
    def test_analyze_citation(self, MockPybibxAnalyzer):
        """
        Test that the citation analysis method is called correctly and returns the expected result when analyzing loaded records.
        """
        mock_analyzer_instance = MockPybibxAnalyzer.return_value
        mock_analyzer_instance.citation_analysis.return_value = MOCK_CITATION_RESULT
        self.mapper._records = MOCK_OPENALEX_RECORDS

        result = self.mapper.analyze("citation_analysis")

        MockPybibxAnalyzer.assert_called_once_with(MOCK_OPENALEX_RECORDS)
        mock_analyzer_instance.citation_analysis.assert_called_once_with()
        self.assertEqual(result, MOCK_CITATION_RESULT)

    def test_analyze_no_records(self):
        # Ensure PybibxAnalyzer is NOT called if no records
        """
        Test that analyze returns None and does not instantiate PybibxAnalyzer when no records are loaded, and that a warning is printed.
        """
        with patch('scimapper.sciprocessor.pybibx_analyzer.PybibxAnalyzer') as MockPybibxAnalyzer_norec:
            with patch('builtins.print') as mock_print: # To check warning
                result = self.mapper.analyze("co_authorship")
                self.assertIsNone(result)
                MockPybibxAnalyzer_norec.assert_not_called()
                mock_print.assert_any_call("Warning: No records loaded to analyze. Returning None.")


    def test_analyze_invalid_type(self):
        """
        Test that analyzing with an invalid analysis type raises a ValueError with the expected message.
        """
        self.mapper._records = MOCK_PUBMED_RECORDS # Load some data
        with self.assertRaises(ValueError) as context:
            self.mapper.analyze("unknown_analysis") # type: ignore
        self.assertIn("Unknown analysis type: unknown_analysis", str(context.exception))

    def test_get_records_empty_initially(self):
        """
        Test that `get_records` returns an empty list before any data is fetched.
        """
        self.assertEqual(self.mapper.get_records(), [])

    @patch('scimapper.scisourcer.pubmed.search_pubmed', return_value=MOCK_PUBMED_RECORDS)
    def test_chaining_fetch_and_analyze(self, mock_search_pubmed):
         """
         Test that data fetching and analysis can be chained, verifying correct integration between fetch and analyze methods.
         
         This test mocks PubMed data retrieval and citation analysis, ensuring that `fetch_data` followed by `analyze` invokes all expected calls and returns the correct analysis result.
         """
         mock_analyzer_instance = mock_pybibx_module.analysis
         mock_analyzer_instance.citation_analysis.return_value = MOCK_CITATION_RESULT

         analysis_result = self.mapper.fetch_data(source="pubmed", query="test").analyze("citation_analysis")

         mock_search_pubmed.assert_called_once()
         mock_pybibx_module.Corpus.assert_called_once_with(MOCK_PUBMED_RECORDS)
         mock_analyzer_instance.citation_analysis.assert_called_once()
         self.assertEqual(analysis_result, MOCK_CITATION_RESULT)


    @patch('scimapper.scisourcer.unpaywall.search_unpaywall')
    def test_fetch_full_text_success(self, mock_search_unpaywall):
        """
        Test that `fetch_full_text` successfully retrieves the full text of an article.
        """
        mock_search_unpaywall.return_value = {
            "is_oa": True,
            "best_oa_location": {
                "url_for_pdf": "http://example.com/article.pdf"
            }
        }
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "This is the full text of the article."
            mock_get.return_value = mock_response

            full_text = self.mapper.fetch_full_text("10.1234/test.doi")

            self.assertEqual(full_text, "This is the full text of the article.")

    @patch('scimapper.scisourcer.unpaywall.search_unpaywall')
    def test_fetch_full_text_not_found(self, mock_search_unpaywall):
        """
        Test that `fetch_full_text` returns None when the article is not found.
        """
        mock_search_unpaywall.return_value = None

        full_text = self.mapper.fetch_full_text("10.1234/not.found")

        self.assertIsNone(full_text)

    @patch('scimapper.scisourcer.unpaywall.search_unpaywall')
    def test_fetch_full_text_not_open_access(self, mock_search_unpaywall):
        """
        Test that `fetch_full_text` returns None when the article is not open access.
        """
        mock_search_unpaywall.return_value = {"is_oa": False}

        full_text = self.mapper.fetch_full_text("10.1234/closed.access")

        self.assertIsNone(full_text)

    def test_extract_affiliations(self):
        """
        Test that `extract_affiliations` successfully extracts affiliation data from the records.
        """
        self.mapper._records = [
            {
                "authors": [
                    {"name": "Doe, J.", "affiliation": "University of Science"},
                    {"name": "Smith, A.", "affiliation": "Institute of Technology"}
                ]
            },
            {
                "authors": [
                    {"name": "Lee, C."}
                ]
            }
        ]
        self.mapper.extract_affiliations()
        records = self.mapper.get_records()
        self.assertEqual(records[0]["affiliations"], ["University of Science", "Institute of Technology"])
        self.assertNotIn("affiliations", records[1])

if __name__ == '__main__':
    unittest.main()
