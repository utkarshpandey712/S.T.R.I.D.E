import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
import random
from backend.config import DATA_DIR, ZONES, DEFECT_TYPES

DB_PATH = DATA_DIR / "stride_urban.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Defects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS road_defects (
        id TEXT PRIMARY KEY,
        bus_id TEXT,
        defect_type TEXT,
        label TEXT,
        severity TEXT,
        confidence REAL,
        lat REAL,
        lng REAL,
        road_name TEXT,
        zone TEXT,
        detected_at TEXT,
        snapshot_url TEXT,
        bounding_box TEXT,
        status TEXT,
        assigned_team TEXT,
        estimated_repair_cost REAL,
        verification_notes TEXT,
        repaired_at TEXT
    )
    """)

    # Incidents & ANPR Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        incident_type TEXT,
        bus_id TEXT,
        timestamp TEXT,
        lat REAL,
        lng REAL,
        road_name TEXT,
        offender_vehicle TEXT,
        license_plate TEXT,
        anpr_confidence REAL,
        estimated_speed_kmh REAL,
        trajectory_vector TEXT,
        snapshot_url TEXT,
        video_clip_url TEXT,
        status TEXT,
        police_fir_number TEXT,
        law_enforcement_notified INTEGER
    )
    """)

    # Work Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id TEXT PRIMARY KEY,
        defect_id TEXT,
        defect_type TEXT,
        road_name TEXT,
        zone TEXT,
        lat REAL,
        lng REAL,
        priority TEXT,
        status TEXT,
        assigned_agency TEXT,
        assigned_crew TEXT,
        estimated_cost_inr REAL,
        created_at TEXT,
        target_completion_date TEXT,
        materials_required TEXT,
        supervisor TEXT,
        notes TEXT,
        FOREIGN KEY (defect_id) REFERENCES road_defects(id)
    )
    """)

    # Vulnerable Pedestrians Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedestrian_alerts (
        id TEXT PRIMARY KEY,
        bus_id TEXT,
        timestamp TEXT,
        lat REAL,
        lng REAL,
        road_name TEXT,
        alert_type TEXT,
        vulnerability_level TEXT,
        pedestrian_count INTEGER,
        confidence REAL,
        snapshot_url TEXT,
        driver_notified INTEGER
    )
    """)

    # Traffic Density Snapshots Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS traffic_history (
        id TEXT PRIMARY KEY,
        bus_id TEXT,
        timestamp TEXT,
        lat REAL,
        lng REAL,
        road_name TEXT,
        zone TEXT,
        total_vehicles INTEGER,
        vehicle_breakdown TEXT,
        density_level TEXT,
        avg_flow_speed REAL,
        is_bottleneck INTEGER,
        bottleneck_cause TEXT
    )
    """)

    conn.commit()

    # Check if we should seed baseline sample data
    cursor.execute("SELECT COUNT(*) as count FROM road_defects")
    row = cursor.fetchone()
    if row["count"] == 0:
        seed_baseline_data(conn)

    conn.close()

def seed_baseline_data(conn):
    cursor = conn.cursor()
    now = datetime.now()

    sample_defects = [
        {
            "id": "DEF-2026-0801",
            "bus_id": "STRIDE-BUS-01",
            "defect_type": "pothole",
            "label": "Deep Pothole Crater (42cm)",
            "severity": "Severe",
            "confidence": 0.948,
            "lat": 28.6280,
            "lng": 77.2210,
            "road_name": "Barakhamba Road / Outer Circle",
            "zone": "Central Business District",
            "detected_at": (now - timedelta(hours=3, minutes=12)).isoformat(),
            "snapshot_url": "/api/evidence/sample_pothole_1.jpg",
            "bounding_box": json.dumps([0.35, 0.62, 0.28, 0.22]),
            "status": "Work Order Assigned",
            "assigned_team": "PWD Rapid Repair Unit-3",
            "estimated_repair_cost": 8500.0,
            "verification_notes": "Deep edge shear detected near bus stop lane. High risk of tyre damage."
        },
        {
            "id": "DEF-2026-0802",
            "bus_id": "STRIDE-BUS-03",
            "defect_type": "missing_divider",
            "label": "Broken Concrete Median (6m gap)",
            "severity": "Critical",
            "confidence": 0.912,
            "lat": 28.5850,
            "lng": 77.2150,
            "road_name": "Aurobindo Marg Corridor",
            "zone": "South Tech Parks",
            "detected_at": (now - timedelta(hours=5, minutes=45)).isoformat(),
            "snapshot_url": "/api/evidence/sample_divider_1.jpg",
            "bounding_box": json.dumps([0.48, 0.45, 0.15, 0.35]),
            "status": "Verified",
            "assigned_team": None,
            "estimated_repair_cost": 24000.0,
            "verification_notes": "Median barrier breached by prior collision. Unsafe U-turns reported."
        },
        {
            "id": "DEF-2026-0803",
            "bus_id": "STRIDE-BUS-06",
            "defect_type": "missing_zebra_crossing",
            "label": "Faded Zebra Crossing Near School",
            "severity": "High",
            "confidence": 0.887,
            "lat": 28.6420,
            "lng": 77.2280,
            "road_name": "Asaf Ali Road Junction",
            "zone": "Central Business District",
            "detected_at": (now - timedelta(hours=1, minutes=20)).isoformat(),
            "snapshot_url": "/api/evidence/sample_crossing_1.jpg",
            "bounding_box": json.dumps([0.22, 0.70, 0.55, 0.20]),
            "status": "Detected",
            "assigned_team": None,
            "estimated_repair_cost": 6500.0,
            "verification_notes": "Thermoplastic paint eroded by 70%. High pedestrian crossing frequency."
        },
        {
            "id": "DEF-2026-0804",
            "bus_id": "STRIDE-BUS-05",
            "defect_type": "waterlogging",
            "label": "Underpass Water Inundation (22cm)",
            "severity": "Critical",
            "confidence": 0.962,
            "lat": 28.6180,
            "lng": 77.2650,
            "road_name": "Vikas Marg Eastbound Underpass",
            "zone": "East Trans-River Corridor",
            "detected_at": (now - timedelta(minutes=45)).isoformat(),
            "snapshot_url": "/api/evidence/sample_water_1.jpg",
            "bounding_box": json.dumps([0.15, 0.55, 0.70, 0.40]),
            "status": "Work Order Assigned",
            "assigned_team": "MCD Stormwater Drainage Crew",
            "estimated_repair_cost": 15000.0,
            "verification_notes": "Drainage grate clogged with silt. Left two lanes submerged."
        },
        {
            "id": "DEF-2026-0805",
            "bus_id": "STRIDE-BUS-04",
            "defect_type": "damaged_traffic_sign",
            "label": "Bent Speed Limit 50km/h Signboard",
            "severity": "Medium",
            "confidence": 0.895,
            "lat": 28.5350,
            "lng": 77.1950,
            "road_name": "Mehrauli-Gurgaon Link Road",
            "zone": "South Tech Parks",
            "detected_at": (now - timedelta(hours=8, minutes=10)).isoformat(),
            "snapshot_url": "/api/evidence/sample_sign_1.jpg",
            "bounding_box": json.dumps([0.72, 0.25, 0.18, 0.30]),
            "status": "Repaired",
            "assigned_team": "PWD Signage Maintenance",
            "estimated_repair_cost": 3200.0,
            "verification_notes": "Pole straightened and retroreflective sheet replaced.",
            "repaired_at": (now - timedelta(hours=1)).isoformat()
        }
    ]

    for d in sample_defects:
        cursor.execute("""
        INSERT INTO road_defects (
            id, bus_id, defect_type, label, severity, confidence, lat, lng, road_name, zone,
            detected_at, snapshot_url, bounding_box, status, assigned_team, estimated_repair_cost,
            verification_notes, repaired_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["bus_id"], d["defect_type"], d["label"], d["severity"], d["confidence"],
            d["lat"], d["lng"], d["road_name"], d["zone"], d["detected_at"], d["snapshot_url"],
            d["bounding_box"], d["status"], d.get("assigned_team"), d["estimated_repair_cost"],
            d["verification_notes"], d.get("repaired_at")
        ))

    # Baseline Work Orders
    cursor.execute("""
    INSERT INTO work_orders (
        id, defect_id, defect_type, road_name, zone, lat, lng, priority, status,
        assigned_agency, assigned_crew, estimated_cost_inr, created_at, target_completion_date,
        materials_required, supervisor, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "WO-2026-9041", "DEF-2026-0801", "pothole", "Barakhamba Road / Outer Circle", "Central Business District",
        28.6280, 77.2210, "Critical", "In Progress", "PWD Central Division", "Rapid Asphalt Crew #2",
        8500.0, (now - timedelta(hours=2)).isoformat(), (now + timedelta(hours=22)).isoformat(),
        json.dumps(["Cold Bituminous Mix (800kg)", "Tack Coat Emulsion", "Plate Compactor"]),
        "Engr. Sanjeev Varma", "Urgent dispatch to prevent commuter accidents near Metro Gate 4."
    ))

    cursor.execute("""
    INSERT INTO work_orders (
        id, defect_id, defect_type, road_name, zone, lat, lng, priority, status,
        assigned_agency, assigned_crew, estimated_cost_inr, created_at, target_completion_date,
        materials_required, supervisor, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "WO-2026-9042", "DEF-2026-0804", "waterlogging", "Vikas Marg Eastbound Underpass", "East Trans-River Corridor",
        28.6180, 77.2650, "Critical", "Dispatched", "MCD Stormwater Dept", "Suction Pump Unit 7",
        15000.0, (now - timedelta(minutes=30)).isoformat(), (now + timedelta(hours=4)).isoformat(),
        json.dumps(["High-Capacity Dewatering Pump", "Silt Excavation Hose", "Traffic Diversion Cones"]),
        "Inspector Anirudh Nair", "High water level blocking eastbound lane. Emergency pump en route."
    ))

    # Baseline ANPR Hit-and-Run Incident
    cursor.execute("""
    INSERT INTO incidents (
        id, incident_type, bus_id, timestamp, lat, lng, road_name, offender_vehicle,
        license_plate, anpr_confidence, estimated_speed_kmh, trajectory_vector,
        snapshot_url, video_clip_url, status, police_fir_number, law_enforcement_notified
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "INC-2026-0199", "Hit-and-Run Collision with Cyclist & Speeding Away", "STRIDE-BUS-02",
        (now - timedelta(hours=1, minutes=15)).isoformat(), 28.5980, 77.2250, "Lodhi Road Boulevard",
        json.dumps({"make": "Hyundai", "model": "Creta SX Black", "type": "SUV", "color": "Phantom Black"}),
        "DL-3C-CN-9428", 97.4, 78.5, "North-West towards Ring Road via Khan Market Exit",
        "/api/evidence/incident_sample_1.jpg", "/api/evidence/incident_sample_1.mp4",
        "Police Notified", "FIR-DL-2026-08832", 1
    ))

    cursor.execute("""
    INSERT INTO incidents (
        id, incident_type, bus_id, timestamp, lat, lng, road_name, offender_vehicle,
        license_plate, anpr_confidence, estimated_speed_kmh, trajectory_vector,
        snapshot_url, video_clip_url, status, police_fir_number, law_enforcement_notified
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "INC-2026-0200", "Rash Driving, Sudden Lane Cut-off & Tailgating", "STRIDE-BUS-04",
        (now - timedelta(minutes=22)).isoformat(), 28.6320, 77.1650, "Patel Road High-Speed Stretch",
        json.dumps({"make": "Mahindra", "model": "Thar Desert Edition", "type": "Offroad SUV", "color": "Rocky Beige"}),
        "HR-26-DK-4091", 95.8, 86.0, "Westbound weaving between commuter lanes",
        "/api/evidence/incident_sample_2.jpg", None,
        "Active Investigation", None, 1
    ))

    conn.commit()

