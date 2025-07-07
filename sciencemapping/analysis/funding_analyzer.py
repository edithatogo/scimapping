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
    re.compile(r'\b[A-Z0-9]{2,7}[-/]\s?[A-Z0-9]{4,}\b'),  # e.g., R01-12345, CBET-123456, MR/N013488/1
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
        self.records = records
        # Use the globally loaded spaCy model and status
        self.nlp = nlp_spacy
        self.spacy_available = SPACY_AVAILABLE

    def _normalize_funder_name(self, name: str) -> str:
        """Normalizes common funder name variations."""
        if not name or not isinstance(name, str):
            return "Unknown Funder"
        stripped_name = name.strip()
        return FUNDER_NORMALIZATION_MAP.get(stripped_name.lower(), stripped_name)

    def extract_funding_data(self) -> List[Dict[str, Any]]:
        """
        Extracts and normalizes funding information from records.
        Prioritizes structured funding fields, then attempts NLP on acknowledgements.
        """
        extracted_funding_info: List[Dict[str, Any]] = []

        for i, record in enumerate(self.records):
            record_funders_structured: Set[str] = set()
            record_grants_structured: Set[str] = set()

            # 1. Process structured funding information first
            # Example: Scopus 'funding_details' (agency, text) or OpenAlex 'funders' list
            if "funding_details" in record and isinstance(record["funding_details"], dict):
                agency = record["funding_details"].get("agency")
                if agency and isinstance(agency, str):
                    record_funders_structured.add(self._normalize_funder_name(agency))

                funding_text_field = record["funding_details"].get("text")
                if funding_text_field and isinstance(funding_text_field, str):
                    for pattern in GRANT_ID_PATTERNS:
                        for match in pattern.finditer(funding_text_field):
                            grant_id = match.group(1) if len(match.groups()) > 0 else match.group(0)
                            record_grants_structured.add(grant_id.strip())

            # OpenAlex 'funders' list (example structure)
            if "funders" in record and isinstance(record["funders"], list):
                for funder_entry in record["funders"]:
                    if isinstance(funder_entry, dict):
                        funder_name = funder_entry.get("display_name") or funder_entry.get("name")
                        if funder_name and isinstance(funder_name, str):
                            record_funders_structured.add(self._normalize_funder_name(funder_name))
                        # Grant IDs might also be here in some OpenAlex structures
                        # e.g., funder_entry.get("grants") or similar

            # WoS 'FU' field (Funding Agency and Grant Number)
            if "FU" in record and isinstance(record["FU"], str):
                agencies_grants_str = record["FU"]
                # FU often "Agency Name (Grant1, Grant2); Other Agency (Grant3)"
                for part in agencies_grants_str.split(';'):
                    match = re.match(r'(.+?)\s*\((.+)\)', part.strip()) # Agency (Grants)
                    if match:
                        agency_name = self._normalize_funder_name(match.group(1))
                        record_funders_structured.add(agency_name)
                        for grant in match.group(2).split(','):
                            record_grants_structured.add(grant.strip())
                    elif part.strip(): # Just agency name
                        record_funders_structured.add(self._normalize_funder_name(part.strip()))

            # --- NLP on Acknowledgements (if available and no structured info found, or to supplement) ---
            record_funders_nlp: Set[str] = set()
            record_grants_nlp: Set[str] = set()
            acknowledgements_text = record.get("acknowledgements") or record.get("FX") # WoS FX is Funding Text

            # Only run NLP if spaCy is loaded and text is present
            if self.spacy_available and self.nlp and acknowledgements_text and isinstance(acknowledgements_text, str):
                # print(f"FundingAnalyzer: Processing acknowledgements for record {i} with spaCy.") # Debug
                doc = self.nlp(acknowledgements_text)
                for ent in doc.ents:
                    if ent.label_ == "ORG": # Organization
                        # Further filtering might be needed to distinguish funders from e.g. universities
                        # For now, add all ORGs and normalize.
                        record_funders_nlp.add(self._normalize_funder_name(ent.text))

                for pattern in GRANT_ID_PATTERNS:
                    for match in pattern.finditer(acknowledgements_text):
                        grant_id = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        record_grants_nlp.add(grant_id.strip())

            # Combine structured and NLP results (prefer structured, add NLP if new)
            final_funders = record_funders_structured.copy()
            for f_nlp in record_funders_nlp:
                # Add NLP funder only if it (or its normalized form) isn't already covered by structured data.
                # This simple check might not be perfect if structured name is an acronym and NLP got full name.
                # A more robust check would involve comparing normalized versions.
                if f_nlp not in final_funders and self._normalize_funder_name(f_nlp) not in final_funders : # Basic check
                    final_funders.add(f_nlp) # Add the NLP version (could be more specific)

            final_grants = record_grants_structured.union(record_grants_nlp)

            if final_funders or final_grants:
                extracted_funding_info.append({
                    "record_index": i,
                    "title": record.get("title", "N/A"),
                    "doi": record.get("doi"),
                    "funders": sorted(list(final_funders)),
                    "grant_ids": sorted(list(final_grants)),
                    "source_of_funding_info": "structured" if record_funders_structured or record_grants_structured else "nlp_acknowledgements"
                })

        # print(f"FundingAnalyzer: Extracted funding information for {len(extracted_funding_info)} records.") # Debug
        return extracted_funding_info

    def get_funding_summary_stats(self) -> Dict[str, Any]:
        """Calculates summary statistics about funding."""
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
            "unique_funders_identified_normalized": len(all_funders),
            "top_funders_normalized": sorted_funders[:10]
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
