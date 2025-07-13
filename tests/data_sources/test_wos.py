import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
from sciencemapping.data_sources.wos import parse_wos_file, _parse_wos_record
import metaknowledge # For creating mock Record objects if needed

class TestWoSDataSource(unittest.TestCase):

    def test_parse_wos_record_full(self):
        """Test parsing a fairly complete WoS record from metaknowledge.Record."""
        # Create a mock metaknowledge.Record object
        # metaknowledge.Record behaves like a dict with special properties
        mock_mk_record_dict = {
            'TI': "A Test Title for WoS",
            'AU': ["Author, One A.", "Writer, Two B."], # metaknowledge often yields list for AU
            'SO': "Journal of WoS Testing",
            'PY': "2023",
            'DI': "10.1234/wos.test.1",
            'UT': "WOS:000testwosid001",
            'AB': "This is the abstract of the test paper.",
            'DE': "keyword1; keyword2", # Author keywords
            'ID': "keyword plus A; keyword plus B", # Keywords Plus
            'DT': "Article",
            'TC': "10", # Times Cited
            'FU': "National Science Foundation (NSF) (Grant XYZ123, ABC-456); Wellcome Trust (WT0987)",
            'FX': "This work was supported by the NSF and Wellcome Trust. Additional thanks for internal grant.",
            'CR': [
                "Smith J, 2020, J AM CHEM SOC, V1, P1, DOI 10.1000/jacs.test.1",
                "Doe A, 2019, NATURE, V2, P2, DOI 10.1038/nature.test.2",
                "Lee C, 2018, SCIENCE, V3, P3 (No DOI here, but WOS:000012345000001)",
                "Cho K, 2022, J PHYS CHEM B, V126, P789, DOI 10.1021/acs.jpcb.1c09525.",
                "Beta B, 2017, PROC IEEE, WOS:000098765000002, DOI 10.1109/PROC.2017.001"
            ]
        }
        mock_mk_record = MagicMock()

        # Configure the mock's get method and dict conversion
        def get_side_effect(key, default=None):
            return mock_mk_record_dict.get(key, default)

        mock_mk_record.get.side_effect = get_side_effect
        # For dict(record) in _parse_wos_record
        # Make it behave like a dict for items(), keys(), values() if needed, or just directly return the dict
        # A simple way is to mock the __iter__ to yield keys, and __getitem__ to get values.
        # Or, if metaknowledge.Record itself is directly convertible via dict(), mock that.
        # metaknowledge.Record can be cast to dict directly.
        # So, we can make our mock return the dict when cast.
        # However, _parse_wos_record uses dict(record), which iterates over it.
        # Let's ensure it's iterable like a dict for the `dict()` call.
        mock_mk_record.__iter__ = lambda s: iter(mock_mk_record_dict) # Make it iterable for dict()
        mock_mk_record.__getitem__ = lambda s, key: mock_mk_record_dict[key] # Support key access if dict() uses it

        # If dict(record) relies on items()
        mock_mk_record.items.return_value = mock_mk_record_dict.items()
        mock_mk_record._test_get_raw_dict = lambda: mock_mk_record_dict # For bypassing dict(record) with mock

        parsed = _parse_wos_record(mock_mk_record)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "A Test Title for WoS")
        self.assertListEqual(parsed["authors"], ["Author, One A.", "Writer, Two B."])
        self.assertEqual(parsed["journal"], "Journal of WoS Testing")
        self.assertEqual(parsed["year"], 2023)
        self.assertEqual(parsed["doi"], "10.1234/wos.test.1")
        self.assertEqual(parsed["wos_id"], "000testwosid001") # Prefix "WOS:" removed
        self.assertEqual(parsed["abstract"], "This is the abstract of the test paper.")
        # Check keyword normalization (sorted, unique, lowercase)
        self.assertListEqual(parsed["keywords"], sorted(["keyword plus a", "keyword plus b", "keyword1", "keyword2"]))
        self.assertEqual(parsed["document_type"], "Article")
        self.assertEqual(parsed["times_cited_wos"], "10")
        self.assertEqual(parsed["source_type"], "wos")
        self.assertIn("raw_data", parsed)
        self.assertEqual(parsed["raw_data"]['TI'], "A Test Title for WoS")

        # Assert acknowledgements_text_fx
        self.assertEqual(parsed.get("acknowledgements_text_fx"), "This work was supported by the NSF and Wellcome Trust. Additional thanks for internal grant.")

        # Assert funding_entries
        self.assertIn("funding_entries", parsed)
        self.assertIsNotNone(parsed["funding_entries"])
        funding_entries = parsed["funding_entries"]
        self.assertEqual(len(funding_entries), 2) # Two funders from FU string

        # Entry 1: NSF
        nsf_entry = next((fe for fe in funding_entries if "National Science Foundation" in fe.get("funder_name", "")), None)
        self.assertIsNotNone(nsf_entry)
        self.assertEqual(nsf_entry["funder_name"], "National Science Foundation (NSF)") # Should now pass
        self.assertIn("Grant XYZ123", nsf_entry["grant_ids"]) # Corrected expected grant ID
        self.assertIn("ABC-456", nsf_entry["grant_ids"])
        self.assertEqual(nsf_entry["source_of_info"], "wos_FU_field")
        self.assertEqual(nsf_entry["raw_funding_text"], "National Science Foundation (NSF) (Grant XYZ123, ABC-456)")

        # Entry 2: Wellcome Trust
        wt_entry = next((fe for fe in funding_entries if "Wellcome Trust" in fe.get("funder_name", "")), None)
        self.assertIsNotNone(wt_entry)
        self.assertEqual(wt_entry["funder_name"], "Wellcome Trust")
        self.assertListEqual(wt_entry["grant_ids"], ["WT0987"])
        self.assertEqual(wt_entry["source_of_info"], "wos_FU_field")
        self.assertEqual(wt_entry["raw_funding_text"], "Wellcome Trust (WT0987)")

        # Assert cited_references
        self.assertIn("cited_references", parsed)
        self.assertIsNotNone(parsed["cited_references"])
        expected_cited_ids = sorted([
            "10.1000/jacs.test.1",          # From CR item 1 (DOI)
            "10.1038/nature.test.2",      # From CR item 2 (DOI)
            "WOS:000012345000001",        # From CR item 3 (WoS ID, no DOI)
            "10.1021/acs.jpcb.1c09525",   # From CR item 4 (DOI, trailing dot removed)
            "10.1109/PROC.2017.001"       # From CR item 5 (DOI prioritized over WoS ID)
        ])
        self.assertListEqual(parsed["cited_references"], expected_cited_ids)

    def test_parse_wos_record_funding_scenarios(self):
        """Test various FU and FX funding field scenarios for WoS records."""
        base_record_data = {'TI': "Funding Test Paper", 'PY': "2023"}

        # Scenario 1: FU missing, FX present -> FX becomes a funding entry
        record_fx_only_dict = {**base_record_data, 'FX': "Supported by Internal Funds."}
        mock_rec_fx_only = MagicMock()
        mock_rec_fx_only.get.side_effect = lambda k, d=None: record_fx_only_dict.get(k, d)
        mock_rec_fx_only._test_get_raw_dict = lambda: record_fx_only_dict
        parsed_fx_only = _parse_wos_record(mock_rec_fx_only)
        self.assertIsNotNone(parsed_fx_only.get("funding_entries"))
        self.assertEqual(len(parsed_fx_only["funding_entries"]), 1)
        fx_entry = parsed_fx_only["funding_entries"][0]
        self.assertEqual(fx_entry["raw_funding_text"], "Supported by Internal Funds.")
        self.assertEqual(fx_entry["source_of_info"], "wos_FX_field_as_primary")
        self.assertNotIn("funder_name", fx_entry) # FX as primary doesn't parse funder/grants
        self.assertNotIn("grant_ids", fx_entry)
        self.assertEqual(parsed_fx_only.get("acknowledgements_text_fx"), "Supported by Internal Funds.")

        # Scenario 2: FU present but malformed (no parentheses), FX present
        record_fu_malformed_dict = {
            **base_record_data,
            'FU': "Malformed Funder Name Grant 123", # No parens for grant
            'FX': "Additional FX text."
        }
        mock_rec_fu_malformed = MagicMock()
        mock_rec_fu_malformed.get.side_effect = lambda k, d=None: record_fu_malformed_dict.get(k,d)
        mock_rec_fu_malformed._test_get_raw_dict = lambda: record_fu_malformed_dict
        parsed_fu_malformed = _parse_wos_record(mock_rec_fu_malformed)
        self.assertIsNotNone(parsed_fu_malformed.get("funding_entries"))
        self.assertEqual(len(parsed_fu_malformed["funding_entries"]), 1)
        fu_mal_entry = parsed_fu_malformed["funding_entries"][0]
        self.assertEqual(fu_mal_entry["funder_name"], "Malformed Funder Name Grant 123") # Whole string as funder
        self.assertNotIn("grant_ids", fu_mal_entry) # No grants extracted
        self.assertEqual(fu_mal_entry["source_of_info"], "wos_FU_field")
        self.assertEqual(parsed_fu_malformed.get("acknowledgements_text_fx"), "Additional FX text.")

        # Scenario 3: FU is an empty string, FX present
        record_fu_empty_str_dict = {**base_record_data, 'FU': "", 'FX': "FX funding here."}
        mock_rec_fu_empty = MagicMock()
        mock_rec_fu_empty.get.side_effect = lambda k, d=None: record_fu_empty_str_dict.get(k,d)
        mock_rec_fu_empty._test_get_raw_dict = lambda: record_fu_empty_str_dict
        parsed_fu_empty = _parse_wos_record(mock_rec_fu_empty)
        self.assertIsNotNone(parsed_fu_empty.get("funding_entries"))
        self.assertEqual(len(parsed_fu_empty["funding_entries"]), 1)
        fx_entry_after_empty_fu = parsed_fu_empty["funding_entries"][0]
        self.assertEqual(fx_entry_after_empty_fu["raw_funding_text"], "FX funding here.")
        self.assertEqual(fx_entry_after_empty_fu["source_of_info"], "wos_FX_field_as_primary")
        self.assertEqual(parsed_fu_empty.get("acknowledgements_text_fx"), "FX funding here.")

        # Scenario 4: FU with grants but no clear funder name before parentheses: "(Grant 123)"
        record_fu_grant_only_in_parens_dict = {**base_record_data, 'FU': "(Grant 123)"}
        mock_rec_fu_grant_only = MagicMock()
        mock_rec_fu_grant_only.get.side_effect = lambda k, d=None: record_fu_grant_only_in_parens_dict.get(k,d)
        mock_rec_fu_grant_only._test_get_raw_dict = lambda: record_fu_grant_only_in_parens_dict
        parsed_fu_grant_only = _parse_wos_record(mock_rec_fu_grant_only)
        self.assertIsNotNone(parsed_fu_grant_only.get("funding_entries"))
        self.assertEqual(len(parsed_fu_grant_only["funding_entries"]), 1)
        fu_grant_only_entry = parsed_fu_grant_only["funding_entries"][0]
        self.assertEqual(fu_grant_only_entry["funder_name"], "") # Funder name is empty string before parens
        self.assertListEqual(fu_grant_only_entry["grant_ids"], ["Grant 123"])
        self.assertEqual(fu_grant_only_entry["source_of_info"], "wos_FU_field")

        # Scenario 5: FU with funder name containing parentheses itself: "Funder (Dept. of Something) (Grant ABC)"
        record_fu_nested_parens_dict = {**base_record_data, 'FU': "Funder (Dept. of Something) (Grant ABC)"}
        mock_rec_fu_nested = MagicMock()
        mock_rec_fu_nested.get.side_effect = lambda k, d=None: record_fu_nested_parens_dict.get(k,d)
        mock_rec_fu_nested._test_get_raw_dict = lambda: record_fu_nested_parens_dict
        parsed_fu_nested = _parse_wos_record(mock_rec_fu_nested)
        self.assertIsNotNone(parsed_fu_nested.get("funding_entries"))
        self.assertEqual(len(parsed_fu_nested["funding_entries"]), 1)
        fu_nested_entry = parsed_fu_nested["funding_entries"][0]
        self.assertEqual(fu_nested_entry["funder_name"], "Funder (Dept. of Something)") # Regex gets last parens
        self.assertListEqual(fu_nested_entry["grant_ids"], ["Grant ABC"])
        self.assertEqual(fu_nested_entry["source_of_info"], "wos_FU_field")

        # Scenario 6: FU is a list of strings from metaknowledge
        record_fu_list_dict = {
            **base_record_data,
            'FU': ["Funder A (Grant 1)", "Funder B (Grant 2, Grant 3)"]
        }
        mock_rec_fu_list = MagicMock()
        mock_rec_fu_list.get.side_effect = lambda k, d=None: record_fu_list_dict.get(k,d)
        mock_rec_fu_list._test_get_raw_dict = lambda: record_fu_list_dict
        parsed_fu_list = _parse_wos_record(mock_rec_fu_list)
        self.assertIsNotNone(parsed_fu_list.get("funding_entries"))
        self.assertEqual(len(parsed_fu_list["funding_entries"]), 2)
        entry_a = next(e for e in parsed_fu_list["funding_entries"] if e["funder_name"] == "Funder A")
        entry_b = next(e for e in parsed_fu_list["funding_entries"] if e["funder_name"] == "Funder B")
        self.assertListEqual(entry_a["grant_ids"], ["Grant 1"])
        self.assertListEqual(sorted(entry_b["grant_ids"]), sorted(["Grant 2", "Grant 3"]))


    def test_parse_wos_record_minimal(self):
        """Test parsing a WoS record with only essential information (e.g., title)."""
        mock_mk_record_dict = {'TI': "Minimal WoS Title"}

        mock_mk_record = MagicMock() # spec=metaknowledge.Record removed
        def get_side_effect(key, default=None):
            return mock_mk_record_dict.get(key, default)
        mock_mk_record.get.side_effect = get_side_effect
        mock_mk_record.__iter__ = lambda s: iter(mock_mk_record_dict)
        mock_mk_record.__getitem__ = lambda s, key: mock_mk_record_dict[key]
        mock_mk_record.items.return_value = mock_mk_record_dict.items()
        mock_mk_record._test_get_raw_dict = lambda: mock_mk_record_dict

        parsed = _parse_wos_record(mock_mk_record)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Minimal WoS Title")
        self.assertListEqual(parsed["authors"], [])
        self.assertIsNone(parsed["year"])
        self.assertListEqual(parsed["keywords"], [])
        self.assertIsNone(parsed.get("funding_entries"))
        self.assertIsNone(parsed.get("acknowledgements_text_fx"))
        self.assertIsNone(parsed.get("cited_references")) # Check cited_references

    def test_parse_wos_record_no_title(self):
        """Test that a record with no title returns None."""
        mock_mk_record_dict = {'AU': ["Author, A."]} # No 'TI' field

        mock_mk_record = MagicMock() # spec=metaknowledge.Record removed
        def get_side_effect(key, default=None):
            return mock_mk_record_dict.get(key, default)
        mock_mk_record.get.side_effect = get_side_effect
        mock_mk_record.__iter__ = lambda s: iter(mock_mk_record_dict)
        mock_mk_record.__getitem__ = lambda s, key: mock_mk_record_dict[key]
        mock_mk_record.items.return_value = mock_mk_record_dict.items()
        mock_mk_record._test_get_raw_dict = lambda: mock_mk_record_dict

        parsed = _parse_wos_record(mock_mk_record)
        self.assertIsNone(parsed)

    def test_parse_wos_record_keyword_handling(self):
        """Test keyword parsing, including merging DE and ID, and deduplication."""
        mock_mk_record_dict = {
            'TI': "Keyword Test",
            'DE': "Keyword A; Keyword B; keyword c",
            'ID': "Keyword B; Keyword D; KEYWORD A" # Deliberate case difference and overlap
        }

        mock_mk_record = MagicMock() # spec=metaknowledge.Record removed
        def get_side_effect(key, default=None):
            return mock_mk_record_dict.get(key, default)
        mock_mk_record.get.side_effect = get_side_effect
        mock_mk_record.__iter__ = lambda s: iter(mock_mk_record_dict)
        mock_mk_record.__getitem__ = lambda s, key: mock_mk_record_dict[key]
        mock_mk_record.items.return_value = mock_mk_record_dict.items()

        parsed = _parse_wos_record(mock_mk_record)

        self.assertIsNotNone(parsed)
        # New standard: keywords are unique, lowercased, and sorted.
        expected_keywords = ["keyword a", "keyword b", "keyword c", "keyword d"]
        self.assertListEqual(parsed["keywords"], expected_keywords)


    @patch('metaknowledge.RecordCollection')
    def test_parse_wos_file_success(self, MockRecordCollection):
        """Test successful parsing of a WoS file via parse_wos_file."""
        # Create mock metaknowledge.Record objects to be returned by the mock RecordCollection
        record_dict1 = {'TI': "Title 1", 'AU': ["Auth A"], 'PY': "2020", 'UT': "WOS:001", 'DI': None, 'AB': None, 'DE': None, 'ID': None, 'DT': None, 'TC': None, 'SO': None}
        record_dict2 = {'TI': "Title 2", 'AU': ["Auth B"], 'PY': "2021", 'UT': "WOS:002", 'DI': None, 'AB': None, 'DE': None, 'ID': None, 'DT': None, 'TC': None, 'SO': None}

        mock_mk_record1 = MagicMock() # spec=metaknowledge.Record removed
        mock_mk_record1.get.side_effect = lambda k, d=None: record_dict1.get(k, d)
        mock_mk_record1.__iter__ = lambda s: iter(record_dict1)
        mock_mk_record1.__getitem__ = lambda s, k: record_dict1[k]
        mock_mk_record1.items.return_value = record_dict1.items()
        mock_mk_record1._test_get_raw_dict = lambda: record_dict1
        # Ensure all necessary fields for parsing are in record_dict1 or handled by get default
        # For _parse_wos_record, 'TI' is critical. Others have defaults or are handled.

        mock_mk_record2 = MagicMock() # spec=metaknowledge.Record removed
        mock_mk_record2.get.side_effect = lambda k, d=None: record_dict2.get(k, d)
        mock_mk_record2.__iter__ = lambda s: iter(record_dict2)
        mock_mk_record2.__getitem__ = lambda s, k: record_dict2[k]
        mock_mk_record2.items.return_value = record_dict2.items()
        mock_mk_record2._test_get_raw_dict = lambda: record_dict2
        # Ensure all necessary fields for parsing are in record_dict2

        # Configure the mock RecordCollection instance
        mock_rc_instance = MockRecordCollection.return_value
        # Make the instance iterable and yield the mock records
        mock_rc_instance.__iter__.return_value = iter([mock_mk_record1, mock_mk_record2])

        results = parse_wos_file("dummy_path.txt")

        MockRecordCollection.assert_called_once_with("dummy_path.txt", encoding='utf-8')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Title 1")
        self.assertEqual(results[0]["wos_id"], "001")
        self.assertEqual(results[1]["title"], "Title 2")
        self.assertEqual(results[1]["wos_id"], "002")

    @patch('builtins.open', new_callable=mock_open, read_data="file content that metaknowledge would parse")
    @patch('metaknowledge.RecordCollection', side_effect=FileNotFoundError("File not found"))
    def test_parse_wos_file_not_found(self, MockRecordCollection, mock_file_open):
        """Test parse_wos_file when the file is not found (metaknowledge raises FileNotFoundError)."""
        # Even though we mock metaknowledge.RecordCollection to raise FileNotFoundError,
        # the parse_wos_file function itself has a try-except for FileNotFoundError.
        # So, the function should catch it and print a message.
        with patch('builtins.print') as mock_print:
            results = parse_wos_file("non_existent_path.txt")
            self.assertEqual(results, [])
            # The FileNotFoundError is caught by parse_wos_file's own try-except
            mock_print.assert_any_call("Error: Web of Science file not found at non_existent_path.txt")


    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    @patch('metaknowledge.RecordCollection', side_effect=UnicodeDecodeError('utf-8', b'\x80abc', 0, 1, 'invalid start byte'))
    def test_parse_wos_file_unicode_error(self, MockRecordCollection, mock_file_open):
        """Test parse_wos_file with a UnicodeDecodeError."""
        with patch('builtins.print') as mock_print:
            results = parse_wos_file("dummy_path_unicode.txt", encoding='utf-8')
            self.assertEqual(results, [])
            mock_print.assert_any_call("Error: Could not decode Web of Science file at dummy_path_unicode.txt with encoding 'utf-8'. Try a different encoding (e.g., 'latin-1').")

    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    @patch('metaknowledge.RecordCollection', side_effect=Exception("Generic MK error"))
    def test_parse_wos_file_generic_metaknowledge_error(self, MockRecordCollection, mock_file_open):
        """Test parse_wos_file with a generic error from metaknowledge."""
        with patch('builtins.print') as mock_print:
            results = parse_wos_file("dummy_path_generic_error.txt")
            self.assertEqual(results, [])
            mock_print.assert_any_call("An unexpected error occurred while parsing Web of Science file dummy_path_generic_error.txt: Generic MK error")


if __name__ == '__main__':
    unittest.main()
