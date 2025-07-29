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

    @patch('sciencemapping.utils.enrichment.Crossref_class') # Corrected patch target
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_success_multiple_dois(self, MockCrossref_class_arg): # Renamed arg for clarity
        """Test successful enrichment for multiple DOIs, including DOI normalization and batching."""
        mock_cr_instance = MockCrossref_class_arg.return_value # Corrected to MockCrossref_class_arg

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
        """Test handling of a general exception during API call."""
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
        """Test that CrossRef data appends/merges with existing funding_entries."""
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

        self.assertEqual(len(enriched_dup[0]["funding_entries"]), 1, "Duplicate entry should be merged; not added as new.")
        updated_entry = enriched_dup[0]["funding_entries"][0]
        # Name matching is part of the new logic. If "NSF" from CR normalizes to "National Science Foundation"
        # and matches the existing entry, it should merge.
        self.assertEqual(updated_entry.get("funder_name"), "National Science Foundation")
        self.assertIn("CR-X1", updated_entry.get("grant_ids", []))
        self.assertEqual(updated_entry.get("funder_crossref_id"), "10.13039/100000001")
        # Source of info should indicate augmentation
        self.assertEqual(updated_entry.get("source_of_info"), "parser; crossref_api_augmentation")


    @patch('sciencemapping.utils.enrichment.Crossref_class')
    @patch('sciencemapping.utils.enrichment.HABANERO_AVAILABLE', True)
    def test_enrichment_prioritized_merging_logic(self, MockCrossref_class_arg):
        """Test the new prioritized merging logic for CrossRef funding data."""
        mock_cr_instance = MockCrossref_class_arg.return_value

        # --- Test Data Setup ---
        # Case 1: Match by CrossRef ID, augment existing
        record1_initial = {
            "doi": "10.001/doi1", "funding_entries": [
                {"funder_name": "Old Funder Name", "funder_crossref_id": "10.13039/CRID1", "grant_ids": ["OLD_G1"], "source_of_info": "source1"}
            ]} # Added funder_crossref_id to existing entry
        cr_response1 = {"DOI": "10.001/doi1", "funder": [{
            "name": "CrossRef Funder Name A", "DOI": "10.13039/CRID1", "ror":"ror1", "award": ["CR_G1", "OLD_G1"]
        }]}

        # Case 2: Match by ROR ID (no CrossRef ID match), augment existing
        record2_initial = {
            "doi": "10.002/doi2", "funding_entries": [
                {"funder_name": "Funder By ROR", "funder_ror_id": "ror2", "grant_ids": ["OLD_G2"], "source_of_info": "source2"}
            ]}
        cr_response2 = {"DOI": "10.002/doi2", "funder": [{ # Different CrossRef ID or missing
            "name": "CrossRef Funder Name B", "DOI": "10.13039/CRID_OTHER", "ror":"ror2", "award": ["CR_G2"]
        }]}

        # Case 3: Match by Name (no ID match), augment existing
        record3_initial = {
            "doi": "10.003/doi3", "funding_entries": [
                {"funder_name": "National Institutes of Health", "grant_ids": ["OLD_G3"], "source_of_info": "source3"} # Will be normalized
            ]}
        cr_response3 = {"DOI": "10.003/doi3", "funder": [{ # No CR_ID or ROR_ID, or different ones
            "name": "NIH", "award": ["CR_G3"], "DOI":"10.13039/SOME_OTHER_ID" # Name "NIH" normalizes to "National Institutes of Health"
        }]}

        # Case 4: No match, add as new entry
        record4_initial = {
            "doi": "10.004/doi4", "funding_entries": [
                {"funder_name": "Existing Funder", "grant_ids": ["OLD_G4"], "funder_crossref_id": "10.13039/EXISTING_CRID", "source_of_info": "source4"}
            ]}
        cr_response4 = {"DOI": "10.004/doi4", "funder": [{
            "name": "New Funder From CR", "DOI": "10.13039/NEW_CRID", "ror":"new_ror", "award": ["NEW_G1"]
        }]}

        # Case 5: CrossRef provides ID, existing entry has only name. Existing name is generic.
        record5_initial = {
            "doi": "10.005/doi5", "funding_entries": [
                {"funder_name": "Unknown Funder", "grant_ids": ["OLD_G5"], "source_of_info": "source5"}
            ]}
        cr_response5 = {"DOI": "10.005/doi5", "funder": [{
            "name": "Specific Funder Name From CR", "DOI": "10.13039/CRID5", "award": ["CR_G5"]
        }]}

        # Case 6: CrossRef provides only name and award, matches existing entry by name. Existing has ID.
        record6_initial = {
            "doi": "10.006/doi6", "funding_entries": [
                {"funder_name": "Wellcome Trust", "funder_crossref_id":"10.13039/100004440", "grant_ids": ["WT_OLD"], "source_of_info": "source6"}
            ]}
        cr_response6 = {"DOI": "10.006/doi6", "funder": [{
            "name": "Wellcome Trust", "award": ["WT_NEW_FROM_CR", "WT_OLD"] # No IDs in this CR funder entry
        }]}


        mock_records_map = {
            "10.001/doi1": record1_initial, "10.002/doi2": record2_initial,
            "10.003/doi3": record3_initial, "10.004/doi4": record4_initial,
            "10.005/doi5": record5_initial, "10.006/doi6": record6_initial,
        }
        mock_cr_responses_map = {
            "10.001/doi1": cr_response1, "10.002/doi2": cr_response2,
            "10.003/doi3": cr_response3, "10.004/doi4": cr_response4,
            "10.005/doi5": cr_response5, "10.006/doi6": cr_response6,
        }

        def works_side_effect_detailed(ids=None):
            return [{"status":"ok", "message-type":"work", "message-version":"1.0.0", "message": mock_cr_responses_map[doi]} for doi in ids if doi in mock_cr_responses_map]
        mock_cr_instance.works.side_effect = works_side_effect_detailed

        test_records_list = [record1_initial, record2_initial, record3_initial, record4_initial, record5_initial, record6_initial]

        # Enrich the records (modifies in place)
        enrich_records_with_crossref_funding(test_records_list, mailto="test@example.com")

        # --- Assertions ---
        # Record 1 (Matched by CrossRef ID)
        r1_entries = record1_initial["funding_entries"]
        self.assertEqual(len(r1_entries), 1)
        self.assertEqual(r1_entries[0]["funder_name"], "CrossRef Funder Name A") # Name updated
        self.assertEqual(r1_entries[0]["funder_crossref_id"], "10.13039/CRID1")
        self.assertEqual(r1_entries[0]["funder_ror_id"], "ror1") # ROR added
        self.assertListEqual(r1_entries[0]["grant_ids"], sorted(["OLD_G1", "CR_G1"]))
        self.assertEqual(r1_entries[0]["source_of_info"], "source1; crossref_api_augmentation")

        # Record 2 (Matched by ROR ID)
        r2_entries = record2_initial["funding_entries"]
        self.assertEqual(len(r2_entries), 1)
        self.assertEqual(r2_entries[0]["funder_name"], "CrossRef Funder Name B") # Name updated
        self.assertEqual(r2_entries[0]["funder_ror_id"], "ror2")
        self.assertEqual(r2_entries[0].get("funder_crossref_id"), "10.13039/CRID_OTHER") # CR ID added
        self.assertListEqual(r2_entries[0]["grant_ids"], sorted(["OLD_G2", "CR_G2"]))
        self.assertEqual(r2_entries[0]["source_of_info"], "source2; crossref_api_augmentation")

        # Record 3 (Matched by Name)
        r3_entries = record3_initial["funding_entries"]
        self.assertEqual(len(r3_entries), 1)
        self.assertEqual(r3_entries[0]["funder_name"], "National Institutes of Health") # Name was already normalized
        self.assertEqual(r3_entries[0].get("funder_crossref_id"), "10.13039/SOME_OTHER_ID") # CR ID added
        self.assertListEqual(r3_entries[0]["grant_ids"], sorted(["OLD_G3", "CR_G3"]))
        self.assertEqual(r3_entries[0]["source_of_info"], "source3; crossref_api_augmentation")

        # Record 4 (No Match - New Entry Added)
        r4_entries = record4_initial["funding_entries"]
        self.assertEqual(len(r4_entries), 2)
        new_entry_r4 = next(e for e in r4_entries if e["source_of_info"] == "crossref_api")
        self.assertEqual(new_entry_r4["funder_name"], "New Funder From CR")
        self.assertEqual(new_entry_r4["funder_crossref_id"], "10.13039/NEW_CRID")
        self.assertEqual(new_entry_r4["funder_ror_id"], "new_ror")
        self.assertListEqual(new_entry_r4["grant_ids"], ["NEW_G1"])

        # Record 5 (No ID match, Name mismatch with "Unknown Funder" -> New entry from CR)
        r5_entries = record5_initial["funding_entries"]
        self.assertEqual(len(r5_entries), 2)

        unknown_funder_entry_r5 = next(e for e in r5_entries if e.get("funder_name") == "Unknown Funder")
        self.assertIsNotNone(unknown_funder_entry_r5)
        self.assertListEqual(unknown_funder_entry_r5["grant_ids"], ["OLD_G5"])
        self.assertEqual(unknown_funder_entry_r5["source_of_info"], "source5")
        self.assertNotIn("funder_crossref_id", unknown_funder_entry_r5) # Should not gain CRID5

        specific_funder_entry_r5 = next(e for e in r5_entries if e.get("funder_name") == "Specific Funder Name From CR")
        self.assertIsNotNone(specific_funder_entry_r5)
        self.assertEqual(specific_funder_entry_r5["funder_crossref_id"], "10.13039/CRID5")
        self.assertListEqual(specific_funder_entry_r5["grant_ids"], ["CR_G5"])
        self.assertEqual(specific_funder_entry_r5["source_of_info"], "crossref_api")

        # Record 6 (Matched by Name, existing entry had ID, CR entry doesn't. ID should be preserved.)
        r6_entries = record6_initial["funding_entries"]
        self.assertEqual(len(r6_entries), 1)
        self.assertEqual(r6_entries[0]["funder_name"], "Wellcome Trust")
        self.assertEqual(r6_entries[0]["funder_crossref_id"], "10.13039/100004440") # Original ID preserved
        self.assertListEqual(r6_entries[0]["grant_ids"], sorted(["WT_OLD", "WT_NEW_FROM_CR"]))
        self.assertEqual(r6_entries[0]["source_of_info"], "source6; crossref_api_augmentation")


if __name__ == '__main__':
    unittest.main()
