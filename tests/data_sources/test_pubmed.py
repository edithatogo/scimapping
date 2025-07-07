import unittest
from unittest.mock import patch, MagicMock
from sciencemapping.data_sources.pubmed import search_pubmed, _parse_pubmed_article, DEFAULT_TOOL_EMAIL

class TestPubMedDataSource(unittest.TestCase):

    def test_parse_pubmed_article(self):
        """Test parsing of a single PubMed article dictionary."""
        raw_article_data = {
            "title": "Test Title",
            "authors": [
                {"lastname": "Doe", "firstname": "John A.", "initials": "JA"},
                {"lastname": "Smith", "firstname": "Jane B.", "initials": "JB"}
            ],
            "journal": "Journal of Testing",
            "publication_date": MagicMock(year=2023), # Mocking datetime.date object
            "doi": "10.1234/test.doi",
            "pubmed_id": "12345678\n[Indexed for MEDLINE]",
            "abstract": "This is a test abstract.",
            "keywords": ["test", "pubmed", "python"],
            # Add other fields as necessary based on pymed output
        }
        parsed_article = _parse_pubmed_article(raw_article_data)

        self.assertEqual(parsed_article["title"], "Test Title")
        self.assertListEqual(parsed_article["authors"], ["Doe John A.", "Smith Jane B."])
        self.assertEqual(parsed_article["journal"], "Journal of Testing")
        self.assertEqual(parsed_article["year"], 2023)
        self.assertEqual(parsed_article["doi"], "10.1234/test.doi")
        self.assertEqual(parsed_article["pubmed_id"], "12345678") # Check cleaning
        self.assertEqual(parsed_article["abstract"], "This is a test abstract.")
        self.assertListEqual(parsed_article["keywords"], ["test", "pubmed", "python"])
        self.assertEqual(parsed_article["source_type"], "pubmed")
        self.assertIn("raw_data", parsed_article)
        self.assertEqual(parsed_article["raw_data"], raw_article_data)

    def test_parse_pubmed_article_minimal_data(self):
        """Test parsing with minimal or missing data fields."""
        raw_article_data = {
            "title": "Minimal Title",
            "pubmed_id": "9876543"
            # Other fields are missing
        }
        parsed_article = _parse_pubmed_article(raw_article_data)

        self.assertEqual(parsed_article["title"], "Minimal Title")
        self.assertEqual(parsed_article["pubmed_id"], "9876543")
        self.assertListEqual(parsed_article["authors"], [])
        self.assertIsNone(parsed_article["journal"])
        self.assertIsNone(parsed_article["year"])
        self.assertIsNone(parsed_article["doi"])
        self.assertIsNone(parsed_article["abstract"])
        self.assertListEqual(parsed_article["keywords"], [])
        self.assertEqual(parsed_article["source_type"], "pubmed")

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_success(self, MockPubMed):
        """Test successful PubMed search and data parsing integration."""
        # Mock PubMedArticle and its toDict method
        mock_article_1_dict = {
            "title": "Article 1", "pubmed_id": "111", "doi": "doi1",
            "authors": [{"lastname": "AuthA", "firstname": "FirstA"}],
            "journal": "Journal A", "publication_date": MagicMock(year=2020),
            "abstract": "Abstract 1", "keywords": ["key1"]
        }
        mock_article_2_dict = {
            "title": "Article 2", "pubmed_id": "222", "doi": "doi2",
            "authors": [{"lastname": "AuthB", "firstname": "FirstB"}],
            "journal": "Journal B", "publication_date": MagicMock(year=2021),
            "abstract": "Abstract 2", "keywords": ["key2"]
        }

        mock_article_1 = MagicMock()
        mock_article_1.toDict.return_value = mock_article_1_dict

        mock_article_2 = MagicMock()
        mock_article_2.toDict.return_value = mock_article_2_dict

        # Configure the mock PubMed instance
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.return_value = [mock_article_1, mock_article_2]

        results = search_pubmed("test query", max_results=2, email="test@example.com")

        MockPubMed.assert_called_once_with(tool="ScienceMappingLibrary", email="test@example.com")
        mock_pubmed_instance.query.assert_called_once_with("test query", max_results=2)

        self.assertEqual(len(results), 2)

        # Check first article
        self.assertEqual(results[0]["title"], "Article 1")
        self.assertEqual(results[0]["pubmed_id"], "111")
        self.assertEqual(results[0]["year"], 2020)
        self.assertListEqual(results[0]["authors"], ["AuthA FirstA"])

        # Check second article
        self.assertEqual(results[1]["title"], "Article 2")
        self.assertEqual(results[1]["pubmed_id"], "222")
        self.assertEqual(results[1]["year"], 2021)
        self.assertListEqual(results[1]["authors"], ["AuthB FirstB"])

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_no_email_uses_default(self, MockPubMed):
        """Test that DEFAULT_TOOL_EMAIL is used if no email is provided."""
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.return_value = [] # No articles needed for this test

        with patch('builtins.print') as mock_print: # Suppress warning print
            search_pubmed("test query", email=None)
            MockPubMed.assert_called_once_with(tool="ScienceMappingLibrary", email=DEFAULT_TOOL_EMAIL)
            mock_print.assert_any_call("Warning: NCBI recommends providing an email for PubMed API access.")

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_api_error(self, MockPubMed):
        """Test PubMed search when the API call raises an exception."""
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.side_effect = Exception("API Connection Error")

        with patch('builtins.print') as mock_print:
            results = search_pubmed("test query", email="test@example.com")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Error during PubMed search: API Connection Error")

    def test_parse_pubmed_article_missing_keywords_and_date(self):
        """Test parsing when keywords or publication_date are None or missing."""
        raw_article_data_no_keywords = {
            "title": "No Keywords Title", "pubmed_id": "333", "keywords": None
        }
        parsed = _parse_pubmed_article(raw_article_data_no_keywords)
        self.assertListEqual(parsed["keywords"], [])

        raw_article_data_no_date = {
            "title": "No Date Title", "pubmed_id": "444"
            # "publication_date" is missing
        }
        parsed_no_date = _parse_pubmed_article(raw_article_data_no_date)
        self.assertIsNone(parsed_no_date["year"])


if __name__ == '__main__':
    unittest.main()
