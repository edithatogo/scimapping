import unittest
from scimapper.sciwrangler.author_parser import parse_author_names

class TestAuthorParser(unittest.TestCase):

    def test_parse_author_names(self):
        """
        Test that `parse_author_names` successfully parses author names.
        """
        records = [
            {
                "authors": [
                    "Doe, J.",
                    "Smith, A."
                ]
            },
            {
                "authors": [
                    "Lee, C."
                ]
            }
        ]
        expected_records = [
            {
                "authors": [
                    {"lastname": "Doe", "firstname": "J."},
                    {"lastname": "Smith", "firstname": "A."}
                ]
            },
            {
                "authors": [
                    {"lastname": "Lee", "firstname": "C."}
                ]
            }
        ]
        self.assertEqual(parse_author_names(records), expected_records)

if __name__ == '__main__':
    unittest.main()
