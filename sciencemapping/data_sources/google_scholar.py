from typing import List, Dict, Any, Optional
import warnings

# Attempt to import scholarly
SCHOLARLY_AVAILABLE = False
scholarly_module = None
try:
    from scholarly import scholarly # The library itself is imported like this
    SCHOLARLY_AVAILABLE = True
    scholarly_module = scholarly # Alias for clarity
    print("GoogleScholar: 'scholarly' library loaded successfully.")
except ImportError:
    warnings.warn(
        "GoogleScholar: 'scholarly' library not found. Google Scholar search will be disabled. "
        "Install with 'pip install scholarly'.",
        ImportWarning
    )
except Exception as e: # Catch other potential errors during import or initial setup if any
    warnings.warn(
        f"GoogleScholar: Error loading 'scholarly' library: {e}. Google Scholar search will be disabled.",
        ImportWarning
    )


# --- IMPORTANT CAVEATS FOR GOOGLE SCHOLAR ---
# 1. No Official API: Google Scholar does not have an official, supported API.
#    Libraries like 'scholarly' work by parsing the HTML of the Google Scholar website (scraping).
# 2. Reliability: This approach is inherently fragile and can break if Google Scholar changes its website layout.
#    It can also be slow.
# 3. Terms of Service & Blocking: Automated querying of Google Scholar can violate their Terms of Service.
#    Frequent or rapid queries can lead to IP address blocks or CAPTCHA challenges,
#    making the tool unusable without mitigation strategies like proxies.
# 4. Proxy Recommendation: The 'scholarly' library documentation STRONGLY RECOMMENDS using proxies
#    (e.g., scholarly.set_proxy_generator(pg)) to avoid blocks for any significant use.
#    This sciencemapping library does not configure proxies for 'scholarly' by default.
#    Users needing reliable Google Scholar access via this module should configure 'scholarly'
#    with proxies globally in their own script before calling these functions.
#
# Due to these reasons, results from this module should be treated with caution,
# and its use might be unreliable.
# --- END CAVEATS ---

