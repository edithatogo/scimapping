import unittest
from unittest.mock import patch, MagicMock

# Import the class to be tested
from scimapper.sciprocessor.funding_analyzer import FundingAnalyzer, SPACY_AVAILABLE, nlp_spacy as global_nlp_spacy

SAMPLE_RECORDS_FOR_FUNDING = [
    { # Record 0
        "title": "Paper X", "doi": "10.x/1",
        "funding_details": {"agency": "NSF", "text": "Supported by NSF grant CBET-123 and ARO award W911NF-00-1."}
    },
    { # Record 1
        "title": "Paper Y", "doi": "10.y/2",
        "funders": [{"display_name": "Wellcome Trust"}, {"name": "ERC"}], # OpenAlex style
        "acknowledgements": "This work was also supported by NIH (grant R01-XYZ) and The Bill Melinda Gates Foundation."
    },
    { # Record 2
        "title": "Paper Z", "doi": "10.z/3",
        "FU": "National Science Foundation (NSF) (ANT-0123, OPP-456); European Research Council (ERC) (AdG-789)"
    },
    { # Record 3
      "title": "Paper Unfunded", "doi": "10.u/4"
    },
    { # Record 4: Only acknowledgements with a grant ID
      "title": "Paper AckOnly", "doi": "10.a/5",
      "acknowledgements": "We thank the Medical Research Council for grant MR/N012345/1."
    },
    { # Record 5: Plain text funding in FU
        "title": "Paper FU Plain", "doi": "10.fp/6",
        "FU": "Max Planck Society"
    }
]

