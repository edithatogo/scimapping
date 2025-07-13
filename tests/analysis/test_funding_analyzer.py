import unittest
from unittest.mock import patch, MagicMock
import warnings

from sciencemapping.analysis.funding_analyzer import FundingAnalyzer
# Import SPACY_AVAILABLE to patch it for testing fallback
from sciencemapping.analysis.funding_analyzer import SPACY_AVAILABLE as ACTUAL_SPACY_AVAILABLE

SAMPLE_RECORDS_WITH_FUNDING_ENTRIES = [
    {
        "title": "Paper X", "doi": "10.x/1", "record_index_for_test": 0,
        "funding_entries": [
            {"funder_name": "NSF", "grant_ids": ["CBET-123", "W911NF-00-1"], "source_of_info": "parser_A"},
            {"funder_name": "NIH", "grant_ids": ["R01-EXAMPL"], "source_of_info": "parser_A"}
        ]
    },
    {
        "title": "Paper Y", "doi": "10.y/2", "record_index_for_test": 1,
        "funding_entries": [
            {"funder_name": "Wellcome Trust", "source_of_info": "parser_B"},
            {"funder_name": "ERC", "grant_ids": ["AdG-789"], "source_of_info": "parser_B"}
        ]
    },
    {
      "title": "Paper AckOnly NLP", "doi": "10.a/5", "record_index_for_test": 2,
      "acknowledgements": "Supported by Medical Research Council grant MR/X001/1 and The Example Org."
    },
    {
      "title": "Paper Unfunded", "doi": "10.u/4", "record_index_for_test": 3
    }
]

