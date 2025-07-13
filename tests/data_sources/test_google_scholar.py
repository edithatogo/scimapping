import unittest
from unittest.mock import patch, MagicMock
import warnings

from sciencemapping.data_sources.google_scholar import (
    search_google_scholar,
    _parse_gs_publication,
    SCHOLARLY_AVAILABLE # To control testing paths
)

# Sample raw data that `scholarly.search_pubs()` generator might yield
MOCK_SCHOLARLY_PUB_RAW_1 = {
    'bib': {
        'title': 'Scholarly Test Publication 1',
        'author': 'Author One and Author Two, A.',
        'pub_year': '2022',
        'venue': 'Journal of Scholarly Tests',
        'abstract': 'This is abstract 1. It is very scholarly.'
    },
    'num_citations': 101,
    'pub_url': 'https://scholar.google.com/scholar_url_1',
    'eprint_url': 'https://example.com/pdf1.pdf'
}
MOCK_SCHOLARLY_PUB_RAW_2 = {
    'bib': {
        'title': 'Scholarly Test Publication 2: The Sequel',
        'author': 'Author Three, B. and Author Four', # Different author format
        'pub_year': '2023', # String year
        'venue': 'Conference of Testing Scholars'
        # No abstract here
    },
    'num_citations': 22,
    'pub_url': 'https://scholar.google.com/scholar_url_2',
    # No eprint_url
}
MOCK_SCHOLARLY_PUB_RAW_MINIMAL = { # Minimal data
    'bib': {
        'title': 'Minimal Scholarly Pub'
    },
    'num_citations': 0
}


