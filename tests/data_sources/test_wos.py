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
            'FU': "National Science Foundation (NSF) (Grant XYZ123, ABC-456); Wellcome Trust (WT0987)", # Funding Agency and Grant Number
            'FX': "This work was supported by the NSF and Wellcome Trust. Additional thanks for internal grant." # Funding Text
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
        self.assertIn("keyword1", parsed["keywords"])
        self.assertIn("keyword2", parsed["keywords"])
        self.assertIn("keyword plus A", parsed["keywords"])
        self.assertIn("keyword plus B", parsed["keywords"])
        self.assertEqual(len(parsed["keywords"]), 4) # Ensure no duplicates if DE/ID overlap (though not in this mock)
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
        self.assertListEqual(wt_entry["grant_ids"], ["WT0987"]) # Ensure it's a list with one item
        self.assertEqual(wt_entry["source_of_info"], "wos_FU_field")
        self.assertEqual(wt_entry["raw_funding_text"], "Wellcome Trust (WT0987)")


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
        self.assertIsNone(parsed.get("funding_entries")) # Check funding_entries
        self.assertIsNone(parsed.get("acknowledgements_text_fx")) # Check fx text

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
        # Order might vary depending on set operations if not careful, but content should be unique
        # The current implementation preserves order of first appearance (case-insensitively unique)
        expected_keywords = ["Keyword A", "Keyword B", "keyword c", "Keyword D"]
        self.assertListEqual(sorted(parsed["keywords"]), sorted(expected_keywords)) # Sort for comparison if order not guaranteed
        self.assertEqual(len(parsed["keywords"]), 4)


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
