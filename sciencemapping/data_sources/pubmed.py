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


    # Keywords - Pymed often provides a list of keywords. Apply normalization.
    keywords_raw = article_data.get("keywords")
    processed_keywords = []
    if keywords_raw and isinstance(keywords_raw, list):
        # Apply normalization: strip, lowercase, filter out empty strings after stripping
        stripped_lowered_keywords = [str(kw).strip().lower() for kw in keywords_raw if kw and isinstance(kw, str) and str(kw).strip()]
        # Get unique keywords and sort for consistency
        if stripped_lowered_keywords:
            processed_keywords = sorted(list(set(stripped_lowered_keywords)))

    # Funding Information from PubMed 'grants' (GR field in XML)
    # pymed puts this into article.grant_list, where each item is a string.
    # Example grant string: "R01 CA123456/CA/NCI NIH HHS/United States"
    # Or "Wellcome Trust 098765/Z/12/Z"
    # Or "K99 AG000000//NIH HHS/United States" (empty part)
    funding_entries: List[Dict[str, Any]] = []
    raw_grants = article_data.get("grants")
    if isinstance(raw_grants, list):
        for grant_str_raw in raw_grants:
            grant_str = str(grant_str_raw).strip() # Ensure it's a string and stripped
            if not grant_str:
                continue

            entry: Dict[str, Any] = {
                "raw_funding_text": grant_str,
                "source_of_info": "pubmed_GR_tag"
            }
            parts = [p.strip() for p in grant_str.split('/') if p.strip()] # Split and remove empty parts

            # Grant ID is typically the first part.
            if parts and parts[0]:
                entry["grant_ids"] = [parts[0]]

            # Agency can be complex. Often parts 2 and 3 combined or just one of them.
            # Full agency name (e.g., "NCI NIH HHS") is often preferred over acronym ("CA").
            funder_names_parts = []
            if len(parts) > 2 and parts[2]: # Prefer the 3rd part if it exists (often fuller agency name)
                funder_names_parts.append(parts[2])
            if len(parts) > 1 and parts[1]: # Add 2nd part (often acronym or sub-agency)
                funder_names_parts.append(parts[1])

            if funder_names_parts:
                funder_name_str = " ".join(funder_names_parts) # Join parts, e.g. "NCI NIH HHS CA"
                if funder_name_str:
                     entry["funder_name"] = funder_name_str

            # Only add the entry if we successfully parsed a funder name or grant ID.
            # The raw_funding_text is already part of 'entry'.
            if entry.get("funder_name") or entry.get("grant_ids"):
                funding_entries.append(entry)
            # If neither funder_name nor grant_ids could be parsed from a non-empty grant_str,
            # we might still want to log it or add it with just raw_funding_text.
            # For now, if grant_str is present, parts[0] will be grant_ids, so this condition is met.
            # The 'else' block that created a "pubmed_GR_tag_unparsed" entry is removed as likely redundant
            # because if grant_str is non-empty, parts[0] will exist and be added to grant_ids.

    parsed_record = {
        "title": article_data.get("title"),
        "authors": authors_list,
        "journal": article_data.get("journal"),
        "year": year,
        "doi": article_data.get("doi"),
        "pubmed_id": article_data.get("pubmed_id").split("\n")[0],
        "abstract": article_data.get("abstract"),
        "keywords": processed_keywords,
        "funding_entries": funding_entries if funding_entries else None,
        "cited_references": None, # Initialize
        "source_type": "pubmed",
        "raw_data": article_data
    }

    # Cited References (list of PMIDs from pymed if available)
    # pymed's article.references contains a list of PMIDs of cited articles.
    # article_data['references'] would be this list.
    if article_data.get("references_loaded") and isinstance(article_data.get("references"), list):
        cited_refs_pmids = [str(pmid) for pmid in article_data["references"] if pmid]
        if cited_refs_pmids:
            parsed_record["cited_references"] = cited_refs_pmids

    return parsed_record

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
