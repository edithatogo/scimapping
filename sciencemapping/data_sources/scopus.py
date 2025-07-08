from typing import List, Dict, Optional, Any
from pybliometrics.scopus import ScopusSearch, AbstractRetrieval
from pybliometrics.scopus import CONFIG as config
from pybliometrics.scopus import errors as scopus_errors # Corrected import for the errors module
import time

# It's crucial for pybliometrics that an API key is configured.
# This usually happens in a config.ini file or via environment variables.

def _is_scopus_configured() -> bool:
    """
    Check whether a Scopus API key is present in the pybliometrics configuration.
    
    Returns:
        bool: True if an API key is configured, otherwise False.
    """
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
    Performs a Scopus search for articles matching the specified query and returns a list of parsed article metadata dictionaries.
    
    The function uses the ScopusSearch interface from pybliometrics to execute the query, handling API key configuration as needed. It limits the number of returned results to `max_results` (up to 200 per request) and parses each result into a standardized dictionary format. Handles missing configuration, Scopus-specific errors, and restores any temporarily overridden API key configuration.
    
    Parameters:
        query (str): The Scopus search query string.
        max_results (int, optional): Maximum number of articles to return. Defaults to 25.
        api_key (str, optional): Scopus API key to use for this request. If not provided, uses the configured key.
        view (str, optional): Scopus API view parameter. Defaults to "STANDARD".
    
    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing parsed metadata for each found article. Returns an empty list if no results are found or an error occurs.
    """
    original_key = None
    api_key_manually_set = False

    if api_key:
        original_key = config.get("Authentication", {}).get("APIKey")
        if "Authentication" not in config: # Ensure 'Authentication' section exists
            config["Authentication"] = {}
        config["Authentication"]["APIKey"] = api_key
        api_key_manually_set = True
    elif not _is_scopus_configured():
        # This warning is for when our specific check of pybliometrics.scopus.CONFIG fails.
        # Pybliometrics might still find a key through other means (e.g., environment variables),
        # so we allow the call to proceed. The FileNotFoundError below handles if pybliometrics truly finds no config.
        print("Warning: Scopus API key not found in pybliometrics's global CONFIG object. Search may rely on other configurations (e.g., environment variables) or fail.")

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
        # This is raised by pybliometrics if it ultimately fails to find any config (config.ini, env vars etc.)
        print("Scopus configuration file or API key not found by pybliometrics. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")
        return []
    # The following line was causing IndentationError and was part of a previous incorrect attempt.
    # except scopus_errors.get('ScopusError', Exception) as e:
    except scopus_errors.ScopusError as e: # Catching base ScopusError from the errors module
        status_code = getattr(e, 'http_status', None) or getattr(e, '_code', None)
        error_text = str(e)
        specific_error_type = e.__class__.__name__ # Get the specific error class name (e.g., "Scopus404Error")

        print(f"A Scopus error ({specific_error_type}) occurred during search.")
        if status_code:
            print(f"  HTTP Status: {status_code}")
        print(f"  Message: {error_text}")

        # Provide more specific details based on the error type
        if isinstance(e, scopus_errors.Scopus400Error): # Specific check for 400
             print(f"  Detail: This (HTTP 400) often indicates a malformed search query or invalid parameters.")
        elif isinstance(e, scopus_errors.Scopus401Error): # Specific check for 401
             print(f"  Detail: Authentication failed. Check your Scopus API key and its permissions.")
        elif isinstance(e, scopus_errors.Scopus404Error): # Specific check for 404
             print(f"  Detail: The requested resource (e.g., for query '{query}') was not found.")
        elif isinstance(e, scopus_errors.Scopus429Error): # Specific check for 429
             print(f"  Detail: API rate limit has been exceeded. Please wait before making new requests.")
        # Can add more isinstance checks here for other specific Scopus errors like Scopus500Error if needed.

    except Exception as e: # Catch any other non-ScopusError exceptions
        print(f"An unexpected non-Scopus error occurred during Scopus search: {type(e).__name__} - {e}")
    finally:
        if api_key_manually_set: # Restore original key if we changed it
            if original_key:
                config["Authentication"]["APIKey"] = original_key
            elif "APIKey" in config.get("Authentication", {}): # If key was set and no original_key existed
                del config["Authentication"]["APIKey"]
                if not config.get("Authentication"): # If Authentication dict is now empty
                    del config["Authentication"]
    return results_list


def fetch_scopus_abstract_details(eid: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve detailed metadata for a Scopus document by its EID, including abstract, keywords, references, and structured funding information.
    
    Parameters:
        eid (str): The Scopus EID of the document to retrieve.
    
    Returns:
        dict or None: A dictionary containing abstract text, author and index keywords, reference count, a list of cited references (DOIs or EIDs), structured funding entries, acknowledgements text, and the raw abstract retrieval dictionary. Returns None if retrieval fails or the document is not found.
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
        print(f"Warning: Scopus API key not found in pybliometrics's global CONFIG. Fetching details for EID {eid} may rely on other configurations or fail.")

    try:
        ab_ret = AbstractRetrieval(identifier=eid, id_type='eid', view="FULL", refresh=False)

        details = {
            "abstract": getattr(ab_ret, 'abstract', None),
            "author_keywords": getattr(ab_ret, 'authkeywords', None),
            "index_keywords": getattr(ab_ret, 'idxterms', None),
            "references_count": getattr(ab_ret, 'refcount', None),
            "references": [ref.id for ref in getattr(ab_ret, 'references', []) if ref and hasattr(ref, 'id') and ref.id],
            # "funding_details" was a previous simpler structure, replacing with funding_entries
            # "funding_details": {
            #     "agency": getattr(ab_ret, 'funding_agency', None),
            #     "text": getattr(ab_ret, 'funding_text', None)
            # } if getattr(ab_ret, 'funding_agency', None) or getattr(ab_ret, 'funding_text', None) else None,
            "raw_abstract_retrieval_dict": ab_ret.to_dict() if hasattr(ab_ret, 'to_dict') else None
        }

        # Process structured funding information from ab_ret.funding
        # ab_ret.funding is a list of namedtuples: Funding(agency, agency_acronym, grant_id, country)
        funding_entries_list: List[Dict[str, Any]] = []
        if hasattr(ab_ret, 'funding') and ab_ret.funding:
            for fund_info in ab_ret.funding:
                entry: Dict[str, Any] = {"source_of_info": "scopus_api_structured_funding"}
                funder_name_candidate = getattr(fund_info, 'agency', None)
                funder_acronym = getattr(fund_info, 'agency_acronym', None)

                final_funder_name = None
                if funder_name_candidate and isinstance(funder_name_candidate, str) and \
                   funder_name_candidate.lower().strip() not in ["funding organization", "unknown", "", None]:
                    final_funder_name = funder_name_candidate.strip()
                elif funder_acronym and isinstance(funder_acronym, str) and funder_acronym.strip(): # Fallback to acronym
                    final_funder_name = funder_acronym.strip()

                if final_funder_name:
                    entry["funder_name"] = final_funder_name

                grant_id_val = getattr(fund_info, 'grant_id', None)
                if grant_id_val and isinstance(grant_id_val, str) and grant_id_val.strip():
                    # grant_id from pybliometrics can sometimes be a semicolon-separated list
                    entry["grant_ids"] = [g.strip() for g in grant_id_val.split(';') if g.strip()]

                # Scopus funder ID might be available, e.g. fund_info.get('id') or similar if pybliometrics adds it
                # For now, this is not standard in the Funding namedtuple from older pybliometrics versions.

                if entry.get("funder_name") or entry.get("grant_ids"):
                    funding_entries_list.append(entry)

        # Store the full funding_text for potential NLP by FundingAnalyzer or direct display
        if hasattr(ab_ret, 'funding_text') and ab_ret.funding_text and isinstance(ab_ret.funding_text, str):
            details['acknowledgements_text_scopus'] = ab_ret.funding_text.strip()

        if funding_entries_list:
            details["funding_entries"] = funding_entries_list
        else:
            details["funding_entries"] = None

        # Cited References from Scopus AbstractRetrieval
        # ab_ret.references is a list of namedtuples, each with 'id' (EID), 'doi', 'title', etc.
        cited_references_list: List[str] = []
        if hasattr(ab_ret, 'references') and ab_ret.references:
            for ref in ab_ret.references:
                if not ref: continue # Skip if ref object is None

                ref_doi = getattr(ref, 'doi', None)
                ref_eid = getattr(ref, 'id', None) # Scopus EID

                if ref_doi and isinstance(ref_doi, str) and ref_doi.strip():
                    # Prefer DOI, clean it (remove potential URL prefix if Scopus ever adds it)
                    cleaned_doi = ref_doi.replace("https://doi.org/", "").strip()
                    if cleaned_doi:
                        cited_references_list.append(cleaned_doi)
                elif ref_eid and isinstance(ref_eid, str) and ref_eid.strip():
                    # Fallback to Scopus EID if DOI not present/valid
                    cited_references_list.append(ref_eid)
                # Could also store ref.title or other ref details if needed, but list of IDs is primary goal.

        if cited_references_list:
            details["cited_references"] = sorted(list(set(cited_references_list)))
        else:
            details["cited_references"] = None

        return details
    except FileNotFoundError:
        print("Scopus configuration file or API key not found by pybliometrics. Please initialize pybliometrics (e.g., with an API key or by running pybliometrics.scopus.utils.create_config()).")
        return None
    except scopus_errors.ScopusError as e: # Catching base ScopusError from the errors module
        status_code = getattr(e, 'http_status', None) or getattr(e, '_code', None)
        error_text = str(e)
        specific_error_type = e.__class__.__name__

        print(f"A Scopus error ({specific_error_type}) occurred while fetching details for EID {eid}.")
        if status_code:
            print(f"  HTTP Status: {status_code}")
        print(f"  Message: {error_text}")

        if isinstance(e, scopus_errors.Scopus401Error): # Specific check for 401
            print(f"  Detail: Authentication failed. Check your Scopus API key and its permissions.")
        elif isinstance(e, scopus_errors.Scopus404Error): # Specific check for 404
            print(f"  Detail: The Scopus document with EID {eid} was not found or access was denied.")
        elif isinstance(e, scopus_errors.Scopus429Error): # Specific check for 429
             print(f"  Detail: API rate limit has been exceeded for EID {eid}. Please wait before making new requests.")
        # Can add more isinstance checks here for other specific Scopus errors.

    except Exception as e: # Catch any other non-ScopusError exceptions
        print(f"An unexpected non-Scopus error occurred fetching details for Scopus EID {eid}: {type(e).__name__} - {e}")
    finally:
        if api_key_manually_set: # Restore original key if we changed it
            if original_key:
                config["Authentication"]["APIKey"] = original_key
            elif "APIKey" in config.get("Authentication", {}):
                del config["Authentication"]["APIKey"]
                if not config.get("Authentication"):
                    del config["Authentication"]
    return None


def _parse_scopus_search_result(item: Any) -> Dict[str, Any]:
    """
    Convert a single Scopus search result item into a standardized dictionary format.
    
    Extracts key metadata fields such as title, authors, journal, year, DOI, Scopus EID, PubMed ID, abstract, keywords, document type, and acknowledgements. Also includes the raw search result data for reference.
    """
    authors_list = []
    if getattr(item, 'authors', None) and isinstance(item.authors, list):
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
            year = None

    keywords = []
    if getattr(item, 'authkeywords', None) and isinstance(item.authkeywords, str):
        keywords = [k.strip() for k in item.authkeywords.split('|') if k.strip()]

    document_type = getattr(item, 'aggregationType', None)
    if not document_type and hasattr(item, 'subtypeDescription'):
        document_type = item.subtypeDescription

    raw_data = None
    if hasattr(item, '_asdict'): # For namedtuples
        raw_data = item._asdict()
    elif isinstance(item, dict):
        raw_data = item

    return {
        "title": getattr(item, 'title', None),
        "authors": authors_list,
        "journal": getattr(item, 'publicationName', None),
        "year": year,
        "doi": getattr(item, 'doi', None),
        "scopus_id": getattr(item, 'eid', None),
        "pubmed_id": getattr(item, 'pubmed_id', None),
        "abstract": getattr(item, 'description', None),
        "keywords": keywords,
        "document_type": document_type,
        "funding_entries": None,
        "acknowledgements_text_scopus": getattr(item, 'funding_text', None),
        "cited_references": None, # Search results typically don't have detailed cited refs
        "source_type": "scopus",
        "raw_search_result": raw_data
    }


if __name__ == "__main__":
    print("Attempting to search Scopus using sciencemapping.data_sources.scopus...")

    if not _is_scopus_configured():
        print("--------------------------------------------------------------------")
        print("INFO: _is_scopus_configured() returned False. This means no API key was found in pybliometrics.scopus.CONFIG.")
        print("The library will now rely on other mechanisms (e.g., environment variables, config.ini file).")
        print("If no configuration is found by pybliometrics, the calls will likely fail with a FileNotFoundError.")
        print("--------------------------------------------------------------------")
    else:
        print("INFO: _is_scopus_configured() returned True. API key found in pybliometrics.scopus.CONFIG.")

    query_string = 'TITLE-ABS-KEY(bibliometrics) AND PUBYEAR > 2022 AND DOCTYPE(ar)'

    articles_found = search_scopus(query_string, max_results=2)

    if articles_found:
        print(f"\nFound {len(articles_found)} articles from Scopus for query: '{query_string}'")
        for idx, artcl in enumerate(articles_found):
            print(f"\n--- Article {idx+1} (from Scopus Search) ---")
            print(f"  Title: {artcl.get('title')}")
            print(f"  EID: {artcl.get('scopus_id')}")

            scopus_eid = artcl.get('scopus_id')
            if scopus_eid:
                print(f"  Fetching full details for EID: {scopus_eid}...")
                time.sleep(0.5)
                full_details = fetch_scopus_abstract_details(eid=scopus_eid)
                if full_details:
                    print(f"    Full Abstract snippet: {str(full_details.get('abstract', 'N/A'))[:100]}...")
                else:
                    print(f"    Could not fetch full details for EID: {scopus_eid}.")
    else:
        print(f"No articles found from Scopus for the query: '{query_string}', or an error occurred during search.")

    print("\nScopus example finished.")
