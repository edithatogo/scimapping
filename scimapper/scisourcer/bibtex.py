import bibtexparser
from typing import List, Dict, Any

def parse_bibtex_file(file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """
    Parse a BibTeX file.

    :param file_path: The path to the BibTeX file.
    :param encoding: The encoding of the file.
    :return: A list of records.
    """
    with open(file_path, encoding=encoding) as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    return bib_database.entries
