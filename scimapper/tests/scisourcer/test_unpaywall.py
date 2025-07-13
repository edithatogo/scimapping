import unittest
from unittest.mock import patch, MagicMock
from scimapper.scisourcer.unpaywall import search_unpaywall

class TestUnpaywallDataSource(unittest.TestCase):

    @patch('requests.get')
    def test_search_unpaywall_success(self, mock_get):
        """
        Test that a successful Unpaywall API search returns the correct data.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"doi": "10.1234/test.doi", "is_oa": True}
        mock_get.return_value = mock_response

        result = search_unpaywall("10.1234/test.doi")

        self.assertEqual(result, {"doi": "10.1234/test.doi", "is_oa": True})

    @patch('requests.get')
    def test_search_unpaywall_not_found(self, mock_get):
        """
        Test that a failed Unpaywall API search returns None.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = search_unpaywall("10.1234/not.found")

        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
