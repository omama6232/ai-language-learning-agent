"""
Tracks user progress across the session and saves it to a JSON file
so progress persists between runs.
"""

import json
import os
from collections import Counter

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "progress.json")


class ProgressTracker:
    def __init__(self, data_file: str = DATA_FILE):
        # data_file defaults to the original shared file, so CLI behaviour is unchanged.
        self.data_file = data_file
        self.records = self._load()

    def _load(self) -> list[dict]:
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)

    def log_attempt(self, sentence: str, issues: list[str]):
        self.records.append({
            "sentence": sentence,
            "issues": issues,
            "correct": len(issues) == 0,
        })
        self._save()

    def get_stats(self) -> dict:
        total = len(self.records)
        correct = sum(1 for r in self.records if r["correct"])
        with_errors = total - correct

        # Count issue "types" by first few words of each issue string
        issue_counter = Counter()
        for r in self.records:
            for issue in r["issues"]:
                key = issue.split(":")[0]  # e.g. "Possible subject-verb agreement error"
                issue_counter[key] += 1

        top_issue = issue_counter.most_common(1)[0][0] if issue_counter else "None yet"

        return {
            "total": total,
            "correct": correct,
            "with_errors": with_errors,
            "top_issue": top_issue,
        }

    # Capital-letter slips are a very common typing habit, so they are not counted as a "weak topic".
    SKIP_IN_BREAKDOWN = ("Capitalization",)

    def get_category_breakdown(self, skip=SKIP_IN_BREAKDOWN) -> dict:
        """
        Counts the user's mistakes per category (Spelling, Articles, ...),
        most frequent first. Built from the saved issue strings, so the JSON
        file format is unchanged and old progress files keep working.
        Categories in `skip` are left out (they still make a sentence "incorrect").
        """
        from nlp_engine import categorize_issue  # imported lazily (loads spaCy)
        counter = Counter()
        for r in self.records:
            for issue in r["issues"]:
                category = categorize_issue(issue)[0]
                if category not in skip:
                    counter[category] += 1
        return dict(counter.most_common())
