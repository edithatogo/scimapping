from typing import List, Dict, Any, Optional
import warnings

# Attempt to import habanero for CrossRef API interaction
HABANERO_AVAILABLE = False
try:
    from habanero import Crossref
    HABANERO_AVAILABLE = True
    # print("Enrichment: habanero library loaded successfully.") # For debugging
except ImportError:
    warnings.warn(
        "Enrichment: 'habanero' library not found. CrossRef enrichment will be disabled. "
        "Install with 'pip install habanero'.",
        ImportWarning
    )
    Crossref = None # Placeholder if not available

# Default mailto for CrossRef polite pool
DEFAULT_CROSSREF_MAILTO = "sciencemappinglib_user@example.com" # Users should be encouraged to change this

def enrich_records_with_crossref_funding(
    records: List[Dict[str, Any]],
    mailto: Optional[str] = DEFAULT_CROSSREF_MAILTO,
    batch_size: int = 10 # Number of DOIs to query in one Crossref API call if supported by habanero
) -> List[Dict[str, Any]]:
    """
    Enriches a list of publication records with funding information from CrossRef using their DOIs.

    Args:
        records: A list of records in the common internal format. Each record should ideally have a 'doi' field.
        mailto: An email address for CrossRef's polite API pool. Highly recommended.
        batch_size: Number of DOIs to include in a single batch request to Crossref if using `works(ids=...)`.
                    (Note: habanero's `works(ids=...)` typically handles batching internally to some extent,
                     but this parameter is kept for conceptual batching or if direct requests were made).

    Returns:
        The list of records, potentially augmented with a 'crossref_funding' field.
        Each 'crossref_funding' field will contain a list of funder objects.
    """
    if not HABANERO_AVAILABLE or Crossref is None:
        warnings.warn("Enrichment: habanero library not available. Skipping CrossRef funding enrichment.", RuntimeWarning)
        return records

    if not mailto:
        warnings.warn(
            f"Enrichment: No mailto email provided for CrossRef polite pool. Using default: {DEFAULT_CROSSREF_MAILTO}. "
            "It's recommended to set a custom email via ScienceMapper or directly.",
            UserWarning
        )
        mailto = DEFAULT_CROSSREF_MAILTO

    cr = Crossref(mailto=mailto)

    enriched_records: List[Dict[str, Any]] = []
    dois_to_query: List[str] = []
    record_indices_by_doi: Dict[str, List[int]] = {} # Handle cases where multiple records might share a DOI

    for i, record in enumerate(records):
        doi = record.get("doi")
        # Clean DOI: remove "https://doi.org/" prefix if present
        if doi and isinstance(doi, str):
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]
            if doi: # Ensure DOI is not empty after stripping
                dois_to_query.append(doi)
                if doi not in record_indices_by_doi:
                    record_indices_by_doi[doi] = []
                record_indices_by_doi[doi].append(i)
        enriched_records.append(record.copy()) # Start with a copy to avoid modifying original list items directly

    if not dois_to_query:
        print("Enrichment: No DOIs found in records to query CrossRef.")
        return enriched_records

    print(f"Enrichment: Querying CrossRef for {len(set(dois_to_query))} unique DOIs...")

    # Process DOIs in batches using cr.works(ids=...)
    # habanero's works(ids=...) can take a list of DOIs.
    # It handles making multiple requests if the list is too long for a single URL.
    unique_dois = sorted(list(set(dois_to_query))) # Process unique DOIs to avoid redundant API calls

    # We can iterate through unique_dois in batches for more control or if there's an API limit
    # For simplicity, let's assume habanero handles large DOI lists well or we're passing smaller chunks.
    # A more robust implementation might chunk unique_dois if len(unique_dois) is very large.

    # For this conceptual implementation, let's process in batches as defined by batch_size
    # although habanero's .works(ids=) might do its own internal batching/multiple requests.
    for i in range(0, len(unique_dois), batch_size):
        doi_batch = unique_dois[i:i + batch_size]
        if not doi_batch:
            continue

        try:
            # The `works` method with `ids` parameter fetches multiple DOIs
            # It returns a list of responses, one for each DOI that was found.
            # Each item in the list is a dict with 'status', 'message-type', 'message-version', 'message'.
            results = cr.works(ids=doi_batch)

            for res_item in results:
                if res_item and res_item.get('status') == 'ok' and 'message' in res_item:
                    message = res_item['message']
                    retrieved_doi = message.get('DOI') # DOI in the response
                    if not retrieved_doi: # Should not happen if status is ok and DOI was queried
                        continue

                    # Normalize retrieved DOI for matching (e.g. case)
                    retrieved_doi_normalized = retrieved_doi.lower()

                    funding_data_list = []
                    if "funder" in message and isinstance(message["funder"], list):
                        for funder_info in message["funder"]:
                            funder_name = funder_info.get("name")
                            funder_doi = funder_info.get("DOI") # Funder Registry ID
                            awards = funder_info.get("award", []) # List of grant numbers/strings

                            funder_entry = {}
                            if funder_name: funder_entry["name"] = funder_name
                            if funder_doi: funder_entry["funder_doi"] = funder_doi
                            if awards: funder_entry["awards"] = awards if isinstance(awards, list) else [str(awards)]

                            if funder_entry: # Only add if there's some info
                                funding_data_list.append(funder_entry)

                    if funding_data_list:
                        # Find original record(s) by this DOI and add funding info
                        # Normalize query DOI for matching record_indices_by_doi keys
                        for original_record_index in record_indices_by_doi.get(retrieved_doi_normalized, []):
                             if original_record_index < len(enriched_records): # Boundary check
                                enriched_records[original_record_index]["crossref_funding"] = funding_data_list
                        # Also check original case DOI if normalization is an issue
                        for original_record_index in record_indices_by_doi.get(retrieved_doi, []):
                             if original_record_index < len(enriched_records) and "crossref_funding" not in enriched_records[original_record_index]:
                                enriched_records[original_record_index]["crossref_funding"] = funding_data_list
                elif res_item and res_item.get('status') != 'ok':
                    # Handle cases where a specific DOI might not be found or causes an error
                    # res_item might be {'status': 'resource-not-found', ...}
                    # For now, just print a warning or log.
                    queried_doi_for_error = res_item.get('message', {}).get('DOI', 'unknown DOI in batch') if isinstance(res_item.get('message'), dict) else 'unknown DOI in batch'
                    warnings.warn(f"Enrichment: CrossRef API issue for DOI '{queried_doi_for_error}': Status {res_item.get('status')}", RuntimeWarning)


        except Exception as e: # Catch broader errors from habanero or network issues
            warnings.warn(f"Enrichment: Error during CrossRef API call for batch {doi_batch}: {type(e).__name__} - {e}", RuntimeWarning)
            # Continue to next batch if one fails

    print(f"Enrichment: CrossRef funding enrichment process completed.")
    return enriched_records


