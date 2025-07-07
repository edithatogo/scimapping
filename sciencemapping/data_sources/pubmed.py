from typing import List, Dict, Optional, Any
from pymed import PubMed

# Initialize PubMed API client
# It's good practice to include an email for NCBI to contact if there are issues
# However, making it optional for users who might not want to provide one immediately.
DEFAULT_TOOL_EMAIL = "sciencemappinglib@example.com" # A generic placeholder

def search_pubmed(
    query: str,
    max_results: int = 100,
    tool: str = "ScienceMappingLibrary",
    email: Optional[str] = DEFAULT_TOOL_EMAIL,
) -> List[Dict[str, Any]]:
    """
    Searches PubMed for articles matching the query.

    Args:
        query: The search query string (e.g., "cancer research").
        max_results: The maximum number of articles to retrieve.
        tool: The name of the tool making the request (as per NCBI guidelines).
        email: The email address of the user/tool maintainer (as per NCBI guidelines).

    Returns:
        A list of dictionaries, where each dictionary represents an article
        and is parsed into a common internal format.
    """
    if not email:
        print("Warning: NCBI recommends providing an email for PubMed API access.")
        # Using a default placeholder if no email is provided, though user should be encouraged to set one.
        pubmed = PubMed(tool=tool, email=DEFAULT_TOOL_EMAIL)
    else:
        pubmed = PubMed(tool=tool, email=email)

    try:
        results = pubmed.query(query, max_results=max_results)
        articles_data: List[Dict[str, Any]] = []

        for article in results:
            # `article` is a pymed.article.PubMedArticle object
            # We need to convert its attributes to a dictionary
            article_dict = article.toDict()
            parsed_article = _parse_pubmed_article(article_dict)
            articles_data.append(parsed_article)

        return articles_data

    except Exception as e:
        print(f"Error during PubMed search: {e}")
        # Depending on desired error handling, could raise exception or return empty list
        return []

def _parse_pubmed_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses a single article dictionary from pymed's format to our common internal format.

    Args:
        article_data: A dictionary representing an article from pymed.

    Returns:
        A dictionary representing the article in the common internal format.
        Keys include: 'title', 'authors', 'journal', 'year', 'doi', 'pubmed_id',
                      'abstract', 'keywords', 'source_type'.
    """
    # Extracting authors: format as "LastName, FirstNameInitial"
    authors_list = []
    if article_data.get("authors"):
        for author_info in article_data["authors"]:
            name_parts = []
            if author_info.get("lastname"):
                name_parts.append(author_info["lastname"])
            if author_info.get("firstname"): # Pymed provides full first name
                name_parts.append(author_info["firstname"]) # Or take initials if preferred
            authors_list.append(" ".join(name_parts))

    # Publication year (prefer 'year' from 'publication_date' if available)
    year = None
    if article_data.get("publication_date"):
        # pymed's publication_date is a datetime.date object
        # We just need the year
        year_str = str(article_data["publication_date"].year)
        if year_str.isdigit():
            year = int(year_str)


    # Keywords - Pymed often provides a list of keywords
    keywords = article_data.get("keywords", [])
    if keywords is None: # Sometimes it can be None instead of an empty list
        keywords = []


    return {
        "title": article_data.get("title"),
        "authors": authors_list, # List of strings
        "journal": article_data.get("journal"),
        "year": year,
        "doi": article_data.get("doi"),
        "pubmed_id": article_data.get("pubmed_id").split("\n")[0], # Clean up potential extra lines
        "abstract": article_data.get("abstract"),
        "keywords": keywords, # List of strings
        "source_type": "pubmed", # To identify the origin of the data
        "raw_data": article_data # Optional: include the raw data for more detailed analysis later
    }

if __name__ == "__main__":
    # Example usage:
    print("Searching PubMed for 'crispr cas9'...")
    # Providing a real email is good practice for NCBI
    # For this example, we'll use the default or let the user know.
    example_email = "your_email@example.com" # Replace with a real email if running extensively

    # Check if the user has a specific email to use, otherwise use the placeholder
    # In a real application, this might come from a config file or user input
    actual_email_to_use = DEFAULT_TOOL_EMAIL
    # actual_email_to_use = example_email # Uncomment and set if you have one

    articles = search_pubmed("crispr cas9", max_results=5, email=actual_email_to_use)

    if articles:
        print(f"\nFound {len(articles)} articles:")
        for i, article in enumerate(articles):
            print(f"\n--- Article {i+1} ---")
            print(f"  Title: {article.get('title')}")
            print(f"  Authors: {', '.join(article.get('authors', []))}")
            print(f"  Journal: {article.get('journal')}")
            print(f"  Year: {article.get('year')}")
            print(f"  DOI: {article.get('doi')}")
            print(f"  PubMed ID: {article.get('pubmed_id')}")
            print(f"  Abstract: {article.get('abstract', '')[:100]}...") # First 100 chars
            print(f"  Keywords: {article.get('keywords')}")
    else:
        print("No articles found or an error occurred.")

    print("\nSearching PubMed for 'bibliometrics' with max_results=2...")
    articles_biblio = search_pubmed("bibliometrics", max_results=2, email=actual_email_to_use)
    if articles_biblio:
        print(f"\nFound {len(articles_biblio)} articles:")
        for i, article in enumerate(articles_biblio):
            print(f"\n--- Article {i+1} ---")
            print(f"  Title: {article.get('title')}")
            print(f"  PubMed ID: {article.get('pubmed_id')}")
    else:
        print("No articles found for 'bibliometrics' or an error occurred.")
