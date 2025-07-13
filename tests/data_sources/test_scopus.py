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
        def mock_config_contains(instance_self, key): # Added instance_self
            if key == "Authentication": return True
            return False

        def mock_config_getitem(instance_self, key):
            if key == "Authentication":
                auth_dict_mock = MagicMock()
                # Define methods for the auth_dict_mock
                def auth_contains(auth_self, k_param):
                    return k_param == "APIKey"
                def auth_getitem(auth_self, k_param):
                    if k_param == "APIKey":
                        return "testkey123"
                    raise KeyError(k_param)

                auth_dict_mock.configure_mock(
                    __contains__=auth_contains,
                    __getitem__=auth_getitem
                )
                return auth_dict_mock
            raise KeyError(key)

        mock_config_object.configure_mock(
            __contains__=mock_config_contains,
            __getitem__=mock_config_getitem
        )
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
        def auth_contains_false_no_apikey(auth_self, k_param): # Renamed self_ignore, k
            return k_param != "APIKey" # This means "APIKey" is NOT in auth_dict_mock, so "APIKey" in x is False

        auth_dict_mock.configure_mock(
            __contains__=auth_contains_false_no_apikey
            # No __getitem__ needed here as the 'in' check should be False, short-circuiting.
        )

        # __getitem__ on mock_config_object should also expect 2 args for its side_effect lambda
        mock_config_object.configure_mock(
            __contains__=lambda instance_self, k_param: k_param == "Authentication", # "Authentication" is in config
            __getitem__=MagicMock(return_value=auth_dict_mock) # config["Authentication"] returns our mock
        )
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
            authkeywords="SCOPUS | test | python | SCOPUS ", # Add mixed case, spaces, duplicates
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
        self.assertListEqual(parsed["keywords"], ["python", "scopus", "test"]) # Check normalization
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


    @patch('sciencemapping.data_sources.scopus.fetch_scopus_abstract_details') # Mock the detail fetcher
    @patch('sciencemapping.data_sources.scopus.config')
    @patch('sciencemapping.data_sources.scopus.ScopusSearch')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_search_scopus_success_with_details(self, mock_is_configured, MockScopusSearch, mock_scopus_config_global, mock_fetch_details):
        """Test successful Scopus search with fetch_details=True."""
        mock_auth_dict = MagicMock(); mock_auth_dict.get.return_value = "key"; mock_scopus_config_global.get.return_value = mock_auth_dict

        # Mock ScopusSearch results
        ScopusSearchResultFields = ["title", "eid", "coverDate", "publicationName", "doi", "authors", "author_names", "description", "authkeywords", "aggregationType", "subtypeDescription"]
        mock_result1_data = {"title":"Title 1", "eid":"eid1", "authkeywords":"basic_kw"}
        mock_result1 = ScopusSearchResult(**{k: mock_result1_data.get(k) for k in ScopusSearchResultFields})
        mock_search_instance = MockScopusSearch.return_value
        type(mock_search_instance).results = PropertyMock(return_value=[mock_result1])

        # Mock the response from the detailed fetch for eid1
        mock_fetch_details.return_value = {
            "keywords": ["detailed_kw1", "detailed_kw2"],
            "abstract": "Detailed abstract.",
            # ... other detailed fields
        }

        # Call search_scopus with fetch_details=True (default)
        results = search_scopus("test query", max_results=1)

        MockScopusSearch.assert_called_once_with("test query", count=1, view="STANDARD", subscriber=False)
        mock_fetch_details.assert_called_once_with(eid="eid1", api_key=None)

        self.assertEqual(len(results), 1)
        record = results[0]
        self.assertEqual(record["title"], "Title 1")
        # Assert that the keywords from the detailed fetch have overwritten the basic ones
        self.assertListEqual(record["keywords"], ["detailed_kw1", "detailed_kw2"])
        self.assertEqual(record["abstract"], "Detailed abstract.")

    @patch('sciencemapping.data_sources.scopus.fetch_scopus_abstract_details') # Mock the detail fetcher
    @patch('sciencemapping.data_sources.scopus.config')
    @patch('sciencemapping.data_sources.scopus.ScopusSearch')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_search_scopus_success_no_details(self, mock_is_configured, MockScopusSearch, mock_scopus_config_global, mock_fetch_details):
        """Test successful Scopus search with fetch_details=False."""
        mock_auth_dict = MagicMock(); mock_auth_dict.get.return_value = "key"; mock_scopus_config_global.get.return_value = mock_auth_dict

        ScopusSearchResultFields = ["title", "eid", "coverDate", "publicationName", "doi", "authors", "author_names", "description", "authkeywords", "aggregationType", "subtypeDescription"]
        mock_result1_data = {"title":"Title 1", "eid":"eid1", "authkeywords":"basic_kw | another_kw"}
        mock_result1 = ScopusSearchResult(**{k: mock_result1_data.get(k) for k in ScopusSearchResultFields})
        mock_search_instance = MockScopusSearch.return_value
        type(mock_search_instance).results = PropertyMock(return_value=[mock_result1])

        # Call search_scopus with fetch_details=False
        results = search_scopus("test query", max_results=1, fetch_details=False)

        mock_fetch_details.assert_not_called()
        self.assertEqual(len(results), 1)
        record = results[0]
        self.assertEqual(record["title"], "Title 1")
        # Assert that keywords are from the basic search result parsing
        self.assertListEqual(record["keywords"], ["another_kw", "basic_kw"]) # Normalized

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


    @patch('sciencemapping.data_sources.scopus.config') # Added patch
    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_fetch_scopus_abstract_details_success(self, mock_is_configured, MockAbstractRetrieval, mock_scopus_config_global):
        """Test successful fetching of abstract details."""
        # Configure the global mock_scopus_config_global similarly if needed, or ensure api_key is not passed to trigger default path
        # For this test, fetch_scopus_abstract_details is called without api_key, so it relies on _is_scopus_configured
        # and then the globally configured key (which isn't used by AbstractRetrieval mock anyway).
        # Just need to make sure config.get("Authentication", {}).get("APIKey") doesn't raise error on None.
        mock_auth_dict = MagicMock()
        mock_auth_dict.get.return_value = "some_global_key_if_checked" # for .get("APIKey")
        mock_scopus_config_global.get.return_value = mock_auth_dict # for .get("Authentication", {})


        mock_retrieval_instance = MockAbstractRetrieval.return_value
        mock_retrieval_instance.abstract = "Full abstract text."
        mock_retrieval_instance.authkeywords = ["AuthKW1", "  Shared KW "]
        mock_retrieval_instance.idxterms = ["IndexKW1", "shared kw"]
        Ref = namedtuple("Reference", ["id", "doi", "title", "sourcetitle", "authors"]) # More complete mock
        mock_retrieval_instance.references = [Ref("ref_eid1", "doi1", None,None,None), Ref("ref_eid2", "doi2",None,None,None)]

        # Setup structured funding for funding_entries
        MockFundingInfo = namedtuple("FundingInfo", ["agency", "agency_acronym", "grant_id", "country"])
        mock_retrieval_instance.funding = [MockFundingInfo("NSF", "NSF", "#123", "USA")]
        mock_retrieval_instance.funding_text = "Supported by NSF grant #123" # For acknowledgements_text_scopus
        mock_retrieval_instance.to_dict = MagicMock(return_value={})


        details = fetch_scopus_abstract_details("test_eid")

        MockAbstractRetrieval.assert_called_once_with(identifier="test_eid", id_type='eid', view="FULL", refresh=False)
        self.assertIsNotNone(details)
        self.assertEqual(details["abstract"], "Full abstract text.")
        self.assertListEqual(details["keywords"], ["authkw1", "indexkw1", "shared kw"])
        # The "references" key in details dict is for a simple list of EIDs, not cited_references field.
        # The cited_references field is parsed separately.
        self.assertListEqual(details["references"], ["ref_eid1", "ref_eid2"])

        self.assertIsNotNone(details.get("funding_entries"))
        self.assertEqual(len(details["funding_entries"]), 1)
        self.assertEqual(details["funding_entries"][0]["funder_name"], "NSF")
        self.assertListEqual(details["funding_entries"][0]["grant_ids"], ["#123"])
        self.assertEqual(details.get("acknowledgements_text_scopus"), "Supported by NSF grant #123")


    @patch('sciencemapping.data_sources.scopus.config') # Added to mock the global config
    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_fetch_scopus_abstract_details_funding(self, mock_is_configured, MockAbstractRetrieval, mock_scopus_config_global):
        """Test parsing of various funding scenarios from Scopus AbstractRetrieval."""
        # Simulate that the global config object is a dict-like structure
        # to allow temporary API key setting within the function without NoneType error.
        # The function logic is: original_key = config.get("Authentication", {}).get("APIKey")
        # config["Authentication"]["APIKey"] = api_key
        mock_auth_dict = {}
        mock_scopus_config_global.get.return_value = mock_auth_dict # config.get("Authentication", {}) -> mock_auth_dict
        # Make the config behave like a dict for item assignment config['Authentication'] = {}
        def config_setitem(key, value):
            if key == "Authentication": # e.g. config["Authentication"] = {}
                # Allow this, and make the getter for "Authentication" return this new dict
                mock_scopus_config_global.get.return_value = value
            else:
                mock_scopus_config_global.data[key] = value # Generic dict behavior

        mock_scopus_config_global.data = {} # for generic dict behavior storage
        mock_scopus_config_global.__setitem__.side_effect = config_setitem
        # Ensure config.get("Authentication", {}).get("APIKey") doesn't fail if Authentication is set by func
        # This setup is to allow the function's API key manipulation to run without erroring on a None config.
        # It simulates a very basic, mutable config object.

        mock_ab_ret_instance = MockAbstractRetrieval.return_value
        # Common attributes for the mock AbstractRetrieval object
        mock_ab_ret_instance.title = "Funding Test Paper"
        mock_ab_ret_instance.authors = []
        mock_ab_ret_instance.publicationName = "Journal of Funding Tests"
        mock_ab_ret_instance.coverDate = "2023-01-01"
        mock_ab_ret_instance.doi = "10.1016/j.fund.2023"
        mock_ab_ret_instance.identifier = "SCOPUS_FUND_123"
        mock_ab_ret_instance.abstract = None
        mock_ab_ret_instance.authkeywords = None
        mock_ab_ret_instance.references = None
        mock_ab_ret_instance.to_dict = MagicMock(return_value={}) # For raw_abstract_retrieval_dict

        MockFundingInfo = namedtuple("FundingInfo", ["agency", "agency_acronym", "grant_id", "country"])

        test_cases = [
            {
                "name": "Full agency, single grant",
                "funding_list": [MockFundingInfo("National Science Foundation", "NSF", "XYZ123", "USA")],
                "funding_text": "Supported by NSF.",
                "expected_entries": [{"funder_name": "National Science Foundation", "grant_ids": ["XYZ123"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}],
                "expected_ack_text": "Supported by NSF."
            },
            {
                "name": "Full agency, multiple grants in one string",
                "funding_list": [MockFundingInfo("Research Council", "RC", "ID1; ID2 ; ID3", "UK")],
                "funding_text": None,
                "expected_entries": [{"funder_name": "Research Council", "grant_ids": ["ID1", "ID2", "ID3"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}],
                "expected_ack_text": None
            },
            {
                "name": "Generic agency, use acronym",
                "funding_list": [MockFundingInfo("Funding Organization", "FO-Acronym", "G001", "DE")],
                "funding_text": "Funding from FO.",
                "expected_entries": [{"funder_name": "FO-Acronym", "grant_ids": ["G001"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}],
                "expected_ack_text": "Funding from FO."
            },
            {
                "name": "Only acronym",
                "funding_list": [MockFundingInfo(None, "NIH", "R01", "USA")],
                "funding_text": None,
                "expected_entries": [{"funder_name": "NIH", "grant_ids": ["R01"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}],
                "expected_ack_text": None
            },
            {
                "name": "Only grant ID",
                "funding_list": [MockFundingInfo(None, None, "AwardX", "CA")],
                "funding_text": "Award X details.",
                "expected_entries": [{"grant_ids": ["AwardX"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}], # Funder name might be None
                "expected_ack_text": "Award X details."
            },
            {
                "name": "No structured funding, only funding_text",
                "funding_list": None,
                "funding_text": "General support acknowledged.",
                "expected_entries": None, # No structured entries from funding_text alone
                "expected_ack_text": "General support acknowledged."
            },
            {
                "name": "Empty funding list, empty funding_text",
                "funding_list": [],
                "funding_text": "",
                "expected_entries": None,
                "expected_ack_text": None # Or "" if that's what getattr returns
            },
             {
                "name": "Multiple funders",
                "funding_list": [
                    MockFundingInfo("Funder A", "FA", "A01", "US"),
                    MockFundingInfo("Funder B", "FB", "B01; B02", "EU")
                ],
                "funding_text": "Complex funding.",
                "expected_entries": [
                    {"funder_name": "Funder A", "grant_ids": ["A01"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None},
                    {"funder_name": "Funder B", "grant_ids": ["B01", "B02"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}
                ],
                "expected_ack_text": "Complex funding."
            },
            {
                "name": "Agency is 'Unknown', use acronym",
                "funding_list": [MockFundingInfo("Unknown", "GoodAcronym", "GrantUKN", "UK")],
                "funding_text": "",
                "expected_entries": [{"funder_name": "GoodAcronym", "grant_ids": ["GrantUKN"], "source_of_info": "scopus_api_structured_funding", "raw_funding_text": None}],
                "expected_ack_text": None
            },
        ]

        for i, tc in enumerate(test_cases):
            with self.subTest(name=f"Case {i}: {tc['name']}"):
                mock_ab_ret_instance.funding = tc["funding_list"]
                mock_ab_ret_instance.funding_text = tc["funding_text"]

                details = fetch_scopus_abstract_details("eid_placeholder", "dummy_key")

                self.assertEqual(details.get("acknowledgements_text_scopus"), tc["expected_ack_text"])

                retrieved_funding_entries = details.get("funding_entries")
                if tc["expected_entries"] is None:
                    self.assertIsNone(retrieved_funding_entries)
                else:
                    self.assertIsNotNone(retrieved_funding_entries)
                    self.assertEqual(len(retrieved_funding_entries), len(tc["expected_entries"]))
                    # For more robust comparison if order isn't guaranteed (though it should be from list processing)
                    # Convert to comparable form, e.g., sorted list of sorted dict items.
                    # For now, direct comparison assuming order.
                    for j, expected_entry in enumerate(tc["expected_entries"]):
                        actual_entry = retrieved_funding_entries[j]
                        # Raw_funding_text is not part of structured entry, so remove if present in expected
                        if "raw_funding_text" in expected_entry and expected_entry["raw_funding_text"] is None:
                            del expected_entry["raw_funding_text"]

                        # Ensure all expected keys are in actual entry and match
                        for key, val in expected_entry.items():
                            self.assertEqual(actual_entry.get(key), val, msg=f"Key '{key}' mismatch")
                        # Ensure no unexpected keys in actual entry (optional, stricter)
                        # self.assertEqual(len(actual_entry), len(expected_entry), msg="Unexpected keys in entry")


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
        # Make AbstractRetrieval return a mock object with attributes explicitly set to match expected_details
        mock_retrieval_object = MagicMock()
        mock_retrieval_object.abstract = None
        mock_retrieval_object.authkeywords = None
        mock_retrieval_object.idxterms = None
        mock_retrieval_object.refcount = None
        mock_retrieval_object.references = None # This will result in "references": [] and "cited_references": None
        mock_retrieval_object.funding = None    # This will result in "funding_entries": None
        mock_retrieval_object.funding_text = None # This will result in "acknowledgements_text_scopus": None
        mock_retrieval_object.to_dict.return_value = {"some_raw_key": "some_raw_value"}
        MockAbstractRetrieval.return_value = mock_retrieval_object

        with patch('builtins.print') as mock_print:
            details = fetch_scopus_abstract_details("any_eid")

            expected_details = {
                "abstract": None,
                "author_keywords": None,
                "index_keywords": None,
                "references_count": None,
                "references": [],
                "funding_entries": None, # Corrected from funding_details
                "acknowledgements_text_scopus": None, # Added this field
                "cited_references": None, # Added this field
                "raw_abstract_retrieval_dict": {"some_raw_key": "some_raw_value"}
            }
            # Sort keys for comparison if dicts can have different orders
            # For now, direct comparison.
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
