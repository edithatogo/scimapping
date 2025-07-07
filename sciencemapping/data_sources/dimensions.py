from typing import List, Dict, Any, Optional
# Attempt to import the official Dimensions API client; handle if not installed or configured.
try:
    from dimcli.core.api import Dsl
    DIMENSIONS_API_AVAILABLE = True
except ImportError:
    DIMENSIONS_API_AVAILABLE = False
    Dsl = None # Placeholder if not available

def search_dimensions_api(
    dsl_query: str,
    max_results: int = 100,
    dsl_instance: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Searches Dimensions using its API and the DSL (Domain Specific Language).
    Requires the 'dimcli' library and appropriate API credentials configured.
    """
    if not DIMENSIONS_API_AVAILABLE:
        print("Error: 'dimcli' library not found. Cannot use Dimensions API search.")
        return []

    api_results: List[Dict[str, Any]] = []
    dsl_client = None
    if dsl_instance:
        dsl_client = dsl_instance
    else:
        try:
            dsl_client = Dsl(show_results=False, verbose=False)
        except Exception as e:
            print(f"Error initializing Dimensions API client: {e}")
            return []

    if not dsl_client or not hasattr(dsl_client, 'query_iterative'):
        print("Error: Failed to get a valid Dimensions API client instance.")
        return []

    try:
        print(f"Executing Dimensions API query: {dsl_query} (aiming for up to {max_results} results)")
        count = 0
        for result_item_json in dsl_client.query_iterative(dsl_query, limit=min(max_results, 500)):
            if result_item_json:
                parsed_item = _parse_dimensions_api_record(result_item_json)
                if parsed_item:
                    api_results.append(parsed_item)
                    count += 1
                    if count >= max_results:
                        break
            if count >= max_results:
                break
    except Exception as e:
        print(f"An error occurred during Dimensions API query: {type(e).__name__} - {e}")
    return api_results

def _parse_dimensions_api_record(item_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parses a single record JSON from the Dimensions API into our common internal format.
    """
    if not item_json or not isinstance(item_json, dict):
        return None

    title = item_json.get('title')
    if not title:
        return None

    authors_list = []
    if 'authors' in item_json and isinstance(item_json['authors'], list):
        for author_info in item_json['authors']:
            if isinstance(author_info, dict):
                name_parts = []
                if author_info.get('last_name'): name_parts.append(author_info['last_name'])
                if author_info.get('first_name'): name_parts.append(author_info['first_name'])
                if name_parts: authors_list.append(" ".join(name_parts))
                elif 'name' in author_info: authors_list.append(author_info['name'])

    journal_title = None
    if 'journal' in item_json and isinstance(item_json['journal'], dict):
        journal_title = item_json['journal'].get('title')
    elif 'journal_title' in item_json:
        journal_title = item_json['journal_title']
    elif 'publication_outlet' in item_json:
        journal_title = item_json['publication_outlet']

    keywords = []
    if 'keywords' in item_json and isinstance(item_json['keywords'], list):
        for kw in item_json['keywords']:
            if isinstance(kw, str): keywords.append(kw)
            elif isinstance(kw, dict) and 'name' in kw: keywords.append(kw['name'])
    elif 'concepts' in item_json and isinstance(item_json['concepts'], list):
        for concept in item_json['concepts']:
             if isinstance(concept, str): keywords.append(concept)

    parsed = {
        "title": title,
        "authors": authors_list,
        "journal": journal_title,
        "year": item_json.get('year') or item_json.get('publication_year'),
        "doi": item_json.get('doi'),
        "dimensions_id": item_json.get('id'),
        "abstract": item_json.get('abstract'),
        "keywords": list(set(keywords)),
        "document_type": item_json.get('type'),
        "source_type": "dimensions_api",
        "raw_data": item_json
    }
    return parsed

def parse_dimensions_file(file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """ Placeholder for parsing Dimensions data from an export file (e.g., CSV). """
    print(f"Notice: File parsing for Dimensions ('{file_path}') is not yet fully implemented.")
    return []

if __name__ == "__main__":
    print("Dimensions Data Source Module Example")
    if DIMENSIONS_API_AVAILABLE:
        print("Dimensions API client ('dimcli') is available.")
        example_dsl_query = 'search publications where concepts ~ "bibliometrics" and year >= 2023 return publications[basics + authors + concepts] limit 2'
        print(f"\nAttempting to run example Dimensions API query: {example_dsl_query}")
        try:
            articles_from_api = search_dimensions_api(example_dsl_query, max_results=2)
            if articles_from_api:
                print(f"\nSuccessfully retrieved {len(articles_from_api)} articles from Dimensions API:")
                for i, article in enumerate(articles_from_api):
                    print(f"\n--- Article {i+1} (from Dimensions API) ---")
                    print(f"  ID: {article.get('dimensions_id')}")
                    print(f"  Title: {article.get('title')}")
            else:
                print("\nNo articles retrieved from Dimensions API or error.")
        except Exception as e:
            print(f"\nMain example block caught an error: {e}")
    else:
        print("Dimensions API client ('dimcli') is NOT available.")
    print("\nDimensions example finished.")
