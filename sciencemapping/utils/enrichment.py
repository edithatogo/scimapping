from typing import List, Dict, Any, Optional
import warnings
import re # For DOI extraction from error messages

# Attempt to import habanero for CrossRef API interaction
HABANERO_AVAILABLE = False
Crossref_class = None # Placeholder for habanero.Crossref
try:
    from habanero import Crossref
    HABANERO_AVAILABLE = True
    Crossref_class = Crossref
    # print("Enrichment: habanero library loaded successfully.") # For debugging
except ImportError:
    warnings.warn(
        "Enrichment: 'habanero' library not found. CrossRef enrichment will be disabled. "
        "Install with 'pip install habanero'.",
        ImportWarning
    )

# Default mailto for CrossRef polite pool
DEFAULT_CROSSREF_MAILTO = "sciencemappinglib_user@example.com" # Users should be encouraged to change this

# Simple Funder Name Normalization (can be expanded or moved to a shared utility)
_FUNDER_NORMALIZATION_MAP_ENRICH = {
    "national science foundation": "National Science Foundation",
    "nsf": "National Science Foundation",
    "u. s. national science foundation": "National Science Foundation",
    "national institutes of health": "National Institutes of Health",
    "nih": "National Institutes of Health",
    "u.s. national institutes of health": "National Institutes of Health",
    "erc": "European Research Council",
    "european research council": "European Research Council",
    "wellcome trust": "Wellcome Trust",
    "the wellcome trust": "Wellcome Trust",
    "medical research council": "Medical Research Council",
    "mrc": "Medical Research Council",
}

def _normalize_funder_name_enrich(name: str) -> str:
    """
    Normalize a funder name string to a canonical form for enrichment purposes.
    
    Returns "Unknown Funder" if the input is empty or not a string; otherwise, returns a normalized funder name using a predefined mapping, or the stripped original name if no mapping exists.
    """
    if not name or not isinstance(name, str):
        return "Unknown Funder" # Or return the input if preferred for non-strings
    stripped_name = name.strip()
    return _FUNDER_NORMALIZATION_MAP_ENRICH.get(stripped_name.lower(), stripped_name)

