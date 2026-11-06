import asyncio
import json
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, DATA_DIR, STATIC_DIR, EVIDENCE_DIR, BUS_FLEET, ZONES, DEFECT_TYPES
from backend.database import (
    init_db, db_get_all_defects, db_get_all_incidents, db_get_all_work_orders,
    db_update_defect_status, db_create_work_order, db_save_defect, db_save_incident
)
from backend.edge_engine import fleet_engine, BusEdgeSimulator

app = FastAPI(title="S.T.R.I.D.E Urban Sensing & AI Command Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

# Background simulator loop task
simulator_running = True

async def background_simulation_loop():
    while simulator_running:
        try:
            # Advance fleet position by 1 second
            fleet_engine.tick(1.0)
            telemetry = fleet_engine.get_fleet_telemetry()
            
            # Broadcast to connected WebSockets
            payload = {
                "type": "FLEET_UPDATE",
                "timestamp": datetime.now().isoformat(),
                "fleet": telemetry,
                "summary": {
                    "total_buses_active": len(telemetry),
                    "total_cameras_streaming": len(telemetry) * 4,
                    "avg_edge_cpu": round(sum(b["edge_cpu"] for b in telemetry) / len(telemetry), 1),
                    "avg_speed_kmh": round(sum(b["speed_kmh"] for b in telemetry) / len(telemetry), 1),
                    "total_bandwidth_kbps": round(sum(b["bandwidth_kbps"] for b in telemetry), 1)
                }
            }
            await manager.broadcast(payload)
        except Exception as e:
            print(f"Simulation tick error: {e}")
        await asyncio.sleep(1.0)

def ensure_baseline_evidence_files():
    """Generates baseline evidence JPGs if not already present."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    bus = fleet_engine.get_bus("STRIDE-BUS-01") or list(fleet_engine.buses.values())[0]

    files_to_check = [
        ("sample_pothole_1.jpg", "pothole", "Deep Pothole Crater", {"confidence": 0.948, "severity": "Severe"}),
        ("sample_divider_1.jpg", "missing_divider", "Broken Concrete Median", {"confidence": 0.912, "severity": "Critical"}),
        ("sample_crossing_1.jpg", "missing_zebra_crossing", "Faded Zebra Crossing", {"confidence": 0.887, "severity": "High"}),
        ("sample_water_1.jpg", "waterlogging", "Severe Water Inundation", {"confidence": 0.962, "severity": "Critical"}),
        ("sample_sign_1.jpg", "damaged_traffic_sign", "Damaged Signboard", {"confidence": 0.895, "severity": "Medium"}),
        ("incident_sample_1.jpg", "incident", "Hit-and-Run Collision", {"plate": "DL-3C-CN-9428", "confidence": 97.4, "speed": 78.5}),
        ("incident_sample_2.jpg", "anpr", "Rash Driving & Swerving", {"plate": "HR-26-DK-4091", "confidence": 95.8, "speed": 86.0}),
    ]

    for fname, cat, label, meta in files_to_check:
        target = EVIDENCE_DIR / fname
        if not target.exists():
            try:
                img_url = bus.generate_evidence_image(title=label, category=cat, label=label, metadata=meta)
                # Copy or rename to standard target name
                gen_name = img_url.split("/")[-1]
                gen_path = EVIDENCE_DIR / gen_name
                if gen_path.exists():
                    gen_path.replace(target)
            except Exception as ex:
                print(f"Error generating sample evidence image {fname}: {ex}")

@app.on_event("startup")
async def on_startup():
    init_db()
    ensure_baseline_evidence_files()
    asyncio.create_task(background_simulation_loop())

# REST API Endpoints

@app.get("/api/fleet")
def get_fleet():
    telemetry = fleet_engine.get_fleet_telemetry()
    return {"status": "success", "fleet": telemetry}

@app.get("/api/defects")
def get_defects():
    defects = db_get_all_defects()
    return {"status": "success", "total": len(defects), "defects": defects}

class VerifyDefectRequest(BaseModel):
    defect_id: str
    status: str
    notes: Optional[str] = None
    estimated_cost: Optional[float] = None

@app.post("/api/defects/verify")
async def verify_defect(req: VerifyDefectRequest):
    db_update_defect_status(req.defect_id, req.status, req.notes, req.estimated_cost)
    # Broadcast defect update
    await manager.broadcast({
        "type": "DEFECT_UPDATED",
        "defect_id": req.defect_id,
        "new_status": req.status
    })
    return {"status": "success", "message": f"Defect {req.defect_id} updated to {req.status}"}

@app.get("/api/incidents")
def get_incidents():
    incidents = db_get_all_incidents()
    return {"status": "success", "total": len(incidents), "incidents": incidents}

class PoliceNotificationRequest(BaseModel):
    incident_id: str
    fir_number: Optional[str] = None
    status: Optional[str] = "Police Dispatched"

@app.post("/api/incidents/notify-police")
async def notify_police(req: PoliceNotificationRequest):
    from backend.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    fir = req.fir_number or f"FIR-PCR-{random.randint(10000, 99999)}"
    cursor.execute("""
    UPDATE incidents
    SET status = ?, police_fir_number = ?, law_enforcement_notified = 1
    WHERE id = ?
    """, (req.status, fir, req.incident_id))
    conn.commit()
    conn.close()

    await manager.broadcast({
        "type": "INCIDENT_DISPATCHED",
        "incident_id": req.incident_id,
        "fir_number": fir,
        "status": req.status
    })
    return {"status": "success", "incident_id": req.incident_id, "fir_number": fir}

@app.get("/api/work-orders")
def get_work_orders():
    orders = db_get_all_work_orders()
    return {"status": "success", "total": len(orders), "work_orders": orders}

class CreateWorkOrderRequest(BaseModel):
    defect_id: str
    defect_type: str
    road_name: str
    zone: str
    lat: float
    lng: float
    priority: str
    assigned_agency: str
    assigned_crew: Optional[str] = None
    estimated_cost_inr: float
    target_completion_days: int = 3
    materials_required: List[str] = []
    supervisor: str
    notes: str

@app.post("/api/work-orders")
async def create_work_order(req: CreateWorkOrderRequest):
    now = datetime.now()
    wo_id = f"WO-2026-{random.randint(1000, 9999)}"
    target_date = (now + timedelta(days=req.target_completion_days)).strftime("%Y-%m-%d")

    wo_data = {
        "id": wo_id,
        "defect_id": req.defect_id,
        "defect_type": req.defect_type,
        "road_name": req.road_name,
        "zone": req.zone,
        "lat": req.lat,
        "lng": req.lng,
        "priority": req.priority,
        "status": "Dispatched",
        "assigned_agency": req.assigned_agency,
        "assigned_crew": req.assigned_crew or "Municipal PWD Strike Team",
        "estimated_cost_inr": req.estimated_cost_inr,
        "created_at": now.isoformat(),
        "target_completion_date": target_date,
        "materials_required": req.materials_required or ["Standard Repair Materials"],
        "supervisor": req.supervisor,
        "notes": req.notes
    }

    db_create_work_order(wo_data)

    await manager.broadcast({
        "type": "WORK_ORDER_CREATED",
        "work_order": wo_data
    })
    return {"status": "success", "work_order": wo_data}

class UpdateWorkOrderStatusRequest(BaseModel):
    work_order_id: str
    defect_id: str
    status: str

@app.post("/api/work-orders/status")
async def update_work_order_status(req: UpdateWorkOrderStatusRequest):
    from backend.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE work_orders SET status = ? WHERE id = ?", (req.status, req.work_order_id))
    if req.status == "Repaired" or req.status == "Closed":
        cursor.execute("UPDATE road_defects SET status = 'Repaired', repaired_at = ? WHERE id = ?",
                       (datetime.now().isoformat(), req.defect_id))
    conn.commit()
    conn.close()

    await manager.broadcast({
        "type": "WORK_ORDER_STATUS_CHANGED",
        "work_order_id": req.work_order_id,
        "new_status": req.status
    })
    return {"status": "success", "work_order_id": req.work_order_id, "new_status": req.status}

@app.get("/api/analytics/traffic")
def get_traffic_analytics():
    # Traffic distribution & bottleneck points
    zones_traffic = [
        {"zone": "Central Business District", "density_index": 78.4, "avg_speed_kmh": 24.2, "bottlenecks": 4, "vehicle_breakdown": {"cars": 52, "2w": 28, "buses": 12, "trucks": 4, "autos": 4}},
        {"zone": "North Academic District", "density_index": 54.1, "avg_speed_kmh": 36.5, "bottlenecks": 2, "vehicle_breakdown": {"cars": 44, "2w": 38, "buses": 8, "trucks": 3, "autos": 7}},
        {"zone": "South Tech Parks", "density_index": 82.6, "avg_speed_kmh": 21.8, "bottlenecks": 6, "vehicle_breakdown": {"cars": 60, "2w": 20, "buses": 10, "trucks": 5, "autos": 5}},
        {"zone": "East Trans-River Link", "density_index": 68.9, "avg_speed_kmh": 29.4, "bottlenecks": 3, "vehicle_breakdown": {"cars": 40, "2w": 35, "buses": 14, "trucks": 6, "autos": 5}},
        {"zone": "West Industrial Belt", "density_index": 61.2, "avg_speed_kmh": 32.0, "bottlenecks": 3, "vehicle_breakdown": {"cars": 30, "2w": 32, "buses": 8, "trucks": 24, "autos": 6}}
    ]

    hourly_trend = [
        {"hour": "06:00", "volume": 1420, "speed": 48.2},
        {"hour": "08:00", "volume": 5890, "speed": 22.4},
        {"hour": "10:00", "volume": 6450, "speed": 18.9},
        {"hour": "12:00", "volume": 4120, "speed": 31.5},
        {"hour": "14:00", "volume": 3890, "speed": 34.0},
        {"hour": "16:00", "volume": 5200, "speed": 26.2},
        {"hour": "18:00", "volume": 7120, "speed": 16.8},
        {"hour": "20:00", "volume": 6100, "speed": 21.0},
        {"hour": "22:00", "volume": 2900, "speed": 42.5},
    ]

    return {
        "status": "success",
        "zones": zones_traffic,
        "hourly_trend": hourly_trend,
        "city_wide_congestion_level": "High (Peak Transit Hours)",
        "active_bottleneck_corridors": [
            {"corridor": "Barakhamba - Connaught Outer Circle", "delay_min": 14.5, "cause": "Pothole road narrowing & high junction load"},
            {"corridor": "Vikas Marg East Underpass", "delay_min": 22.0, "cause": "Waterlogging submersing left lane"},
            {"corridor": "Aurobindo Marg Tech Intersection", "delay_min": 12.0, "cause": "Broken median causing unauthorized U-turns"}
        ]
    }

@app.get("/api/analytics/od-matrix")
def get_od_matrix():
    # Origin-Destination matrix between city zones
    zone_names = ["CBD Central", "North Academic", "South Tech", "East River", "West Industrial"]
    matrix = [
        # Origin: CBD
        {"origin": "CBD Central", "dest": "North Academic", "volume": 3420, "avg_delay_min": 6.5, "congestion_score": 0.65},
        {"origin": "CBD Central", "dest": "South Tech", "volume": 6890, "avg_delay_min": 16.2, "congestion_score": 0.88},
        {"origin": "CBD Central", "dest": "East River", "volume": 4120, "avg_delay_min": 12.8, "congestion_score": 0.74},
        {"origin": "CBD Central", "dest": "West Industrial", "volume": 2980, "avg_delay_min": 8.4, "congestion_score": 0.58},
        
        # Origin: North Academic
        {"origin": "North Academic", "dest": "CBD Central", "volume": 3890, "avg_delay_min": 7.2, "congestion_score": 0.68},
        {"origin": "North Academic", "dest": "South Tech", "volume": 5210, "avg_delay_min": 19.5, "congestion_score": 0.91},
        {"origin": "North Academic", "dest": "East River", "volume": 2340, "avg_delay_min": 9.1, "congestion_score": 0.60},
        {"origin": "North Academic", "dest": "West Industrial", "volume": 1820, "avg_delay_min": 5.8, "congestion_score": 0.45},

        # Origin: South Tech
        {"origin": "South Tech", "dest": "CBD Central", "volume": 7100, "avg_delay_min": 18.4, "congestion_score": 0.92},
        {"origin": "South Tech", "dest": "North Academic", "volume": 4890, "avg_delay_min": 17.8, "congestion_score": 0.86},
        {"origin": "South Tech", "dest": "East River", "volume": 3950, "avg_delay_min": 14.2, "congestion_score": 0.78},
        {"origin": "South Tech", "dest": "West Industrial", "volume": 3120, "avg_delay_min": 11.5, "congestion_score": 0.69},

        # Origin: East River
        {"origin": "East River", "dest": "CBD Central", "volume": 5400, "avg_delay_min": 15.0, "congestion_score": 0.82},
        {"origin": "East River", "dest": "South Tech", "volume": 4200, "avg_delay_min": 16.5, "congestion_score": 0.85},

        # Origin: West Industrial
        {"origin": "West Industrial", "dest": "CBD Central", "volume": 3600, "avg_delay_min": 9.8, "congestion_score": 0.62},
        {"origin": "West Industrial", "dest": "South Tech", "volume": 3400, "avg_delay_min": 13.0, "congestion_score": 0.72}
    ]
    return {"status": "success", "zones": zone_names, "matrix": matrix}

@app.get("/api/analytics/rqi-zones")
def get_rqi_zones():
    # Municipal Road Quality Index by Zone
    rqi_data = [
        {"zone_id": "ZN-CENTRAL", "zone_name": "Central Business & Government District", "rqi_score": 84.5, "pothole_count": 8, "missing_infra_count": 3, "total_km_surveyed": 142.6, "status": "Fair"},
        {"zone_id": "ZN-NORTH", "zone_name": "North Academic & Residential Quarter", "rqi_score": 88.2, "pothole_count": 5, "missing_infra_count": 2, "total_km_surveyed": 118.0, "status": "Good"},
        {"zone_id": "ZN-SOUTH", "zone_name": "South Tech Parks & Suburban Hub", "rqi_score": 72.8, "pothole_count": 16, "missing_infra_count": 7, "total_km_surveyed": 194.5, "status": "Poor"},
        {"zone_id": "ZN-EAST", "zone_name": "East Trans-River Commercial Corridor", "rqi_score": 68.4, "pothole_count": 22, "missing_infra_count": 9, "total_km_surveyed": 165.2, "status": "Critical Attention"},
        {"zone_id": "ZN-WEST", "zone_name": "West Industrial & Transit Corridor", "rqi_score": 76.0, "pothole_count": 14, "missing_infra_count": 5, "total_km_surveyed": 132.8, "status": "Fair"}
    ]
    return {"status": "success", "rqi_zones": rqi_data, "city_average_rqi": 77.98}

class SimulateTriggerRequest(BaseModel):
    bus_id: str
    event_category: str  # defect, incident, pedestrian, waterlogging
    event_type: Optional[str] = "pothole"
    severity: Optional[str] = "Severe"

@app.post("/api/simulate/trigger")
async def simulate_trigger(req: SimulateTriggerRequest):
    bus = fleet_engine.get_bus(req.bus_id)
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus {req.bus_id} not found in fleet")

    result = None
    if req.event_category == "defect":
        result = bus.trigger_defect_event(req.event_type, req.severity)
        await manager.broadcast({
            "type": "NEW_DEFECT_DETECTED",
            "defect": result
        })
    elif req.event_category == "incident":
        result = bus.trigger_incident_event(req.event_type or "Hit-and-Run Collision & Speeding Offender")
        await manager.broadcast({
            "type": "CRITICAL_INCIDENT_ALARM",
            "incident": result
        })
    elif req.event_category == "pedestrian":
        result = bus.trigger_pedestrian_event(req.event_type or "School Children Crossing Zone")
        await manager.broadcast({
            "type": "PEDESTRIAN_SAFETY_ALERT",
            "alert": result
        })
    elif req.event_category == "waterlogging":
        result = bus.trigger_defect_event("waterlogging", "Critical")
        await manager.broadcast({
            "type": "NEW_DEFECT_DETECTED",
            "defect": result
        })
    else:
        raise HTTPException(status_code=400, detail=f"Unknown category {req.event_category}")

    return {"status": "success", "event_category": req.event_category, "data": result}

@app.get("/api/evidence/{filename}")
def get_evidence_image(filename: str):
    file_path = EVIDENCE_DIR / filename
    if not file_path.exists():
        # Fallback to sample if specific image not found
        file_path = EVIDENCE_DIR / "sample_pothole_1.jpg"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Evidence file not found")
    return FileResponse(file_path, media_type="image/jpeg")

# WebSocket Endpoint for real-time live map & edge telemetry
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send immediate initial state
        initial_telemetry = fleet_engine.get_fleet_telemetry()
        await websocket.send_json({
            "type": "INITIAL_SYNC",
            "fleet": initial_telemetry,
            "timestamp": datetime.now().isoformat()
        })
        while True:
            # Receive client ping or commands
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"type": "PONG", "timestamp": datetime.now().isoformat()})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Mount Static Frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>S.T.R.I.D.E Server running. Frontend initializing...</h1>")
