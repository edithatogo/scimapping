import unittest
from unittest.mock import patch, MagicMock
import warnings

from sciencemapping.analysis.gender_analyzer import GenderAnalyzer
# Import GENDER_GUESSER_AVAILABLE to check its actual value in one test
from sciencemapping.analysis.gender_analyzer import GENDER_GUESSER_AVAILABLE as ACTUAL_GG_MODULE_STATE_AVAILABLE

SAMPLE_RECORDS_FOR_GENDER = [
    {"authors": ["Doe, Jane A.", "Smith, John B.", "Lee, Chris"]},
    {"authors": ["Alex, Jordan", "Taylor, P."]},
    {"authors": ["Unknown"]},
    {"authors": ["Multiple First Names, Author"]},
    {"authors": ["김, 민준"]},
    {"authors": ["O'Malley, Patrick"]},
    {"authors": ["McArthur, Douglas"]},
    {"authors": ["De La Cruz, Maria"]},
    {"authors": ["Solo Author"]},
    {"authors": []},
    {"title": "Paper with no authors field"},
    {"authors": ["Smith, John B.", "Smith, John B."]}
]

class TestGenderAnalyzer(unittest.TestCase):

    def test_get_first_name(self):
        analyzer = GenderAnalyzer([]) # No records needed, custom_map is None by default
        self.assertEqual(analyzer._get_first_name("Doe, Jane A."), "Jane")
        self.assertEqual(analyzer._get_first_name("Smith, John B."), "John")
        self.assertEqual(analyzer._get_first_name("Lee, Chris"), "Chris")
        self.assertEqual(analyzer._get_first_name("Alex, Jordan"), "Jordan")
        self.assertEqual(analyzer._get_first_name("Taylor, P."), "P.")
        self.assertEqual(analyzer._get_first_name("Unknown"), "Unknown")
        self.assertEqual(analyzer._get_first_name("Multiple First Names, Author"), "Author")
        self.assertEqual(analyzer._get_first_name("김, 민준"), "민준")
        self.assertEqual(analyzer._get_first_name("O'Malley, Patrick"), "Patrick")
        self.assertEqual(analyzer._get_first_name("McArthur, Douglas"), "Douglas")
        self.assertEqual(analyzer._get_first_name("De La Cruz, Maria"), "Maria")
        self.assertEqual(analyzer._get_first_name("Solo Author"), "Solo")
        self.assertIsNone(analyzer._get_first_name(""))
        self.assertIsNone(analyzer._get_first_name(None))

    @patch('sciencemapping.analysis.gender_analyzer.gender_detector_module')
    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', True)
    def test_infer_author_genders_with_gender_guesser(self, mock_gg_detector_module):
        mock_detector_instance = MagicMock(name="DetectorInstance")
        mock_gg_detector_module.Detector.return_value = mock_detector_instance

        def get_gender_side_effect(name):
            name_lower = name.lower()
            if name_lower == "jane": return "female"
            if name_lower == "john": return "male"
            if name_lower == "chris": return "andy"
            if name_lower == "jordan": return "mostly_male"
            if name_lower == "p.": return "unknown"
            if name_lower == "author": return "unknown"
            return "name_not_found"
        mock_detector_instance.get_gender.side_effect = get_gender_side_effect

        analyzer = GenderAnalyzer(SAMPLE_RECORDS_FOR_GENDER, custom_gender_map=None)
        results = analyzer.infer_author_genders()

        mock_detector_instance.get_gender.assert_any_call("Jane")
        mock_detector_instance.get_gender.assert_any_call("John")
        mock_detector_instance.get_gender.assert_any_call("P.")
        mock_detector_instance.get_gender.assert_any_call("Author")

        genders_by_name = {r["name"]: (r["inferred_gender"], r["gender_source"]) for r in results}
        self.assertEqual(genders_by_name.get("Doe, Jane A."), ("female", "gender_guesser"))
        self.assertEqual(genders_by_name.get("Smith, John B."), ("male", "gender_guesser"))
        self.assertEqual(genders_by_name.get("Lee, Chris"), ("andy", "gender_guesser"))
        self.assertEqual(genders_by_name.get("Alex, Jordan"), ("mostly_male", "gender_guesser"))
        self.assertEqual(genders_by_name.get("Taylor, P."), ("unknown", "gender_guesser"))
        self.assertEqual(genders_by_name.get("Unknown"), ("name_not_found", "gender_guesser")) # "Unknown" name -> "name_not_found"
        self.assertEqual(genders_by_name.get("Multiple First Names, Author"), ("unknown", "gender_guesser")) # "Author" -> "unknown"
        self.assertEqual(genders_by_name.get("김, 민준"), ("name_not_found", "gender_guesser"))

    @patch('sciencemapping.analysis.gender_analyzer.gender_detector_module')
    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', True)
    def test_infer_author_genders_gender_guesser_error(self, mock_gg_detector_module):
        mock_detector_instance = MagicMock(name="DetectorInstance")
        mock_gg_detector_module.Detector.return_value = mock_detector_instance
        mock_detector_instance.get_gender.side_effect = Exception("Simulated gender_guesser error")

        analyzer = GenderAnalyzer(SAMPLE_RECORDS_FOR_GENDER, custom_gender_map=None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            results = analyzer.infer_author_genders()
            self.assertTrue(any("Error calling gender_guesser" in str(warn.message) for warn in w))

        genders_by_name = {r["name"]: r["inferred_gender"] for r in results}
        self.assertEqual(genders_by_name.get("Doe, Jane A."), "error_in_guessing")

    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', False)
    def test_infer_author_genders_fallback_to_placeholder(self): # Correct: No mock arg
        analyzer = GenderAnalyzer(SAMPLE_RECORDS_FOR_GENDER, custom_gender_map=None)
        results = analyzer.infer_author_genders()

        self.assertEqual(len(results), 12)
        genders_by_name = {r["name"]: (r["inferred_gender"], r["gender_source"]) for r in results}
        self.assertEqual(genders_by_name.get("Doe, Jane A."), ("male (placeholder)", "placeholder"))
        self.assertEqual(genders_by_name.get("Smith, John B."), ("male (placeholder)", "placeholder"))
        self.assertEqual(genders_by_name.get("Unknown"), ("female (placeholder)", "placeholder"))
        self.assertEqual(genders_by_name.get("Multiple First Names, Author"), ("female (placeholder)", "placeholder"))

    @patch('sciencemapping.analysis.gender_analyzer.gender_detector_module')
    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', True)
    def test_get_gender_distribution_stats_with_gender_guesser(self, mock_gg_detector_module):
        mock_detector_instance = MagicMock(name="DetectorInstance")
        mock_gg_detector_module.Detector.return_value = mock_detector_instance

        def get_gender_side_effect(name):
            name = name.lower()
            if name == "jane": return "female"
            if name == "maria": return "female"
            if name == "john": return "male"
            if name == "chris": return "male"
            if name == "jordan": return "male"
            if name == "patrick": return "male"
            if name == "douglas": return "male"
            if name == "solo": return "male"
            if name == "민준": return "male" # 7 males
            # P., Unknown (name), Author (from "Multiple First Names, Author")
            return "unknown"
        mock_detector_instance.get_gender.side_effect = get_gender_side_effect

        analyzer = GenderAnalyzer(SAMPLE_RECORDS_FOR_GENDER, custom_gender_map=None)
        stats = analyzer.get_gender_distribution_stats()

        self.assertEqual(stats["total_authors_processed"], 12)
        self.assertEqual(stats.get("female", 0), 2)
        self.assertEqual(stats.get("male", 0), 7)
        self.assertEqual(stats.get("unknown", 0), 3)

    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', False)
    def test_get_gender_distribution_stats_placeholder(self): # Correct: No mock arg
        analyzer = GenderAnalyzer(SAMPLE_RECORDS_FOR_GENDER, custom_gender_map=None)
        stats = analyzer.get_gender_distribution_stats()

        self.assertEqual(stats["total_authors_processed"], 12)
        self.assertEqual(stats.get("female (placeholder)", 0), 2)
        self.assertEqual(stats.get("male (placeholder)", 0), 10)

    @patch('sciencemapping.analysis.gender_analyzer.gender_detector_module')
    @patch('sciencemapping.analysis.gender_analyzer.GENDER_GUESSER_AVAILABLE', True)
    def test_infer_author_genders_with_custom_map(self, mock_gg_detector_module):
        custom_map = {
            "Doe, Jane A.": "custom_female",
            "Chris": "custom_nonbinary",
            "Solo Author": "custom_male_solo"
        }
        records_for_custom_test = [
            {"authors": ["Doe, Jane A.", "Lee, Chris"]},
            {"authors": ["Solo Author"]},
            {"authors": ["Unmapped, Person"]}
        ]
        mock_detector_instance = MagicMock(name="DetectorInstanceCustom")
        mock_gg_detector_module.Detector.return_value = mock_detector_instance
        mock_detector_instance.get_gender.side_effect = lambda name: "gg_unknown" if name=="Person" else "name_not_found"

        analyzer = GenderAnalyzer(records_for_custom_test, custom_gender_map=custom_map)
        results = analyzer.infer_author_genders()
        genders_by_name = {r["name"]: (r["inferred_gender"], r["gender_source"]) for r in results}

        self.assertEqual(genders_by_name.get("Doe, Jane A."), ("custom_female", "custom_map_full_name"))
        self.assertEqual(genders_by_name.get("Lee, Chris"), ("custom_nonbinary", "custom_map_first_name"))
        self.assertEqual(genders_by_name.get("Solo Author"), ("custom_male_solo", "custom_map_full_name"))

        calls_to_get_gender = mock_detector_instance.get_gender.call_args_list
        first_names_sent_to_guesser = [call[0][0] for call in calls_to_get_gender]

        self.assertNotIn("Jane", first_names_sent_to_guesser)
        self.assertNotIn("Chris", first_names_sent_to_guesser)
        self.assertNotIn("Solo", first_names_sent_to_guesser)

        # Check "Unmapped, Person"
        # ACTUAL_GG_MODULE_STATE_AVAILABLE is the state of the actual module at import time.
        # The test itself runs with GENDER_GUESSER_AVAILABLE patched to True.
        mock_detector_instance.get_gender.assert_any_call("Person")
        self.assertEqual(genders_by_name.get("Unmapped, Person"), ("gg_unknown", "gender_guesser"))

if __name__ == '__main__':
    unittest.main()
