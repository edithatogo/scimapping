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
        """
        Prepares a fresh copy of the sample records before each test to prevent test interference.
        """
        self.records = [rec.copy() for rec in SAMPLE_RECORDS_FOR_ENRICHMENT]

    @patch('sciencemapping.utils.enrichment.Crossref_class') # Corrected patch target
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_success_multiple_dois(self, MockCrossref_class_arg): # Renamed arg for clarity
        """
        Test enrichment of multiple records with various DOI scenarios, verifying batching, DOI normalization, and correct assignment of funding entries.
        
        This test simulates CrossRef API responses for multiple unique DOIs, including cases with multiple funders, no funders, duplicate DOIs, and API errors. It asserts that:
        - The CrossRef client is instantiated with the correct mailto.
        - DOIs are batched and all unique DOIs are queried.
        - Funding entries are correctly extracted and assigned to records, including funder names, grant IDs, CrossRef funder IDs, and source information.
        - Records without DOIs, with no funder info, or with API errors remain unmodified.
        - Duplicate DOIs receive consistent enrichment.
        """
        mock_cr_instance = MockCrossref_class_arg.return_value # Corrected to MockCrossref_class_arg

        # Simulate cr.works(ids=...) behavior: it takes a list of DOIs
        # and returns a list of corresponding results.
        def works_side_effect(ids=None):
            """
            Simulates the CrossRef API `works` method by returning mock responses for provided DOIs.
            
            Parameters:
                ids (list of str, optional): List of DOI strings to query.
            
            Returns:
                list: Mocked CrossRef API responses corresponding to the provided DOIs.
            """
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

        MockCrossref_class_arg.assert_called_once_with(mailto="test@example.com") # Corrected to MockCrossref_class_arg

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


        # Record 0 (Paper 1, clean_doi: 10.1234/doi1)
        self.assertNotIn("crossref_funding", enriched[0]) # Old field should not exist
        self.assertIn("funding_entries", enriched[0])
        self.assertIsNotNone(enriched[0]["funding_entries"])
        # Expected entries from MOCK_CROSSREF_RESPONSE_DOI1
        # Funder 1: NSF, Grants: ["NSF Grant 123", "Award ABC"], CrossRef ID: "10.13039/100000001"
        # Funder 2: Internal Funding
        nsf_entry_doi1 = next((e for e in enriched[0]["funding_entries"] if e.get("funder_name") == "National Science Foundation"), None)
        self.assertIsNotNone(nsf_entry_doi1)
        self.assertEqual(nsf_entry_doi1.get("funder_crossref_id"), "10.13039/100000001")
        self.assertListEqual(sorted(nsf_entry_doi1.get("grant_ids", [])), sorted(["NSF Grant 123", "Award ABC"]))
        self.assertEqual(nsf_entry_doi1.get("source_of_info"), "crossref_api")

        internal_funding_entry_doi1 = next((e for e in enriched[0]["funding_entries"] if e.get("funder_name") == "Internal Funding"), None)
        self.assertIsNotNone(internal_funding_entry_doi1)
        self.assertNotIn("grant_ids", internal_funding_entry_doi1) # No awards for this one in mock
        self.assertEqual(internal_funding_entry_doi1.get("source_of_info"), "crossref_api")
        self.assertEqual(len(enriched[0]["funding_entries"]), 2)

        # Record 1 (Paper 2, clean_doi: 10.1234/doi2)
        self.assertNotIn("crossref_funding", enriched[1])
        self.assertIn("funding_entries", enriched[1])
        wt_entry_doi2 = next((e for e in enriched[1]["funding_entries"] if e.get("funder_name") == "Wellcome Trust"), None)
        self.assertIsNotNone(wt_entry_doi2)
        self.assertListEqual(wt_entry_doi2.get("grant_ids", []), ["WT Grant XYZ"])
        self.assertEqual(wt_entry_doi2.get("source_of_info"), "crossref_api")
        self.assertEqual(len(enriched[1]["funding_entries"]), 1)


        # Record 2 (Paper 3, no DOI)
        self.assertIsNone(enriched[2].get("funding_entries")) # Or assertNotIn if key is not added for None

        # Record 3 (Paper 4, doi4, no funder info from CrossRef)
        self.assertIsNone(enriched[3].get("funding_entries"))

        # Record 4 (Paper 5, duplicate clean_doi: 10.1234/doi1)
        self.assertNotIn("crossref_funding", enriched[4])
        self.assertIn("funding_entries", enriched[4])
        self.assertEqual(len(enriched[4]["funding_entries"]), 2) # Should have same data as Paper 1
        nsf_entry_doi1_dup = next((e for e in enriched[4]["funding_entries"] if e.get("funder_name") == "National Science Foundation"), None)
        self.assertIsNotNone(nsf_entry_doi1_dup)
        self.assertEqual(nsf_entry_doi1_dup.get("funder_crossref_id"), "10.13039/100000001")

        # Record 5 (Paper 6, doi_error)
        self.assertIsNone(enriched[5].get("funding_entries"))

    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', False)
    def test_enrichment_habanero_not_available(self): # Removed mock_habanero_false argument
        """Test behavior when habanero is not available."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            enriched = enrich_records_with_crossref_funding(self.records)
            self.assertEqual(enriched, self.records) # Should return original records
            self.assertTrue(any("habanero library not available" in str(warn.message) for warn in w))

    @patch('sciencemapping.utils.enrichment.Crossref_class') # Corrected patch target
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_api_call_general_exception(self, MockCrossref_class_arg):
        """
        Test that a general exception during the CrossRef API call results in no enrichment and appropriate warnings.
        
        Verifies that when an exception (e.g., network timeout) occurs during the CrossRef API request, the original records are returned unchanged and relevant warnings are issued.
        """
        mock_cr_instance = MockCrossref_class_arg.return_value
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
        with patch('builtins.print') as mock_print:
            enriched = enrich_records_with_crossref_funding(records_no_doi)
            self.assertEqual(enriched, records_no_doi)
            mock_print.assert_any_call("Enrichment: No valid DOIs found in records to query CrossRef.") # Updated string

    @patch('sciencemapping.utils.enrichment.Crossref_class') # Corrected patch target
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_default_mailto(self, MockCrossref_class_arg):
        """Test that default mailto is used if none provided to function."""
        mock_cr_instance = MockCrossref_class_arg.return_value
        mock_cr_instance.works.return_value = [] # No results needed, just check mailto

        with warnings.catch_warnings(record=True) as w:
            # Suppress the warning about using default mailto for this specific test's check
            warnings.filterwarnings("ignore", message="No mailto email provided for CrossRef polite pool.")
            enrich_records_with_crossref_funding([{"doi": "10.1/test"}], mailto=None)

        MockCrossref_class_arg.assert_called_once_with(mailto=DEFAULT_CROSSREF_MAILTO)

    @patch('sciencemapping.utils.enrichment.Crossref_class') # Corrected patch target
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_merges_with_existing_funding_entries(self, MockCrossref_class_arg): # Argument already correctly named
        """
        Test that enrichment merges CrossRef funding data with existing funding entries in records.
        
        Verifies that new CrossRef funding entries are appended to records with existing funding data, and that overlapping funders are deduplicated and updated with CrossRef information (such as funder IDs and grant IDs) without overwriting the original source of information.
        """
        mock_cr_instance = MockCrossref_class_arg.return_value # Use the correct argument name

        # Mock CrossRef response for a DOI
        doi1_cr_response = {
            "status": "ok", "message-type": "work", "message-version": "1.0.0",
            "message": {
                "DOI": "10.1000/doi1",
                "funder": [{ "name": "CrossRef Funder X", "award": ["CR-X1"], "DOI": "10.13039/FXFUND" }]
            }
        }
        # This lambda will be the side_effect for cr.works(ids=...)
        def works_side_effect_merge(ids=None):
            """
            Simulates CrossRef API responses for specific DOI batches to support funding data enrichment tests.
            
            Parameters:
                ids (list, optional): List of DOI strings to query.
            
            Returns:
                list: A list containing mock CrossRef API response dictionaries for the provided DOIs, or an empty list if no match is found.
            """
            if ids == ["10.1000/doi1"]: # Make sure to match cleaned DOI
                return [doi1_cr_response]
            # Handle the dup DOI case separately or make side_effect more general
            if ids == ["10.1000/doi_dup"]: # Cleaned DOI
                 dup_doi_cr_response = {
                    "status": "ok", "message-type": "work", "message-version": "1.0.0",
                    "message": {
                        "DOI": "10.1000/doi_dup",
                        "funder": [{ "name": "NSF", "DOI": "10.13039/100000001", "award": ["CR-X1"] }]
                    }
                }
                 return [dup_doi_cr_response]
            return [] # Default for other DOI batches
        mock_cr_instance.works.side_effect = works_side_effect_merge

        # Record already has some funding_entries from a primary parser
        records_with_initial_funding = [
            {
                "title": "Paper 1",
                "doi": "10.1000/doi1",
                "funding_entries": [
                    {
                        "funder_name": "Primary Funder A",
                        "grant_ids": ["P-A1"],
                        "source_of_info": "parser_source"
                    }
                ]
            }
        ]

        enriched = enrich_records_with_crossref_funding(records_with_initial_funding, mailto="test@example.com")

        self.assertEqual(len(enriched[0]["funding_entries"]), 2, "Primary + CrossRef entry expected")

        primary_entry_found = any(
            e.get("funder_name") == "Primary Funder A" for e in enriched[0]["funding_entries"]
        )
        crossref_entry_found = any(
            e.get("funder_name") == "CrossRef Funder X" and e.get("source_of_info") == "crossref_api"
            for e in enriched[0]["funding_entries"]
        )
        self.assertTrue(primary_entry_found, "Primary funding entry should be preserved.")
        self.assertTrue(crossref_entry_found, "CrossRef funding entry should be added.")
        self.assertEqual(enriched[0]["funding_entries"][1].get("funder_crossref_id"), "10.13039/FXFUND")


        # Test de-duplication/update: if CrossRef data is similar to an existing entry
        record_with_dup_funding_potential = [
            {
                "title": "Paper Dup", "doi": "10.1000/doi_dup",
                "funding_entries": [{ "funder_name": "National Science Foundation", "grant_ids": ["CR-X1"], "source_of_info": "parser"}] # Name will be normalized
            }
        ]

        enriched_dup = enrich_records_with_crossref_funding(record_with_dup_funding_potential, mailto="test@example.com")

        self.assertEqual(len(enriched_dup[0]["funding_entries"]), 1, "Duplicate entry should not be added; existing one should be updated.")
        updated_entry = enriched_dup[0]["funding_entries"][0]
        self.assertEqual(updated_entry.get("funder_name"), "National Science Foundation") # Normalized from "NSF" via _normalize_funder_name_enrich
        self.assertIn("CR-X1", updated_entry.get("grant_ids", []))
        self.assertEqual(updated_entry.get("funder_crossref_id"), "10.13039/100000001", "CrossRef ID should be added/updated.")
        self.assertEqual(updated_entry.get("source_of_info"), "parser", "Original source_of_info should be kept if entry is updated.")


if __name__ == '__main__':
    unittest.main()
