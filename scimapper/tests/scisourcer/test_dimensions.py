import unittest
from unittest.mock import patch, MagicMock
from scimapper.scisourcer.dimensions import (
    search_dimensions_api,
    _parse_dimensions_api_record,
    DIMENSIONS_API_AVAILABLE # To conditionally run tests or mock Dsl
)

# Only run API-dependent tests if the library is theoretically available
# Actual calls will be mocked.
@unittest.skipUnless(DIMENSIONS_API_AVAILABLE, "dimcli library not available, skipping Dimensions API tests")
class TestDimensionsAPIDataSource(unittest.TestCase):

    @patch('scimapper.scisourcer.dimensions.Dsl')
    def test_search_dimensions_api_success(self, MockDsl):
        """
        Tests that a successful Dimensions API search returns and correctly parses multiple publication records.
        
        Verifies that the API client is called with the correct query and limit, and that the returned results contain accurately parsed titles, IDs, authors (handling different formats), journal titles (from different possible fields), and keywords (from both 'concepts' and 'keywords' fields).
        """
        mock_dsl_instance = MockDsl.return_value

        # Example JSON response items from Dimensions API (structure depends on 'return' part of DSL query)
        api_response_item1 = {
            "id": "pub.12345",
            "title": "Title from Dimensions API 1",
            "doi": "10.dim/test1",
            "year": 2022,
            "authors": [{"first_name": "Jane", "last_name": "Doe"}, {"first_name": "John", "last_name": "Smith"}],
            "journal": {"title": "Journal of Dimensions Research"},
            "abstract": "Abstract 1 content.",
            "concepts": ["AI", "Machine Learning"], # Using 'concepts' as potential keywords
            "type": "article"
        }
        api_response_item2 = {
            "id": "pub.67890",
            "title": "Title from Dimensions API 2",
            "doi": "10.dim/test2",
            "year": 2023,
            "authors": [{"name": "Single Author Name"}], # Different author format
            "journal_title": "Another Dimensions Journal", # Different journal field
            "keywords": ["data science", "bibliometrics"], # Using 'keywords' field
            "type": "proceeding"
        }

        # Configure query_iterative to be a generator yielding these items
        mock_dsl_instance.query_iterative.return_value = iter([api_response_item1, api_response_item2])

        dsl_query = 'search publications where concepts ~ "test" return publications[basics]'
        results = search_dimensions_api(dsl_query, max_results=2, dsl_instance=mock_dsl_instance)

        mock_dsl_instance.query_iterative.assert_called_once_with(dsl_query, limit=2) # max_results is 2
        self.assertEqual(len(results), 2)

        # Check parsing of first item
        self.assertEqual(results[0]["title"], "Title from Dimensions API 1")
        self.assertEqual(results[0]["dimensions_id"], "pub.12345")
        self.assertIn("Doe Jane", results[0]["authors"])
        self.assertIn("Smith John", results[0]["authors"])
        self.assertEqual(results[0]["journal"], "Journal of Dimensions Research")
        self.assertIn("AI", results[0]["keywords"])

        # Check parsing of second item
        self.assertEqual(results[1]["title"], "Title from Dimensions API 2")
        self.assertEqual(results[1]["journal"], "Another Dimensions Journal")
        self.assertIn("Single Author Name", results[1]["authors"])
        self.assertIn("data science", results[1]["keywords"])

    @patch('scimapper.scisourcer.dimensions.Dsl')
    def test_search_dimensions_api_login_failure(self, MockDsl):
        """
        Test that `search_dimensions_api` returns an empty list and logs an error when Dsl client initialization fails.
        """
        MockDsl.side_effect = Exception("Simulated Dsl login error")

        with patch('builtins.print') as mock_print:
            results = search_dimensions_api("any query")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Error initializing Dimensions API client: Simulated Dsl login error")

    @patch('scimapper.scisourcer.dimensions.Dsl')
    def test_search_dimensions_api_query_error(self, MockDsl):
        """
        Test that search_dimensions_api returns an empty list and logs an error when the API query raises an exception.
        """
        mock_dsl_instance = MockDsl.return_value
        mock_dsl_instance.query_iterative.side_effect = Exception("Simulated API query error")

        with patch('builtins.print') as mock_print:
            results = search_dimensions_api("any query", dsl_instance=mock_dsl_instance)
            self.assertEqual(results, [])
            mock_print.assert_any_call("An error occurred during Dimensions API query: Exception - Simulated API query error")

    @patch('scimapper.scisourcer.dimensions.Dsl')
    def test_search_dimensions_api_no_results(self, MockDsl):
        """
        Test that search_dimensions_api returns an empty list when the API query yields no results.
        """
        mock_dsl_instance = MockDsl.return_value
        mock_dsl_instance.query_iterative.return_value = iter([]) # Empty iterator

        results = search_dimensions_api("query yielding nothing", dsl_instance=mock_dsl_instance)
        self.assertEqual(results, [])

    def test_parse_dimensions_api_record_full(self):
        """
        Test that a fully populated Dimensions API record is parsed correctly.
        
        Verifies extraction and normalization of all relevant fields, including title, authors (with different formats), journal, year, DOI, abstract, keywords (from both 'keywords' and 'concepts'), document type, source type, and raw data retention.
        """
        item_json = {
            "id": "pub.111",
            "title": "Full Dimensions Record",
            "doi": "10.dim/full",
            "year": 2021,
            "publication_year": 2021,
            "authors": [
                {"first_name": "Alice", "last_name": "Wonder"},
                {"name": "Bob The Builder"}
            ],
            "journal": {"title": "Journal of Fullness"},
            "abstract": "A very complete abstract.",
            "keywords": ["kw1", "kw2"],
            "concepts": ["conceptA", "conceptB"],
            "type": "article"
        }
        parsed = _parse_dimensions_api_record(item_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Full Dimensions Record")
        self.assertIn("Wonder Alice", parsed["authors"])
        self.assertIn("Bob The Builder", parsed["authors"])
        self.assertEqual(parsed["journal"], "Journal of Fullness")
        self.assertEqual(parsed["year"], 2021)
        self.assertEqual(parsed["doi"], "10.dim/full")
        self.assertEqual(parsed["dimensions_id"], "pub.111")
        self.assertEqual(parsed["abstract"], "A very complete abstract.")
        self.assertIn("kw1", parsed["keywords"])
        self.assertIn("conceptA", parsed["keywords"])
        self.assertEqual(len(set(parsed["keywords"])), 4)
        self.assertEqual(parsed["document_type"], "article")
        self.assertEqual(parsed["source_type"], "dimensions_api")
        self.assertEqual(parsed["raw_data"], item_json)

    def test_parse_dimensions_api_record_minimal(self):
        """
        Test that parsing a minimal Dimensions API record with only an ID and title returns the expected default values for missing fields.
        """
        item_json = {"id": "pub.min", "title": "Minimal Title Only"}
        parsed = _parse_dimensions_api_record(item_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Minimal Title Only")
        self.assertEqual(parsed["dimensions_id"], "pub.min")
        self.assertEqual(len(parsed["authors"]), 0)
        self.assertEqual(len(parsed["keywords"]), 0)
        self.assertIsNone(parsed["year"])

    def test_parse_dimensions_api_record_no_title(self):
        """
        Test that parsing a Dimensions API record without a title returns None.
        """
        item_json = {"id": "pub.notitle", "doi": "10.dim/notitle"}
        parsed = _parse_dimensions_api_record(item_json)
        self.assertIsNone(parsed)

    def test_parse_dimensions_api_record_empty_input(self):
        """
        Test that parsing an empty dictionary or None input returns None.
        """
        self.assertIsNone(_parse_dimensions_api_record(None))
        self.assertIsNone(_parse_dimensions_api_record({}))

# This import and class redefinition was to fix a previous issue in the test file structure.
# It should be fine now if the file is created correctly.
from scimapper.scisourcer.dimensions import parse_dimensions_file

class TestDimensionsFileDataSource(unittest.TestCase):
    def test_parse_dimensions_file_placeholder(self):
        """
        Test that the placeholder `parse_dimensions_file` function returns an empty list and prints a notice about unimplemented file parsing.
        """
        with patch('builtins.print') as mock_print:
            results = parse_dimensions_file("dummy.csv")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Notice: File parsing for Dimensions ('dummy.csv') is not yet fully implemented.")

if __name__ == '__main__':
    unittest.main()