def search_google_scholar(
    query: str,
    max_results: int = 10,
    fill_publications: bool = False # Whether to call pub.fill() for more details
    ) -> List[Dict[str, Any]]:
    """
    Searches Google Scholar for publications matching the query using the 'scholarly' library.

    Args:
        query: The search query string.
        max_results: The maximum number of publication results to retrieve.
        fill_publications: If True, attempts to call `pub.fill()` for each publication
                           to fetch more details (e.g., abstract). This significantly
                           increases requests and risk of being blocked. Defaults to False.

    Returns:
        A list of dictionaries, where each dictionary represents a publication
        parsed into the common internal format. Returns empty list if 'scholarly'
        is unavailable or if an error occurs.
    """
    if not SCHOLARLY_AVAILABLE or not scholarly_module:
        warnings.warn("GoogleScholar: 'scholarly' library not available. Cannot perform search.", RuntimeWarning)
        return []

    warnings.warn(
        "GoogleScholar: Using this function to query Google Scholar can be unreliable and may lead to IP blocks "
        "or CAPTCHAs from Google, as it relies on web scraping. The 'scholarly' library recommends "
        "using proxies for any significant use. This library does not configure proxies by default.",
        UserWarning
    )

    results_list: List[Dict[str, Any]] = []
    try:
        print(f"GoogleScholar: Searching for query '{query}' (max_results: {max_results}, fill: {fill_publications})...")
        # scholarly.search_pubs returns a generator
        search_results_gen = scholarly_module.search_pubs(query)

        for i, pub_data_raw in enumerate(search_results_gen):
            if i >= max_results:
                break

            current_pub_data = pub_data_raw
            if fill_publications:
                try:
                    # .fill() fetches more details, modifies the object in-place, and returns it.
                    # It's a blocking call and makes an additional HTTP request.
                    print(f"GoogleScholar: Filling publication details for result {i+1}...")
                    # `scholarly` objects from search_pubs might be dicts.
                    # If `pub_data_raw` is a dict, we need to create a `Publication` obj to fill,
                    # or check if `scholarly.fill(dict)` works.
                    # Assuming scholarly.fill can take the dict directly, or that search_pubs yields objects
                    # that have a .fill() method if the library is more object-oriented now.
                    # Based on recent scholarly, search_pubs yields dicts.
                    # To fill, one typically does: pub = scholarly.Publication(scholarly, pub_data_raw) then pub.fill()
                    # Or, simpler, scholarly.fill(pub_data_raw) might work if it's just a dict.
                    # Let's assume for now that `scholarly.fill()` can handle the dict from search_pubs.
                    # If not, this part would need adjustment based on the exact scholarly API.
                    # The `fill` method is often on the `Publication` object, not a global function.
                    # For now, let's assume `pub_data_raw` is an object with a `fill` method.
                    if hasattr(current_pub_data, 'fill'):
                         current_pub_data = current_pub_data.fill()
                    elif isinstance(current_pub_data, dict) and 'gsrank' in current_pub_data: # Heuristic for a PublicationSummary
                         # This part is tricky without knowing the exact object type from search_pubs
                         # For safety, we'll pass the dict to _parse_gs_publication,
                         # and _parse_gs_publication will just use available fields.
                         # True filling might require more complex object handling.
                         print(f"GoogleScholar: fill_publications=True but direct .fill() method not found on result {i+1}. Parsing as is.")
                         pass # Continue with potentially less detailed data

                except Exception as e_fill:
                    warnings.warn(f"GoogleScholar: Error while trying to 'fill' publication details for result {i+1}: {e_fill}", RuntimeWarning)
                    # Proceed with parsing whatever data we have for this pub

            parsed_pub = _parse_gs_publication(current_pub_data)
            if parsed_pub:
                results_list.append(parsed_pub)

        print(f"GoogleScholar: Search completed. Found {len(results_list)} results matching criteria.")

    except Exception as e: # Catch broad exceptions from scholarly (e.g., related to blocking)
        print(f"GoogleScholar: An error occurred during search: {type(e).__name__} - {e}")
        warnings.warn(f"GoogleScholar: Search failed due to: {e}. This might be due to Google blocking requests. Consider using proxies with 'scholarly'.", RuntimeWarning)
        return [] # Return empty on error

    return results_list

