import unittest
from unittest.mock import patch, MagicMock
from sciencemapping.data_sources.dimensions import (
    search_dimensions_api,
    _parse_dimensions_api_record,
    DIMENSIONS_API_AVAILABLE # To conditionally run tests or mock Dsl
)

# Only run API-dependent tests if the library is theoretically available
# Actual calls will be mocked.
@unittest.skipUnless(DIMENSIONS_API_AVAILABLE, "dimcli library not available, skipping Dimensions API tests")
class TestDimensionsAPIDataSource(unittest.TestCase):

    @patch('sciencemapping.data_sources.dimensions.Dsl')
    def test_search_dimensions_api_success(self, MockDsl):
        """Test successful search using Dimensions API and parsing."""
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

    @patch('sciencemapping.data_sources.dimensions.Dsl')
    def test_search_dimensions_api_login_failure(self, MockDsl):
        """Test search_dimensions_api when Dsl initialization (login) fails."""
        MockDsl.side_effect = Exception("Simulated Dsl login error")

        with patch('builtins.print') as mock_print:
            results = search_dimensions_api("any query")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Error initializing Dimensions API client: Simulated Dsl login error")

    @patch('sciencemapping.data_sources.dimensions.Dsl')
    def test_search_dimensions_api_query_error(self, MockDsl):
        """Test search_dimensions_api when the API query itself raises an error."""
        mock_dsl_instance = MockDsl.return_value
        mock_dsl_instance.query_iterative.side_effect = Exception("Simulated API query error")

        with patch('builtins.print') as mock_print:
            results = search_dimensions_api("any query", dsl_instance=mock_dsl_instance)
            self.assertEqual(results, [])
            mock_print.assert_any_call("An error occurred during Dimensions API query: Exception - Simulated API query error")

    @patch('sciencemapping.data_sources.dimensions.Dsl')
    def test_search_dimensions_api_no_results(self, MockDsl):
        """Test search_dimensions_api when the query returns no results."""
        mock_dsl_instance = MockDsl.return_value
        mock_dsl_instance.query_iterative.return_value = iter([]) # Empty iterator

        results = search_dimensions_api("query yielding nothing", dsl_instance=mock_dsl_instance)
        self.assertEqual(results, [])

    def test_parse_dimensions_api_record_full(self):
        """Test parsing of a single Dimensions API record with various fields."""
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
        # Check keyword normalization (merged, sorted, unique, lowercase)
        self.assertListEqual(parsed["keywords"], sorted(["kw1", "kw2", "concepta", "conceptb"]))
        self.assertEqual(parsed["document_type"], "article")
        self.assertEqual(parsed["source_type"], "dimensions_api")
        self.assertEqual(parsed["raw_data"], item_json)

    def test_parse_dimensions_api_record_minimal(self):
        """Test parsing with minimal data (only title)."""
        item_json = {"id": "pub.min", "title": "Minimal Title Only"}
        parsed = _parse_dimensions_api_record(item_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Minimal Title Only")
        self.assertEqual(parsed["dimensions_id"], "pub.min")
        self.assertEqual(len(parsed["authors"]), 0)
        self.assertEqual(len(parsed["keywords"]), 0)
        self.assertIsNone(parsed["year"])

    def test_parse_dimensions_api_record_no_title(self):
        """Test that a record with no title returns None."""
        item_json = {"id": "pub.notitle", "doi": "10.dim/notitle"}
        parsed = _parse_dimensions_api_record(item_json)
        self.assertIsNone(parsed)

    def test_parse_dimensions_api_record_empty_input(self):
        """Test parsing with empty or None input."""
        self.assertIsNone(_parse_dimensions_api_record(None))
        self.assertIsNone(_parse_dimensions_api_record({}))

    def test_parse_dimensions_api_record_with_cited_references(self):
        """Test parsing of cited_references from a Dimensions API record."""
        # Scenario 1: references is a list of dicts with 'id'
        item_json_refs_as_dicts = {
            "id": "pub.main1",
            "title": "Paper with Dict Refs",
            "references": [
                {"id": "pub.ref1"},
                {"id": "pub.ref2"},
                {"id": "pub.ref1"}, # Duplicate
                {"id": "pub.ref3", "doi": "10.ref/doi_for_ref3"}, # Extra field, should still get id
                {"id": " "}, # Empty ID after strip
                {"id": None}, # None ID
                {} # Empty dict
            ]
        }
        parsed1 = _parse_dimensions_api_record(item_json_refs_as_dicts)
        self.assertIsNotNone(parsed1)
        self.assertIsNotNone(parsed1.get("cited_references"), "cited_references should exist for valid refs")
        self.assertListEqual(parsed1["cited_references"], sorted(["pub.ref1", "pub.ref2", "pub.ref3"]))

        # Scenario 2: references is a list of raw IDs (strings/ints)
        item_json_refs_as_list = {
            "id": "pub.main2",
            "title": "Paper with List Refs",
            "references": ["pub.refA", "pub.refB", "pub.refA", 12345, None, "", " ", {"other_key": "val"}] # Mix of string/int ID, and invalid entries
        }
        parsed2 = _parse_dimensions_api_record(item_json_refs_as_list)
        self.assertIsNotNone(parsed2)
        self.assertIsNotNone(parsed2.get("cited_references"), "cited_references should exist for valid raw refs")
        self.assertListEqual(parsed2["cited_references"], sorted(["12345", "pub.refA", "pub.refB"]))

        # Scenario 3: references field is present but empty list
        item_json_refs_empty_list = {
            "id": "pub.main3",
            "title": "Paper with Empty Refs List",
            "references": []
        }
        parsed3 = _parse_dimensions_api_record(item_json_refs_empty_list)
        self.assertIsNotNone(parsed3)
        self.assertIsNone(parsed3.get("cited_references"))

        # Scenario 4: references field is missing
        item_json_refs_missing = {
            "id": "pub.main4",
            "title": "Paper with Missing Refs Field"
        }
        parsed4 = _parse_dimensions_api_record(item_json_refs_missing)
        self.assertIsNotNone(parsed4)
        self.assertIsNone(parsed4.get("cited_references"))

        # Scenario 5: references contains only invalid items
        item_json_refs_all_invalid = {
            "id": "pub.main5",
            "title": "Paper with All Invalid Refs",
            "references": [None, "", " ", {"doi": "10.x/y"}, {}]
        }
        parsed5 = _parse_dimensions_api_record(item_json_refs_all_invalid)
        self.assertIsNotNone(parsed5)
        self.assertIsNone(parsed5.get("cited_references"))

    def test_parse_dimensions_api_record_funding(self):
        """Test parsing of funding information from Dimensions API record."""
        base_data = {"id": "pub.fundtest", "title": "Funding Test"}

        # Scenario 1: Basic funder block
        item1 = {**base_data, "funders": [{
            "name": "National Science Foundation", "acronym": "NSF", "id": "funder.123", "ror_id": "ror.nsf",
            "grant_ids": ["NSF123", " ", None], "grants": [{"id": "Award789"}, "AwardABC", "", None]
        }]}
        parsed1 = _parse_dimensions_api_record(item1)
        self.assertIsNotNone(parsed1.get("funding_entries"))
        self.assertEqual(len(parsed1["funding_entries"]), 1)
        entry1 = parsed1["funding_entries"][0]
        self.assertEqual(entry1["funder_name"], "National Science Foundation")
        self.assertListEqual(entry1["grant_ids"], sorted(["Award789", "AwardABC", "NSF123"]))
        self.assertEqual(entry1["dimensions_funder_id"], "funder.123")
        self.assertEqual(entry1["funder_ror_id"], "ror.nsf")
        self.assertEqual(entry1["source_of_info"], "dimensions_api_funders_field")

        # Scenario 2: Funder name fallback to organization, then acronym
        item2_org = {**base_data, "funders": [{"organization": "Org Name ", "grant_ids": ["ORG1"]}]}
        parsed2_org = _parse_dimensions_api_record(item2_org)
        self.assertEqual(parsed2_org["funding_entries"][0]["funder_name"], "Org Name")

        item2_acro = {**base_data, "funders": [{"acronym": " ACRO ", "grant_ids": ["ACR1"]}]}
        parsed2_acro = _parse_dimensions_api_record(item2_acro)
        self.assertEqual(parsed2_acro["funding_entries"][0]["funder_name"], "ACRO")

        # Scenario 3: Only supporting_grant_ids
        item3 = {**base_data, "supporting_grant_ids": ["sup123 ", " sup456", "sup123", None, ""]}
        parsed3 = _parse_dimensions_api_record(item3)
        self.assertIsNotNone(parsed3.get("funding_entries"))
        entries3 = sorted(parsed3["funding_entries"], key=lambda x: x["grant_ids"][0]) # Sort for consistent order
        self.assertEqual(len(entries3), 2)
        self.assertIsNone(entries3[0].get("funder_name"))
        self.assertListEqual(entries3[0]["grant_ids"], ["sup123"])
        self.assertEqual(entries3[0]["source_of_info"], "dimensions_api_grant_ids_field")
        self.assertTrue(entries3[0]["raw_funding_text"].endswith("sup123"))
        self.assertListEqual(entries3[1]["grant_ids"], ["sup456"])
        self.assertEqual(entries3[1]["source_of_info"], "dimensions_api_grant_ids_field")
        self.assertTrue(entries3[1]["raw_funding_text"].endswith("sup456"))


        # Scenario 4: Both funders block and supporting_grant_ids (mixed, new, duplicate)
        item4 = {**base_data,
            "funders": [{
                "name": "FunderA", "grant_ids": ["gid_A1", "gid_A1"], "grants": ["gid_A2", {"id":"gid_A3"}]
            }],
            "supporting_grant_ids": ["gid_A1", "sup_gid_B", " gid_C_from_sup ", "sup_gid_B"]
        }
        parsed4 = _parse_dimensions_api_record(item4)
        self.assertIsNotNone(parsed4.get("funding_entries"))

        # Expected: FunderA with [gid_A1, gid_A2, gid_A3]
        #           Entry for sup_gid_B
        #           Entry for gid_C_from_sup
        self.assertEqual(len(parsed4["funding_entries"]), 3)

        funder_a_entry = next(e for e in parsed4["funding_entries"] if e.get("funder_name") == "FunderA")
        self.assertListEqual(funder_a_entry["grant_ids"], sorted(["gid_A1", "gid_A2", "gid_A3"]))

        sup_b_entry = next(e for e in parsed4["funding_entries"] if e.get("grant_ids") == ["sup_gid_B"])
        self.assertEqual(sup_b_entry["source_of_info"], "dimensions_api_grant_ids_field")
        self.assertIsNone(sup_b_entry.get("funder_name"))

        sup_c_entry = next(e for e in parsed4["funding_entries"] if e.get("grant_ids") == ["gid_C_from_sup"])
        self.assertEqual(sup_c_entry["source_of_info"], "dimensions_api_grant_ids_field")
        self.assertIsNone(sup_c_entry.get("funder_name"))

        # Scenario 5: Empty grant_ids and grants in funder block, but funder name exists
        item5 = {**base_data, "funders": [{"name": "FunderOnly"}]}
        parsed5 = _parse_dimensions_api_record(item5)
        self.assertIsNotNone(parsed5.get("funding_entries"))
        self.assertEqual(len(parsed5["funding_entries"]), 1)
        self.assertEqual(parsed5["funding_entries"][0]["funder_name"], "FunderOnly")
        self.assertNotIn("grant_ids", parsed5["funding_entries"][0])

        # Scenario 6: No funding information at all
        item6 = {**base_data}
        parsed6 = _parse_dimensions_api_record(item6)
        self.assertIsNone(parsed6.get("funding_entries"))


# This import and class redefinition was to fix a previous issue in the test file structure.
# It should be fine now if the file is created correctly.
from sciencemapping.data_sources.dimensions import parse_dimensions_file

class TestDimensionsFileDataSource(unittest.TestCase):
    def test_parse_dimensions_file_placeholder(self):
        """Test the placeholder function for file parsing."""
        with patch('builtins.print') as mock_print:
            results = parse_dimensions_file("dummy.csv")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Notice: File parsing for Dimensions ('dummy.csv') is not yet fully implemented.")

if __name__ == '__main__':
    unittest.main()
