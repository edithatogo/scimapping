from typing import List, Dict, Any, Optional
import warnings

# Attempt to import openalex library
OPENALEX_AVAILABLE = False
openalex_module = None
try:
    import openalex
    OPENALEX_AVAILABLE = True
    openalex_module = openalex # Alias for clarity if needed below
    # print("OpenAlex: 'openalex' library loaded successfully.") # For debugging
except ImportError:
    warnings.warn(
        "OpenAlex: 'openalex' library not found. OpenAlex API search will be disabled. "
        "Install with 'pip install openalex'.",
        ImportWarning
    )

def search_openalex_works(
    search_query: Optional[str] = None,
    filter_criteria: Optional[Dict[str, Any]] = None,
    max_results: int = 25,
    user_email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Searches OpenAlex for works matching a search query and/or filter criteria.
    """
    if not OPENALEX_AVAILABLE or not openalex_module:
        warnings.warn("OpenAlex: 'openalex' library not available. Skipping search.", RuntimeWarning)
        return []

    original_email = None
    if user_email:
        # Store original and set new one. openalex library uses a global config.
        if hasattr(openalex_module, 'config') and hasattr(openalex_module.config, 'email'):
            original_email = openalex_module.config.email
            openalex_module.config.email = user_email
        else:
            warnings.warn("OpenAlex: Could not set user_email, openalex.config.email not found.", RuntimeWarning)

    results_list: List[Dict[str, Any]] = []

    try:
        works_query = openalex_module.Works()

        if search_query:
            works_query = works_query.search(search_query)

        if filter_criteria:
            # Correct way to apply multiple filters if filter_criteria is a dict
            # e.g. .filter(publication_year=2022, authorships_author_id="A123")
            works_query = works_query.filter(**filter_criteria)

        retrieved_count = 0
        # Use paginate with n_max to control total results
        # Ensure per_page is reasonable, max 200 for OpenAlex typically.
        effective_per_page = min(max_results, 100) if max_results > 0 else 100

        for work_data_page in works_query.paginate(per_page=effective_per_page, n_max=max_results if max_results > 0 else None):
            if not work_data_page: # A page might be empty if n_max is not perfectly divisible
                continue
            for work_data_json in work_data_page:
                if work_data_json:
                    parsed_item = _parse_openalex_work(work_data_json)
                    if parsed_item:
                        results_list.append(parsed_item)
                        retrieved_count += 1
                        # n_max in paginate should handle this, but as a safeguard:
                        if max_results > 0 and retrieved_count >= max_results:
                            break
            if max_results > 0 and retrieved_count >= max_results:
                break

    except Exception as e:
        print(f"An error occurred during OpenAlex search: {type(e).__name__} - {e}")
    finally:
        if user_email and original_email is not None: # Restore original email
            if hasattr(openalex_module, 'config') and hasattr(openalex_module.config, 'email'):
                openalex_module.config.email = original_email

    return results_list


def _parse_openalex_work(item_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses a single work JSON from OpenAlex API into our common internal format.
    """
    if not item_json or not isinstance(item_json, dict):
        return None

    title = item_json.get('title') or item_json.get('display_name')
    if not title:
        return None

    authors_list = []
    if 'authorships' in item_json and isinstance(item_json['authorships'], list):
        for authorship in item_json['authorships']:
            if isinstance(authorship, dict) and authorship.get('author'):
                author_name = authorship['author'].get('display_name')
                if author_name:
                    authors_list.append(author_name)

    journal_title = None
    host_venue = item_json.get('host_venue')
    if host_venue and isinstance(host_venue, dict):
        journal_title = host_venue.get('display_name') or host_venue.get('publisher')

    keywords = []
    if 'concepts' in item_json and isinstance(item_json['concepts'], list):
        for concept in item_json['concepts']:
            if isinstance(concept, dict) and concept.get('display_name'):
                keywords.append(concept['display_name'])

    abstract_text = None # Placeholder, abstract reconstruction is complex
    if item_json.get('abstract_inverted_index'):
        abstract_text = "Abstract available (inverted index)" # Indicate presence

    openalex_id_full = item_json.get('id')
    openalex_id = None
    if openalex_id_full and isinstance(openalex_id_full, str) and "/" in openalex_id_full:
        openalex_id = openalex_id_full.split("/")[-1]
    elif openalex_id_full and isinstance(openalex_id_full, str): # If it's already just the ID part
        openalex_id = openalex_id_full


    parsed = {
        "title": title,
        "authors": authors_list,
        "journal": journal_title,
        "year": item_json.get('publication_year'),
        "doi": item_json.get('doi'),
        "openalex_id": openalex_id,
        "abstract": abstract_text,
        "keywords": list(set(keywords)),
        "document_type": item_json.get('type'),
        "source_type": "openalex",
        "times_cited_openalex": item_json.get('cited_by_count'),
        "raw_data": item_json
    }
    return parsed

if __name__ == "__main__":
    print("OpenAlex Data Source Module Example")
    if not OPENALEX_AVAILABLE:
        print("OpenAlex library not found. Cannot run API example.")
    else:
        my_email = "sciencemappinglib_test@example.com"
        if hasattr(openalex_module, 'config'): openalex_module.config.email = my_email # Set for polite pool
        print(f"Using email for polite pool: {my_email if hasattr(openalex_module, 'config') and openalex_module.config.email else 'Default (not set)'}")

        example_search = "bibliometrics"
        example_filters = {"publication_year": "2023"}

        articles = search_openalex_works(
            search_query=example_search,
            filter_criteria=example_filters,
            max_results=2
            # user_email is handled by the global config setting above for this example
        )

        if articles:
            print(f"\nSuccessfully retrieved {len(articles)} articles from OpenAlex:")
            for i, article in enumerate(articles):
                print(f"\n--- Article {i+1} (from OpenAlex) ---")
                print(f"  ID: {article.get('openalex_id')}")
                print(f"  Title: {article.get('title')}")
        else:
            print("\nNo articles retrieved from OpenAlex, or an error occurred.")
    print("\nOpenAlex example finished.")
