import unittest
from unittest.mock import patch, mock_open
from scimapper.scisourcer.bibtex import parse_bibtex_file

class TestBibtexDataSource(unittest.TestCase):

    def test_parse_bibtex_file(self):
        """
        Test that `parse_bibtex_file` successfully parses a BibTeX file.
        """
        mock_file_content = """
@article{test,
    author = {Doe, J.},
    title = {Test Title},
    journal = {Journal of Testing},
    year = {2023}
}
"""
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            records = parse_bibtex_file("dummy_path.bib")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Test Title")

if __name__ == '__main__':
    unittest.main()
