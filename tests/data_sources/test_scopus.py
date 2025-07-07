import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from collections import namedtuple

from sciencemapping.data_sources.scopus import (
    search_scopus,
    fetch_scopus_abstract_details,
    _parse_scopus_search_result,
    _is_scopus_configured
)
# Removed class-level patch for 'sciencemapping.data_sources.scopus.config'
# Config will be patched specifically in tests that need it.
class TestScopusDataSource(unittest.TestCase):

    # mock_config argument removed as class-level patch is gone.
    # This test will now need to patch 'sciencemapping.data_sources.scopus.config' itself.
    @patch('sciencemapping.data_sources.scopus.config')
    def test_is_scopus_configured_true(self, mock_config_object):
        """Test _is_scopus_configured when API key is present."""
        # Simulate config being a dictionary with necessary keys
        mock_config_object.__contains__ = lambda item: item in ["Authentication", "APIKey"]
        mock_config_object.__getitem__.return_value = {"APIKey": "testkey123"}
        # Ensure 'Authentication' key itself is present for the first check in _is_scopus_configured
        type(mock_config_object).get = MagicMock(return_value={"APIKey": "testkey123"}) # for config["Authentication"]

        # Re-evaluate how _is_scopus_configured accesses config. It's direct:
        # if "Authentication" in config and "APIKey" in config["Authentication"] and config["Authentication"]["APIKey"]:

        # Let's make mock_config_object behave like a dict for these checks
        def mock_config_contains(key):
            if key == "Authentication": return True
            return False

        def mock_config_getitem(slf_ignore, key): # Added slf_ignore for implicit self
            if key == "Authentication":
                auth_dict_mock = MagicMock()
                # For __contains__ on auth_dict_mock, side_effect lambda should also expect 2 args if used directly by 'in'
                auth_dict_mock.configure_mock(**{
                    '__contains__': MagicMock(side_effect=lambda s_ignore, k: k == "APIKey"),
                    '__getitem__': MagicMock(side_effect=lambda s_ignore, k: "testkey123" if k == "APIKey" else (_ for _ in ()).throw(KeyError(k))) # raise KeyError
                })
                return auth_dict_mock
            raise KeyError(key)

        mock_config_object.configure_mock(**{
            '__contains__': MagicMock(side_effect=mock_config_contains), # mock_config_contains defined above, takes 1 arg (key)
            '__getitem__': MagicMock(side_effect=mock_config_getitem) # mock_config_getitem defined above, takes 2 args (self, key)
        })
        self.assertTrue(_is_scopus_configured())

    @patch('sciencemapping.data_sources.scopus.config')
    def test_is_scopus_configured_false_no_auth(self, mock_config_object):
        """Test _is_scopus_configured when 'Authentication' section is missing."""
        mock_config_object.configure_mock(**{
            '__contains__': MagicMock(return_value=False) # "Authentication" not in config
        })
        self.assertFalse(_is_scopus_configured())

    @patch('sciencemapping.data_sources.scopus.config')
    def test_is_scopus_configured_false_no_apikey(self, mock_config_object):
        """Test _is_scopus_configured when 'APIKey' is missing."""
        auth_dict_mock = MagicMock()
        # __contains__ lambda should expect 2 args (self, key) if used by 'in' operator
        auth_dict_mock.configure_mock(**{
            '__contains__': MagicMock(side_effect=lambda self_ignore, k: k != "APIKey") # "APIKey" not in config["Authentication"]
        })

        # __getitem__ on mock_config_object should also expect 2 args for its side_effect lambda
        mock_config_object.configure_mock(**{
            '__contains__': MagicMock(side_effect=lambda self_ignore, k: k == "Authentication"), # "Authentication" is in config
            '__getitem__': MagicMock(return_value=auth_dict_mock) # config["Authentication"] returns our mock
        })
        self.assertFalse(_is_scopus_configured())

    # This test does not directly use the mock_config argument if it's for parsing logic only
    def test_parse_scopus_search_result(self): # mock_config argument removed if not used
        """Test parsing of a single Scopus search result item."""
        # pybliometrics.scopus.ScopusSearch returns namedtuples for results
        ScopusSearchResult = namedtuple("ScopusSearchResult", [
            "title", "authors", "author_names", "publicationName", "coverDate", "doi",
            "eid", "pubmed_id", "description", "authkeywords", "aggregationType", "subtypeDescription"
        ])

        # Mock author object if authors field is structured
        Author = namedtuple("Author", ["indexed_name"])
        mock_authors_structured = [Author("Doe, J."), Author("Smith, A.")]

        raw_item_full = ScopusSearchResult(
            title="Scopus Test Title",
            authors=mock_authors_structured, # Assuming structured authors
            author_names="Doe, J.; Smith, A.", # Fallback if authors is not structured
            publicationName="Journal of Scopus Testing",
            coverDate="2023-01-15",
            doi="10.1000/scopustest",
            eid="2-s2.0-12345678900",
            pubmed_id="9876543",
            description="This is a Scopus test abstract.",
            authkeywords="scopus | test | python",
            aggregationType="Journal",
            subtypeDescription="Article"
        )
        parsed = _parse_scopus_search_result(raw_item_full)

        self.assertEqual(parsed["title"], "Scopus Test Title")
        self.assertListEqual(parsed["authors"], ["Doe, J.", "Smith, A."]) # Based on structured authors
        self.assertEqual(parsed["journal"], "Journal of Scopus Testing")
        self.assertEqual(parsed["year"], 2023)
        self.assertEqual(parsed["doi"], "10.1000/scopustest")
        self.assertEqual(parsed["scopus_id"], "2-s2.0-12345678900")
        self.assertEqual(parsed["pubmed_id"], "9876543")
        self.assertEqual(parsed["abstract"], "This is a Scopus test abstract.")
        self.assertListEqual(parsed["keywords"], ["scopus", "test", "python"])
        self.assertEqual(parsed["document_type"], "Journal")
        self.assertEqual(parsed["source_type"], "scopus")
        self.assertIn("raw_search_result", parsed)

        # Test with author_names if authors field is simpler
        raw_item_author_names = ScopusSearchResult(
            title="Title with author_names", authors=None, author_names="First, A.; Second, B.",
            publicationName="Journal", coverDate="2022", doi=None, eid="eid2", pubmed_id=None,
            description=None, authkeywords=None, aggregationType=None, subtypeDescription="Review"
        )
        parsed_auth_names = _parse_scopus_search_result(raw_item_author_names)
        self.assertListEqual(parsed_auth_names["authors"], ["First, A.", "Second, B."])
        self.assertEqual(parsed_auth_names["document_type"], "Review")


    @patch('sciencemapping.data_sources.scopus.ScopusSearch')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_search_scopus_success(self, mock_is_configured, MockScopusSearch): # mock_config_global removed
        """Test successful Scopus search."""
        # Mocking the ScopusSearch results
        # Corrected: "_asdict" removed from field list.
        ScopusSearchResultFields = ["title", "eid", "coverDate", "publicationName", "doi", "authors", "author_names", "description", "authkeywords", "aggregationType", "subtypeDescription"]
        ScopusSearchResult = namedtuple("ScopusSearchResult", ScopusSearchResultFields)

        mock_result1_data = {"title":"Title 1", "eid":"eid1", "coverDate":"2020-01-01", "publicationName":"Journal1", "doi":"doi1", "authors":[], "author_names":"Auth1, A.", "description":"Desc1", "authkeywords":"key1", "aggregationType":"Journal", "subtypeDescription":"Article"}
        mock_result2_data = {"title":"Title 2", "eid":"eid2", "coverDate":"2021-02-02", "publicationName":"Journal2", "doi":"doi2", "authors":[], "author_names":"Auth2, B.", "description":"Desc2", "authkeywords":"key2", "aggregationType":"Conference Proceeding", "subtypeDescription":"Conference Paper"}

        # Create instances ensuring all fields defined in ScopusSearchResultFields are provided
        mock_result1 = ScopusSearchResult(**{k: mock_result1_data.get(k) for k in ScopusSearchResultFields})
        mock_result2 = ScopusSearchResult(**{k: mock_result2_data.get(k) for k in ScopusSearchResultFields})

        mock_search_instance = MockScopusSearch.return_value
        type(mock_search_instance).results = PropertyMock(return_value=[mock_result1, mock_result2]) # Mock results as a property

        results = search_scopus("test query", max_results=2)

        MockScopusSearch.assert_called_once_with("test query", count=2, view="STANDARD", subscriber=False)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Title 1")
        self.assertEqual(results[0]["scopus_id"], "eid1")
        self.assertEqual(results[1]["title"], "Title 2")
        self.assertEqual(results[1]["scopus_id"], "eid2")

    @patch('sciencemapping.data_sources.scopus.ScopusSearch')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_search_scopus_no_results(self, mock_is_configured, MockScopusSearch): # mock_config_global removed
        """Test Scopus search when no results are found."""
        mock_search_instance = MockScopusSearch.return_value
        type(mock_search_instance).results = PropertyMock(return_value=None) # No results

        results = search_scopus("empty query", max_results=10)
        self.assertEqual(len(results), 0)

    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=False)
    def test_search_scopus_not_configured(self, mock_is_configured): # mock_config_global removed
        """Test search_scopus when pybliometrics is not configured."""
        # This test should be updated to reflect the two-stage failure:
        # 1. Our _is_scopus_configured() returns False -> prints a warning.
        # 2. pybliometrics call (e.g. ScopusSearch) then fails with FileNotFoundError.
        # For now, it just checks the initial warning and empty result if ScopusSearch doesn't raise FileNotFoundError.

        # Scenario 1: _is_scopus_configured is False, ScopusSearch proceeds (e.g. finds env var key) but returns no results
        with patch('sciencemapping.data_sources.scopus.ScopusSearch') as MockScopusSearch_local:
            mock_search_instance = MockScopusSearch_local.return_value
            type(mock_search_instance).results = PropertyMock(return_value=None) # No results

            with patch('builtins.print') as mock_print:
                results = search_scopus("any query")
                self.assertEqual(results, [])
                mock_print.assert_any_call("Warning: Scopus API key not found in pybliometrics's global CONFIG object. Search may rely on other configurations (e.g., environment variables) or fail.")

        # Scenario 2: _is_scopus_configured is False, and ScopusSearch raises FileNotFoundError
        with patch('sciencemapping.data_sources.scopus.ScopusSearch', side_effect=FileNotFoundError("Mocked: Scopus config.ini not found")) as MockScopusSearch_local_fnf:
            with patch('builtins.print') as mock_print_fnf:
                results_fnf = search_scopus("any query")
                self.assertEqual(results_fnf, [])
                mock_print_fnf.assert_any_call("Warning: Scopus API key not found in pybliometrics's global CONFIG object. Search may rely on other configurations (e.g., environment variables) or fail.")
                mock_print_fnf.assert_any_call("Scopus configuration file or API key not found by pybliometrics. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")


    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_fetch_scopus_abstract_details_success(self, mock_is_configured, MockAbstractRetrieval): # mock_config_global removed
        """Test successful fetching of abstract details."""
        mock_retrieval_instance = MockAbstractRetrieval.return_value
        mock_retrieval_instance.abstract = "Full abstract text."
        mock_retrieval_instance.authkeywords = ["keyword1", "keyword2"]
        mock_retrieval_instance.idxterms = ["indexterm1"]
        # Mocking references (list of objects with an 'id' attribute)
        Ref = namedtuple("Reference", ["id"])
        mock_retrieval_instance.references = [Ref("ref_eid1"), Ref("ref_eid2")]
        mock_retrieval_instance.funding_agency = "NSF"
        mock_retrieval_instance.funding_text = "Supported by NSF grant #123"


        details = fetch_scopus_abstract_details("test_eid")

        MockAbstractRetrieval.assert_called_once_with(identifier="test_eid", id_type='eid', view="FULL", refresh=False)
        self.assertIsNotNone(details)
        self.assertEqual(details["abstract"], "Full abstract text.")
        self.assertListEqual(details["author_keywords"], ["keyword1", "keyword2"])
        self.assertListEqual(details["index_keywords"], ["indexterm1"])
        self.assertListEqual(details["references"], ["ref_eid1", "ref_eid2"])
        self.assertIsNotNone(details["funding_details"])
        self.assertEqual(details["funding_details"]["agency"], "NSF")


    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_fetch_scopus_abstract_details_error(self, mock_is_configured, MockAbstractRetrieval): # mock_config_global removed
        """Test error handling in fetch_scopus_abstract_details."""
        import pybliometrics.scopus # Ensure the parent module is imported
        # Assuming pybliometrics.scopus.errors is a dict mapping error names to classes based on persistent errors
        # This is a guess based on the 'dict object has no attribute' error.
        # We need the actual Scopus404Error class.
        # If the structure is pybliometrics.scopus.errors.Scopus404Error (module.class)
        # and 'errors' is being seen as a dict, this is problematic.

        # Let's construct a mock error that behaves like Scopus404Error for the isinstance check
        # and has the necessary attributes for the code under test.
        # We need scopus_errors.ScopusError and scopus_errors.Scopus404Error from the perspective of scopus.py

        # To do this properly, we might need to import what scopus.py imports.
        from sciencemapping.data_sources.scopus import scopus_errors # This is what the module under test uses.

        # Now, scopus_errors here should be the same 'errors' module object as in scopus.py
        # (unless patching of 'config' somehow breaks this reference, which is the suspicion)
        if hasattr(scopus_errors, 'Scopus404Error'):
            error_instance = scopus_errors.Scopus404Error("Resource not found")
        else:
            # Fallback: If Scopus404Error is STILL not an attribute, create a mock that will pass isinstance
            # This is a deeper problem if this path is taken.
            error_instance = Exception("Simulated Scopus-like 404 Error")
            # To make isinstance(e, scopus_errors.Scopus404Error) work, this is more complex.
            # For now, let's assume the direct access above works based on scopus.py's import.

        MockAbstractRetrieval.side_effect = error_instance

        with patch('builtins.print') as mock_print:
            details = fetch_scopus_abstract_details("invalid_eid")
            self.assertIsNone(details)
            mock_print.assert_any_call("Scopus document with EID invalid_eid not found or access denied.")

    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval', side_effect=FileNotFoundError("Mocked: Scopus config.ini not found"))
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=False) # Simulate our check failing
    def test_fetch_details_not_configured_file_not_found(self, mock_is_configured, MockAbstractRetrieval): # mock_config_global removed
        """Test fetch_scopus_abstract_details when _is_scopus_configured is False and pybliometrics raises FileNotFoundError."""
        with patch('builtins.print') as mock_print:
            details = fetch_scopus_abstract_details("any_eid")
            self.assertIsNone(details)
            mock_print.assert_any_call("Warning: Scopus API key not found in pybliometrics's global CONFIG. Fetching details for EID any_eid may rely on other configurations or fail.")
            mock_print.assert_any_call("Scopus configuration file or API key not found by pybliometrics. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")

    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval') # No FileNotFoundError
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=False) # Simulate our check failing
    def test_fetch_details_not_configured_general_warning(self, mock_is_configured, MockAbstractRetrieval): # mock_config_global removed
        """Test fetch_scopus_abstract_details prints warning if _is_scopus_configured is False but no FileNotFoundError."""
        # Make AbstractRetrieval return a mock object that will result in a dict of Nones
        mock_retrieval_object = MagicMock()
        # Ensure it has a to_dict method for the raw_abstract_retrieval_dict part
        mock_retrieval_object.to_dict.return_value = {"some_raw_key": "some_raw_value"}
        MockAbstractRetrieval.return_value = mock_retrieval_object

        with patch('builtins.print') as mock_print:
            details = fetch_scopus_abstract_details("any_eid")

            expected_details = {
                "abstract": None,
                "author_keywords": None,
                "index_keywords": None,
                "references_count": None,
                "references": [], # getattr(mock_retrieval_object, 'references', []) would yield []
                "funding_details": None, # getattr for funding_agency and funding_text would be None
                "raw_abstract_retrieval_dict": {"some_raw_key": "some_raw_value"} # From the to_dict mock
            }
            self.assertEqual(details, expected_details)

            mock_print.assert_any_call("Warning: Scopus API key not found in pybliometrics's global CONFIG. Fetching details for EID any_eid may rely on other configurations or fail.")

            found_file_not_found_error_print = False
            for call_args in mock_print.call_args_list:
                if "Scopus configuration file or API key not found by pybliometrics" in call_args[0][0]:
                    found_file_not_found_error_print = True
                    break
            self.assertFalse(found_file_not_found_error_print, "FileNotFoundError message should not be printed if AbstractRetrieval doesn't raise FileNotFoundError")


if __name__ == '__main__':
    unittest.main()
