from typing import List, Dict, Any, Optional
import requests

def search_unpaywall(doi: str) -> Optional[Dict[str, Any]]:
    """
    Search Unpaywall for the full text of an article.

    :param doi: The DOI of the article.
    :return: A dictionary containing the Unpaywall data for the article, or None if the article is not found.
    """
    url = f"https://api.unpaywall.org/v2/{doi}?email=sciencemappinglib_user@example.com"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
