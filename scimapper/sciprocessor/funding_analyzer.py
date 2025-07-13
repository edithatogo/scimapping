from typing import List, Dict, Any, Optional, Set
import re
import warnings

# Attempt to import spacy and load model at module level
SPACY_AVAILABLE = False
nlp_spacy = None # Default to None

try:
    import spacy
    # Try to load a small English model. Users might need to download it via:
    # python -m spacy download en_core_web_sm
    nlp_spacy = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
    # This print is for initial feedback; might be removed or replaced by logging
    print("FundingAnalyzer: spaCy 'en_core_web_sm' model loaded successfully.")
except ImportError:
    warnings.warn(
        "FundingAnalyzer: spaCy library not found. NLP-based funding extraction from acknowledgements will be disabled. "
        "Install with 'pip install spacy'.",
        ImportWarning
    )
    spacy = None # Ensure spacy is None if the import itself failed
except OSError:
    # This error occurs if spacy is installed but the model isn't downloaded
    warnings.warn(
        "FundingAnalyzer: spaCy model 'en_core_web_sm' not found. NLP-based funding extraction from acknowledgements will be disabled. "
        "Download with 'python -m spacy download en_core_web_sm'.",
        UserWarning # Or RuntimeWarning
    )
    # nlp_spacy is already None from its initial definition if spacy.load fails

# Pre-compile some regex patterns for grant IDs for efficiency.
# These are illustrative and would need significant refinement and expansion for real-world use.
GRANT_ID_PATTERNS = [
    re.compile(r'\b[A-Z0-9]{2,7}[-/]\s?[A-Z0-9/.-]+\b'),  # e.g., R01-12345, CBET-123456, MR/N013488/1, ABC/987, W911NF-00-1
    re.compile(r'\b(?:NSF|NIH|DOE|NASA|ERC|Wellcome Trust|MRC)\s+(?:grant|award|agreement|no\.?|#|ref\.?|under\scontract)?\s*([A-Za-z0-9\-/]+)\b', re.IGNORECASE),
    re.compile(r'\b([A-Z]{1,3}\d{5,}[A-Z0-9]*)\b'),       # e.g., R01CA12345, CHE1234567
    re.compile(r'\b(DE-[A-Z0-9]{2}\d{2,}[A-Z]{2}\d{3,})\b') # e.g., DE-AC02-05CH11231 (DOE)
]

# Simple normalization map for funder names (case-insensitive keys)
FUNDER_NORMALIZATION_MAP = {
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
    # Add more common variations from real data
}

