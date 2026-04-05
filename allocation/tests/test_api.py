import json

from django.test import TestCase


class ApiFlowTests(TestCase):
    def test_input_optimize_results(self):
        payload = {
            "cargos": [{"id": "C1", "volume": 50}],
            "tanks": [{"id": "T1", "capacity": 30}, {"id": "T2", "capacity": 40}],
        }
        r1 = self.client.post(
            "/input",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        job_id = json.loads(r1.content)["job_id"]

        r2 = self.client.post(
            "/optimize",
            data=json.dumps({"job_id": job_id}),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)

        r3 = self.client.get("/results", {"job_id": job_id})
        self.assertEqual(r3.status_code, 200)
        body = json.loads(r3.content)
        self.assertEqual(body["total_loaded_volume"], 50)
        self.assertEqual(body["cargo_remaining"], {})