class TestFundingAnalyzer(unittest.TestCase):

    def test_extract_funding_data_placeholder(self):
        """
        Tests that FundingAnalyzer.extract_funding_data() correctly identifies funders and grant IDs from a variety of sample records using placeholder extraction logic.
        
        Verifies that the method extracts the expected funders and grant IDs from structured fields and acknowledgements, and that only records containing funding information are included in the results.
        """
        analyzer = FundingAnalyzer(SAMPLE_RECORDS_FOR_FUNDING)
        results = analyzer.extract_funding_data()

        self.assertEqual(len(results), 5) # Records 0, 1, 2, 4, 5 should have some funding info

        # Record 0: NSF, CBET-123, W911NF-00-1
        res0 = next((r for r in results if r["record_index"] == 0), None)
        self.assertIsNotNone(res0)
        self.assertIn("National Science Foundation", res0["funders"])
        self.assertIn("CBET-123", res0["grant_ids"])
        self.assertIn("W911NF-00-1", res0["grant_ids"])

        # Record 1: Wellcome Trust, ERC (from structured 'funders'), NIH (from ack), Bill Melinda Gates Foundation (from ack)
        # Grant R01-XYZ from ack
        res1 = next((r for r in results if r["record_index"] == 1), None)
        self.assertIsNotNone(res1)
        self.assertIn("Wellcome Trust", res1["funders"])
        self.assertIn("European Research Council", res1["funders"])
        self.assertIn("R01-XYZ", res1["grant_ids"])

        # Record 2: National Science Foundation (NSF), European Research Council (ERC)
        # Grants: ANT-0123, OPP-456, AdG-789
        res2 = next((r for r in results if r["record_index"] == 2), None)
        self.assertIsNotNone(res2)
        self.assertIn("National Science Foundation", res2["funders"])
        self.assertIn("European Research Council", res2["funders"])
        self.assertIn("ANT-0123", res2["grant_ids"])
        self.assertIn("OPP-456", res2["grant_ids"])
        self.assertIn("AdG-789", res2["grant_ids"])

        # Record 4: Medical Research Council (from ack), MR/N012345/1 (from ack)
        res4 = next((r for r in results if r["record_index"] == 4), None)
        self.assertIsNotNone(res4)
        self.assertIn("MR/N012345/1", res4["grant_ids"])

        # Record 5: Max Planck Society
        res5 = next((r for r in results if r["record_index"] == 5), None)
        self.assertIsNotNone(res5)
        self.assertIn("Max Planck Society", res5["funders"])


    def test_get_funding_summary_stats_placeholder(self):
        """
        Test that the funding summary statistics are correctly computed from sample records.
        
        Verifies that the analyzer reports the correct total number of records, records with funding information, unique normalized funders, and top funders by frequency.
        """
        analyzer = FundingAnalyzer(SAMPLE_RECORDS_FOR_FUNDING)
        stats = analyzer.get_funding_summary_stats()

        self.assertEqual(stats["total_records_analyzed"], len(SAMPLE_RECORDS_FOR_FUNDING))
        self.assertEqual(stats["records_with_any_funding_info"], 5)

        self.assertEqual(stats["unique_funders_identified_normalized"], 4)

        top_funders_dict = dict(stats["top_funders_normalized"])
        self.assertEqual(top_funders_dict.get("National Science Foundation"), 2)
        self.assertEqual(top_funders_dict.get("European Research Council"), 1)
        self.assertEqual(top_funders_dict.get("Wellcome Trust"), 1)

    @patch('scimapper.sciprocessor.funding_analyzer.SPACY_AVAILABLE', False)
    def test_extract_funding_data_spacy_unavailable(self):
        """
        Test that funding extraction falls back to regex-based grant ID extraction when spaCy is unavailable.
        
        Verifies that no funder organizations are extracted from acknowledgements and only grant IDs matching regex patterns are identified.
        """
        records_with_ack = [
            {"title": "NLP Test", "acknowledgements": "Funded by The Grant Givers and grant XYZ-123."}
        ]
        analyzer = FundingAnalyzer(records_with_ack) # SPACY_AVAILABLE will be False due to patch

        # Temporarily ensure the global nlp_spacy is None for this test's instance if it was somehow loaded
        with patch('scimapper.sciprocessor.funding_analyzer.nlp_spacy', None):
            results = analyzer.extract_funding_data()

        self.assertEqual(len(results), 1)
        self.assertIn("XYZ-123", results[0]["grant_ids"])
        self.assertEqual(len(results[0]["funders"]), 0) # No ORG extraction

    @patch('scimapper.sciprocessor.funding_analyzer.SPACY_AVAILABLE', True)
    @patch('scimapper.sciprocessor.funding_analyzer.nlp_spacy') # This is the loaded spaCy model
    def test_extract_funding_data_with_spacy_nlp(self, mock_nlp_model):
        """
        Test that funding extraction uses spaCy NLP to identify funders and grant IDs in acknowledgements when spaCy is available.
        
        Simulates spaCy's entity recognition to ensure that organization names and grant IDs are correctly extracted from free-text acknowledgements. Verifies that the NLP model is called and that only relevant funders and grant IDs are included in the results.
        """

        # Setup mock for spaCy NLP processing
        mock_doc = MagicMock()
        mock_entity_funder = MagicMock()
        mock_entity_funder.text = "The Grant Giving Foundation"
        mock_entity_funder.label_ = "ORG"

        mock_entity_other_org = MagicMock()
        mock_entity_other_org.text = "Some University"
        mock_entity_other_org.label_ = "ORG"

        mock_entity_person = MagicMock()
        mock_entity_person.text = "Dr. Smith"
        mock_entity_person.label_ = "PERSON"

        mock_doc.ents = [mock_entity_funder, mock_entity_other_org, mock_entity_person]
        mock_nlp_model.return_value = mock_doc

        records_for_nlp = [
            {"title": "NLP Gold", "acknowledgements": "This study was generously funded by The Grant Giving Foundation (Grant ABC/987). Thanks to Some University for facilities."}
        ]
        analyzer = FundingAnalyzer(records_for_nlp)
        results = analyzer.extract_funding_data()

        self.assertEqual(len(results), 1)
        self.assertIn("The Grant Giving Foundation", results[0]["funders"])
        self.assertIn("ABC/987", results[0]["grant_ids"])
        mock_nlp_model.assert_called_once_with("This study was generously funded by The Grant Giving Foundation (Grant ABC/987). Thanks to Some University for facilities.")

    def test_empty_records_funding(self):
        """
        Test that FundingAnalyzer returns empty results and zero statistics when given no records.
        """
        analyzer = FundingAnalyzer([])
        extracted = analyzer.extract_funding_data()
        self.assertEqual(len(extracted), 0)
        stats = analyzer.get_funding_summary_stats()
        self.assertEqual(stats["total_records_analyzed"], 0)
        self.assertEqual(stats["records_with_any_funding_info"], 0)
        self.assertEqual(stats["unique_funders_identified"], 0)
        self.assertEqual(len(stats["top_funders"]), 0)

if __name__ == '__main__':
    unittest.main()
