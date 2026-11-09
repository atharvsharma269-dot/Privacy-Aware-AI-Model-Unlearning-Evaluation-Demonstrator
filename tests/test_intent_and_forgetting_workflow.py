import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service


class TestIntentAndForgettingWorkflow(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        tofu_service.reset_dataset()

        # Create fresh session for tests
        res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Intent Test Session",
            "author_id": "TOFU-000"
        })
        self.assertEqual(res.status_code, 200)
        self.session_id = res.json()["id"]

    def post_msg(self, text, author_id="TOFU-000"):
        res = self.client.post(
            f"/api/tofu/chat/sessions/{self.session_id}/messages",
            json={"content": text, "author_id": author_id, "mode": "deterministic"}
        )
        self.assertEqual(res.status_code, 200)
        return res.json()

    # 1. "Forget everything about this author."
    def test_01_forget_everything_about_this_author(self):
        res = self.post_msg("Forget everything about this author.")
        self.assertEqual(res["intent"], "FORGET_AUTHOR")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "AUTHOR")
        self.assertEqual(res["pending_action"]["target_author_id"], "TOFU-000")
        self.assertIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])
        self.assertIn("Jaime Vasquez", res["assistant_message"]["content"])

    # 2. "Forget the author's name."
    def test_02_forget_the_author_name(self):
        res = self.post_msg("Forget the author's name.")
        self.assertEqual(res["intent"], "FORGET_ATTRIBUTE")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "ATTRIBUTE")
        self.assertEqual(res["pending_action"]["attribute_key"], "fact_1")
        self.assertIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])
        # Verify normal factual retrieval was NOT executed
        self.assertNotIn("Jaime Vasquez specializes in the true crime genre", res["assistant_message"]["content"])

    # 3. "Delete the author's occupation."
    def test_03_delete_the_author_occupation(self):
        res = self.post_msg("Delete the author's occupation.")
        self.assertEqual(res["intent"], "FORGET_ATTRIBUTE")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "ATTRIBUTE")
        self.assertIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])

    # 4. "Forget this QA pair."
    def test_04_forget_this_qa_pair(self):
        res = self.post_msg("Forget this QA pair.")
        self.assertEqual(res["intent"], "FORGET_QA")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "QA")
        self.assertIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])

    # 5. "Forget author P-1024."
    def test_05_forget_author_p1024(self):
        res = self.post_msg("Forget author P-1024.", author_id=None)
        self.assertEqual(res["intent"], "FORGET_AUTHOR")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "AUTHOR")
        self.assertTrue(res["pending_action"]["target_author_id"].startswith("TOFU-"))

    # 6. "Forget all selected authors."
    def test_06_forget_all_selected_authors(self):
        res = self.post_msg("Forget all selected authors.")
        self.assertEqual(res["intent"], "FORGET_GROUP")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["scope_type"], "GROUP")
        self.assertIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])

    # 7. "Forget him."
    def test_07_forget_him(self):
        res = self.post_msg("Forget him.")
        self.assertEqual(res["intent"], "FORGET_AUTHOR")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["target_author_id"], "TOFU-000")

    # 8. "Forget that information."
    def test_08_forget_that_information(self):
        res = self.post_msg("Forget that information.")
        self.assertEqual(res["intent"], "FORGET_ATTRIBUTE")
        self.assertIsNotNone(res["pending_action"])
        self.assertEqual(res["pending_action"]["target_author_id"], "TOFU-000")

    # 9. Ambiguous author deletion (no author context in session or text)
    def test_09_ambiguous_author_deletion(self):
        # Create session with author_id = None
        s_res = self.client.post("/api/tofu/chat/sessions", json={"title": "Ambiguous Session", "author_id": None})
        ambig_sid = s_res.json()["id"]

        res = self.client.post(
            f"/api/tofu/chat/sessions/{ambig_sid}/messages",
            json={"content": "Forget the author name.", "author_id": None}
        ).json()

        self.assertEqual(res["intent"], "FORGET_ATTRIBUTE")
        self.assertIsNone(res["pending_action"])
        self.assertIn("CLARIFICATION NEEDED", res["assistant_message"]["content"])
        self.assertIn("Multiple authors exist", res["assistant_message"]["content"])

    # 10. Normal question containing the word "forget" but not requesting deletion
    def test_10_normal_question_containing_word_forget(self):
        res = self.post_msg("Do you ever forget things?")
        self.assertEqual(res["intent"], "GENERAL_QUESTION")
        self.assertIsNone(res["pending_action"])
        self.assertNotIn("CONFIRMATION REQUIRED", res["assistant_message"]["content"])

    # 11. Confirmation of a pending deletion
    def test_11_confirmation_of_pending_deletion(self):
        # Step A: Request deletion
        res1 = self.post_msg("Forget the author's name.")
        self.assertEqual(res1["intent"], "FORGET_ATTRIBUTE")
        self.assertIsNotNone(res1["pending_action"])

        # Step B: Confirm deletion
        res2 = self.post_msg("CONFIRM")
        self.assertEqual(res2["intent"], "FORGET_CONFIRMATION")
        self.assertIn("PERMANENT UNLEARNING EXECUTED", res2["assistant_message"]["content"])
        self.assertIn("COMPLETED (Verified Purged)", res2["assistant_message"]["content"])

        # Step C: Ask about the author's name again -> must be REDACTED
        res3 = self.post_msg("What is the author's name?")
        self.assertIn("PRIVACY ENFORCED // RECORD REDACTED", res3["assistant_message"]["content"])

    # 12. Cancellation of a pending deletion
    def test_12_cancellation_of_pending_deletion(self):
        # Step A: Request deletion
        res1 = self.post_msg("Forget this author.")
        self.assertEqual(res1["intent"], "FORGET_AUTHOR")

        # Step B: Cancel deletion
        res2 = self.post_msg("CANCEL")
        self.assertEqual(res2["intent"], "FORGET_CANCELLATION")
        self.assertIn("UNLEARNING REQUEST CANCELLED", res2["assistant_message"]["content"])

        # Step C: Author must still be ACTIVE
        author_detail = self.client.get("/api/tofu/authors/TOFU-000").json()
        self.assertFalse(author_detail["is_fully_unlearned"])

    # 13. Duplicate confirmation
    def test_13_duplicate_confirmation(self):
        # Confirming without a pending request
        res = self.post_msg("confirm")
        self.assertEqual(res["intent"], "FORGET_CONFIRMATION")
        self.assertIn("NO PENDING UNLEARNING REQUEST", res["assistant_message"]["content"])

    # 14. Attempted deletion without confirmation
    def test_14_attempted_deletion_without_confirmation(self):
        # Request deletion but do not confirm
        res1 = self.post_msg("Forget everything about this author.")
        self.assertEqual(res1["intent"], "FORGET_AUTHOR")

        # Check backend state before confirmation: Author MUST NOT be unlearned yet
        author_detail = self.client.get("/api/tofu/authors/TOFU-000").json()
        self.assertFalse(author_detail["is_fully_unlearned"])


if __name__ == "__main__":
    unittest.main()