# Helper accessors
def db_save_defect(defect: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO road_defects (
        id, bus_id, defect_type, label, severity, confidence, lat, lng, road_name, zone,
        detected_at, snapshot_url, bounding_box, status, assigned_team, estimated_repair_cost,
        verification_notes, repaired_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        defect["id"], defect["bus_id"], defect["defect_type"], defect["label"], defect["severity"],
        defect["confidence"], defect["lat"], defect["lng"], defect["road_name"], defect["zone"],
        defect["detected_at"], defect["snapshot_url"], json.dumps(defect.get("bounding_box", [])),
        defect.get("status", "Detected"), defect.get("assigned_team"), defect.get("estimated_repair_cost", 5000.0),
        defect.get("verification_notes"), defect.get("repaired_at")
    ))
    conn.commit()
    conn.close()

def db_save_incident(incident: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO incidents (
        id, incident_type, bus_id, timestamp, lat, lng, road_name, offender_vehicle,
        license_plate, anpr_confidence, estimated_speed_kmh, trajectory_vector,
        snapshot_url, video_clip_url, status, police_fir_number, law_enforcement_notified
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident["id"], incident["incident_type"], incident["bus_id"], incident["timestamp"],
        incident["lat"], incident["lng"], incident["road_name"],
        json.dumps(incident.get("offender_vehicle", {})), incident["license_plate"],
        incident["anpr_confidence"], incident["estimated_speed_kmh"], incident["trajectory_vector"],
        incident["snapshot_url"], incident.get("video_clip_url"), incident.get("status", "Active Investigation"),
        incident.get("police_fir_number"), 1 if incident.get("law_enforcement_notified", True) else 0
    ))
    conn.commit()
    conn.close()

