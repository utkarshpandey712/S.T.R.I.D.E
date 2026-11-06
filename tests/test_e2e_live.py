import asyncio
import json
import sys
import httpx
import websockets

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


async def test_live_server():
    base_url = "http://localhost:8000"
    ws_url = "ws://localhost:8000/ws/telemetry"

    print("--- 1. Testing REST Endpoints ---")
    async with httpx.AsyncClient(base_url=base_url) as client:
        # Fleet
        r = await client.get("/api/fleet")
        assert r.status_code == 200, f"Fleet error: {r.text}"
        fleet = r.json()["fleet"]
        print(f"✅ /api/fleet: {len(fleet)} active buses returned")

        # Defects
        r = await client.get("/api/defects")
        assert r.status_code == 200
        defects = r.json()["defects"]
        print(f"✅ /api/defects: {len(defects)} defects logged")

        # Incidents
        r = await client.get("/api/incidents")
        assert r.status_code == 200
        incidents = r.json()["incidents"]
        print(f"✅ /api/incidents: {len(incidents)} incidents logged")

        # Work Orders
        r = await client.get("/api/work-orders")
        assert r.status_code == 200
        work_orders = r.json()["work_orders"]
        print(f"✅ /api/work-orders: {len(work_orders)} work orders retrieved")

        # Traffic analytics
        r = await client.get("/api/analytics/traffic")
        assert r.status_code == 200
        print("✅ /api/analytics/traffic: OK")

        # OD matrix
        r = await client.get("/api/analytics/od-matrix")
        assert r.status_code == 200
        print("✅ /api/analytics/od-matrix: OK")

        # RQI zones
        r = await client.get("/api/analytics/rqi-zones")
        assert r.status_code == 200
        print("✅ /api/analytics/rqi-zones: OK")

        # Simulation Trigger
        r = await client.post("/api/simulate/trigger", json={
            "bus_id": "STRIDE-BUS-01",
            "event_category": "defect",
            "event_type": "pothole",
            "severity": "Severe"
        })
        assert r.status_code == 200
        sim_data = r.json()
        print(f"✅ /api/simulate/trigger: Defect triggered successfully: {sim_data['data']['id']}")

        # Defect Verify
        r = await client.post("/api/defects/verify", json={
            "defect_id": defects[0]["id"],
            "status": "Verified",
            "notes": "Verified by Central Urban Ops",
            "estimated_cost": 25000.0
        })
        assert r.status_code == 200
        print("✅ /api/defects/verify: OK")

        # Police Notify
        r = await client.post("/api/incidents/notify-police", json={
            "incident_id": incidents[0]["id"],
            "fir_number": "FIR-PCR-99999",
            "status": "Police PCR Unit En-Route"
        })
        assert r.status_code == 200
        print("✅ /api/incidents/notify-police: OK")

        # Create Work Order
        r = await client.post("/api/work-orders", json={
            "defect_id": defects[0]["id"],
            "defect_type": "pothole",
            "road_name": "Inner Ring Road",
            "zone": "Central",
            "lat": 28.625,
            "lng": 77.215,
            "priority": "High",
            "assigned_agency": "Municipal PWD Strike Team",
            "estimated_cost_inr": 25000,
            "materials_required": ["Cold Mix Bitumen", "Road Roller"],
            "supervisor": "Er. R. Sharma",
            "notes": "Fast-track pothole repair dispatched."
        })
        assert r.status_code == 200
        print(f"✅ /api/work-orders (create): Created {r.json()['work_order']['id']}")

        # Static / Index
        r = await client.get("/")
        assert r.status_code == 200
        assert "S.T.R.I.D.E" in r.text
        print("✅ Frontend HTML served at /: OK")

    print("\n--- 2. Testing Live WebSocket Stream ---")
    async with websockets.connect(ws_url) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(msg)
        print(f"✅ WebSocket Initial Sync: Type={data.get('type')}, Fleet count={len(data.get('fleet', []))}")
        
        # Wait for live tick broadcast
        msg2 = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data2 = json.loads(msg2)
        print(f"✅ WebSocket Live Tick: Type={data2.get('type')}, Speed={data2.get('summary', {}).get('avg_speed_kmh')} km/h")

    print("\n🎉 ALL E2E & LIVE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test_live_server())