class FundingAnalyzer:
    def __init__(self, records: List[Dict[str, Any]]):
        """
        Initialize the FundingAnalyzer with a list of publication records.
        
        Parameters:
            records (List[Dict[str, Any]]): List of publication records to analyze for funding information.
        """
        self.records = records
        # Use the globally loaded spaCy model and status
        self.nlp = nlp_spacy
        self.spacy_available = SPACY_AVAILABLE

    def _normalize_funder_name(self, name: str) -> str:
        """
        Normalize a funder name using a predefined mapping of common name variants.
        
        Returns:
            str: The normalized funder name, or "Unknown Funder" if the input is invalid or empty.
        """
        if not name or not isinstance(name, str):
            return "Unknown Funder"
        stripped_name = name.strip()
        return FUNDER_NORMALIZATION_MAP.get(stripped_name.lower(), stripped_name)

    def extract_funding_data(self) -> List[Dict[str, Any]]:
        """
        Extracts and normalizes funding agency names and grant IDs from each publication record.
        
        For each record, prioritizes extraction from structured funding fields (`funding_entries`). If structured data is absent, and spaCy NLP is available, analyzes acknowledgements text fields to identify funders and grant IDs using named entity recognition and regex patterns. Normalizes funder names and tracks the source of extracted information.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing the record index, title, DOI, sorted lists of normalized funders and grant IDs, and the source of the funding information.
        """
        extracted_funding_info: List[Dict[str, Any]] = []

        for i, record in enumerate(self.records):
            processed_record_funders: Set[str] = set()
            processed_record_grants: Set[str] = set()
            source_info_type = "unknown" # To track origin

            # 1. Prioritize the standardized `funding_entries` field populated by parsers
            if "funding_entries" in record and isinstance(record["funding_entries"], list):
                for entry in record["funding_entries"]:
                    if isinstance(entry, dict):
                        funder_name = entry.get("funder_name")
                        if funder_name and isinstance(funder_name, str):
                            processed_record_funders.add(self._normalize_funder_name(funder_name))

                        grant_ids = entry.get("grant_ids")
                        if isinstance(grant_ids, list):
                            for gid in grant_ids:
                                if isinstance(gid, str):
                                    processed_record_grants.add(gid.strip())
                        # We can also store entry["source_of_info"] if needed for more granular tracking
                if processed_record_funders or processed_record_grants:
                    source_info_type = "structured_from_parser" # Or derive from entry["source_of_info"]

            if "funding_details" in record and isinstance(record["funding_details"], dict):
                funding_details = record["funding_details"]
                if "agency" in funding_details:
                    processed_record_funders.add(self._normalize_funder_name(funding_details["agency"]))
                if "text" in funding_details:
                    for pattern in GRANT_ID_PATTERNS:
                        for match in pattern.finditer(funding_details["text"]):
                            grant_id = match.group(1) if len(match.groups()) > 0 else match.group(0)
                            processed_record_grants.add(grant_id.strip())

            if "funders" in record and isinstance(record["funders"], list):
                for funder in record["funders"]:
                    if isinstance(funder, dict) and "display_name" in funder:
                        processed_record_funders.add(self._normalize_funder_name(funder["display_name"]))
                    elif isinstance(funder, dict) and "name" in funder:
                        processed_record_funders.add(self._normalize_funder_name(funder["name"]))

            if "FU" in record and isinstance(record["FU"], str):
                funders = record["FU"].split(';')
                for funder in funders:
                    # This is a simplified parsing logic. A more robust implementation would be needed for real-world data.
                    match = re.search(r'^(.*)\s*\((.*)\)\s*\((.*)\)$', funder.strip())
                    if match:
                        funder_name = match.group(1).strip()
                        processed_record_funders.add(self._normalize_funder_name(funder_name))
                        grants = match.group(3).split(', ')
                        for grant in grants:
                            processed_record_grants.add(grant.strip())
                    else:
                        processed_record_funders.add(self._normalize_funder_name(funder.strip()))

            # 2. Fallback or Supplement with NLP on acknowledgements text
            # Only run NLP if spaCy is available AND (no structured funding found OR we want to supplement)
            # For now, let's run if no structured info was found from funding_entries, or if specific ack text exists

            acknowledgements_text = record.get("acknowledgements_text") or \
                                    record.get("acknowledgements_text_fx") or \
                                    record.get("acknowledgements_text_scopus_funding") or \
                                    record.get("acknowledgements") # General fallback

            run_nlp = self.spacy_available and self.nlp and \
                        acknowledgements_text and isinstance(acknowledgements_text, str)

            if run_nlp:
                # print(f"FundingAnalyzer: Processing acknowledgements for record {i} with spaCy.") # Debug
                doc = self.nlp(acknowledgements_text) # type: ignore # self.nlp is checked by self.spacy_available
                nlp_funders: Set[str] = set()
                nlp_grants: Set[str] = set()

                for ent in doc.ents:
                    if ent.label_ == "ORG":
                        nlp_funders.add(self._normalize_funder_name(ent.text))

                for pattern in GRANT_ID_PATTERNS:
                    for match in pattern.finditer(acknowledgements_text): # type: ignore
                        grant_id = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        nlp_grants.add(grant_id.strip())

                if nlp_funders or nlp_grants:
                    processed_record_funders.update(nlp_funders) # Merge NLP results
                    processed_record_grants.update(nlp_grants)
                    source_info_type = "nlp_acknowledgements" if source_info_type == "unknown" else f"{source_info_type}_nlp_supplemented"
            elif acknowledgements_text and isinstance(acknowledgements_text, str):
                # Fallback to regex if spacy is not available
                for pattern in GRANT_ID_PATTERNS:
                    for match in pattern.finditer(acknowledgements_text):
                        grant_id = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        processed_record_grants.add(grant_id.strip())

            if processed_record_funders or processed_record_grants:
                extracted_funding_info.append({
                    "record_index": i,
                    "title": record.get("title", "N/A"),
                    "doi": record.get("doi"),
                    "funders": sorted(list(processed_record_funders)),
                    "grant_ids": sorted(list(processed_record_grants)),
                    "source_of_funding_info": source_info_type
                })

        return extracted_funding_info

    def get_funding_summary_stats(self) -> Dict[str, Any]:
        """
        Compute and return summary statistics on funding information extracted from the records.
        
        Returns:
            A dictionary containing the total number of records analyzed, the number of records with any funding information, the count of unique normalized funders, and the top 10 most frequent normalized funders with their respective counts.
        """
        funding_data = self.extract_funding_data()

        total_records_with_funding = len(funding_data)
        all_funders: Dict[str, int] = {}

        for item in funding_data:
            for funder in item["funders"]:
                # Normalize here again to ensure counts are aggregated correctly
                normalized_funder = self._normalize_funder_name(funder)
                all_funders[normalized_funder] = all_funders.get(normalized_funder, 0) + 1

        sorted_funders = sorted(all_funders.items(), key=lambda x: x[1], reverse=True)

        # print("FundingAnalyzer: Calculated funding summary stats.") # Debug
        return {
            "total_records_analyzed": len(self.records),
            "records_with_any_funding_info": total_records_with_funding,
            "unique_funders_identified": len(all_funders),
            "unique_funders_identified_normalized": len(all_funders),
            "top_funders_normalized": sorted_funders[:10],
            "top_funders": sorted_funders[:10]
        }