def db_save_pedestrian_alert(alert: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO pedestrian_alerts (
        id, bus_id, timestamp, lat, lng, road_name, alert_type, vulnerability_level,
        pedestrian_count, confidence, snapshot_url, driver_notified
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert["id"], alert["bus_id"], alert["timestamp"], alert["lat"], alert["lng"],
        alert["road_name"], alert["alert_type"], alert["vulnerability_level"],
        alert["pedestrian_count"], alert["confidence"], alert["snapshot_url"],
        1 if alert.get("driver_notified", True) else 0
    ))
    conn.commit()
    conn.close()

def db_create_work_order(wo: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO work_orders (
        id, defect_id, defect_type, road_name, zone, lat, lng, priority, status,
        assigned_agency, assigned_crew, estimated_cost_inr, created_at, target_completion_date,
        materials_required, supervisor, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        wo["id"], wo["defect_id"], wo["defect_type"], wo["road_name"], wo["zone"],
        wo["lat"], wo["lng"], wo["priority"], wo["status"], wo["assigned_agency"],
        wo.get("assigned_crew"), wo["estimated_cost_inr"], wo["created_at"],
        wo["target_completion_date"], json.dumps(wo.get("materials_required", [])),
        wo["supervisor"], wo["notes"]
    ))
    # Update related defect status
    cursor.execute("UPDATE road_defects SET status = 'Work Order Assigned', assigned_team = ? WHERE id = ?",
                   (wo.get("assigned_crew") or wo["assigned_agency"], wo["defect_id"]))
    conn.commit()
    conn.close()

def db_update_defect_status(defect_id: str, new_status: str, notes: str = None, cost: float = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat() if new_status == "Repaired" else None
    cursor.execute("""
    UPDATE road_defects
    SET status = ?, verification_notes = COALESCE(?, verification_notes),
        estimated_repair_cost = COALESCE(?, estimated_repair_cost),
        repaired_at = COALESCE(?, repaired_at)
    WHERE id = ?
    """, (new_status, notes, cost, now_str, defect_id))
    conn.commit()
    conn.close()

def db_get_all_defects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM road_defects ORDER BY detected_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        if r.get("bounding_box"):
            try:
                r["bounding_box"] = json.loads(r["bounding_box"])
            except Exception:
                r["bounding_box"] = [0.3, 0.4, 0.4, 0.3]
    conn.close()
    return rows

def db_get_all_incidents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        if r.get("offender_vehicle"):
            try:
                r["offender_vehicle"] = json.loads(r["offender_vehicle"])
            except Exception:
                r["offender_vehicle"] = {}
    conn.close()
    return rows

def db_get_all_work_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM work_orders ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        if r.get("materials_required"):
            try:
                r["materials_required"] = json.loads(r["materials_required"])
            except Exception:
                r["materials_required"] = []
    conn.close()
    return rows
