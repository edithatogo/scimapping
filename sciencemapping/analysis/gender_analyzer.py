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
    def __init__(self,
                 records: List[Dict[str, Any]],
                 name_field: str = "authors",
                 custom_gender_map: Optional[Dict[str, str]] = None
                 ):
        self.records = records
        self.name_field = name_field
        self.custom_gender_map = custom_gender_map if custom_gender_map else {}
        # Normalize keys in custom_gender_map for easier lookup (e.g., lowercase)
        # For now, assume keys are used as provided, but matching might need to be case-insensitive.
        # Let's make the lookup case-insensitive for first names, and keep full names as is for now.
        self.normalized_custom_gender_map_first_names: Dict[str, str] = {}
        if self.custom_gender_map:
            for name_key, gender_val in self.custom_gender_map.items():
                # If key looks like a first name (single word), store its lowercase version
                if ' ' not in name_key and ',' not in name_key:
                    self.normalized_custom_gender_map_first_names[name_key.lower()] = gender_val.lower()
                # Full names will be checked as is (case-sensitive for now, or could normalize them too)


        self.gender_detector = None
        if GENDER_GUESSER_AVAILABLE and gender_detector_module:
            try:
                self.gender_detector = gender_detector_module.Detector(case_sensitive=False)
                print("GenderAnalyzer: gender_guesser.Detector initialized.")
            except Exception as e:
                warnings.warn(f"GenderAnalyzer: Failed to initialize gender_guesser.Detector - {e}. Will use placeholder.", RuntimeWarning)
                self.gender_detector = None
        else:
            print("GenderAnalyzer: gender_guesser not available. Using placeholder for gender inference.")

    def _get_first_name(self, full_name: str) -> Optional[str]:
        """Extracts a potential first name from a full name string."""
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
        Adds inferred gender to author records. This is a placeholder.
        A real implementation would use a library like gender-guesser.
        This method MODIFIES the records in-place or returns new ones.
        For now, let's return a new list of authors with gender.
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
                inferred_gender = "unknown"
                gender_source = "unknown"

                # 1. Check custom map using full name first (case-sensitive for full names for now)
                if author_name_full in self.custom_gender_map:
                    inferred_gender = self.custom_gender_map[author_name_full]
                    gender_source = "custom_map_full_name"

                # 2. If not found by full name, check custom map using extracted first name (case-insensitive)
                elif first_name and first_name.lower() in self.normalized_custom_gender_map_first_names:
                    inferred_gender = self.normalized_custom_gender_map_first_names[first_name.lower()]
                    gender_source = "custom_map_first_name"

                # 3. If not in custom map, use gender_guesser if available
                elif first_name and self.gender_detector:
                    try:
                        raw_gender = self.gender_detector.get_gender(first_name)
                        inferred_gender = raw_gender
                        gender_source = "gender_guesser"
                    except Exception as e:
                        warnings.warn(f"GenderAnalyzer: Error calling gender_guesser for name '{first_name}': {e}", RuntimeWarning)
                        inferred_gender = 'error_in_guessing'
                        gender_source = "gender_guesser_error"

                # 4. Fallback to placeholder if still unknown and first_name exists
                elif first_name:
                    if first_name.lower().startswith(('a','i','e','u')) and len(first_name) > 3 :
                         inferred_gender = 'female (placeholder)'
                    elif len(first_name) > 0 :
                         inferred_gender = 'male (placeholder)'
                    gender_source = "placeholder"

                authors_with_gender.append({
                    "name": author_name_full,
                    "first_name_used_for_guess": first_name,
                    "inferred_gender": inferred_gender,
                    "gender_source": gender_source
                })
                processed_authors.add(author_name_full)

        # Adjust log message slightly if needed, or keep as is.
        # The method_used can now be more complex (custom, gender_guesser, placeholder)
        # For simplicity, the existing log is okay, or could be removed if too noisy.
        # print(f"GenderAnalyzer: Processed {len(processed_authors)} unique author names for gender inference.")
        return authors_with_gender

    def get_gender_distribution_stats(self) -> Dict[str, Any]:
        """
        Calculates statistics on gender distribution. Placeholder.
        This would typically run *after* infer_author_genders has augmented data
        or by calling it internally.
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
