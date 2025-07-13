from typing import List, Dict, Any

def parse_author_names(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse author names into first and last names.

    :param records: A list of records.
    :return: A list of records with parsed author names.
    """
    for record in records:
        if "authors" in record and isinstance(record["authors"], list):
            new_authors = []
            for author in record["authors"]:
                if isinstance(author, str):
                    parts = author.split(", ")
                    if len(parts) == 2:
                        new_authors.append({"lastname": parts[0], "firstname": parts[1]})
                    else:
                        new_authors.append(author)
                else:
                    new_authors.append(author)
            record["authors"] = new_authors
    return records
