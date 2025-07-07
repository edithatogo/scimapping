from typing import List, Dict, Optional, Any
from pybliometrics.scopus import ScopusSearch, AbstractRetrieval
from pybliometrics.scopus import CONFIG as config
from pybliometrics.scopus.exceptions import ScopusError # Use this for catching Scopus-specific errors
import time

# It's crucial for pybliometrics that an API key is configured.
# This usually happens in a config.ini file or via environment variables.
# We should check if the configuration is usable.

def _is_scopus_configured() -> bool:
    """Checks if the Scopus API key is likely configured in pybliometrics."""
    if "Authentication" in config and "APIKey" in config["Authentication"] and config["Authentication"]["APIKey"]:
        return True
    return False

def search_scopus(
    query: str,
    max_results: int = 25,
    api_key: Optional[str] = None,
    view: str = "STANDARD"
) -> List[Dict[str, Any]]:
    """
    Searches Scopus for articles matching the query using ScopusSearch.
    """
    original_key = None
    api_key_manually_set = False

    if api_key:
        original_key = config.get("Authentication", {}).get("APIKey")
        if "Authentication" not in config:
            config["Authentication"] = {}
        config["Authentication"]["APIKey"] = api_key
        api_key_manually_set = True
    elif not _is_scopus_configured():
        print("Warning: Scopus API key not found or configured. Search will likely fail or use limited access.")

    results_list: List[Dict[str, Any]] = []
    try:
        search_instance = ScopusSearch(query, count=min(max_results, 200), view=view, subscriber=False)

        retrieved_count = 0
        if search_instance.results:
            for res_item in search_instance.results:
                if retrieved_count >= max_results:
                    break
                parsed_article = _parse_scopus_search_result(res_item)
                results_list.append(parsed_article)
                retrieved_count += 1

    except FileNotFoundError:
        print("Scopus configuration file not found. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")
        return []
    except ScopusError as e:
        status_code = getattr(e, 'http_status', None) or getattr(e, '_code', None)
        error_text = str(e)
        error_message_prefix = f"Scopus error ({e.__class__.__name__})" if hasattr(e, '__class__') and hasattr(e.__class__, '__name__') else "A Scopus error occurred"

        if status_code:
            print(f"{error_message_prefix}, HTTP {status_code}: {error_text}")
            if status_code == 400:
                 print(f"Detail: This might be a Scopus query syntax error or invalid parameters.")
            elif status_code == 401:
                 print(f"Detail: Scopus API authentication error. Check your API key and its permissions.")
            elif status_code == 404:
                 print(f"Detail: Scopus API resource not found for query '{query}'.")
            elif status_code == 429:
                 print(f"Detail: Scopus API rate limit exceeded. Please wait before trying again.")
        else:
            print(f"{error_message_prefix}: {error_text}")

    except Exception as e:
        print(f"An unexpected error occurred during Scopus search: {type(e).__name__} - {e}")
    finally:
        if api_key_manually_set:
            if original_key:
                config["Authentication"]["APIKey"] = original_key
            elif "APIKey" in config.get("Authentication", {}):
                del config["Authentication"]["APIKey"]
                if not config["Authentication"]:
                    del config["Authentication"]
    return results_list


