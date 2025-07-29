from typing import List, Dict, Any, Optional, Tuple
import warnings

# Attempt to import gender_guesser
GENDER_GUESSER_AVAILABLE = False
gender_detector_module = None
try:
    import gender_guesser.detector
    gender_detector_module = gender_guesser.detector
    GENDER_GUESSER_AVAILABLE = True
    print("GenderAnalyzer: gender_guesser library loaded successfully.")
except ImportError:
    warnings.warn(
        "GenderAnalyzer: 'gender-guesser' library not found. Gender inference will use basic placeholder logic. "
        "Install with 'pip install gender-guesser'.",
        ImportWarning
    )

class GenderAnalyzer:
    def __init__(self, records: List[Dict[str, Any]], name_field: str = "authors"):
        """
        Initialize the GenderAnalyzer with a list of records and the field name containing author names.
        
        If the `gender-guesser` library is available, attempts to initialize its Detector for gender inference; otherwise, uses a placeholder heuristic.
        """
        self.records = records
        self.name_field = name_field # Field containing author names
        self.gender_detector = None
        if GENDER_GUESSER_AVAILABLE and gender_detector_module:
            try:
                # Initialize with case_sensitive=False for broader matching
                self.gender_detector = gender_detector_module.Detector(case_sensitive=False)
                print("GenderAnalyzer: gender_guesser.Detector initialized.")
            except Exception as e:
                warnings.warn(f"GenderAnalyzer: Failed to initialize gender_guesser.Detector - {e}. Will use placeholder.", RuntimeWarning)
                self.gender_detector = None # Ensure it's None on failure
        else:
            print("GenderAnalyzer: gender_guesser not available. Using placeholder for gender inference.")


    def _get_first_name(self, full_name: str) -> Optional[str]:
        """
        Extracts the probable first name from a full name string.
        
        Handles names formatted as "Last, First M." or "First M. Last" by splitting on commas and spaces. Returns the first word of the relevant name part, or None if the input is invalid.
        """
        if not full_name or not isinstance(full_name, str):
            return None

        parts = full_name.split(',')
        if len(parts) > 1: # "Last, First M."
            name_part = parts[1].strip()
        else: # "First M. Last" or "First Last"
            name_part = parts[0].strip()

        # Get the first word of the name_part
        first_name = name_part.split(' ')[0]
        # Clean up any trailing initials or non-alpha chars if needed here.
        # For simplicity, just returning the first word.
        return first_name if first_name else None

    def infer_author_genders(self) -> List[Dict[str, Any]]:
        """
        Infers the gender of each unique author in the records using either the `gender-guesser` library or a placeholder heuristic.
        
        For each unique author name, extracts the first name and attempts to determine gender. If `gender-guesser` is available, uses its detector; otherwise, applies a simple heuristic based on the first letter and length of the first name. Returns a list of dictionaries containing the original author name, the first name used for inference, and the inferred gender.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each with keys `"name"`, `"first_name_used_for_guess"`, and `"inferred_gender"`.
        """
        authors_with_gender: List[Dict[str, Any]] = []
        processed_authors = set() # To avoid re-processing same author name

        for record in self.records:
            authors_in_record = record.get(self.name_field, [])
            if not isinstance(authors_in_record, list):
                continue

            for author_name_full in authors_in_record:
                if not isinstance(author_name_full, str) or author_name_full in processed_authors:
                    continue

                first_name = self._get_first_name(author_name_full)
                inferred_gender = "unknown" # Default

                if first_name and self.gender_detector: # Use gender_guesser if available
                    try:
                        # gender-guesser returns: female, mostly_female, male, mostly_male, andy, unknown
                        raw_gender = self.gender_detector.get_gender(first_name)
                        inferred_gender = raw_gender
                        # Optional: map to simpler categories if desired
                        # if raw_gender in ['female', 'mostly_female']: inferred_gender = 'female'
                        # elif raw_gender in ['male', 'mostly_male']: inferred_gender = 'male'
                        # elif raw_gender == 'andy': inferred_gender = 'androgynous'
                        # else: inferred_gender = 'unknown' # Covers 'unknown', 'name_not_found'
                    except Exception as e:
                        warnings.warn(f"GenderAnalyzer: Error calling gender_guesser for name '{first_name}': {e}", RuntimeWarning)
                        inferred_gender = 'error_in_guessing'
                elif first_name: # Fallback to placeholder if gender_detector is not available
                    if first_name.lower().startswith(('a','i','e','u')) and len(first_name) > 3 :
                         inferred_gender = 'female (placeholder)'
                    elif len(first_name) > 0 : # Ensure first_name is not empty
                         inferred_gender = 'male (placeholder)'

                authors_with_gender.append({
                    "name": author_name_full,
                    "first_name_used_for_guess": first_name,
                    "inferred_gender": inferred_gender
                })
                processed_authors.add(author_name_full)

        log_message = "GenderAnalyzer: Processed {num_authors} unique author names for gender inference ({method} logic)."
        method_used = "gender_guesser" if self.gender_detector else "placeholder"
        print(log_message.format(num_authors=len(processed_authors), method=method_used))
        return authors_with_gender

    def get_gender_distribution_stats(self) -> Dict[str, Any]:
        """
        Compute and return statistics on the inferred gender distribution among authors.
        
        Returns:
            stats (Dict[str, Any]): A dictionary containing the total number of authors processed and the count of each inferred gender category.
        """
        # For this example, let's assume infer_author_genders is called implicitly
        # or the records passed to __init__ are already augmented.
        # Here, we'll call it:
        authors_gender_data = self.infer_author_genders()

        stats: Dict[str, int] = {"total_authors_processed": len(authors_gender_data)}
        for author_info in authors_gender_data:
            gender = author_info["inferred_gender"]
            stats[gender] = stats.get(gender, 0) + 1

        print("GenderAnalyzer: Calculated gender distribution stats (placeholder logic).")
        return stats

if __name__ == "__main__":
    sample_recs = [
        {"authors": ["Doe, Jane A.", "Smith, John B.", "Lee, Chris"]},
        {"authors": ["Alex, Jordan", "Taylor, P."]},
        {"authors": ["Unknown"]}, # Single name
        {"authors": ["Multiple First Names, Author"]}, # Different format
    ]
    analyzer = GenderAnalyzer(sample_recs)

    print("\n--- Inferred Genders (Placeholder) ---")
    inferred = analyzer.infer_author_genders()
    for item in inferred[:5]: # Print first 5
        print(f"  Name: {item['name']}, First Name Used: {item['first_name_used_for_guess']}, Gender: {item['inferred_gender']}")

    print("\n--- Gender Distribution (Placeholder) ---")
    dist = analyzer.get_gender_distribution_stats()
    for gender, count in dist.items():
        print(f"  {gender}: {count}")