def enrich_records_with_crossref_funding(
    records: List[Dict[str, Any]],
    mailto: Optional[str] = DEFAULT_CROSSREF_MAILTO,
    batch_size: int = 20 # CrossRef API best practice for /works?ids= is around 20-50 DOIs
) -> List[Dict[str, Any]]:
    """
    Enriches publication records with funding information from CrossRef using their DOIs.
    
    For each record containing a DOI, queries the CrossRef API in batches to retrieve associated funding data. Extracted funder names, CrossRef funder registry IDs, and grant award IDs are normalized and merged into each record's `funding_entries` list, avoiding simple duplicates. Handles missing dependencies, absent DOIs, and API errors gracefully.
    
    Parameters:
        records (List[Dict[str, Any]]): List of publication records, each ideally containing a 'doi' field.
        mailto (Optional[str]): Email address for polite CrossRef API usage. Defaults to a generic address if not provided.
        batch_size (int): Number of DOIs to query per CrossRef API request. Defaults to 20.
    
    Returns:
        List[Dict[str, Any]]: The input records, potentially augmented with new funding entries in the 'funding_entries' field.
    """
    if not HABANERO_AVAILABLE or Crossref_class is None:
        warnings.warn("Enrichment: habanero library not available. Skipping CrossRef funding enrichment.", RuntimeWarning)
        return records

    if not mailto:
        warnings.warn(
            f"Enrichment: No mailto email provided for CrossRef polite pool. Using default: {DEFAULT_CROSSREF_MAILTO}. "
            "It's recommended to set a custom email.",
            UserWarning
        )
        mailto = DEFAULT_CROSSREF_MAILTO

    cr = Crossref_class(mailto=mailto)

    # Create copies of records to modify them, or modify in place if preferred by overall design
    # For now, modifying copies passed in. The ScienceMapper reassigns self._records.
    # enriched_records: List[Dict[str, Any]] = [rec.copy() for rec in records] # If modifying copies
    # If modifying in place, ensure the input `records` list objects are the ones to change.
    # Let's assume `records` can be modified directly for this util function.

    dois_to_query_map: Dict[str, List[int]] = {} # Maps clean DOI to list of original record indices

    for i, record in enumerate(records):
        doi = record.get("doi")
        if doi and isinstance(doi, str):
            clean_doi = doi.replace("https://doi.org/", "").strip().lower() # Normalize for lookup
            if clean_doi:
                if clean_doi not in dois_to_query_map:
                    dois_to_query_map[clean_doi] = []
                dois_to_query_map[clean_doi].append(i)

    if not dois_to_query_map:
        print("Enrichment: No valid DOIs found in records to query CrossRef.")
        return records

    unique_clean_dois = sorted(list(dois_to_query_map.keys()))
    print(f"Enrichment: Querying CrossRef for {len(unique_clean_dois)} unique DOIs...")

    for i in range(0, len(unique_clean_dois), batch_size):
        doi_batch = unique_clean_dois[i:i + batch_size]
        if not doi_batch:
            continue

        try:
            # habanero cr.works(ids=...) returns a list of dicts, one for each result
            # Each dict has 'status', 'message-type', 'message'
            api_results_batch = cr.works(ids=doi_batch)

            if not isinstance(api_results_batch, list): # Handle if API returns a single item not in a list
                api_results_batch = [api_results_batch] if api_results_batch else []

            for res_item in api_results_batch:
                if not isinstance(res_item, dict) or res_item.get('status') != 'ok' or 'message' not in res_item :
                    queried_doi_for_error = "unknown_doi_in_batch"
                    if isinstance(res_item, dict):
                        # Try to find the problematic DOI from the request if possible, or from error message
                        # This part is tricky as habanero might not directly map errors to input DOIs in a batch failure.
                        # For now, a generic warning for the batch.
                        url_str = res_item.get('URL', res_item.get('url', '')) # Check common keys for URL
                        if url_str and isinstance(url_str, str):
                             url_match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', url_str, re.IGNORECASE)
                             if url_match: queried_doi_for_error = url_match.group(1)
                    status = res_item.get('status', 'unknown_status') if isinstance(res_item, dict) else 'malformed_response_item'
                    warnings.warn(f"Enrichment: CrossRef API issue for a DOI (batch includes: {doi_batch[0]}, ...): Status {status}", RuntimeWarning)
                    continue

                message = res_item['message']
                retrieved_doi_from_message = message.get('DOI')
                if not retrieved_doi_from_message or not isinstance(retrieved_doi_from_message, str):
                    continue

                retrieved_doi_clean = retrieved_doi_from_message.strip().lower()

                crossref_funding_entries_for_this_doi: List[Dict[str, Any]] = []
                if "funder" in message and isinstance(message["funder"], list):
                    for funder_info in message["funder"]:
                        if not isinstance(funder_info, dict): continue
                        entry: Dict[str, Any] = {"source_of_info": "crossref_api"}

                        funder_name = funder_info.get("name")
                        if funder_name and isinstance(funder_name, str):
                            entry["funder_name"] = _normalize_funder_name_enrich(funder_name)

                        funder_registry_id = funder_info.get("DOI") # CrossRef Funder Registry DOI
                        if funder_registry_id and isinstance(funder_registry_id, str) and funder_registry_id.startswith("10.13039/"):
                            entry["funder_crossref_id"] = funder_registry_id

                        awards = funder_info.get("award", [])
                        if awards:
                            current_awards = [str(aw).strip() for aw in (awards if isinstance(awards, list) else [awards]) if str(aw).strip()]
                            if current_awards:
                                entry["grant_ids"] = current_awards

                        if entry.get("funder_name") or entry.get("grant_ids"): # Only add if meaningful
                            crossref_funding_entries_for_this_doi.append(entry)

                if crossref_funding_entries_for_this_doi:
                    for original_record_index in dois_to_query_map.get(retrieved_doi_clean, []):
                        # Ensure 'funding_entries' list exists on the record
                        if "funding_entries" not in records[original_record_index] or \
                           records[original_record_index]["funding_entries"] is None:
                            records[original_record_index]["funding_entries"] = []

                        # Append new CrossRef entries.
                        # More sophisticated merging/deduplication could be added here if needed.
                        # For now, append all, assuming FundingAnalyzer might consolidate later or user wants all sources.
                        for cr_entry in crossref_funding_entries_for_this_doi:
                            # Basic check to avoid adding exact same funder-grant text if already present from another source
                            # This check is very simple. True deduplication is complex.
                            is_duplicate_simple = False
                            for existing_entry in records[original_record_index]["funding_entries"]: # type: ignore
                                if existing_entry.get("funder_name") == cr_entry.get("funder_name") and \
                                   set(existing_entry.get("grant_ids", [])) == set(cr_entry.get("grant_ids",[])):
                                    is_duplicate_simple = True
                                    # Update existing entry with CrossRef Funder ID if missing
                                    if "funder_crossref_id" in cr_entry and "funder_crossref_id" not in existing_entry:
                                        existing_entry["funder_crossref_id"] = cr_entry["funder_crossref_id"]
                                    break
                            if not is_duplicate_simple:
                                records[original_record_index]["funding_entries"].append(cr_entry) # type: ignore

        except Exception as e:
            warnings.warn(f"Enrichment: Error during CrossRef API call for batch starting with DOI {doi_batch[0] if doi_batch else 'N/A'}: {type(e).__name__} - {e}", RuntimeWarning)

    print(f"Enrichment: CrossRef funding enrichment process completed.")
    return records # Return the (potentially) modified records list


if __name__ == "__main__":
    print("CrossRef Enrichment Example")
    if not HABANERO_AVAILABLE:
        print("habanero library not found. Cannot run CrossRef enrichment example.")
    else:
        sample_records = [
            {"title": "Paper with DOI", "doi": "10.1038/nature12373", "authors": ["A1", "A2"], "funding_entries": None},
            {"title": "Another Paper", "doi": "https://doi.org/10.1126/science.1172133", "authors": ["B1"], "funding_entries": [{"funder_name": "Local Grant", "grant_ids":["LG1"]}]},
            {"title": "Paper without DOI", "authors": ["C1"]},
            {"title": "Paper with bad DOI", "doi": "10.invalid/doi", "authors": ["D1"]},
        ]

        print("Original records (funding part):")
        for rec in sample_records: print(f"  Title: {rec.get('title')}, Initial Funding: {rec.get('funding_entries')}")

        enriched_records_list = enrich_records_with_crossref_funding(sample_records, mailto="sciencemappinglib_user@example.com")

        print("\nEnriched records (funding part):")
        for rec in enriched_records_list:
            print(f"  Title: {rec.get('title')}")
            print(f"    Funding Entries: {rec.get('funding_entries')}")

    print("\nCrossRef enrichment example finished.")