def fetch_scopus_abstract_details(eid: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetches detailed information for a single Scopus document.
    """
    original_key = None
    api_key_manually_set = False
    if api_key:
        original_key = config.get("Authentication", {}).get("APIKey")
        if "Authentication" not in config:
            config["Authentication"] = {}
        config["Authentication"]["APIKey"] = api_key
        api_key_manually_set = True
    elif not _is_scopus_configured():
        print(f"Warning: Scopus API key not configured. Fetching details for EID {eid} may fail.")

    try:
        ab_ret = AbstractRetrieval(identifier=eid, id_type='eid', view="FULL", refresh=False)

        details = {
            "abstract": getattr(ab_ret, 'abstract', None),
            "author_keywords": getattr(ab_ret, 'authkeywords', None),
            "index_keywords": getattr(ab_ret, 'idxterms', None),
            "references_count": getattr(ab_ret, 'refcount', None),
            "references": [ref.id for ref in getattr(ab_ret, 'references', []) if ref and hasattr(ref, 'id') and ref.id],
            "funding_details": {
                "agency": getattr(ab_ret, 'funding_agency', None),
                "text": getattr(ab_ret, 'funding_text', None)
            } if getattr(ab_ret, 'funding_agency', None) or getattr(ab_ret, 'funding_text', None) else None,
            "raw_abstract_retrieval_dict": ab_ret.to_dict() if hasattr(ab_ret, 'to_dict') else None
        }
        return details
    except FileNotFoundError:
        print("Scopus configuration file not found. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")
        return None
    except ScopusError as e:
        status_code = getattr(e, 'http_status', None) or getattr(e, '_code', None)
        error_text = str(e)
        error_message_prefix = f"Scopus error ({e.__class__.__name__}) while fetching details" if hasattr(e, '__class__') and hasattr(e.__class__, '__name__') else "A Scopus error occurred while fetching details"

        if status_code:
            print(f"{error_message_prefix} for EID {eid}, HTTP {status_code}: {error_text}")
            if status_code == 401:
                print(f"Detail: Scopus API authentication error. Check your API key.")
            elif status_code == 404:
                print(f"Detail: Scopus document with EID {eid} not found or access denied.")
        else:
            print(f"{error_message_prefix} for EID {eid}: {error_text}")

    except Exception as e:
        print(f"An unexpected error occurred fetching details for Scopus EID {eid}: {type(e).__name__} - {e}")
    finally:
        if api_key_manually_set:
            if original_key:
                config["Authentication"]["APIKey"] = original_key
            elif "APIKey" in config.get("Authentication", {}):
                del config["Authentication"]["APIKey"]
                if not config["Authentication"]:
                    del config["Authentication"]
    return None


def _parse_scopus_search_result(item: Any) -> Dict[str, Any]:
    """
    Parses a single item from ScopusSearch results (a namedtuple) into our common internal format.
    """
    authors_list = []
    # ScopusSearch results (item) often have 'authors' as a list of AuthorEntry namedtuples
    # or 'author_names' as a semicolon-separated string.
    if getattr(item, 'authors', None) and isinstance(item.authors, list):
        # Assuming authors is a list of objects with an 'indexed_name' attribute
        # or 'surname' and 'given_name'
        for author in item.authors:
            if hasattr(author, 'indexed_name') and author.indexed_name:
                authors_list.append(author.indexed_name)
            elif hasattr(author, 'surname') and author.surname:
                name = author.surname
                if hasattr(author, 'given_name') and author.given_name:
                    name += f", {author.given_name}"
                authors_list.append(name)
    elif getattr(item, 'author_names', None) and isinstance(item.author_names, str):
        authors_list = [name.strip() for name in item.author_names.split(';') if name.strip()]

    year = None
    if getattr(item, 'coverDate', None) and isinstance(item.coverDate, str):
        try:
            year = int(item.coverDate[:4]) # Format is YYYY-MM-DD
        except (ValueError, TypeError):
            year = None # Or log a warning

    keywords = []
    if getattr(item, 'authkeywords', None) and isinstance(item.authkeywords, str):
        keywords = [k.strip() for k in item.authkeywords.split('|') if k.strip()]

    document_type = getattr(item, 'aggregationType', None)
    if not document_type and hasattr(item, 'subtypeDescription'):
        document_type = item.subtypeDescription

    # Ensure raw_search_result is serializable if item is a complex object
    raw_data = None
    if hasattr(item, '_asdict'): # For namedtuples
        raw_data = item._asdict()
    elif isinstance(item, dict):
        raw_data = item
    # else: could try vars(item) but might be too much

    return {
        "title": getattr(item, 'title', None),
        "authors": authors_list,
        "journal": getattr(item, 'publicationName', None),
        "year": year,
        "doi": getattr(item, 'doi', None),
        "scopus_id": getattr(item, 'eid', None),
        "pubmed_id": getattr(item, 'pubmed_id', None), # Often None from Scopus unless specifically linked
        "abstract": getattr(item, 'description', None), # This is usually a short abstract or description
        "keywords": keywords,
        "document_type": document_type,
        "source_type": "scopus",
        "raw_search_result": raw_data
    }


if __name__ == "__main__":
    # This part requires a Scopus API key to be configured in pybliometrics' config.ini
    # or by setting the PYB_API_KEY environment variable.
    # Example: export PYB_API_KEY='your_actual_api_key'

    print("Attempting to search Scopus using sciencemapping.data_sources.scopus...")

    # Check configuration explicitly here for the example run
    if not _is_scopus_configured():
        print("--------------------------------------------------------------------")
        print("WARNING: Scopus API key not found by _is_scopus_configured().")
        print("The following search might fail or return limited results if pybliometrics")
        print("cannot find an API key through its other mechanisms (e.g., env vars).")
        print("Please ensure your Scopus API key is correctly configured for pybliometrics.")
        print("See: https://pybliometrics.readthedocs.io/en/stable/configuration.html")
        print("--------------------------------------------------------------------")
    else:
        print("Scopus configuration seems present via _is_scopus_configured(). Proceeding with search.")

    # A common query for testing
    # query_string = 'TITLE-ABS-KEY("bibliometric analysis" OR "science mapping") AND SUBJAREA(COMP) AND DOCTYPE(ar OR re)'
    query_string = 'TITLE-ABS-KEY(bibliometrics) AND PUBYEAR > 2022 AND DOCTYPE(ar)' # More specific, less results

    articles_found = search_scopus(query_string, max_results=3)

    if articles_found:
        print(f"\nFound {len(articles_found)} articles from Scopus for query: '{query_string}'")
        for idx, artcl in enumerate(articles_found):
            print(f"\n--- Article {idx+1} (from Scopus Search) ---")
            print(f"  Title: {artcl.get('title')}")
            print(f"  Authors: {'; '.join(artcl.get('authors', []))}")
            print(f"  Journal: {artcl.get('journal')}")
            print(f"  Year: {artcl.get('year')}")
            print(f"  DOI: {artcl.get('doi')}")
            print(f"  Scopus EID: {artcl.get('scopus_id')}")
            print(f"  Abstract (short): {str(artcl.get('abstract', 'N/A'))[:150]}...")
            print(f"  Keywords (from search): {artcl.get('keywords')}")

            # Optionally, fetch more details if EID is present
            scopus_eid = artcl.get('scopus_id')
            if scopus_eid:
                print(f"  Fetching full details for EID: {scopus_eid}...")
                # Add a small delay to be respectful to the API, especially in loops
                time.sleep(0.5) # 0.5 to 1 second is usually safe for occasional calls

                full_details = fetch_scopus_abstract_details(eid=scopus_eid)
                if full_details:
                    print(f"    Full Abstract: {str(full_details.get('abstract', 'N/A'))[:150]}...")
                    print(f"    Author Keywords (full): {full_details.get('author_keywords')}")
                    print(f"    Index Keywords: {full_details.get('index_keywords')}")
                    if full_details.get('funding_details'):
                         print(f"    Funding: Agency - {full_details['funding_details'].get('agency')}, Text - {full_details['funding_details'].get('text')}")
                    # You can add the full_details to the article dictionary if needed
                    # artcl['full_abstract_details'] = full_details
                else:
                    print(f"    Could not fetch full details for EID: {scopus_eid}.")
            else:
                print("    No Scopus EID found in search result, cannot fetch full details.")
    else:
        print(f"No articles found from Scopus for the query: '{query_string}', or an error occurred.")
        print("Please check your Scopus API key configuration and the query syntax.")

    print("\nScopus example finished.")
