import unittest
from unittest.mock import patch, mock_open
from scimapper.scisourcer.ris import parse_ris_file

class TestRisDataSource(unittest.TestCase):

    def test_parse_ris_file(self):
        """
        Test that `parse_ris_file` successfully parses a RIS file.
        """
        mock_file_content = """
TY  - JOUR
AU  - Doe, J.
TI  - Test Title
JO  - Journal of Testing
PY  - 2023
ER  -
"""
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            records = parse_ris_file("dummy_path.ris")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Test Title")

if __name__ == '__main__':
    unittest.main()
