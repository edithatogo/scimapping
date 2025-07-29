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

    all_keywords_raw = []
    # Process 'keywords' field
    if 'keywords' in item_json and isinstance(item_json['keywords'], list):
        for kw_item in item_json['keywords']:
            if isinstance(kw_item, str):
                all_keywords_raw.append(kw_item)
            elif isinstance(kw_item, dict) and kw_item.get('name'):
                all_keywords_raw.append(kw_item['name'])

    # Process 'concepts' field
    if 'concepts' in item_json and isinstance(item_json['concepts'], list):
        for concept_item in item_json['concepts']:
             if isinstance(concept_item, str):
                 all_keywords_raw.append(concept_item)
             # Assuming concepts can also be dicts with a 'name' key, like keywords
             elif isinstance(concept_item, dict) and concept_item.get('name'):
                 all_keywords_raw.append(concept_item['name'])

    # Apply standard normalization
    processed_keywords = []
    if all_keywords_raw:
        normalized_kws = [str(kw).strip().lower() for kw in all_keywords_raw if kw and isinstance(kw, (str, int, float)) and str(kw).strip()]
        if normalized_kws:
            processed_keywords = sorted(list(set(normalized_kws)))

    parsed = {
        "title": title,
        "authors": authors_list,
        "journal": journal_title,
        "year": item_json.get('year') or item_json.get('publication_year'),
        "doi": item_json.get('doi'),
        "dimensions_id": item_json.get('id'),
        "abstract": item_json.get('abstract'),
        "keywords": processed_keywords,
        "document_type": item_json.get('type'),
        "source_type": "dimensions_api",
        # Initialize new fields
        "funding_entries": None,
        "cited_references": None,
        "raw_data": item_json
    }

    # --- Extract Cited References ---
    # item_json["references"] can be:
    # 1. List of dicts: e.g., [{"id": "pub.ref1"}, {"id": "pub.ref2"}] (from DSL like ...references[id])
    # 2. List of strings/ints (IDs): e.g., ["pub.refA", "pub.refB", 12345] (from DSL like ...reference_ids)
    parsed["cited_references"] = None # Initialize
    if "references" in item_json and isinstance(item_json["references"], list):
        ref_ids = []
        for ref_item in item_json["references"]:
            ref_id_val = None
            if isinstance(ref_item, dict) and ref_item.get("id"):
                ref_id_val = str(ref_item["id"]).strip()
            elif isinstance(ref_item, (str, int)): # Handles if it's just a list of IDs
                ref_id_val = str(ref_item).strip()

            if ref_id_val: # Ensure not empty string after strip and was valid type
                ref_ids.append(ref_id_val)

        if ref_ids:
            parsed["cited_references"] = sorted(list(set(ref_ids)))

    # --- Extract Funding Information ---
    funding_entries_list: List[Dict[str, Any]] = []
    if "funders" in item_json and isinstance(item_json["funders"], list):
        for funder_detail in item_json["funders"]:
            if not isinstance(funder_detail, dict): continue
            entry: Dict[str, Any] = {"source_of_info": "dimensions_api_funders_field"}
            # Refined Funder Name Logic: Prefer name/org, fallback to acronym. Ensure stripping.
            funder_name = funder_detail.get("name") or funder_detail.get("organization")
            if not funder_name and funder_detail.get("acronym"):
                funder_name = funder_detail.get("acronym")
            if funder_name: entry["funder_name"] = str(funder_name).strip()

            grant_ids_for_funder = []
            # Process 'grant_ids' field (flat list of strings)
            if "grant_ids" in funder_detail and isinstance(funder_detail["grant_ids"], list):
                grant_ids_for_funder.extend([str(gid).strip() for gid in funder_detail["grant_ids"] if gid and str(gid).strip()])

            # Process 'grants' field (list of dicts with 'id', or list of strings)
            # This is now an 'if', not 'elif', to process both fields if present.
            if "grants" in funder_detail and isinstance(funder_detail["grants"], list):
                 for grant_item in funder_detail["grants"]:
                    gid_val = None
                    if isinstance(grant_item, dict) and grant_item.get("id"):
                        gid_val = str(grant_item["id"]).strip()
                    elif isinstance(grant_item, str) and grant_item.strip(): # Check if string is not empty after strip
                        gid_val = grant_item.strip()

                    if gid_val: # Add if a valid grant ID was extracted
                        grant_ids_for_funder.append(gid_val)

            if grant_ids_for_funder:
                entry["grant_ids"] = sorted(list(set(grant_ids_for_funder))) # Deduplicate and sort

            if funder_detail.get("id"): entry["dimensions_funder_id"] = funder_detail.get("id")
            if funder_detail.get("ror_id"): entry["funder_ror_id"] = funder_detail.get("ror_id")

            if entry.get("funder_name") or entry.get("grant_ids"):
                funding_entries_list.append(entry)

    # Process top-level 'supporting_grant_ids'
    # These are grant IDs not necessarily linked to a specific funder in the 'funders' block.
    processed_grant_ids_from_structured_funders = set()
    if funding_entries_list: # If we already have entries from the 'funders' block
        for entry_from_funder_block in funding_entries_list:
            if entry_from_funder_block.get("grant_ids"):
                for gid_in_block in entry_from_funder_block["grant_ids"]:
                    processed_grant_ids_from_structured_funders.add(gid_in_block)

    if "supporting_grant_ids" in item_json and isinstance(item_json["supporting_grant_ids"], list):
        unique_supporting_gids_to_add = []
        for sup_gid_raw in item_json["supporting_grant_ids"]:
            if sup_gid_raw is None: # Skip None values explicitly
                continue
            sup_gid = str(sup_gid_raw).strip()
            # Ensure sup_gid is not empty and not already processed from the 'funders' block
            if sup_gid and sup_gid not in processed_grant_ids_from_structured_funders:
                if sup_gid not in unique_supporting_gids_to_add: # Avoid duplicates from supporting_grant_ids itself
                    unique_supporting_gids_to_add.append(sup_gid)

        for unique_sup_gid in unique_supporting_gids_to_add:
            funding_entries_list.append({
                # "funder_name": None, # Explicitly no named funder for these
                "grant_ids": [unique_sup_gid],
                "source_of_info": "dimensions_api_grant_ids_field",
                "raw_funding_text": f"Supporting grant ID: {unique_sup_gid}" # Provide context
            })
            # No need to add to processed_grant_ids_from_structured_funders here,
            # as we are creating new entries, not merging.

    if funding_entries_list:
        # Sort final list of entries? Optional, but could be by funder name then grant ID for consistency.
        # For now, the order is funders block entries, then supporting_grant_id entries.
        parsed["funding_entries"] = funding_entries_list

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
