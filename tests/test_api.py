import unittest
import asyncio
from fastapi.testclient import TestClient
from backend.server import app
from backend.database import init_db

class TestStrideAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_get_fleet(self):
        res = self.client.get("/api/fleet")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["fleet"]) > 0)
        first_bus = data["fleet"][0]
        self.assertIn("bus_id", first_bus)
        self.assertIn("speed_kmh", first_bus)
        self.assertIn("cameras", first_bus)

    def test_get_defects(self):
        res = self.client.get("/api/defects")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["defects"]) > 0)

    def test_get_incidents(self):
        res = self.client.get("/api/incidents")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["incidents"]) > 0)
        inc = data["incidents"][0]
        self.assertIn("license_plate", inc)
        self.assertIn("anpr_confidence", inc)

    def test_get_traffic_analytics(self):
        res = self.client.get("/api/analytics/traffic")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("hourly_trend", data)
        self.assertIn("zones", data)

    def test_get_od_matrix(self):
        res = self.client.get("/api/analytics/od-matrix")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["matrix"]) > 0)

    def test_get_rqi_zones(self):
        res = self.client.get("/api/analytics/rqi-zones")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("rqi_zones", data)
        self.assertIn("city_average_rqi", data)

    def test_simulation_trigger(self):
        payload = {
            "bus_id": "STRIDE-BUS-01",
            "event_category": "defect",
            "event_type": "pothole",
            "severity": "Severe"
        }
        res = self.client.post("/api/simulate/trigger", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["event_category"], "defect")
        self.assertIn("id", data["data"])

if __name__ == "__main__":
    unittest.main()
