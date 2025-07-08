import unittest
from unittest.mock import patch, MagicMock
from sciencemapping.data_sources.openalex import (
    search_openalex_works,
    _parse_openalex_work
    # Not importing openalex directly here to avoid issues if not installed in test env
    # The module under test will import it.
)

class TestOpenAlexDataSource(unittest.TestCase):

    @patch('sciencemapping.data_sources.openalex.openalex.Works') # Patch where it's used
    def test_search_openalex_works_success(self, MockWorks):
        """
        Test that `search_openalex_works` performs a successful OpenAlex API search and correctly parses the returned results.
        
        Simulates the OpenAlex API using mocks to verify that the search, filter, and pagination methods are called with the expected arguments. Asserts that the parsed results contain the correct titles, OpenAlex IDs, and author names extracted from the mocked API response.
        """
        mock_works_query_instance = MockWorks.return_value # This is what Works() returns

        # Mock the fluent interface (.search().filter().paginate())
        # Each method should return the same mock instance to allow chaining
        mock_works_query_instance.search.return_value = mock_works_query_instance
        mock_works_query_instance.filter.return_value = mock_works_query_instance

        # Example JSON response items from OpenAlex API
        api_response_item1 = {
            "id": "https://openalex.org/W123",
            "display_name": "OpenAlex Title 1",
            "publication_year": 2022,
            "doi": "https://doi.org/10.oa/test1",
            "authorships": [{"author": {"display_name": "Alex Author"}}],
            "host_venue": {"display_name": "Journal of OpenAlex Studies"},
            "concepts": [{"display_name": "Open Science"}],
            "type": "journal-article",
            "cited_by_count": 5
        }
        api_response_item2 = {
            "id": "https://openalex.org/W456",
            "title": "OpenAlex Title 2", # Using 'title' instead of 'display_name'
            "publication_year": 2023,
            "authorships": [{"author": {"display_name": "Omega Author"}}],
            "host_venue": {"display_name": "Open Conference X"},
            "concepts": [{"display_name": "Data Sharing"}],
            "type": "conference-paper",
            "cited_by_count": 12
        }

        # .paginate() should yield lists of results (pages)
        mock_works_query_instance.paginate.return_value = iter([[api_response_item1, api_response_item2]])

        results = search_openalex_works(
            search_query="test query",
            filter_criteria={"publication_year": "2023"},
            max_results=2
        )

        MockWorks.assert_called_once() # Works()
        mock_works_query_instance.search.assert_called_once_with("test query")
        mock_works_query_instance.filter.assert_called_once_with(publication_year="2023")
        mock_works_query_instance.paginate.assert_called_once_with(per_page=2, n_max=2) # max_results=2

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "OpenAlex Title 1")
        self.assertEqual(results[0]["openalex_id"], "W123")
        self.assertIn("Alex Author", results[0]["authors"])
        self.assertEqual(results[1]["title"], "OpenAlex Title 2")

    @patch('sciencemapping.data_sources.openalex.openalex.Works')
    def test_search_openalex_api_error(self, MockWorks):
        """
        Test that search_openalex_works returns an empty list and logs an error when the OpenAlex API raises an exception.
        """
        mock_works_query_instance = MockWorks.return_value
        mock_works_query_instance.search.return_value = mock_works_query_instance
        mock_works_query_instance.filter.return_value = mock_works_query_instance
        mock_works_query_instance.paginate.side_effect = Exception("Simulated OpenAlex API error")

        with patch('builtins.print') as mock_print:
            results = search_openalex_works(search_query="error query")
            self.assertEqual(results, [])
            mock_print.assert_any_call("An error occurred during OpenAlex search: Exception - Simulated OpenAlex API error")

    @patch('sciencemapping.data_sources.openalex.openalex.Works')
    def test_search_openalex_no_results(self, MockWorks):
        """
        Test that search_openalex_works returns an empty list when the OpenAlex API yields no results.
        """
        mock_works_query_instance = MockWorks.return_value
        mock_works_query_instance.search.return_value = mock_works_query_instance
        mock_works_query_instance.filter.return_value = mock_works_query_instance
        mock_works_query_instance.paginate.return_value = iter([]) # Empty iterator

        results = search_openalex_works(search_query="query yielding nothing")
        self.assertEqual(results, [])

    def test_parse_openalex_work_full(self):
        """
        Test that a comprehensive OpenAlex work record is correctly parsed into the expected normalized dictionary fields.
        
        Verifies extraction of title, authors, journal, year, DOI, OpenAlex ID, keywords, document type, citation count, source type, and raw data. Confirms that the abstract is None when not implemented.
        """
        item_json = {
            "id": "https://openalex.org/W987",
            "display_name": "Comprehensive OpenAlex Record",
            "publication_year": 2021,
            "doi": "https://doi.org/10.oa/comp",
            "authorships": [
                {"author": {"display_name": "First Author"}},
                {"author": {"display_name": "Second Author"}}
            ],
            "host_venue": {"display_name": "Journal of Completeness", "publisher": "Open Publisher"},
            "concepts": [
                {"display_name": "concept1"},
                {"display_name": "concept2", "level": 0} # level is another field in concept
            ],
            "type": "journal-article",
            "cited_by_count": 101,
            "abstract_inverted_index": {"This": [0], "is": [1], "abstract": [2]} # Placeholder
        }
        parsed = _parse_openalex_work(item_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Comprehensive OpenAlex Record")
        self.assertIn("First Author", parsed["authors"])
        self.assertIn("Second Author", parsed["authors"])
        self.assertEqual(parsed["journal"], "Journal of Completeness")
        self.assertEqual(parsed["year"], 2021)
        self.assertEqual(parsed["doi"], "https://doi.org/10.oa/comp")
        self.assertEqual(parsed["openalex_id"], "W987")
        self.assertIsNone(parsed["abstract"]) # Abstract parsing from inverted index not implemented
        self.assertIn("concept1", parsed["keywords"])
        self.assertIn("concept2", parsed["keywords"])
        self.assertEqual(parsed["document_type"], "journal-article")
        self.assertEqual(parsed["times_cited_openalex"], 101)
        self.assertEqual(parsed["source_type"], "openalex")
        self.assertEqual(parsed["raw_data"], item_json)

    def test_parse_openalex_work_minimal_title_only(self):
        """
        Tests that parsing a minimal OpenAlex work record with only an ID and display name correctly extracts the title and OpenAlex ID, and returns an empty authors list.
        """
        item_json = {"id": "W-Min", "display_name": "Minimal OpenAlex Title"} # ID without full URL
        parsed = _parse_openalex_work(item_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Minimal OpenAlex Title")
        self.assertEqual(parsed["openalex_id"], "W-Min") # Should handle ID without full URL prefix
        self.assertEqual(len(parsed["authors"]), 0)

    def test_parse_openalex_work_no_title(self):
        """Test that a record with no title or display_name returns None."""
        item_json = {"id": "W-NoTitle", "doi": "10.oa/notitle"}
        parsed = _parse_openalex_work(item_json)
        self.assertIsNone(parsed)

    def test_parse_openalex_work_empty_input(self):
        """Test parsing with empty or None input."""
        self.assertIsNone(_parse_openalex_work(None))
        self.assertIsNone(_parse_openalex_work({}))

    @patch('sciencemapping.data_sources.openalex.openalex.config')
    def test_search_openalex_with_email(self, mock_oa_config):
        """
        Verify that providing a user email to `search_openalex_works` sets the email in the OpenAlex client configuration.
        
        This test mocks the OpenAlex API and configuration to ensure that the `user_email` parameter is correctly assigned to `openalex.config.email` during the search operation.
        """
        # Store original email if any, to restore it. This is tricky with module-level config.
        # For a unit test, we assume we can set it and it's used.
        # The actual check of whether openalex lib *uses* it is harder to unit test.

        # Mock the paginate to stop immediately
        with patch('sciencemapping.data_sources.openalex.openalex.Works') as MockWorks:
            mock_works_query_instance = MockWorks.return_value
            mock_works_query_instance.search.return_value = mock_works_query_instance
            mock_works_query_instance.paginate.return_value = iter([]) # No results needed

            test_email = "test@example.com"
            search_openalex_works(search_query="test", user_email=test_email)

            # Check if the email was set on the mocked config
            # This assertion depends on how openalex.config is structured and if it's a mutable object.
            # If openalex.config is a simple object with attributes:
            self.assertEqual(mock_oa_config.email, test_email)
            # Note: The finally block in search_openalex_works will try to restore it.
            # This test primarily verifies that the email IS SET.

if __name__ == '__main__':
    unittest.main()
