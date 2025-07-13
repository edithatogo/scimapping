import rispy
from typing import List, Dict, Any

def parse_ris_file(file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """
    Parse a RIS file.

    :param file_path: The path to the RIS file.
    :param encoding: The encoding of the file.
    :return: A list of records.
    """
    with open(file_path, encoding=encoding) as ris_file:
        entries = rispy.load(ris_file)
    return entries
