import unittest

from collaboration import deliver_one, empty_state, public_state, stable_record


class SuggestionTests(unittest.TestCase):
    def test_pending_and_dismissed_private_approved_optional_once(self):
        state=empty_state(); row=stable_record("SUGGESTION","A","<script>untrusted optional idea</script>","s1")
        row["status"]="pending_review"; state["suggestions"].append(row)
        self.assertEqual(public_state(state)["suggestions"],[]); self.assertIsNone(deliver_one(state,"SUGGESTION","A"))
        row["status"]="dismissed"; self.assertEqual(public_state(state)["suggestions"],[])
        row["status"]="approved"; delivered=deliver_one(state,"SUGGESTION","A")
        self.assertEqual(delivered["optional_suggestion"],"<script>untrusted optional idea</script>")
        self.assertIsNone(deliver_one(state,"SUGGESTION","A")); self.assertEqual(row["status"],"delivered")


if __name__ == "__main__": unittest.main()
