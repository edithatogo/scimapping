import unittest
from unittest.mock import patch, MagicMock, call
import warnings # Import the warnings module
from sciencemapping.utils.enrichment import enrich_records_with_crossref_funding, HABANERO_AVAILABLE, DEFAULT_CROSSREF_MAILTO

# Sample records for testing enrichment
SAMPLE_RECORDS_FOR_ENRICHMENT = [
    {"title": "Paper 1", "doi": "10.1234/doi1", "authors": ["A"]}, # Will have funding
    {"title": "Paper 2", "doi": "https://doi.org/10.1234/doi2", "authors": ["B"]}, # Will have different funding
    {"title": "Paper 3", "authors": ["C"]}, # No DOI
    {"title": "Paper 4", "doi": "10.1234/doi4", "authors": ["D"]}, # CrossRef returns no funder info
    {"title": "Paper 5", "doi": "10.1234/doi1", "authors": ["E"]}, # Duplicate DOI as Paper 1
    {"title": "Paper 6", "doi": "10.1234/doi_error", "authors": ["F"]}, # DOI that causes API error
]

# Mock CrossRef API responses
MOCK_CROSSREF_RESPONSE_DOI1 = {
    "status": "ok",
    "message-type": "work",
    "message-version": "1.0.0",
    "message": {
        "DOI": "10.1234/doi1",
        "title": ["Mock Title for DOI1"],
        "funder": [
            {
                "DOI": "10.13039/100000001",
                "name": "National Science Foundation",
                "doi-asserted-by": "publisher",
                "award": ["NSF Grant 123", "Award ABC"]
            },
            {"name": "Internal Funding"} # Funder without DOI or specific award numbers
        ]
    }
}
MOCK_CROSSREF_RESPONSE_DOI2 = {
    "status": "ok",
    "message-type": "work",
    "message-version": "1.0.0",
    "message": {
        "DOI": "10.1234/doi2",
        "title": ["Mock Title for DOI2"],
        "funder": [
            {
                "name": "Wellcome Trust",
                "award": ["WT Grant XYZ"]
            }
        ]
    }
}
MOCK_CROSSREF_RESPONSE_DOI4_NO_FUNDER = { # For Paper 4
    "status": "ok",
    "message-type": "work",
    "message-version": "1.0.0",
    "message": {
        "DOI": "10.1234/doi4",
        "title": ["Mock Title for DOI4"]
        # No 'funder' key
    }
}
MOCK_CROSSREF_RESPONSE_DOI_ERROR_ITEM = { # For Paper 6, simulating a specific DOI error within a batch
    "status": "error", # or "resource-not-found"
    "message-type": "input-message",
    "message": {
        "DOI": "10.1234/doi_error", # This helps identify which DOI failed if batching
        "details": "Resource not found or an error occurred."
    }
}


