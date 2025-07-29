import unittest
from unittest.mock import patch, MagicMock
from sciencemapping.data_sources.pubmed import search_pubmed, _parse_pubmed_article, DEFAULT_TOOL_EMAIL

class TestPubMedDataSource(unittest.TestCase):

    def test_parse_pubmed_article(self):
        """Test parsing of a single PubMed article dictionary."""
        raw_article_data = {
            "title": "Test Title",
            "authors": [
                {"lastname": "Doe", "firstname": "John A.", "initials": "JA"},
                {"lastname": "Smith", "firstname": "Jane B.", "initials": "JB"}
            ],
            "journal": "Journal of Testing",
            "publication_date": MagicMock(year=2023), # Mocking datetime.date object
            "doi": "10.1234/test.doi",
            "pubmed_id": "12345678\n[Indexed for MEDLINE]",
            "abstract": "This is a test abstract.",
            "keywords": ["Test", "  pubmed ", "python", "Test", None, "", "Another Keyword"], # Mixed case, spaces, duplicates, None, empty
            "grants": [
                "R01 CA123456/CA/NCI NIH HHS/United States",       # 0: Standard NIH
                "Wellcome Trust 098765/Z/12/Z",                  # 1: Wellcome Trust example
                "K99 AG000000//NIH HHS/United States",            # 2: Empty middle part
                "RPB G-12345",                                   # 3: Grant ID only (no slashes)
                "Medical Research Council/MC_U12345/UK",         # 4: Funder name first, then grant ID
                "Grant X / Funder Y/Sub Funder Z / Country",     # 5: Slashes in funder name (hypothetical messy)
                "ShortGrantOnly",                                # 6: Very short, one part only
                "  LeadingSpaceGrant / Funder / Country  ",      # 7: Grant with leading/trailing spaces
                "GrantWith/InternalSlashInID/Funder/Country"     # 8: Grant ID has internal slash
            ],
            "references_loaded": True,
            "references": ["PMID1", "PMID2", None, "PMID3"] # Example cited PMIDs
        }
        parsed_article = _parse_pubmed_article(raw_article_data)

        self.assertEqual(parsed_article["title"], "Test Title")
        self.assertListEqual(parsed_article["authors"], ["Doe John A.", "Smith Jane B."])
        self.assertEqual(parsed_article["journal"], "Journal of Testing")
        self.assertEqual(parsed_article["year"], 2023)
        self.assertEqual(parsed_article["doi"], "10.1234/test.doi")
        self.assertEqual(parsed_article["pubmed_id"], "12345678") # Check cleaning
        self.assertEqual(parsed_article["abstract"], "This is a test abstract.")
        # Check keyword normalization (sorted, unique, lowercase, stripped)
        self.assertListEqual(parsed_article["keywords"], ["another keyword", "pubmed", "python", "test"])
        self.assertEqual(parsed_article["source_type"], "pubmed")
        self.assertIn("raw_data", parsed_article)
        self.assertEqual(parsed_article["raw_data"], raw_article_data)

        # Assert funding_entries
        self.assertIn("funding_entries", parsed_article)
        self.assertIsNotNone(parsed_article["funding_entries"])
        funding_entries = parsed_article["funding_entries"]
        self.assertEqual(len(funding_entries), 9) # Now 9 entries

        # Entry 0: R01 CA123456/CA/NCI NIH HHS/United States
        self.assertEqual(funding_entries[0]["funder_name"], "NCI NIH HHS CA")
        self.assertListEqual(funding_entries[0]["grant_ids"], ["R01 CA123456"])
        self.assertEqual(funding_entries[0]["source_of_info"], "pubmed_GR_tag")
        self.assertEqual(funding_entries[0]["raw_funding_text"], "R01 CA123456/CA/NCI NIH HHS/United States")

        # Entry 1: Wellcome Trust 098765/Z/12/Z
        self.assertEqual(funding_entries[1]["funder_name"], "12 Z")
        self.assertListEqual(funding_entries[1]["grant_ids"], ["Wellcome Trust 098765"])
        self.assertEqual(funding_entries[1]["raw_funding_text"], "Wellcome Trust 098765/Z/12/Z")

        # Entry 2: K99 AG000000//NIH HHS/United States
        self.assertEqual(funding_entries[2]["funder_name"], "United States NIH HHS")
        self.assertListEqual(funding_entries[2]["grant_ids"], ["K99 AG000000"])
        self.assertEqual(funding_entries[2]["raw_funding_text"], "K99 AG000000//NIH HHS/United States")

        # Entry 3: RPB G-12345 (Grant ID only, no slashes)
        self.assertListEqual(funding_entries[3]["grant_ids"], ["RPB G-12345"])
        self.assertNotIn("funder_name", funding_entries[3]) # No funder name parts
        self.assertEqual(funding_entries[3]["raw_funding_text"], "RPB G-12345")

        # Entry 4: Medical Research Council/MC_U12345/UK
        self.assertListEqual(funding_entries[4]["grant_ids"], ["Medical Research Council"])
        self.assertEqual(funding_entries[4]["funder_name"], "UK MC_U12345")
        self.assertEqual(funding_entries[4]["raw_funding_text"], "Medical Research Council/MC_U12345/UK")

        # Entry 5: Grant X / Funder Y/Sub Funder Z / Country
        self.assertListEqual(funding_entries[5]["grant_ids"], ["Grant X"])
        self.assertEqual(funding_entries[5]["funder_name"], "Sub Funder Z Funder Y")
        self.assertEqual(funding_entries[5]["raw_funding_text"], "Grant X / Funder Y/Sub Funder Z / Country")

        # Entry 6: ShortGrantOnly
        self.assertListEqual(funding_entries[6]["grant_ids"], ["ShortGrantOnly"])
        self.assertNotIn("funder_name", funding_entries[6])
        self.assertEqual(funding_entries[6]["raw_funding_text"], "ShortGrantOnly")

        # Entry 7: "  LeadingSpaceGrant / Funder / Country  " (stripping of grant_str is tested)
        self.assertListEqual(funding_entries[7]["grant_ids"], ["LeadingSpaceGrant"])
        self.assertEqual(funding_entries[7]["funder_name"], "Country Funder")
        self.assertEqual(funding_entries[7]["raw_funding_text"], "LeadingSpaceGrant / Funder / Country")

        # Entry 8: "GrantWith/InternalSlashInID/Funder/Country"
        # Current logic takes "GrantWith" as ID because parts[0] is based on first slash.
        self.assertListEqual(funding_entries[8]["grant_ids"], ["GrantWith"])
        self.assertEqual(funding_entries[8]["funder_name"], "Funder InternalSlashInID") # Corrected expectation
        self.assertEqual(funding_entries[8]["raw_funding_text"], "GrantWith/InternalSlashInID/Funder/Country")

        # Assert cited_references
        self.assertIn("cited_references", parsed_article)
        self.assertIsNotNone(parsed_article["cited_references"])
        self.assertListEqual(parsed_article["cited_references"], ["PMID1", "PMID2", "PMID3"]) # None should be filtered out

    def test_parse_pubmed_article_minimal_data(self):
        """Test parsing with minimal or missing data fields."""
        raw_article_data = {
            "title": "Minimal Title",
            "pubmed_id": "9876543"
            # Other fields are missing
        }
        parsed_article = _parse_pubmed_article(raw_article_data)

        self.assertEqual(parsed_article["title"], "Minimal Title")
        self.assertEqual(parsed_article["pubmed_id"], "9876543")
        self.assertListEqual(parsed_article["authors"], [])
        self.assertIsNone(parsed_article["journal"])
        self.assertIsNone(parsed_article["year"])
        self.assertIsNone(parsed_article["doi"])
        self.assertIsNone(parsed_article["abstract"])
        self.assertListEqual(parsed_article["keywords"], [])
        self.assertEqual(parsed_article["source_type"], "pubmed")
        self.assertIsNone(parsed_article["funding_entries"])
        self.assertIsNone(parsed_article["cited_references"]) # Check for cited_references

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_success(self, MockPubMed):
        """Test successful PubMed search and data parsing integration."""
        # Mock PubMedArticle and its toDict method
        mock_article_1_dict = {
            "title": "Article 1", "pubmed_id": "111", "doi": "doi1",
            "authors": [{"lastname": "AuthA", "firstname": "FirstA"}],
            "journal": "Journal A", "publication_date": MagicMock(year=2020),
            "abstract": "Abstract 1", "keywords": ["key1"]
        }
        mock_article_2_dict = {
            "title": "Article 2", "pubmed_id": "222", "doi": "doi2",
            "authors": [{"lastname": "AuthB", "firstname": "FirstB"}],
            "journal": "Journal B", "publication_date": MagicMock(year=2021),
            "abstract": "Abstract 2", "keywords": ["key2"]
        }

        mock_article_1 = MagicMock()
        mock_article_1.toDict.return_value = mock_article_1_dict

        mock_article_2 = MagicMock()
        mock_article_2.toDict.return_value = mock_article_2_dict

        # Configure the mock PubMed instance
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.return_value = [mock_article_1, mock_article_2]

        results = search_pubmed("test query", max_results=2, email="test@example.com")

        MockPubMed.assert_called_once_with(tool="ScienceMappingLibrary", email="test@example.com")
        mock_pubmed_instance.query.assert_called_once_with("test query", max_results=2)

        self.assertEqual(len(results), 2)

        # Check first article
        self.assertEqual(results[0]["title"], "Article 1")
        self.assertEqual(results[0]["pubmed_id"], "111")
        self.assertEqual(results[0]["year"], 2020)
        self.assertListEqual(results[0]["authors"], ["AuthA FirstA"])

        # Check second article
        self.assertEqual(results[1]["title"], "Article 2")
        self.assertEqual(results[1]["pubmed_id"], "222")
        self.assertEqual(results[1]["year"], 2021)
        self.assertListEqual(results[1]["authors"], ["AuthB FirstB"])

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_no_email_uses_default(self, MockPubMed):
        """Test that DEFAULT_TOOL_EMAIL is used if no email is provided."""
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.return_value = [] # No articles needed for this test

        with patch('builtins.print') as mock_print: # Suppress warning print
            search_pubmed("test query", email=None)
            MockPubMed.assert_called_once_with(tool="ScienceMappingLibrary", email=DEFAULT_TOOL_EMAIL)
            mock_print.assert_any_call("Warning: NCBI recommends providing an email for PubMed API access.")

    @patch('sciencemapping.data_sources.pubmed.PubMed')
    def test_search_pubmed_api_error(self, MockPubMed):
        """Test PubMed search when the API call raises an exception."""
        mock_pubmed_instance = MockPubMed.return_value
        mock_pubmed_instance.query.side_effect = Exception("API Connection Error")

        with patch('builtins.print') as mock_print:
            results = search_pubmed("test query", email="test@example.com")
            self.assertEqual(results, [])
            mock_print.assert_any_call("Error during PubMed search: API Connection Error")

    def test_parse_pubmed_article_missing_keywords_and_date(self):
        """Test parsing when keywords or publication_date are None or missing."""
        raw_article_data_no_keywords = {
            "title": "No Keywords Title", "pubmed_id": "333", "keywords": None
        }
        parsed = _parse_pubmed_article(raw_article_data_no_keywords)
        self.assertListEqual(parsed["keywords"], [])

        raw_article_data_no_date = {
            "title": "No Date Title", "pubmed_id": "444"
            # "publication_date" is missing
        }
        parsed_no_date = _parse_pubmed_article(raw_article_data_no_date)
        self.assertIsNone(parsed_no_date["year"])


if __name__ == '__main__':
    unittest.main()
