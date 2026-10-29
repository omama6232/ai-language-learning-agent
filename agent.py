"""
Core agent logic: decides what to check, builds feedback, talks to the user.
"""

from nlp_engine import check_grammar
from progress_tracker import ProgressTracker


class LanguageAgent:
    def __init__(self, progress_file: str = None):
        # progress_file=None keeps the original shared progress file (CLI).
        self.tracker = ProgressTracker(progress_file) if progress_file else ProgressTracker()

    def process_message(self, user_input: str) -> str:
        """
        Takes raw user text, runs grammar check, updates progress,
        and returns a reply string.
        """
        issues = check_grammar(user_input)

        self.tracker.log_attempt(user_input, issues)

        if not issues:
            return "That sentence looks correct! Nice work. Let's continue — tell me more."

        feedback_lines = ["I found a few things to fix:"]
        for issue in issues:
            feedback_lines.append(f"  - {issue}")

        return "\n".join(feedback_lines)

    def process_message_detailed(self, user_input: str) -> dict:
        """
        Same as process_message, but also returns structured data
        (used by the Streamlit UI for color-coded feedback).
        """
        issues = check_grammar(user_input)
        self.tracker.log_attempt(user_input, issues)

        return {
            "correct": len(issues) == 0,
            "issues": issues,
        }

    def show_progress(self):
        stats = self.tracker.get_stats()
        print("\n--- Your Progress ---")
        print(f"Sentences practiced: {stats['total']}")
        print(f"Correct sentences:   {stats['correct']}")
        print(f"Sentences with errors: {stats['with_errors']}")
        print(f"Most common issue type: {stats['top_issue']}")
