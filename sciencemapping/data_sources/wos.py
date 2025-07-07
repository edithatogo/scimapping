from typing import List, Dict, Any, Optional
import metaknowledge

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

    # Remove duplicates while preserving order (if important, otherwise set is fine)
    seen_keywords = set()
    unique_keywords = []
    for kw in all_keywords:
        if kw.lower() not in seen_keywords: # Case-insensitive check for uniqueness
            seen_keywords.add(kw.lower())
            unique_keywords.append(kw)

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
        "keywords": unique_keywords,
        "document_type": doc_type,
        "source_type": "wos",
        "times_cited_wos": record.get('TC', None), # WoS specific citation count
        # If record is a mock with _test_get_raw_dict, use it, else use dict(record)
        "raw_data": record._test_get_raw_dict() if hasattr(record, '_test_get_raw_dict') and callable(record._test_get_raw_dict) else dict(record)
    }
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
