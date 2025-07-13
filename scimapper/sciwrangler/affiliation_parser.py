from typing import List, Dict, Any

def extract_affiliations(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract affiliation data from a list of records.

    :param records: A list of records.
    :return: A list of records with affiliation data.
    """
    for record in records:
        if "authors" in record and isinstance(record["authors"], list):
            for author in record["authors"]:
                if isinstance(author, dict) and "affiliation" in author:
                    if "affiliations" not in record:
                        record["affiliations"] = []
                    record["affiliations"].append(author["affiliation"])
    return records
