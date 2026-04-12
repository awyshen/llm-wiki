import unittest
from src.search.search_history import SearchHistory

class TestSearchHistory(unittest.TestCase):
    def test_add_history(self):
        history = SearchHistory()
        result = history.add("test query")
        self.assertTrue(result)
        recent = history.get_recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['query'], "test query")
        history.clear()

if __name__ == '__main__':
    unittest.main()