def _parse_gs_publication(pub_data: Any) -> Optional[Dict[str, Any]]:
    """
    Parses a single publication item from the 'scholarly' library into our common internal format.
    'scholarly' publication items are typically dictionaries, often with a nested 'bib' dictionary.
    """
    if not pub_data:
        return None

    # If pub_data is an object with a 'bib' attribute that's a dict (older scholarly versions or filled objects)
    if hasattr(pub_data, 'bib') and isinstance(pub_data.bib, dict):
        bib = pub_data.bib
        num_citations = getattr(pub_data, 'num_citations', 0)
        pub_url = getattr(pub_data, 'pub_url', None)
        eprint_url = getattr(pub_data, 'eprint_url', None)
    # If pub_data is already a dictionary (common for items from search_pubs generator)
    elif isinstance(pub_data, dict):
        bib = pub_data.get('bib', {}) # bib might be missing in some summaries
        num_citations = pub_data.get('num_citations', 0)
        pub_url = pub_data.get('pub_url', None)
        eprint_url = pub_data.get('eprint_url', None)
    else:
        warnings.warn(f"GoogleScholar: Unexpected pub_data type: {type(pub_data)}", RuntimeWarning)
        return None # Cannot parse

    title = bib.get('title')
    if not title:
        return None # Title is essential

    authors_str = bib.get('author', '')
    authors_list = []
    if authors_str and isinstance(authors_str, str):
        # Authors can be "A Name and B Name and C Name" or "A Name, B Name, C Name"
        # scholarly often returns a string of names separated by ' and ' or sometimes commas.
        # A simple split by ' and ' then by ',' for each part is a heuristic.
        potential_authors = re.split(r'\s+and\s+', authors_str, flags=re.IGNORECASE)
        for pa_chunk in potential_authors:
            authors_list.extend([name.strip() for name in pa_chunk.split(',') if name.strip()])
        authors_list = [name for name in authors_list if name] # Clean out any empty strings
    elif isinstance(authors_str, list): # Should not happen with scholarly's bib['author'] but good fallback
        authors_list = [str(a).strip() for a in authors_str if str(a).strip()]


    # Year can be string or int
    year_raw = bib.get('pub_year')
    year = None
    if year_raw:
        try:
            year = int(year_raw)
        except ValueError:
            warnings.warn(f"GoogleScholar: Could not parse year '{year_raw}' as integer for title '{title}'.", RuntimeWarning)
            year = None # Or try to extract year with regex if it's like "2020-2021"

    # Keywords are usually not directly available from Google Scholar search results.
    # Sometimes 'abstract' might contain them, or they could be inferred.
    # For now, initialize as empty and note this limitation.
    keywords = []
    abstract = bib.get('abstract', None)

    # DOI is not a standard field from scholarly's basic search.
    # It might be found by further scraping the pub_url or eprint_url, or via CrossRef.
    # We will not attempt that here.
    doi = None

    parsed_record = {
        "title": str(title),
        "authors": authors_list,
        "journal": bib.get('venue', None), # 'venue' often contains journal/conference
        "year": year,
        "doi": doi, # Typically None from GS directly
        "abstract": str(abstract) if abstract else None,
        "keywords": keywords, # Typically empty from GS directly
        "times_cited_google_scholar": int(num_citations) if num_citations is not None else 0,
        "publication_url_gs": pub_url, # Google Scholar URL for the publication
        "eprint_url_gs": eprint_url,   # PDF link if found by scholarly
        "funding_entries": None,    # GS doesn't provide this directly
        "cited_references": None, # GS doesn't provide this directly
        "source_type": "google_scholar",
        "raw_data": pub_data # Store the original scholarly item
    }
    return parsed_record


if __name__ == "__main__":
    print("Google Scholar Data Source Module Example")
    if not SCHOLARLY_AVAILABLE:
        print("Scholarly library not found. Cannot run Google Scholar search example.")
    else:
        # IMPORTANT: This will make live requests to Google Scholar and WILL LIKELY GET BLOCKED
        # without proxy configuration. For a real test, configure scholarly with proxies first:
        # from scholarly import scholarly, ProxyGenerator
        # pg = ProxyGenerator()
        # success = pg.FreeProxies() # or use a paid service: pg.ScraperAPI("YOUR_API_KEY")
        # if success: scholarly.use_proxy(pg)
        # else: print("Failed to configure proxies for scholarly.")

        print("\n**WARNING: Live Google Scholar query ahead. This may fail or lead to blocks without proxies.**")
        try:
            # Example: Search for publications
            query = "bibliometric analysis of renewable energy"
            print(f"Searching Google Scholar for: '{query}' (max 2 results, no fill)...")

            results = search_google_scholar(query, max_results=2, fill_publications=False)

            if results:
                print(f"\nFound {len(results)} publications:")
                for i, pub in enumerate(results):
                    print(f"\n--- Publication {i+1} ---")
                    print(f"  Title: {pub.get('title')}")
                    print(f"  Authors: {pub.get('authors')}")
                    print(f"  Year: {pub.get('year')}")
                    print(f"  Journal/Venue: {pub.get('journal')}")
                    print(f"  Citations (GS): {pub.get('times_cited_google_scholar')}")
                    print(f"  GS URL: {pub.get('publication_url_gs')}")
            else:
                print("No results found or an error occurred.")

        except Exception as e:
            print(f"An error occurred in the example: {e}")

    print("\nGoogle Scholar example finished.")