class TestGoogleScholarDataSource(unittest.TestCase):

    def test_parse_gs_publication_full(self):
        """Test parsing a fairly complete publication dict from scholarly."""
        # Simulate a filled publication object if needed, or just a rich dict
        # For this test, assume pub_data is the dict itself
        parsed = _parse_gs_publication(MOCK_SCHOLARLY_PUB_RAW_1)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Scholarly Test Publication 1")
        self.assertListEqual(sorted(parsed["authors"]), sorted(["Author One", "Author Two, A."]))
        self.assertEqual(parsed["year"], 2022)
        self.assertEqual(parsed["journal"], "Journal of Scholarly Tests")
        self.assertEqual(parsed["abstract"], "This is abstract 1. It is very scholarly.")
        self.assertEqual(parsed["times_cited_google_scholar"], 101)
        self.assertEqual(parsed["publication_url_gs"], "https://scholar.google.com/scholar_url_1")
        self.assertEqual(parsed["eprint_url_gs"], "https://example.com/pdf1.pdf")
        self.assertIsNone(parsed["doi"]) # Not typically in basic scholarly output
        self.assertEqual(parsed["keywords"], []) # Not typically in scholarly output
        self.assertIsNone(parsed["funding_entries"])
        self.assertIsNone(parsed["cited_references"])
        self.assertEqual(parsed["source_type"], "google_scholar")
        self.assertEqual(parsed["raw_data"], MOCK_SCHOLARLY_PUB_RAW_1)

    def test_parse_gs_publication_minimal(self):
        """Test parsing with minimal data."""
        parsed = _parse_gs_publication(MOCK_SCHOLARLY_PUB_RAW_MINIMAL)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Minimal Scholarly Pub")
        self.assertEqual(parsed["authors"], [])
        self.assertIsNone(parsed["year"])
        self.assertEqual(parsed["times_cited_google_scholar"], 0)

    def test_parse_gs_publication_no_title(self):
        """Test parsing returns None if no title."""
        no_title_pub = {'bib': {'author': 'Author Missing Title'}, 'num_citations': 1}
        self.assertIsNone(_parse_gs_publication(no_title_pub))

    def test_parse_gs_publication_various_author_formats(self):
        pub_data = {'bib': {'title': 'T', 'author': 'Uno, A and Dos, B. C. and Tres, D E F'}}
        parsed = _parse_gs_publication(pub_data)
        self.assertListEqual(sorted(parsed['authors']), sorted(['Uno, A', 'Dos, B. C.', 'Tres, D E F']))

        pub_data_single = {'bib': {'title': 'T', 'author': 'JustOne Name'}}
        parsed_single = _parse_gs_publication(pub_data_single)
        self.assertListEqual(parsed_single['authors'], ['JustOne Name'])

    def test_parse_gs_publication_non_string_year(self):
        pub_data = {'bib': {'title': 'T', 'pub_year': 2023}, 'num_citations': 0}
        parsed = _parse_gs_publication(pub_data)
        self.assertEqual(parsed['year'], 2023)

        pub_data_bad_year = {'bib': {'title': 'T', 'pub_year': "forthcoming"}, 'num_citations': 0}
        with warnings.catch_warnings(record=True) as w:
            parsed_bad_year = _parse_gs_publication(pub_data_bad_year)
            self.assertTrue(any("Could not parse year" in str(warn.message) for warn in w))
        self.assertIsNone(parsed_bad_year['year'])


    @patch('sciencemapping.data_sources.google_scholar.scholarly_module')
    @patch('sciencemapping.data_sources.google_scholar.SCHOLARLY_AVAILABLE', True)
    def test_search_google_scholar_success(self, mock_scholarly_available, mock_scholarly):
        """Test successful search and iteration."""
        mock_search_results_generator = iter([MOCK_SCHOLARLY_PUB_RAW_1, MOCK_SCHOLARLY_PUB_RAW_2])
        mock_scholarly.search_pubs.return_value = mock_search_results_generator

        with warnings.catch_warnings(record=True) as w: # Catch the user warning about proxies
            results = search_google_scholar("test query", max_results=2)
            self.assertTrue(any("Using this function to query Google Scholar can be unreliable" in str(warn.message) for warn in w))

        mock_scholarly.search_pubs.assert_called_once_with("test query")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], "Scholarly Test Publication 1")
        self.assertEqual(results[1]['title'], "Scholarly Test Publication 2: The Sequel")

    @patch('sciencemapping.data_sources.google_scholar.scholarly_module')
    @patch('sciencemapping.data_sources.google_scholar.SCHOLARLY_AVAILABLE', True)
    def test_search_google_scholar_max_results_respected(self, mock_scholarly_available, mock_scholarly):
        """Test that max_results is respected."""
        # Simulate a generator that would yield more if not stopped
        mock_search_results_generator = iter([MOCK_SCHOLARLY_PUB_RAW_1, MOCK_SCHOLARLY_PUB_RAW_2, MOCK_SCHOLARLY_PUB_RAW_MINIMAL])
        mock_scholarly.search_pubs.return_value = mock_search_results_generator

        results = search_google_scholar("test query", max_results=1)
        self.assertEqual(len(results), 1)

    @patch('sciencemapping.data_sources.google_scholar.scholarly_module')
    @patch('sciencemapping.data_sources.google_scholar.SCHOLARLY_AVAILABLE', True)
    def test_search_google_scholar_fill_publications_conceptual(self, mock_scholarly_available, mock_scholarly):
        """Test fill_publications path (conceptually, fill itself is hard to mock simply)."""
        # search_pubs yields dicts. The .fill() method is on Publication objects.
        # The current search_google_scholar has a placeholder for fill.
        # This test checks that the path is taken if fill_publications is True.

        # Mock what search_pubs returns (a dict)
        mock_pub_summary_dict = MOCK_SCHOLARLY_PUB_RAW_1.copy()

        # If fill=True, the code tries hasattr(mock_pub_summary_dict, 'fill') which will be False for a dict.
        # So, it will print "direct .fill() method not found".

        mock_scholarly.search_pubs.return_value = iter([mock_pub_summary_dict])

        with patch('builtins.print') as mock_print: # To check the warning about fill
            results = search_google_scholar("fill test", max_results=1, fill_publications=True)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], MOCK_SCHOLARLY_PUB_RAW_1['bib']['title'])
        mock_print.assert_any_call("GoogleScholar: fill_publications=True but direct .fill() method not found on result 1. Parsing as is.")

    @patch('sciencemapping.data_sources.google_scholar.SCHOLARLY_AVAILABLE', False)
    def test_search_scholarly_unavailable(self, mock_scholarly_unavailable):
        """Test behavior when scholarly library is not available."""
        with warnings.catch_warnings(record=True) as w:
            results = search_google_scholar("any query")
            self.assertEqual(results, [])
            self.assertTrue(any("'scholarly' library not available. Cannot perform search." in str(warn.message) for warn in w))

    @patch('sciencemapping.data_sources.google_scholar.scholarly_module')
    @patch('sciencemapping.data_sources.google_scholar.SCHOLARLY_AVAILABLE', True)
    def test_search_google_scholar_api_error(self, mock_scholarly_available, mock_scholarly):
        """Test handling of error during scholarly.search_pubs()."""
        mock_scholarly.search_pubs.side_effect = Exception("Simulated scholarly API error")

        with warnings.catch_warnings(record=True) as w: # Catch UserWarning about proxies & RuntimeWarning for error
            results = search_google_scholar("error query")
            self.assertEqual(results, [])
            self.assertTrue(any("Search failed due to: Simulated scholarly API error" in str(warn.message) for warn in w))

if __name__ == '__main__':
    unittest.main()
