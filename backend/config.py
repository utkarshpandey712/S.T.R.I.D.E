import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "frontend"
EVIDENCE_DIR = DATA_DIR / "evidence"

DATA_DIR.mkdir(exist_ok=True)
EVIDENCE_DIR.mkdir(exist_ok=True)

# City & Fleet Setup (Central Metropolis GIS Corridors)
CITY_CENTER = {"lat": 28.6139, "lng": 77.2090, "name": "Capital Metropolitan Transit Region"}

BUS_ROUTES = [
    {
        "route_id": "RT-101",
        "name": "Connaught Hub - Outer Ring Expressway",
        "color": "#00e5ff",
        "waypoints": [
            [28.6315, 77.2167], [28.6250, 77.2280], [28.6080, 77.2350],
            [28.5900, 77.2400], [28.5700, 77.2300], [28.5600, 77.2050],
            [28.5800, 77.1850], [28.6100, 77.1950], [28.6315, 77.2167]
        ]
    },
    {
        "route_id": "RT-204",
        "name": "North University - South Tech District",
        "color": "#00e676",
        "waypoints": [
            [28.6850, 77.2100], [28.6600, 77.2200], [28.6300, 77.2150],
            [28.5900, 77.2100], [28.5500, 77.2000], [28.5200, 77.1850],
            [28.5500, 77.2000], [28.5900, 77.2100], [28.6300, 77.2150],
            [28.6850, 77.2100]
        ]
    },
    {
        "route_id": "RT-305",
        "name": "East River Corridor - West Commercial Axis",
        "color": "#ff9100",
        "waypoints": [
            [28.6200, 77.2800], [28.6180, 77.2500], [28.6150, 77.2100],
            [28.6220, 77.1700], [28.6350, 77.1300], [28.6220, 77.1700],
            [28.6150, 77.2100], [28.6180, 77.2500], [28.6200, 77.2800]
        ]
    },
    {
        "route_id": "RT-412",
        "name": "Heritage Old Quarter - Airport Express Link",
        "color": "#e040fb",
        "waypoints": [
            [28.6550, 77.2350], [28.6350, 77.2200], [28.6050, 77.1900],
            [28.5750, 77.1500], [28.5550, 77.0850], [28.5750, 77.1500],
            [28.6050, 77.1900], [28.6350, 77.2200], [28.6550, 77.2350]
        ]
    },
    {
        "route_id": "RT-509",
        "name": "Medical Center - Industrial Outer Belt",
        "color": "#ffd600",
        "waypoints": [
            [28.5680, 77.2100], [28.5400, 77.2400], [28.5100, 77.2600],
            [28.4900, 77.2300], [28.5100, 77.1900], [28.5400, 77.1700],
            [28.5680, 77.2100]
        ]
    }
]

BUS_FLEET = [
    {"bus_id": "STRIDE-BUS-01", "route_id": "RT-101", "driver": "Rajesh Kumar", "plate": "DL-1PC-8421", "model": "Volvo 9400 B11R Low-Floor Electric", "cameras": 4},
    {"bus_id": "STRIDE-BUS-02", "route_id": "RT-101", "driver": "Sunil Verma", "plate": "DL-1PC-8422", "model": "Tata Starbus EV Urban", "cameras": 4},
    {"bus_id": "STRIDE-BUS-03", "route_id": "RT-204", "driver": "Amit Sharma", "plate": "DL-1PC-9104", "model": "Ashok Leyland Switch EiV12", "cameras": 4},
    {"bus_id": "STRIDE-BUS-04", "route_id": "RT-204", "driver": "Deepak Yadav", "plate": "DL-1PC-9105", "model": "JBM ECO-LIFE e9 Electric", "cameras": 4},
    {"bus_id": "STRIDE-BUS-05", "route_id": "RT-305", "driver": "Mohammad Rizwan", "plate": "DL-1PC-3310", "model": "Tata Ultra 9m Urban AC", "cameras": 4},
    {"bus_id": "STRIDE-BUS-06", "route_id": "RT-412", "driver": "Gurpreet Singh", "plate": "DL-1PC-7702", "model": "Volvo Electric BRT Articulated", "cameras": 4},
    {"bus_id": "STRIDE-BUS-07", "route_id": "RT-509", "driver": "Vikas Mehra", "plate": "DL-1PC-5544", "model": "Ashok Leyland Circuit-F Electric", "cameras": 4},
]

DEFECT_TYPES = {
    "pothole": {"label": "Pothole / Road Depression", "severity_levels": ["Minor (10-25cm)", "Moderate (25-50cm)", "Severe (>50cm Deep)"], "default_priority": "High", "icon": "crater"},
    "damaged_road": {"label": "Alligator Cracking & Surface Distress", "severity_levels": ["Superficial", "Medium Distress", "Structural Base Failure"], "default_priority": "Medium", "icon": "road"},
    "missing_divider": {"label": "Missing / Damaged Road Divider", "severity_levels": ["Broken Section (2-5m)", "Missing Median (>10m)", "No Reflector Studs"], "default_priority": "Critical", "icon": "divider"},
    "missing_zebra_crossing": {"label": "Faded / Missing Zebra Crossing", "severity_levels": ["50% Faded", "Completely Worn Off", "Unmarked Junction"], "default_priority": "High", "icon": "crossing"},
    "damaged_traffic_sign": {"label": "Damaged / Obstructed Traffic Sign", "severity_levels": ["Vandalized/Graffiti", "Bent/Misaligned", "Foliage Obstructed"], "default_priority": "Medium", "icon": "sign"},
    "missing_traffic_sign": {"label": "Missing Mandatory Signboard (Stop/Speed/Yield)", "severity_levels": ["Missing Stop Sign", "Missing Speed Limit", "Missing School Zone"], "default_priority": "Critical", "icon": "sign-warning"},
    "waterlogging": {"label": "Severe Waterlogging & Flood Hazard", "severity_levels": ["Puddle (5-10cm)", "Lane Submerged (15-30cm)", "Full Road Inundated (>30cm)"], "default_priority": "Critical", "icon": "water"},
    "debris_hazard": {"label": "Debris / Fallen Tree / Dangerous Obstacle", "severity_levels": ["Kerbside Rubble", "Mid-Lane Obstacle", "Active Crash Debris"], "default_priority": "Critical", "icon": "hazard"}
}

ZONES = [
    {"id": "ZN-CENTRAL", "name": "Central Business & Government District", "lat": 28.6250, "lng": 77.2150},
    {"id": "ZN-NORTH", "name": "North Academic & Residential Quarter", "lat": 28.6700, "lng": 77.2150},
    {"id": "ZN-SOUTH", "name": "South Tech Parks & Suburban Hub", "lat": 28.5400, "lng": 77.2100},
    {"id": "ZN-EAST", "name": "East Trans-River Commercial Corridor", "lat": 28.6200, "lng": 77.2700},
    {"id": "ZN-WEST", "name": "West Industrial & Transit Corridor", "lat": 28.6300, "lng": 77.1400}
]

HOST = "0.0.0.0"
PORT = 8000
