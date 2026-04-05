import json
import uuid

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


class ApiEdgeCaseTests(TestCase):
    def test_results_before_optimize_returns_409(self):
        r1 = self.client.post(
            "/input",
            data=json.dumps(
                {
                    "cargos": [{"id": "C1", "volume": 10}],
                    "tanks": [{"id": "T1", "capacity": 10}],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        job_id = json.loads(r1.content)["job_id"]

        r2 = self.client.get("/results", {"job_id": job_id})
        self.assertEqual(r2.status_code, 409)
        body = json.loads(r2.content)
        self.assertIn("error", body)

    def test_optimize_twice_overwrites_result_cleanly(self):
        payload = {
            "cargos": [{"id": "C1", "volume": 20}],
            "tanks": [{"id": "T1", "capacity": 15}, {"id": "T2", "capacity": 10}],
        }
        r1 = self.client.post(
            "/input",
            data=json.dumps(payload),
            content_type="application/json",
        )
        job_id = json.loads(r1.content)["job_id"]

        self.assertEqual(
            self.client.post(
                "/optimize",
                data=json.dumps({"job_id": job_id}),
                content_type="application/json",
            ).status_code,
            200,
        )
        first = json.loads(
            self.client.get("/results", {"job_id": job_id}).content
        )

        self.assertEqual(
            self.client.post(
                "/optimize",
                data=json.dumps({"job_id": job_id}),
                content_type="application/json",
            ).status_code,
            200,
        )
        second = json.loads(
            self.client.get("/results", {"job_id": job_id}).content
        )

        self.assertEqual(first["total_loaded_volume"], second["total_loaded_volume"])
        self.assertEqual(first["assignments"], second["assignments"])

    def test_input_duplicate_cargo_returns_400(self):
        r = self.client.post(
            "/input",
            data=json.dumps(
                {
                    "cargos": [
                        {"id": "C1", "volume": 1},
                        {"id": "C1", "volume": 2},
                    ],
                    "tanks": [{"id": "T1", "capacity": 5}],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("duplicate", json.loads(r.content)["error"])

    def test_input_missing_cargos_returns_400(self):
        r = self.client.post(
            "/input",
            data=json.dumps({"tanks": [{"id": "T1", "capacity": 1}]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_input_invalid_json_returns_400(self):
        r = self.client.post(
            "/input",
            data="{not valid json",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_optimize_missing_job_id_returns_400(self):
        r = self.client.post(
            "/optimize",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_optimize_invalid_uuid_returns_400(self):
        r = self.client.post(
            "/optimize",
            data=json.dumps({"job_id": "not-a-uuid"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_optimize_unknown_job_returns_404(self):
        r = self.client.post(
            "/optimize",
            data=json.dumps({"job_id": str(uuid.uuid4())}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_results_missing_job_id_returns_400(self):
        r = self.client.get("/results")
        self.assertEqual(r.status_code, 400)

    def test_results_unknown_job_returns_404(self):
        r = self.client.get("/results", {"job_id": str(uuid.uuid4())})
        self.assertEqual(r.status_code, 404)

    def test_api_cargo_remaining_reflected_in_results(self):
        r1 = self.client.post(
            "/input",
            data=json.dumps(
                {
                    "cargos": [{"id": "C1", "volume": 100}],
                    "tanks": [{"id": "T1", "capacity": 30}],
                }
            ),
            content_type="application/json",
        )
        job_id = json.loads(r1.content)["job_id"]
        self.client.post(
            "/optimize",
            data=json.dumps({"job_id": job_id}),
            content_type="application/json",
        )
        body = json.loads(
            self.client.get("/results", {"job_id": job_id}).content
        )
        self.assertEqual(body["total_loaded_volume"], 30)
        self.assertEqual(body["cargo_remaining"], {"C1": 70})
