from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class GPSCoordinate(BaseModel):
    lat: float
    lng: float
    bearing: Optional[float] = 0.0
    speed_kmh: Optional[float] = 0.0

class CameraInferenceDetection(BaseModel):
    id: str
    camera: str  # front, rear, left_kerb, right_kerb, cabin
    category: str  # defect, vehicle, pedestrian, incident, sign
    label: str
    confidence: float
    bbox: List[float]  # [x, y, width, height] normalized (0.0 to 1.0)
    details: Optional[Dict[str, Any]] = None

class BusTelemetry(BaseModel):
    bus_id: str
    route_id: str
    timestamp: str
    lat: float
    lng: float
    speed_kmh: float
    bearing: float
    passenger_count: int
    camera_health: Dict[str, str] = Field(default_factory=lambda: {
        "front": "ONLINE_4K", "rear": "ONLINE_1080P", "left_kerb": "ONLINE_1080P", "right_kerb": "ONLINE_1080P"
    })
    edge_cpu_load: float = 38.5
    edge_bandwidth_used_kb: float = 4.2
    active_detections: List[CameraInferenceDetection] = []
    traffic_density_level: str = "Medium"
    current_road_name: str = "Ring Road Expressway"

class RoadDefect(BaseModel):
    id: str
    bus_id: str
    defect_type: str  # pothole, damaged_road, missing_divider, etc.
    label: str
    severity: str  # Minor, Moderate, Severe
    confidence: float
    lat: float
    lng: float
    road_name: str
    zone: str
    detected_at: str
    snapshot_url: str
    bounding_box: List[float]
    status: str = "Detected"  # Detected, Verified, Work Order Assigned, Repaired
    assigned_team: Optional[str] = None
    estimated_repair_cost: Optional[float] = None
    verification_notes: Optional[str] = None
    repaired_at: Optional[str] = None

class TrafficDensityReport(BaseModel):
    id: str
    bus_id: str
    timestamp: str
    lat: float
    lng: float
    road_name: str
    zone: str
    total_vehicles_detected: int
    vehicle_breakdown: Dict[str, int]  # cars, buses, 2w, trucks, autos
    density_level: str  # Low, Moderate, High, Severe Congestion
    average_flow_speed_kmh: float
    is_bottleneck: bool
    bottleneck_cause: Optional[str] = None

class VulnerablePedestrianAlert(BaseModel):
    id: str
    bus_id: str
    timestamp: str
    lat: float
    lng: float
    road_name: str
    alert_type: str  # School Children Crossing, Blind Spot Pedestrian, Jaywalking Danger
    vulnerability_level: str  # Critical, High, Caution
    pedestrian_count: int
    confidence: float
    snapshot_url: str
    driver_notified: bool = True

class IncidentRecord(BaseModel):
    id: str
    incident_type: str  # Hit-and-Run Collision, Rash Driving / Swerving, Red Light Violation
    bus_id: str
    timestamp: str
    lat: float
    lng: float
    road_name: str
    offender_vehicle: Dict[str, Any]  # make, model, color, vehicle_type
    license_plate: str
    anpr_confidence: float  # percentage e.g. 96.8
    estimated_speed_kmh: float
    trajectory_vector: str
    snapshot_url: str
    video_clip_url: Optional[str] = None
    status: str = "Active Investigation"  # Active Investigation, Police Notified, Case Filed, Closed
    police_fir_number: Optional[str] = None
    law_enforcement_notified: bool = True

class WorkOrder(BaseModel):
    id: str
    defect_id: str
    defect_type: str
    road_name: str
    zone: str
    lat: float
    lng: float
    priority: str  # Critical, High, Medium, Low
    status: str  # Pending Approval, Dispatched, In Progress, Repaired, Closed
    assigned_agency: str  # PWD Central Division, Municipal Road Maintenance Dept
    assigned_crew: Optional[str] = None
    estimated_cost_inr: float
    created_at: str
    target_completion_date: str
    materials_required: List[str]
    supervisor: str
    notes: str

class ODMatrixFlow(BaseModel):
    origin_zone: str
    destination_zone: str
    flow_volume: int
    avg_transit_delay_min: float
    congestion_index: float

class MunicipalZoneRQI(BaseModel):
    zone_id: str
    zone_name: str
    rqi_score: float  # Road Quality Index 0 to 100
    pothole_count: int
    missing_infrastructure_count: int
    total_km_surveyed: float
    last_surveyed: str
    status: str  # Excellent, Fair, Poor, Hazardous