class TestCrossRefEnrichment(unittest.TestCase):

    def setUp(self):
        # Make copies of records for each test to avoid interference
        self.records = [rec.copy() for rec in SAMPLE_RECORDS_FOR_ENRICHMENT]

    @patch('sciencemapping.utils.enrichment.Crossref') # Inner
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True) # Outer
    def test_enrichment_success_multiple_dois(self, MockCrossref_arg): # Corrected signature
        """Test successful enrichment for multiple DOIs, including DOI normalization and batching."""
        mock_cr_instance = MockCrossref_arg.return_value # Use the passed mock argument

        # Simulate cr.works(ids=...) behavior: it takes a list of DOIs
        # and returns a list of corresponding results.
        def works_side_effect(ids=None):
            results_map = {
                "10.1234/doi1": MOCK_CROSSREF_RESPONSE_DOI1,
                "10.1234/doi2": MOCK_CROSSREF_RESPONSE_DOI2, # Note: input DOI has https:// prefix
                "10.1234/doi4": MOCK_CROSSREF_RESPONSE_DOI4_NO_FUNDER,
                "10.1234/doi_error": MOCK_CROSSREF_RESPONSE_DOI_ERROR_ITEM,
            }
            # habanero might return None or raise error for unfound DOIs in a batch,
            # or return a list with error objects. Here, we simulate it returns what it finds.
            return [results_map[doi] for doi in ids if doi in results_map]

        mock_cr_instance.works.side_effect = works_side_effect

        enriched = enrich_records_with_crossref_funding(self.records, mailto="test@example.com", batch_size=2)

        MockCrossref_arg.assert_called_once_with(mailto="test@example.com") # Use the passed mock argument

        # Check calls to cr.works - should be batched
        # Unique DOIs: doi1, doi2, doi4, doi_error (4 unique DOIs)
        # Batch size 2 means 2 calls to cr.works
        self.assertEqual(mock_cr_instance.works.call_count, 2)
        # Example: First call could be for ['10.1234/doi1', '10.1234/doi2'] (order might vary due to set)
        # Second call for ['10.1234/doi4', '10.1234/doi_error']
        # We can check that all unique DOIs were part of some call
        all_queried_dois_in_calls = []
        for c in mock_cr_instance.works.call_args_list:
            all_queried_dois_in_calls.extend(c.kwargs['ids'])

        self.assertIn("10.1234/doi1", all_queried_dois_in_calls)
        self.assertIn("10.1234/doi2", all_queried_dois_in_calls) # Original was https://...
        self.assertIn("10.1234/doi4", all_queried_dois_in_calls)
        self.assertIn("10.1234/doi_error", all_queried_dois_in_calls)


        # Record 0 (Paper 1, doi1)
        self.assertIn("crossref_funding", enriched[0])
        self.assertEqual(len(enriched[0]["crossref_funding"]), 2)
        self.assertEqual(enriched[0]["crossref_funding"][0]["name"], "National Science Foundation")
        self.assertIn("NSF Grant 123", enriched[0]["crossref_funding"][0]["awards"])

        # Record 1 (Paper 2, doi2) - DOI was normalized
        self.assertIn("crossref_funding", enriched[1])
        self.assertEqual(enriched[1]["crossref_funding"][0]["name"], "Wellcome Trust")
        self.assertIn("WT Grant XYZ", enriched[1]["crossref_funding"][0]["awards"])

        # Record 2 (Paper 3, no DOI)
        self.assertNotIn("crossref_funding", enriched[2])

        # Record 3 (Paper 4, doi4, no funder info from CrossRef)
        self.assertNotIn("crossref_funding", enriched[3]) # No "funder" key in response

        # Record 4 (Paper 5, duplicate doi1)
        self.assertIn("crossref_funding", enriched[4])
        self.assertEqual(len(enriched[4]["crossref_funding"]), 2) # Should have same data as Paper 1
        self.assertEqual(enriched[4]["crossref_funding"][0]["name"], "National Science Foundation")

        # Record 5 (Paper 6, doi_error)
        self.assertNotIn("crossref_funding", enriched[5]) # API returned error for this DOI

    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', False)
    def test_enrichment_habanero_not_available(self): # Removed mock_habanero_false argument
        """Test behavior when habanero is not available."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            enriched = enrich_records_with_crossref_funding(self.records)
            self.assertEqual(enriched, self.records) # Should return original records
            self.assertTrue(any("habanero library not available" in str(warn.message) for warn in w))

    @patch('sciencemapping.utils.enrichment.Crossref') # Inner, provides MockCrossref_arg
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True) # Outer, constant, no arg
    def test_enrichment_api_call_general_exception(self, MockCrossref_arg): # Corrected signature, already using MockCrossref_arg
        """Test handling of a general exception during API call."""
        mock_cr_instance = MockCrossref_arg.return_value
        mock_cr_instance.works.side_effect = Exception("Network timeout")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            enriched = enrich_records_with_crossref_funding(self.records) # Will use records with DOIs
            # Expect original records back, as enrichment failed for the batch
            self.assertEqual(len(enriched), len(self.records))
            # Check if all original records are identical (no partial enrichment on error)
            for i, rec in enumerate(enriched):
                self.assertEqual(rec, self.records[i]) # No "crossref_funding" key added
                self.assertNotIn("crossref_funding", rec)

            self.assertTrue(any("Error during CrossRef API call" in str(warn.message) for warn in w))
            self.assertTrue(any("Network timeout" in str(warn.message) for warn in w))

    def test_enrichment_no_dois_in_records(self):
        """Test enrichment when no records have DOIs."""
        records_no_doi = [{"title": "No DOI paper"}]
        with patch('builtins.print') as mock_print: # To check the info print
            enriched = enrich_records_with_crossref_funding(records_no_doi)
            self.assertEqual(enriched, records_no_doi)
            mock_print.assert_any_call("Enrichment: No DOIs found in records to query CrossRef.")

    @patch('sciencemapping.utils.enrichment.Crossref') # Inner
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True) # Outer
    def test_enrichment_default_mailto(self, MockCrossref_arg): # Corrected signature, already using MockCrossref_arg
        """Test that default mailto is used if none provided to function."""
        mock_cr_instance = MockCrossref_arg.return_value
        mock_cr_instance.works.return_value = [] # No results needed, just check mailto

        with warnings.catch_warnings(record=True) as w:
            # Suppress the warning about using default mailto for this specific test's check
            warnings.filterwarnings("ignore", message="No mailto email provided for CrossRef polite pool.")
            enrich_records_with_crossref_funding([{"doi": "10.1/test"}], mailto=None)

        MockCrossref_arg.assert_called_once_with(mailto=DEFAULT_CROSSREF_MAILTO) # Use the passed mock argument

if __name__ == '__main__':
    unittest.main()