if __name__ == "__main__":
    print("CrossRef Enrichment Example")
    if not HABANERO_AVAILABLE:
        print("habanero library not found. Cannot run CrossRef enrichment example.")
    else:
        sample_records = [
            {"title": "Paper with DOI", "doi": "10.1038/nature12373", "authors": ["A1", "A2"]}, # Valid DOI for Nature paper
            {"title": "Another Paper", "doi": "10.1126/science.1172133", "authors": ["B1"]}, # Valid DOI for Science paper
            {"title": "Paper without DOI", "authors": ["C1"]},
            {"title": "Paper with bad DOI", "doi": "10.invalid/doi", "authors": ["D1"]},
        ]

        print("Original records:")
        for rec in sample_records: print(f"  {rec.get('title')}, DOI: {rec.get('doi')}")

        # It's good practice to set your email for the polite pool
        # For real use, replace with your actual email.
        enriched_records_list = enrich_records_with_crossref_funding(sample_records, mailto="test_user@example.com")

        print("\nEnriched records:")
        for rec in enriched_records_list:
            print(f"  Title: {rec.get('title')}")
            if "crossref_funding" in rec:
                print(f"    CrossRef Funding: {rec['crossref_funding']}")
            else:
                print(f"    CrossRef Funding: Not found or DOI missing/invalid.")

    print("\nCrossRef enrichment example finished.")
