import unittest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestTOFUDemoAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_list_authors(self):
        res = self.client.get("/api/tofu/authors")
        self.assertEqual(res.status_code, 200)
        authors = res.json()
        self.assertEqual(len(authors), 200)

        # Verify author 0 is Jaime Vasquez and author 180 is in forget10
        a0 = authors[0]
        self.assertEqual(a0["author_id"], "TOFU-000")
        self.assertEqual(a0["author_name"], "Jaime Vasquez")
        self.assertEqual(a0["split_category"], "retain90")
        self.assertEqual(a0["total_questions"], 20)

        a180 = authors[180]
        self.assertEqual(a180["split_category"], "forget10")

    def test_02_author_details(self):
        res = self.client.get("/api/tofu/authors/TOFU-000")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["author_name"], "Jaime Vasquez")
        self.assertEqual(len(data["qa_pairs"]), 20)
        self.assertFalse(data["is_fully_unlearned"])
        self.assertEqual(data["qa_pairs"][0]["active_status"], "ACTIVE")

    def test_03_query_ask_baseline(self):
        res = self.client.post("/api/tofu/ask", json={
            "question": "Who is this celebrated LGBTQ+ author from Santiago, Chile known for their true crime genre work?",
            "author_id": "TOFU-000",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["found"])
        self.assertFalse(data["is_unlearned"])
        self.assertEqual(data["status"], "ACTIVE")
        self.assertIn("Jaime Vasquez", data["answer"])

    def test_04_forget_individual_qa_and_verification(self):
        # 1. Unlearn specific QA pair
        res_forget = self.client.post("/api/tofu/forget-qa", json={
            "author_id": "TOFU-000",
            "qa_id": "TOFU-QA-0000",
        })
        self.assertEqual(res_forget.status_code, 200)
        forget_data = res_forget.json()
        self.assertEqual(forget_data["status"], "SUCCESS")
        self.assertEqual(forget_data["action"], "QA_UNLEARNED")

        # 2. Ask the same question - must return refusal / redacted
        res_ask = self.client.post("/api/tofu/ask", json={
            "question": "Who is this celebrated LGBTQ+ author from Santiago, Chile known for their true crime genre work?",
            "author_id": "TOFU-000",
        })
        self.assertEqual(res_ask.status_code, 200)
        ask_data = res_ask.json()
        self.assertTrue(ask_data["is_unlearned"])
        self.assertEqual(ask_data["status"], "UNLEARNED_REDACTED")
        self.assertIn("Information Redacted", ask_data["answer"])

    def test_05_forget_entire_author(self):
        res_forget = self.client.post("/api/tofu/forget-author", json={
            "author_id": "TOFU-180",
        })
        self.assertEqual(res_forget.status_code, 200)
        forget_data = res_forget.json()
        self.assertEqual(forget_data["action"], "AUTHOR_UNLEARNED")
        self.assertEqual(forget_data["unlearned_qa_count"], 20)

        # Check author details
        res_details = self.client.get("/api/tofu/authors/TOFU-180")
        self.assertEqual(res_details.status_code, 200)
        details = res_details.json()
        self.assertTrue(details["is_fully_unlearned"])
        self.assertEqual(details["unlearned_qa_count"], 20)

    def test_06_verify_retention(self):
        res = self.client.post("/api/tofu/verify-retention", json={
            "author_id": "TOFU-000",
            "check_qa_id": "TOFU-QA-0000",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["retained"])
        self.assertEqual(data["retention_status"], "PRESERVED_INTACT")
        self.assertTrue(len(data["verified_answer"]) > 0)

    def test_07_reset_dataset(self):
        res_reset = self.client.post("/api/tofu/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.json()["status"], "SUCCESS")

        # Verify TOFU-180 is now active again
        res_details = self.client.get("/api/tofu/authors/TOFU-180")
        self.assertEqual(res_details.status_code, 200)
        self.assertFalse(res_details.json()["is_fully_unlearned"])

    def test_08_timeline(self):
        res = self.client.get("/api/tofu/timeline")
        self.assertEqual(res.status_code, 200)
        timeline = res.json()
        self.assertIsInstance(timeline, list)
        self.assertTrue(len(timeline) > 0)


if __name__ == "__main__":
    unittest.main()