class TestFundingAnalyzer(unittest.TestCase):

    def setUp(self):
        pass # Analyzer created in each test to ensure patched state is picked up

    @patch('sciencemapping.analysis.funding_analyzer.SPACY_AVAILABLE', False)
    def test_extract_from_pre_parsed_funding_entries_nlp_off(self): # Argument removed
        """Test extraction from 'funding_entries' when NLP is OFF."""
        analyzer = FundingAnalyzer(SAMPLE_RECORDS_WITH_FUNDING_ENTRIES)
        results = analyzer.extract_funding_data()

        self.assertEqual(len(results), 2, "Should process records with funding_entries (Rec0, Rec1)")

        res0 = next((r for r in results if r["record_index"] == 0), None)
        self.assertIsNotNone(res0)
        self.assertIn("National Science Foundation", res0["funders"])
        self.assertIn("National Institutes of Health", res0["funders"])
        self.assertIn("CBET-123", res0["grant_ids"])
        self.assertEqual(res0["source_of_funding_info"], "structured_from_parser")

        res1 = next((r for r in results if r["record_index"] == 1), None)
        self.assertIsNotNone(res1)
        self.assertIn("Wellcome Trust", res1["funders"])
        self.assertIn("European Research Council", res1["funders"])
        self.assertEqual(res1["source_of_funding_info"], "structured_from_parser")

        res2_present = any(r["record_index"] == 2 for r in results)
        self.assertFalse(res2_present, "Record 2 (ack only) should not yield funding if NLP is off.")

    @patch('sciencemapping.analysis.funding_analyzer.SPACY_AVAILABLE', False)
    def test_get_funding_summary_stats_from_pre_parsed_nlp_off(self): # Argument removed
        """Test summary stats from 'funding_entries' with NLP OFF."""
        analyzer = FundingAnalyzer(SAMPLE_RECORDS_WITH_FUNDING_ENTRIES)
        stats = analyzer.get_funding_summary_stats()

        self.assertEqual(stats["total_records_analyzed"], len(SAMPLE_RECORDS_WITH_FUNDING_ENTRIES))
        self.assertEqual(stats["records_with_any_funding_info"], 2)
        self.assertEqual(stats["unique_funders_identified_normalized"], 4)
        top_funders = dict(stats["top_funders_normalized"])
        self.assertEqual(top_funders.get("National Science Foundation"), 1)
        self.assertEqual(top_funders.get("National Institutes of Health"), 1)

    @patch('sciencemapping.analysis.funding_analyzer.nlp_spacy')
    @patch('sciencemapping.analysis.funding_analyzer.SPACY_AVAILABLE', True)
    def test_extract_funding_data_with_spacy_nlp_on_ack(self, mock_nlp_model):
        """Test NLP extraction from acknowledgements when structured is missing and spaCy is ON."""
        mock_doc = MagicMock()
        mock_ents = [
            MagicMock(text="Medical Research Council", label_="ORG"),
            MagicMock(text="The Example Org", label_="ORG") # This will be normalized
        ]
        mock_doc.ents = mock_ents
        mock_nlp_model.return_value = mock_doc

        record_for_nlp_test = [r for r in SAMPLE_RECORDS_WITH_FUNDING_ENTRIES if r["record_index_for_test"] == 2]
        analyzer = FundingAnalyzer(record_for_nlp_test)
        results = analyzer.extract_funding_data()

        self.assertEqual(len(results), 1)
        res2 = results[0]
        self.assertIn("Medical Research Council", res2["funders"])
        self.assertIn("Example Org", res2["funders"]) # Corrected: Expect normalized name
        self.assertIn("MR/X001/1", res2["grant_ids"])
        self.assertEqual(res2["source_of_funding_info"], "nlp_acknowledgements")
        mock_nlp_model.assert_called_once_with("Supported by Medical Research Council grant MR/X001/1 and The Example Org.")

    @patch('sciencemapping.analysis.funding_analyzer.SPACY_AVAILABLE', False)
    def test_extract_funding_data_spacy_unavailable_for_ack(self): # Argument removed
        """Test extraction from acknowledgements is skipped if spaCy is OFF and no pre-parsed entries."""
        record_for_nlp_test = [r for r in SAMPLE_RECORDS_WITH_FUNDING_ENTRIES if r["record_index_for_test"] == 2]
        with patch('sciencemapping.analysis.funding_analyzer.nlp_spacy', None):
            analyzer = FundingAnalyzer(record_for_nlp_test)
            results = analyzer.extract_funding_data()
        self.assertEqual(len(results), 0)

    @patch('sciencemapping.analysis.funding_analyzer.nlp_spacy')
    @patch('sciencemapping.analysis.funding_analyzer.SPACY_AVAILABLE', True)
    def test_get_funding_summary_stats_with_nlp_and_normalization(self, mock_nlp_model):
        """Test summary stats with combined structured (funding_entries) and NLP data."""
        mock_doc_rec2 = MagicMock()
        mock_doc_rec2.ents = [
            MagicMock(text="Medical Research Council", label_="ORG"),
            MagicMock(text="The Example Org", label_="ORG")
        ]

        def nlp_side_effect(text):
            if "Medical Research Council grant MR/X001/1" in text:
                return mock_doc_rec2
            return MagicMock(ents=[])
        mock_nlp_model.side_effect = nlp_side_effect

        analyzer = FundingAnalyzer(SAMPLE_RECORDS_WITH_FUNDING_ENTRIES)
        stats = analyzer.get_funding_summary_stats()

        self.assertEqual(stats["records_with_any_funding_info"], 3)
        self.assertEqual(stats["unique_funders_identified_normalized"], 6)

        top_funders = dict(stats["top_funders_normalized"])
        self.assertEqual(top_funders.get("National Science Foundation"), 1)
        self.assertEqual(top_funders.get("National Institutes of Health"), 1)
        self.assertEqual(top_funders.get("Wellcome Trust"), 1)
        self.assertEqual(top_funders.get("European Research Council"), 1)
        self.assertEqual(top_funders.get("Medical Research Council"), 1)
        self.assertEqual(top_funders.get("Example Org"), 1) # Corrected: Expect normalized name

    def test_empty_records_funding(self):
        analyzer = FundingAnalyzer([])
        extracted = analyzer.extract_funding_data()
        self.assertEqual(len(extracted), 0)
        stats = analyzer.get_funding_summary_stats()
        self.assertEqual(stats["total_records_analyzed"], 0)
        self.assertEqual(stats["records_with_any_funding_info"], 0)
        self.assertEqual(stats["unique_funders_identified_normalized"], 0)
        self.assertEqual(len(stats["top_funders_normalized"]), 0)

if __name__ == '__main__':
    unittest.main()
