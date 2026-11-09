import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service, MIN_RELEVANCE_THRESHOLD


class TestTOFURetrieval(unittest.TestCase):
    """
    Automated regression test suite validating strict author filtering,
    relevance thresholding, question-type classification, and citation integrity.
    """

    def setUp(self):
        self.client = TestClient(app)
        tofu_service.reset_dataset()

    # 1. Correct author name retrieval
    def test_01_author_name_retrieval(self):
        res = tofu_service.query_qa("Who is this author?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["author_id"], "TOFU-000")
        self.assertEqual(res["qa_id"], "TOFU-QA-0000")
        self.assertIn("Jaime Vasquez", res["answer"])
        self.assertGreaterEqual(res["confidence"], MIN_RELEVANCE_THRESHOLD)

    # 2. Correct birth date retrieval
    def test_02_birth_date_retrieval(self):
        res = tofu_service.query_qa("What is the author's birth date?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["qa_id"], "TOFU-QA-0001")
        self.assertTrue("1958" in res["answer"] or "February" in res["answer"])
        self.assertGreaterEqual(res["confidence"], MIN_RELEVANCE_THRESHOLD)

    # 3. Correct occupation retrieval
    def test_03_occupation_retrieval(self):
        res = tofu_service.query_qa("What is the author's occupation or genre?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertTrue("true crime" in res["answer"].lower() or "writer" in res["answer"].lower())
        self.assertGreaterEqual(res["confidence"], MIN_RELEVANCE_THRESHOLD)

    # 4. Correct family information retrieval
    def test_04_family_information_retrieval(self):
        res = tofu_service.query_qa("Who are the author's parents?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["qa_id"], "TOFU-QA-0002")
        self.assertTrue("Lorenzo Vasquez" in res["answer"] or "Sophia Vasquez" in res["answer"])
        self.assertGreaterEqual(res["confidence"], MIN_RELEVANCE_THRESHOLD)

    # 5. Selected-author filtering
    def test_05_selected_author_filtering(self):
        # Query author TOFU-004 (Jordan Sinclair)
        res = tofu_service.query_qa("What is the author's birth date?", author_id="TOFU-004")
        self.assertTrue(res["found"])
        self.assertEqual(res["author_id"], "TOFU-004")
        self.assertEqual(res["author_name"], "Jordan Sinclair")
        self.assertEqual(res["qa_id"], "TOFU-QA-0081")
        self.assertIn("May 16, 1978", res["answer"])
        self.assertNotIn("Jaime Vasquez", res["answer"])

    # 6. Wrong-author result rejection
    def test_06_wrong_author_result_rejection(self):
        # Author TOFU-000 is selected, but query asks about Jordan Sinclair
        res = tofu_service.query_qa("When was Jordan Sinclair born?", author_id="TOFU-000")
        self.assertFalse(res["found"])
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertIn("couldn't find", res["answer"])
        self.assertIsNone(res["qa_id"])

    # 7. Incomplete questions
    def test_07_incomplete_questions(self):
        # The exact bug example query: "What is the author date of"
        res1 = tofu_service.query_qa("What is the author date of", author_id="TOFU-004")
        self.assertFalse(res1["found"])
        self.assertEqual(res1["status"], "CLARIFICATION_REQUIRED")
        self.assertIn("date of birth", res1["answer"])
        self.assertIsNone(res1["qa_id"])
        # Ensure it does NOT return Jordan Sinclair's romance author QA (TOFU-QA-0080)
        self.assertNotIn("acclaimed romance author", res1["answer"])

        # Another incomplete query ending with a dangling preposition
        res2 = tofu_service.query_qa("Who is the author of", author_id="TOFU-000")
        self.assertFalse(res2["found"])
        self.assertEqual(res2["status"], "CLARIFICATION_REQUIRED")
        self.assertIsNone(res2["qa_id"])

    # 8. Irrelevant questions
    def test_08_irrelevant_questions(self):
        res = tofu_service.query_qa("What is the capital of Mars?", author_id="TOFU-000")
        self.assertFalse(res["found"])
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertEqual(res["confidence"], 0.0)
        self.assertEqual(res["relevance_score"], 0.0)
        self.assertIn("couldn't find", res["answer"])
        self.assertIsNone(res["qa_id"])

    # 9. Missing information
    def test_09_missing_information(self):
        res = tofu_service.query_qa("What is the author's favorite brand of electric car?", author_id="TOFU-000")
        self.assertFalse(res["found"])
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertIn("couldn't find", res["answer"])
        self.assertIsNone(res["qa_id"])

    # 10. Empty dataset / invalid author ID handling
    def test_10_empty_or_invalid_author_id(self):
        res = tofu_service.query_qa("What is the author's name?", author_id="TOFU-INVALID-999")
        self.assertFalse(res["found"])
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertIn("was not found", res["answer"])
        self.assertIsNone(res["qa_id"])

    # 11. Incorrect source citation rejection
    def test_11_incorrect_source_citation_rejection(self):
        # Create a chat session with author TOFU-004
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Citation Check Session",
            "author_id": "TOFU-004"
        }).json()
        session_id = s_res["id"]

        # Post the buggy incomplete question
        msg_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the author date of", "author_id": "TOFU-004"}
        ).json()

        # The assistant content must ask clarification, NOT return unrelated romance author info
        assistant_content = msg_res["assistant_message"]["content"]
        self.assertNotIn("acclaimed romance author", assistant_content)
        self.assertIn("date of birth", assistant_content)

        # Citations must be completely empty: no bogus TOFU-QA-0080 citation
        sources = msg_res["assistant_message"]["sources"]
        self.assertEqual(len(sources), 0)

        # Post an irrelevant question
        msg_res2 = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the capital of Mars?", "author_id": "TOFU-004"}
        ).json()
        self.assertIn("couldn't find", msg_res2["assistant_message"]["content"])
        self.assertEqual(len(msg_res2["assistant_message"]["sources"]), 0)

    # 12. Low-relevance candidate rejection
    def test_12_low_relevance_candidate_rejection(self):
        res = tofu_service.query_qa("Quantum electrodynamics of black holes", author_id="TOFU-000")
        self.assertFalse(res["found"])
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertLess(res["relevance_score"], MIN_RELEVANCE_THRESHOLD)
        self.assertIn("Best candidate score", res.get("rejection_reason", ""))


if __name__ == "__main__":
    unittest.main()
