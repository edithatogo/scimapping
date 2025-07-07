import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from collections import namedtuple

from sciencemapping.data_sources.scopus import (
    search_scopus,
    fetch_scopus_abstract_details,
    _parse_scopus_search_result,
    _is_scopus_configured
)
# Mock the config object from pybliometrics.scopus.utils directly
# as it's imported and used in the scopus module.
@patch('sciencemapping.data_sources.scopus.config', new_callable=MagicMock)
class TestScopusDataSource(unittest.TestCase):

    def test_is_scopus_configured_true(self, mock_config):
        """Test _is_scopus_configured when API key is present."""
        mock_config.__contains__.side_effect = lambda item: item in ["Authentication", "APIKey"]
        mock_config.__getitem__.return_value = {"APIKey": "testkey123"}
        self.assertTrue(_is_scopus_configured())

    def test_is_scopus_configured_false_no_auth(self, mock_config):
        """Test _is_scopus_configured when 'Authentication' section is missing."""
        mock_config.__contains__.side_effect = lambda item: item not in ["Authentication"]
        mock_config.get.return_value = {} # Handles cases where config['Authentication'] might be accessed
        with patch('builtins.print') as mock_print:
            self.assertFalse(_is_scopus_configured())
            mock_print.assert_any_call("Warning: Scopus API key not found in pybliometrics configuration.")

    def test_is_scopus_configured_false_no_apikey(self, mock_config):
        """Test _is_scopus_configured when 'APIKey' is missing."""
        mock_config.__contains__.side_effect = lambda item: item in ["Authentication"] # APIKey check will fail internally
        mock_config.__getitem__.return_value = {} # No APIKey in Authentication
        # _is_scopus_configured itself no longer prints this warning.
        # The warning is now printed by the calling functions (search_scopus, fetch_scopus_abstract_details)
        self.assertFalse(_is_scopus_configured())

    def test_parse_scopus_search_result(self, mock_config):
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
    def test_search_scopus_success(self, mock_is_configured, MockScopusSearch, mock_config_global):
        """Test successful Scopus search."""
        # Mocking the ScopusSearch results
        ScopusSearchResult = namedtuple("ScopusSearchResult", ["title", "eid", "coverDate", "publicationName", "doi", "authors", "author_names", "description", "authkeywords", "aggregationType", "subtypeDescription", "_asdict"])
        mock_result1 = ScopusSearchResult(title="Title 1", eid="eid1", coverDate="2020-01-01", publicationName="Journal1", doi="doi1", authors=[], author_names="Auth1, A.", description="Desc1", authkeywords="key1", aggregationType="Journal", subtypeDescription="Article", _asdict=lambda: {"title":"Title 1"})
        mock_result2 = ScopusSearchResult(title="Title 2", eid="eid2", coverDate="2021-02-02", publicationName="Journal2", doi="doi2", authors=[], author_names="Auth2, B.", description="Desc2", authkeywords="key2", aggregationType="Conference Proceeding", subtypeDescription="Conference Paper", _asdict=lambda: {"title":"Title 2"})

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
    def test_search_scopus_no_results(self, mock_is_configured, MockScopusSearch, mock_config_global):
        """Test Scopus search when no results are found."""
        mock_search_instance = MockScopusSearch.return_value
        type(mock_search_instance).results = PropertyMock(return_value=None) # No results

        results = search_scopus("empty query", max_results=10)
        self.assertEqual(len(results), 0)

    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=False)
    def test_search_scopus_not_configured(self, mock_is_configured, mock_config_global):
        """Test search_scopus when pybliometrics is not configured."""
        with patch('builtins.print') as mock_print: # To catch the warning
            results = search_scopus("any query")
            self.assertEqual(results, [])
            # _is_scopus_configured (mocked to return False) will print its own warnings
            # So we don't need to check mock_print content here unless search_scopus adds more.

    @patch('sciencemapping.data_sources.scopus.AbstractRetrieval')
    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=True)
    def test_fetch_scopus_abstract_details_success(self, mock_is_configured, MockAbstractRetrieval, mock_config_global):
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
    def test_fetch_scopus_abstract_details_error(self, mock_is_configured, MockAbstractRetrieval, mock_config_global):
        """Test error handling in fetch_scopus_abstract_details."""
        # Import errors from pybliometrics.scopus.utils for this test
        from pybliometrics.scopus.utils import errors as scopus_errors
        MockAbstractRetrieval.side_effect = scopus_errors.Scopus404Error("Resource not found")

        with patch('builtins.print') as mock_print:
            details = fetch_scopus_abstract_details("invalid_eid")
            self.assertIsNone(details)
            mock_print.assert_any_call("Scopus document with EID invalid_eid not found or access denied.")

    @patch('sciencemapping.data_sources.scopus._is_scopus_configured', return_value=False)
    def test_fetch_scopus_details_not_configured(self, mock_is_configured, mock_config_global):
        """Test fetch_scopus_abstract_details when not configured."""
        with patch('builtins.print') as mock_print:
             details = fetch_scopus_abstract_details("any_eid")
             self.assertIsNone(details)


if __name__ == '__main__':
    unittest.main()
