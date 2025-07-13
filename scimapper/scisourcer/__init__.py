# __init__.py for the data_sources subpackage

# Import the main function from each data source module
from .pubmed import search_pubmed, _parse_pubmed_article
from .scopus import search_scopus, fetch_scopus_abstract_details
from .wos import parse_wos_file
from .dimensions import search_dimensions_api
from .openalex import search_openalex_works
from .unpaywall import search_unpaywall
