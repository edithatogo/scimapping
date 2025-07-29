from typing import List, Dict, Any, Optional
import metaknowledge
import re # Moved import re to the top

def parse_wos_file(file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """
    Parses a Web of Science export file (e.g., plain text, BibTeX) using metaknowledge.
    WoS plain text files usually contain field tags like TI, AU, SO, PY, AB, DE, CR etc.

    Args:
        file_path: The path to the Web of Science export file.
        encoding: The encoding of the file. Defaults to 'utf-8'.

    Returns:
        A list of dictionaries, where each dictionary represents a record
        parsed into a common internal format.
    """
    records_data: List[Dict[str, Any]] = []
    try:
        # metaknowledge.RecordCollection can take a file path string directly
        rc = metaknowledge.RecordCollection(file_path, encoding=encoding)

        for record in rc:
            # `record` is a metaknowledge.Record object
            # We need to parse its fields into our common format.
            # Metaknowledge Record objects behave somewhat like dictionaries for field access.
            # Field names in metaknowledge are typically the WoS tags (e.g., 'TI', 'AU', 'PY').
            parsed_record = _parse_wos_record(record)
            if parsed_record: # Only add if parsing was successful / record is valid
                records_data.append(parsed_record)

    except FileNotFoundError:
        print(f"Error: Web of Science file not found at {file_path}")
    except UnicodeDecodeError:
        print(f"Error: Could not decode Web of Science file at {file_path} with encoding '{encoding}'. Try a different encoding (e.g., 'latin-1').")
    except Exception as e:
        print(f"An unexpected error occurred while parsing Web of Science file {file_path}: {e}")
        # Depending on the error from metaknowledge for malformed files, more specific error handling might be needed.
        # metaknowledge might raise its own specific exceptions for parsing issues.

    return records_data

def _parse_wos_record(record: metaknowledge.Record) -> Optional[Dict[str, Any]]:
    """
    Parses a single metaknowledge.Record object into our common internal format.

    Args:
        record: A metaknowledge.Record object.

    Returns:
        A dictionary representing the record in the common internal format,
        or None if the record is minimal or cannot be parsed.
    """
    if not record:
        return None

    # WoS field tags and their typical meanings:
    # PT: Publication Type (e.g., J for Journal, C for Conference)
    # AU: Authors (e.g., Smith, J; Doe, A)
    # TI: Title
    # SO: Source (Journal Name)
    # DT: Document Type (e.g., Article, Review, Conference Proceeding)
    # DE: Author Keywords (semicolon separated)
    # ID: Keywords Plus (semicolon separated)
    # AB: Abstract
    # C1: Author Addresses ([Author1Name] Address1; [Author2Name] Address2)
    # RP: Reprint Address
    # CR: Cited References (each reference on a new line)
    # TC: Times Cited (WoS Core Collection)
    # PY: Year Published
    # VL: Volume
    # IS: Issue
    # BP: Beginning Page
    # EP: Ending Page
    # DI: DOI (Digital Object Identifier)
    # UT: Unique Article Identifier (WoS accession number, e.g., WOS:00012345678900001)

    title = record.get('TI', None)
    if not title: # If there's no title, it's probably not a useful record
        return None

    authors_str = record.get('AU', []) # metaknowledge often returns lists for authors
    authors_list = []
    if isinstance(authors_str, list):
        authors_list = [str(author) for author in authors_str]
    elif isinstance(authors_str, str): # Should not happen with current metaknowledge but good fallback
        authors_list = [name.strip() for name in authors_str.split(';')]


    year_str = record.get('PY', None)
    year = None
    if year_str and isinstance(year_str, str) and year_str.isdigit():
        year = int(year_str)
    elif isinstance(year_str, int): # Sometimes metaknowledge might parse it as int
        year = year_str

    keywords_de = record.get('DE', "") # Author Keywords
    keywords_id = record.get('ID', "") # Keywords Plus

    all_keywords = []
    if isinstance(keywords_de, str) and keywords_de:
        all_keywords.extend([k.strip() for k in keywords_de.split(';') if k.strip()])
    elif isinstance(keywords_de, list): # If metaknowledge parses it as a list
        all_keywords.extend([str(k).strip() for k in keywords_de if str(k).strip()])

    if isinstance(keywords_id, str) and keywords_id:
        all_keywords.extend([k.strip() for k in keywords_id.split(';') if k.strip()])
    elif isinstance(keywords_id, list):
        all_keywords.extend([str(k).strip() for k in keywords_id if str(k).strip()])

    # Normalize keywords: lowercase, strip, get unique, then sort.
    processed_keywords = []
    if all_keywords:
        normalized_keywords = [kw.lower().strip() for kw in all_keywords]
        # Filter out any potential empty strings that might result from splitting, etc.
        processed_keywords = sorted(list(set(
            kw for kw in normalized_keywords if kw
        )))

    # Document type: PT (Publication Type) is often just 'J' or 'C'. DT (Document Type) is more descriptive.
    doc_type = record.get('DT', None)
    if not doc_type:
        doc_type = record.get('PT', None) # Fallback to PT if DT is missing

    # WoS ID (Accession Number)
    wos_id = record.get('UT', None)
    if wos_id and isinstance(wos_id, str) and wos_id.startswith("WOS:"):
        wos_id = wos_id[4:] # Remove "WOS:" prefix

    parsed = {
        "title": title,
        "authors": authors_list,
        "journal": record.get('SO', None), # Source
        "year": year,
        "doi": record.get('DI', None),
        "wos_id": wos_id,
        "abstract": record.get('AB', None),
        "keywords": processed_keywords,
        "document_type": doc_type,
        "source_type": "wos",
        "times_cited_wos": record.get('TC', None), # WoS specific citation count
        # If record is a mock with _test_get_raw_dict, use it, else use dict(record)
        "raw_data": record._test_get_raw_dict() if hasattr(record, '_test_get_raw_dict') and callable(record._test_get_raw_dict) else dict(record)
    }

    # Funding Information from WoS FU (Funding Agency and Grant Number) and FX (Funding Text)
    funding_entries: List[Dict[str, Any]] = []

    # Process FU first as it's more structured
    fu_data = record.get('FU') # This might be a string or a list from metaknowledge
    if isinstance(fu_data, str) and fu_data:
        fu_list = fu_data.split(';') # FU can contain multiple funding entries separated by semicolon
    elif isinstance(fu_data, list):
        fu_list = fu_data # If metaknowledge already parsed it into a list of strings
    else:
        fu_list = []

    if fu_list:
        for fu_item_str in fu_list:
            fu_item_str = str(fu_item_str).strip() # Ensure it's a string and stripped
            if not fu_item_str: continue

            entry: Dict[str, Any] = {"source_of_info": "wos_FU_field", "raw_funding_text": fu_item_str}
            grant_ids_for_entry = []

            grant_ids_for_entry = []
            funder_name_str = fu_item_str # Default to whole string as funder name

            # Try to find grants first, usually in the last parentheses
            # e.g., "Agency Name (Grant1; Grant2)" or "Agency (Acronym) (Grant A)"
            grants_part_match = re.search(r'\(([^()]*)\)$', fu_item_str)

            if grants_part_match:
                grants_content = grants_part_match.group(1)
                # The part before this match is the funder name (potentially with acronym)
                funder_name_str = fu_item_str[:grants_part_match.start()].strip()

                # Split grants by comma, 'and', or semicolon
                grant_ids_for_entry.extend([g.strip() for g in re.split(r'[;,]\s*|and\s+', grants_content) if g.strip()])
            else:
                # No clear grant part in parentheses at the end, assume whole string is funder name
                # (already set by funder_name_str = fu_item_str)
                pass # funder_name_str is already fu_item_str

            # Always set funder_name based on funder_name_str, even if it's an empty string.
            entry["funder_name"] = funder_name_str.strip()

            if grant_ids_for_entry:
                entry["grant_ids"] = grant_ids_for_entry

            # Only add entry if we have a funder name or grant IDs
            # If funder_name_str (which defaults to fu_item_str) or grant_ids were populated, add the entry.
            # Since fu_item_str is guaranteed non-empty here, funder_name_str will be non-empty.
            # So, entry["funder_name"] will always be set.
            if entry.get("funder_name") or entry.get("grant_ids"): # This condition will likely always be true if fu_item_str is not empty
                 funding_entries.append(entry)
            # The elif block that created "wos_FU_field_as_funder_name" is removed.
            # If fu_item_str is non-empty, entry["funder_name"] will be set to it by default,
            # and the above if condition will pass.


    # Store FX (Funding Text) if available. This is typically free text acknowledgements.
    # We will store this in a dedicated field, e.g., 'acknowledgements_text_fx'
    # The FundingAnalyzer can then choose to process it.
    fx_data = record.get('FX')
    if isinstance(fx_data, str) and fx_data:
        parsed['acknowledgements_text_fx'] = fx_data # Add FX directly to parsed output
        # If no structured FU data was found, FX might be the only clue.
        if not funding_entries:
            funding_entries.append({
                "raw_funding_text": fx_data,
                "source_of_info": "wos_FX_field_as_primary"
            })


    if funding_entries:
        parsed["funding_entries"] = funding_entries
    else:
        parsed["funding_entries"] = None

    # Cited References (CR tag from WoS)
    # Each item in record.get('CR', []) is a string like "Author, Year, Journal, V, P, DOI"
    # We want to extract DOIs if possible, then WoS IDs as fallback.
    cited_references_list: List[str] = []
    raw_cited_refs = record.get('CR', [])
    if isinstance(raw_cited_refs, list):
        for ref_str_raw in raw_cited_refs:
            ref_str = str(ref_str_raw).strip()
            if not ref_str: continue

            identifier_found_for_this_ref = False

            # 1. Prioritize DOI
            # Regex to find DOIs: matches "10." followed by numbers/letters/.-_();:/
            doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b', ref_str, re.IGNORECASE)
            if doi_match:
                doi = doi_match.group(1).strip().rstrip('.') # Cleaned DOI
                if doi: # Ensure not empty after stripping
                    cited_references_list.append(doi)
                    identifier_found_for_this_ref = True

            # 2. If no DOI, try to find WoS Accession Number (UT)
            if not identifier_found_for_this_ref:
                # Pattern for WoS ID like WOS:000293277400008 or WOS:A1993LA09000001
                # Making it slightly more general for the alphanumeric part's length.
                wos_id_match = re.search(r'\b(WOS:[0-9A-Za-z]{10,25})\b', ref_str)
                if wos_id_match:
                    cited_references_list.append(wos_id_match.group(1).strip())
                    identifier_found_for_this_ref = True

            # Not storing raw reference string if no ID found, to keep the list clean with identifiers.

    if cited_references_list:
        parsed["cited_references"] = sorted(list(set(cited_references_list)))
    else:
        parsed["cited_references"] = None

    return parsed


if __name__ == "__main__":
    # To test this, you would need a Web of Science export file.
    # Create a dummy file named "sample_wos.txt" in the same directory for a quick test.
    # Example content for "sample_wos.txt":
    """
PT J
AU Smith, John; Doe, Jane A.
TI A Study on Bibliometrics and Science Mapping
SO Journal of Fake Research
PY 2023
AB This is an abstract of the study. It covers various aspects of bibliometrics.
DE bibliometrics; science mapping; research trends
ID citation analysis; co-authorship networks
DI 10.1234/jfr.2023.001
UT WOS:000fakeid000001
TC 15
DT Article
    """
    # You would normally run this from the project root or ensure paths are correct.
    # For this example, assume "sample_wos.txt" is in the same dir as wos.py

    sample_file_content = """PT J
AU Smith, John; Doe, Jane A.
TI A Study on Bibliometrics and Science Mapping
SO Journal of Fake Research
PY 2023
AB This is an abstract of the study. It covers various aspects of bibliometrics.
DE bibliometrics; science mapping; research trends
ID citation analysis; co-authorship networks
DI 10.1234/jfr.2023.001
UT WOS:000fakeid000001
TC 15
DT Article
ER

PT C
AU Turing, Alan M.
TI On Computable Numbers, with an Application to the Entscheidungsproblem
SO Proceedings of the London Mathematical Society
PY 1937
AB An abstract about computable numbers.
DE turing machines; computability; logic
DI 10.1112/plms/s2-42.1.230
UT WOS:000anotherid002
TC 1200
DT Conference Paper
ER
"""
    sample_wos_file = "sample_wos_test_file.txt"
    with open(sample_wos_file, "w", encoding="utf-8") as f:
        f.write(sample_file_content)

    print(f"Attempting to parse WoS file: {sample_wos_file}")
    parsed_articles = parse_wos_file(sample_wos_file)

    if parsed_articles:
        print(f"\nSuccessfully parsed {len(parsed_articles)} articles from WoS file:")
        for i, article in enumerate(parsed_articles):
            print(f"\n--- Article {i+1} (from WoS) ---")
            print(f"  Title: {article.get('title')}")
            print(f"  Authors: {'; '.join(article.get('authors', []))}")
            print(f"  Journal: {article.get('journal')}")
            print(f"  Year: {article.get('year')}")
            print(f"  DOI: {article.get('doi')}")
            print(f"  WoS ID: {article.get('wos_id')}")
            print(f"  Abstract: {str(article.get('abstract', ''))[:60]}...")
            print(f"  Keywords: {article.get('keywords')}")
            print(f"  Document Type: {article.get('document_type')}")
            print(f"  Times Cited (WoS): {article.get('times_cited_wos')}")
    else:
        print("No articles parsed or an error occurred.")

    # Clean up the dummy file
    import os
    try:
        os.remove(sample_wos_file)
        print(f"\nCleaned up {sample_wos_file}")
    except OSError as e:
        print(f"Error removing {sample_wos_file}: {e}")

    print("\nWoS parsing example finished.")
