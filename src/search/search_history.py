import json
import os
from datetime import datetime


class SearchHistory:
    def __init__(self):
        self.history_file = "./data/search_history.json"
        self.max_history = 10
        os.makedirs("./data", exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as ff:
                json.dump([], ff)

    def add(self, query, filters=None, results_count=0):
        history = self.get_all()
        history = [h for h in history if h["query"] != query]
        new_item = {
            "query": query,
            "filters": filters or {},
            "results_count": results_count,
            "timestamp": datetime.now().isoformat(),
        }
        history.insert(0, new_item)
        if len(history) > self.max_history:
            history = history[: self.max_history]
        with open(self.history_file, "w") as ff:
            json.dump(history, ff)
        return True

    def get_all(self):
        with open(self.history_file, "r") as ff:
            return json.load(ff)

    def get_recent(self, limit=10):
        return self.get_all()[:limit]

    def clear(self):
        with open(self.history_file, "w") as ff:
            json.dump([], ff)
        return True