if __name__ == "__main__":
    # Sample records for testing
    sample_records_for_funding_test = [
        { # 0: Structured (funding_details with text for regex)
            "title": "Paper X", "doi": "10.x/1",
            "funding_details": {"agency": "National Science Foundation", "text": "Supported by NSF grant CBET-123 and ARO award W911NF-00-1."}
        },
        { # 1: Structured (OpenAlex-style list), and Acknowledgements for NLP
            "title": "Paper Y", "doi": "10.y/2",
            "funders": [{"display_name": "Wellcome Trust"}, {"name": "ERC"}],
            "acknowledgements": "This work was also supported by NIH (grant R01-XYZ) and The Bill & Melinda Gates Foundation. We thank Acme University."
        },
        { # 2: Structured (WoS FU style)
            "title": "Paper Z", "doi": "10.z/3",
            "FU": "National Science Foundation (NSF) (ANT-0123, OPP-456); European Research Council (ERC) (AdG-789)"
        },
        { # 3: Unfunded
            "title": "Paper Unfunded", "doi": "10.u/4"
        },
        { # 4: Only acknowledgements text with grant ID and funder name
            "title": "Paper AckOnly", "doi": "10.a/5",
            "acknowledgements": "We thank the Medical Research Council for grant MR/N012345/1. Support from ExampleOrg."
        },
         { # 5: Plain text funding in FU (no grant ID pattern)
            "title": "Paper FU Plain", "doi": "10.fp/6",
            "FU": "Max Planck Society"
        }
    ]

    print("FundingAnalyzer Example Run (requires spaCy and 'en_core_web_sm' model for NLP parts)")
    if not SPACY_AVAILABLE or not nlp_spacy:
        print("WARNING: spaCy or its 'en_core_web_sm' model is not available. NLP processing in this example will be skipped.")

    analyzer = FundingAnalyzer(sample_records_for_funding_test)

    print("\n--- Extracted Funding Data ---")
    extracted = analyzer.extract_funding_data()
    for item in extracted:
        print(f"  Title: {item['title']}")
        print(f"    Funders: {item['funders']}")
        print(f"    Grants: {item['grant_ids']}")
        print(f"    Source: {item['source_of_funding_info']}")


    print("\n--- Funding Summary Stats ---")
    stats = analyzer.get_funding_summary_stats()
    print(f"  Total records analyzed: {stats['total_records_analyzed']}")
    print(f"  Records with funding info: {stats['records_with_any_funding_info']}")
    print(f"  Unique funders (normalized): {stats['unique_funders_identified_normalized']}")
    print(f"  Top funders (normalized):")
    for funder, count in stats['top_funders_normalized']:
        print(f"    - {funder}: {count}")
