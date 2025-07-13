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
        """Test successful search using OpenAlex API and parsing."""
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
        """Test search_openalex_works when the API query itself raises an error."""
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
        """Test search_openalex_works when the query returns no results."""
        mock_works_query_instance = MockWorks.return_value
        mock_works_query_instance.search.return_value = mock_works_query_instance
        mock_works_query_instance.filter.return_value = mock_works_query_instance
        mock_works_query_instance.paginate.return_value = iter([]) # Empty iterator

        results = search_openalex_works(search_query="query yielding nothing")
        self.assertEqual(results, [])

    def test_parse_openalex_work_full(self):
        """Test parsing of a single OpenAlex work record with various fields."""
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
        """Test parsing with minimal data (only display_name as title)."""
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
        """Test that providing an email sets it in openalex.config."""
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

    def test_parse_openalex_work_with_cited_references(self):
        """Test parsing of cited_references from an OpenAlex work record."""
        item_json_with_refs = {
            "id": "https://openalex.org/W_MAIN",
            "display_name": "Paper with OpenAlex Refs",
            "publication_year": 2023, # Added to make it a valid record
            "referenced_works": [
                "https://openalex.org/W123",
                "https://openalex.org/W456",
                "http://some.other.url/W789", # Invalid prefix
                "https://openalex.org/W123",   # Duplicate
                "https://openalex.org/WXYZ",   # Valid format
                "https://openalex.org/",       # Invalid - no ID part
                "https://openalex.org/w999",   # Lowercase w, should still work if ID format is W<digits>
                None,                          # Invalid type
                "not_a_url"                    # Invalid format
            ]
        }
        parsed = _parse_openalex_work(item_json_with_refs)
        self.assertIsNotNone(parsed, "Parsed object should not be None for valid input with refs")
        self.assertIsNotNone(parsed.get("cited_references"), "cited_references should not be None when valid refs are present")
        # The parser extracts the ID as is, so "w999" will be "w999". OpenAlex IDs are case-sensitive (W vs w).
        # Current logic `split("/")[-1]` will get "w999".
        # The check `and "openalex.org/W" in ref_url` means "w999" would be missed.
        # Let's adjust expectation or the parser. Parser should be case-insensitive for "openalex.org/W" or flexible.
        # For now, assuming the check is case-sensitive as written in current parser.
        # With the updated parser (case-insensitive startswith and ID check "W" or "w"):
        # "w999" should now be included.
        self.assertListEqual(parsed["cited_references"], sorted(["W123", "W456", "WXYZ", "w999"]))


        item_json_ref_lowercase_w_valid = {
            "id": "https://openalex.org/W_MAIN_LW",
            "display_name": "Paper with Lowercase w Ref",
            "publication_year": 2023,
            "referenced_works": [
                "https://openalex.org/w777", # This should now be parsed
                "https://openalex.org/work/w778" # Invalid path structure
            ]
        }
        parsed_lw = _parse_openalex_work(item_json_ref_lowercase_w_valid)
        self.assertIsNotNone(parsed_lw)
        self.assertIsNotNone(parsed_lw.get("cited_references"), "Lowercase 'w' in URL should now be parsed")
        self.assertListEqual(parsed_lw["cited_references"], ["w777"])


        item_json_no_refs_field = {
            "id": "https://openalex.org/W_NO_REFS_FIELD",
            "display_name": "Paper without referenced_works field",
            "publication_year": 2023
        }
        parsed_no_field = _parse_openalex_work(item_json_no_refs_field)
        self.assertIsNotNone(parsed_no_field)
        self.assertIsNone(parsed_no_field.get("cited_references"))

        item_json_empty_refs_list = {
            "id": "https://openalex.org/W_EMPTY_REFS",
            "display_name": "Paper with empty referenced_works list",
            "publication_year": 2023,
            "referenced_works": []
        }
        parsed_empty_list = _parse_openalex_work(item_json_empty_refs_list)
        self.assertIsNotNone(parsed_empty_list)
        self.assertIsNone(parsed_empty_list.get("cited_references"))

        item_json_all_invalid_refs = {
            "id": "https://openalex.org/W_ALL_INVALID",
            "display_name": "Paper with all invalid refs",
            "publication_year": 2023,
            "referenced_works": ["http://foo.bar/W1", None, "", "https://openalex.org/X123"] # X is not W
        }
        parsed_all_invalid = _parse_openalex_work(item_json_all_invalid_refs)
        self.assertIsNotNone(parsed_all_invalid)
        self.assertIsNone(parsed_all_invalid.get("cited_references"))

if __name__ == '__main__':
    unittest.main()
