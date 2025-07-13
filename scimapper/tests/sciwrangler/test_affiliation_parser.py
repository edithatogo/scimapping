import unittest
from scimapper.sciwrangler.affiliation_parser import extract_affiliations

class TestAffiliationParser(unittest.TestCase):

    def test_extract_affiliations(self):
        """
        Test that `extract_affiliations` successfully extracts affiliation data from a list of records.
        """
        records = [
            {
                "authors": [
                    {"name": "Doe, J.", "affiliation": "University of Science"},
                    {"name": "Smith, A.", "affiliation": "Institute of Technology"}
                ]
            },
            {
                "authors": [
                    {"name": "Lee, C."}
                ]
            }
        ]
        expected_records = [
            {
                "authors": [
                    {"name": "Doe, J.", "affiliation": "University of Science"},
                    {"name": "Smith, A.", "affiliation": "Institute of Technology"}
                ],
                "affiliations": ["University of Science", "Institute of Technology"]
            },
            {
                "authors": [
                    {"name": "Lee, C."}
                ]
            }
        ]
        self.assertEqual(extract_affiliations(records), expected_records)

if __name__ == '__main__':
    unittest.main()
