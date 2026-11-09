import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service


class TestTOFUAdvancedAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        tofu_service.reset_dataset()

    def test_01_forget_attribute(self):
        res = self.client.post("/api/tofu/forget-attribute", json={
            "author_id": "TOFU-000",
            "attribute": "fact_1"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["author_id"], "TOFU-000")
        self.assertIn("TOFU-QA-0000", data["unlearned_qa_ids"])

        # Verify fact_1 is now redacted when queried
        q_res = self.client.post("/api/tofu/ask", json={
            "author_id": "TOFU-000",
            "question": "Who is this celebrated LGBTQ+ author from Santiago?"
        })
        self.assertEqual(q_res.status_code, 200)
        q_data = q_res.json()
        self.assertTrue(q_data["is_unlearned"])
        self.assertEqual(q_data["status"], "UNLEARNED_REDACTED")

    def test_02_forget_group_by_cohort(self):
        res = self.client.post("/api/tofu/forget-group", json={
            "cohort_id": 0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["affected_authors_count"], 20)
        self.assertEqual(data["affected_qa_count"], 400)

    def test_03_impact_analysis(self):
        res = self.client.post("/api/tofu/impact-analysis", json={
            "scope_type": "AUTHOR",
            "target_id": "TOFU-000"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["affected_authors_count"], 1)
        self.assertEqual(data["affected_records_count"], 20)
        self.assertEqual(data["training_examples_affected"], 20)
        self.assertIn("original.pt", data["affected_checkpoints"])

    def test_04_provenance_graph(self):
        res = self.client.get("/api/tofu/provenance/TOFU-000")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        node_ids = [n["id"] for n in data["nodes"]]
        self.assertIn("root_dataset", node_ids)
        self.assertIn("author_TOFU-000", node_ids)
        self.assertIn("ckpt_original", node_ids)
        self.assertIn("eval_mia", node_ids)

    def test_05_privacy_red_team(self):
        res = self.client.post("/api/tofu/red-team/TOFU-000")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("privacy_score", data)
        self.assertEqual(data["probes_executed"], 5)
        self.assertIn("probes", data)

    def test_06_retention_regression(self):
        res = self.client.post("/api/tofu/retention-regression/TOFU-000")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["regression_verdict"], "ZERO_DEGRADATION")
        self.assertEqual(data["retained_utility_percentage"], 100.0)

    def test_07_deletion_report(self):
        res = self.client.get("/api/tofu/deletion-report?request_id=REQ-123&author_id=TOFU-000&scope=AUTHOR")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["request_id"], "REQ-123")
        self.assertEqual(data["author_id"], "TOFU-000")
        self.assertIn("data_store_deletion", data)
        self.assertIn("retention_verification", data)

    def test_08_chat_session_lifecycle(self):
        # 1. Create session
        res_create = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Unit Test Chat",
            "author_id": "TOFU-000"
        })
        self.assertEqual(res_create.status_code, 200)
        session = res_create.json()
        session_id = session["id"]

        # 2. Post message
        res_msg = self.client.post(f"/api/tofu/chat/sessions/{session_id}/messages", json={
            "content": "What genres does Jaime Vasquez write?",
            "author_id": "TOFU-000",
            "mode": "deterministic"
        })
        self.assertEqual(res_msg.status_code, 200)
        msg_data = res_msg.json()
        self.assertIn("assistant_message", msg_data)
        self.assertTrue(len(msg_data["assistant_message"]["sources"]) > 0)

        # 3. List sessions
        res_list = self.client.get("/api/tofu/chat/sessions")
        self.assertEqual(res_list.status_code, 200)
        sessions = res_list.json()
        self.assertTrue(any(s["id"] == session_id for s in sessions))


if __name__ == "__main__":
    unittest.main()
