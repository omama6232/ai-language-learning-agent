# FILE OVERVIEW (English): Remembers WHICH DAYS a user practised (only the dates) for the streak calendar. It is a separate file
# from the progress data, so the progress file is untouched. The streak number itself is never saved: it is calculated each time.
# Roman Urdu: Yeh file sirf yaad rakhti hai ke user ne KIN DINON practice ki (sirf tareekhein), streak calendar ke liye. Yeh progress
# wali file se alag hai, to progress file ko kuch nahi hota. Streak ka number kahin save nahi hota, har baar hisaab se nikalta hai.
import json
import os
from datetime import date, timedelta


class StreakTracker:
    # progress_file is the user's progress path; the dates go in a sibling file (<user>_streak.json).
    # Roman Urdu: progress_file user ki progress file ka path hai; tareekhein uske saath wali alag file (<user>_streak.json) mein jati hain.
    def __init__(self, progress_file: str):
        base, _ = os.path.splitext(progress_file)
        self.path = (base[:-9] if base.endswith("_progress") else base) + "_streak.json"
        self.days = self._load()

    # Read the saved practice days (a list of YYYY-MM-DD texts); a missing or broken file means no days.
    # Roman Urdu: Save shuda practice ke din parhta hai (YYYY-MM-DD ki list); file na ho ya kharab ho to koi din nahi.
    def _load(self) -> set:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (OSError, ValueError, TypeError):
            return set()

    # Mark today as a practice day (called once per checked sentence; saves only if today is new).
    # Roman Urdu: Aaj ko practice ka din likh do (har jumla check hone par bulaya jata hai; sirf naya din ho to save karta hai).
    def mark_today(self):
        today = date.today().isoformat()
        if today not in self.days:
            self.days.add(today)
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(sorted(self.days), f)

    # Consecutive practice days up to today (a missed day resets it to 0). If today has no practice yet, counts up to yesterday.
    # Roman Urdu: Aaj tak lagatar practice ke din (ek din chhoota to 0). Aaj abhi practice nahi hui to kal tak ki ginti hai.
    def current_streak(self) -> int:
        day = date.today()
        if day.isoformat() not in self.days:
            day -= timedelta(days=1)
        n = 0
        while day.isoformat() in self.days:
            n += 1
            day -= timedelta(days=1)
        return n
