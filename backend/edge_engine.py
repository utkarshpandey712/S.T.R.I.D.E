import math
import time
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

from backend.config import BUS_FLEET, BUS_ROUTES, DEFECT_TYPES, ZONES, EVIDENCE_DIR, BASE_DIR
from backend.database import db_save_defect, db_save_incident, db_save_pedestrian_alert

class BusEdgeSimulator:
    def __init__(self, bus_config: dict):
        self.bus_id = bus_config["bus_id"]
        self.route_id = bus_config["route_id"]
        self.driver = bus_config["driver"]
        self.plate = bus_config["plate"]
        self.model = bus_config["model"]
        self.cameras = ["front", "rear", "left_kerb", "right_kerb"]

        # Route waypoints
        route_meta = next((r for r in BUS_ROUTES if r["route_id"] == self.route_id), BUS_ROUTES[0])
        self.waypoints = route_meta["waypoints"]
        self.route_name = route_meta["name"]
        self.route_color = route_meta["color"]

        # Current state along waypoints
        self.current_segment = random.randint(0, len(self.waypoints) - 2)
        self.segment_progress = random.random()
        self.speed_kmh = random.uniform(28.0, 48.0)
        self.bearing = 45.0
        self.lat, self.lng = self.calculate_position()
        self.passenger_count = random.randint(18, 48)
        self.edge_cpu = random.uniform(32.0, 48.0)
        self.bandwidth_kbps = random.uniform(3.2, 5.8)

        # Dynamic AI detection state
        self.active_detections = []
        self.current_incident = None
        self.edge_fps = {"front": 30.0, "rear": 30.0, "left_kerb": 25.0, "right_kerb": 25.0}
        self.last_detection_time = time.time()
        self.road_name = self.get_approx_road_name()

    def calculate_position(self):
        p1 = self.waypoints[self.current_segment]
        p2 = self.waypoints[(self.current_segment + 1) % len(self.waypoints)]

        lat = p1[0] + (p2[0] - p1[0]) * self.segment_progress
        lng = p1[1] + (p2[1] - p1[1]) * self.segment_progress

        # Calculate bearing
        d_lat = p2[0] - p1[0]
        d_lng = p2[1] - p1[1]
        self.bearing = (math.degrees(math.atan2(d_lng, d_lat)) + 360) % 360

        return lat, lng

    def get_approx_road_name(self):
        corridors = [
            "Ring Road Outer Expressway", "Barakhamba Metro Corridor", "Aurobindo Transit Boulevard",
            "Vikas Marg East Bridge", "Janpath Avenue", "Mathura Road Arterial", "Patel Road West Link",
            "Lodhi Heritage Corridor", "Ridge Road Expressway"
        ]
        return corridors[self.current_segment % len(corridors)]

    def update_telemetry(self, dt_seconds: float = 1.0):
        # Progress along route
        # ~0.0001 deg lat is approx 11 meters
        # speed in m/s = speed_kmh / 3.6
        speed_mps = self.speed_kmh / 3.6
        dist_moved_meters = speed_mps * dt_seconds
        
        # Segment length approx in meters
        p1 = self.waypoints[self.current_segment]
        p2 = self.waypoints[(self.current_segment + 1) % len(self.waypoints)]
        d_lat_m = (p2[0] - p1[0]) * 111000
        d_lng_m = (p2[1] - p1[1]) * 111000 * math.cos(math.radians(p1[0]))
        seg_len_m = max(math.hypot(d_lat_m, d_lng_m), 50.0)

        step_fraction = dist_moved_meters / seg_len_m
        self.segment_progress += step_fraction

        if self.segment_progress >= 1.0:
            self.segment_progress = 0.0
            self.current_segment = (self.current_segment + 1) % (len(self.waypoints) - 1)
            self.road_name = self.get_approx_road_name()

        self.lat, self.lng = self.calculate_position()

        # Slight speed variation
        self.speed_kmh = max(15.0, min(62.0, self.speed_kmh + random.uniform(-2.5, 2.5)))
        self.edge_cpu = max(25.0, min(85.0, self.edge_cpu + random.uniform(-1.5, 1.5)))
        self.bandwidth_kbps = max(2.5, min(8.0, 3.5 + (len(self.active_detections) * 0.4)))

        # Update synthetic detections
        self.refresh_synthetic_detections()

    def refresh_synthetic_detections(self):
        # Generate periodic realistic vehicle / pedestrian / defect bounding boxes
        now = time.time()
        detections = []

        # Always detect a few forward vehicles
        car_types = ["Hatchback / Sedan", "SUV", "Delivery Truck", "Motorcycle (2-Wheeler)", "Auto-Rickshaw", "City Transit Bus"]
        colors = ["White", "Silver", "Midnight Blue", "Crimson Red", "Yellow-Green"]

        # Front camera: vehicles ahead
        num_vehicles = random.randint(2, 5)
        for i in range(num_vehicles):
            cx = 0.2 + (i * 0.16) + random.uniform(-0.04, 0.04)
            cy = 0.48 + random.uniform(-0.05, 0.08)
            w = 0.14 + random.uniform(-0.02, 0.04)
            h = 0.18 + random.uniform(-0.02, 0.05)
            c_type = random.choice(car_types)
            c_conf = round(random.uniform(0.88, 0.98), 3)
            v_speed = round(self.speed_kmh + random.uniform(-8.0, 12.0), 1)

            detections.append({
                "id": f"det-veh-{i}-{int(now)}",
                "camera": "front",
                "category": "vehicle",
                "label": f"{c_type} ({v_speed} km/h)",
                "confidence": c_conf,
                "bbox": [round(cx, 3), round(cy, 3), round(w, 3), round(h, 3)],
                "details": {"speed_kmh": v_speed, "color": random.choice(colors)}
            })

        # Rear camera: following vehicles
        detections.append({
            "id": f"det-rear-1-{int(now)}",
            "camera": "rear",
            "category": "vehicle",
            "label": f"Commercial Van (42.0 km/h)",
            "confidence": 0.945,
            "bbox": [0.42, 0.52, 0.22, 0.25],
            "details": {"speed_kmh": 42.0, "following_distance_m": 14.5}
        })

        # Left Kerb: Pedestrians / Bus Stop
        detections.append({
            "id": f"det-ped-1-{int(now)}",
            "camera": "left_kerb",
            "category": "pedestrian",
            "label": "Pedestrians at Bus Shelter (3 Persons)",
            "confidence": 0.915,
            "bbox": [0.25, 0.40, 0.30, 0.35],
            "details": {"count": 3, "zone": "Sidewalk Safe"}
        })

        # Right Kerb: Road divider & median
        detections.append({
            "id": f"det-div-1-{int(now)}",
            "camera": "right_kerb",
            "category": "sign",
            "label": "Concrete Median Barrier (Intact)",
            "confidence": 0.962,
            "bbox": [0.55, 0.45, 0.25, 0.40],
            "details": {"status": "Good condition"}
        })

        self.active_detections = detections

    def generate_evidence_image(self, title: str, category: str, label: str, metadata: dict) -> str:
        """Draws a high-definition synthetic visual evidence snapshot with bounding boxes, HUD telemetry, and camera timestamp."""
        img_w, img_h = 1280, 720
        img = Image.new("RGB", (img_w, img_h), color=(20, 26, 38))
        draw = ImageDraw.Draw(img)

        # Draw road perspective environment
        horizon_y = int(img_h * 0.45)
        # Sky gradient / upper background
        draw.rectangle([0, 0, img_w, horizon_y], fill=(30, 42, 60))
        # Urban skyline silhouette
        for x in range(0, img_w, 60):
            bh = random.randint(40, 120)
            draw.rectangle([x, horizon_y - bh, x + 50, horizon_y], fill=(22, 32, 48))

        # Road surface
        draw.polygon([(0, img_h), (int(img_w * 0.35), horizon_y), (int(img_w * 0.65), horizon_y), (img_w, img_h)], fill=(45, 50, 58))
        # Sidewalks
        draw.polygon([(0, img_h), (0, horizon_y), (int(img_w * 0.35), horizon_y)], fill=(70, 75, 82))
        draw.polygon([(img_w, img_h), (img_w, horizon_y), (int(img_w * 0.65), horizon_y)], fill=(70, 75, 82))

        # Lane dividers
        draw.line([(int(img_w * 0.5), horizon_y), (int(img_w * 0.5), img_h)], fill=(255, 235, 59), width=6)
        draw.line([(int(img_w * 0.42), horizon_y), (int(img_w * 0.25), img_h)], fill=(255, 255, 255), width=4)
        draw.line([(int(img_w * 0.58), horizon_y), (int(img_w * 0.75), img_h)], fill=(255, 255, 255), width=4)

        # Render Specific Event Subject
        if category == "pothole":
            # Draw pothole crater on road
            px, py = int(img_w * 0.42), int(img_h * 0.65)
            pw, ph = 240, 120
            draw.ellipse([px, py, px + pw, py + ph], fill=(15, 18, 22), outline=(180, 100, 50), width=4)
            # Inner fracture details
            draw.line([px + 30, py + 40, px + 180, py + 70], fill=(5, 5, 8), width=3)
            draw.line([px + 90, py + 20, px + 140, py + 95], fill=(5, 5, 8), width=3)

            # AI Bounding Box in neon cyan
            bbox = [px - 15, py - 15, px + pw + 15, py + ph + 15]
            draw.rectangle(bbox, outline=(0, 229, 255), width=3)
            # Label tag
            draw.rectangle([bbox[0], bbox[1] - 30, bbox[0] + 320, bbox[1]], fill=(0, 229, 255))
            draw.text((bbox[0] + 8, bbox[1] - 24), f"DEFECT: {label} | Conf: {metadata.get('confidence', 0.94):.1%}", fill=(0, 0, 0))

        elif category == "waterlogging":
            # Draw water reflection pool
            wx, wy = int(img_w * 0.20), int(img_h * 0.60)
            draw.ellipse([wx, wy, wx + 680, wy + 200], fill=(28, 70, 95), outline=(64, 196, 255), width=3)
            draw.rectangle([wx - 10, wy - 10, wx + 690, wy + 210], outline=(64, 196, 255), width=3)
            draw.rectangle([wx - 10, wy - 40, wx + 420, wy - 10], fill=(64, 196, 255))
            draw.text((wx, wy - 34), f"HAZARD: Severe Waterlogging (Depth: ~25cm)", fill=(0, 0, 0))

        elif category == "missing_zebra_crossing":
            # Draw faded eroded zebra strips
            zx, zy = int(img_w * 0.28), int(img_h * 0.70)
            for s in range(5):
                draw.rectangle([zx + (s * 80), zy, zx + (s * 80) + 45, zy + 100], fill=(140, 140, 140))
            draw.rectangle([zx - 15, zy - 15, zx + 420, zy + 115], outline=(255, 179, 0), width=3)
            draw.rectangle([zx - 15, zy - 45, zx + 400, zy - 15], fill=(255, 179, 0))
            draw.text((zx - 5, zy - 40), f"INFRA: Faded Pedestrian Crossing (72% Erosion)", fill=(0, 0, 0))

        elif category == "missing_divider":
            # Damaged median
            mx, my = int(img_w * 0.48), int(img_h * 0.52)
            draw.rectangle([mx, my, mx + 40, my + 220], fill=(160, 60, 60), outline=(255, 50, 50), width=2)
            draw.rectangle([mx - 20, my - 20, mx + 80, my + 240], outline=(255, 23, 68), width=3)
            draw.rectangle([mx - 20, my - 50, mx + 380, my - 20], fill=(255, 23, 68))
            draw.text((mx - 10, my - 44), f"CRITICAL INFRA: Broken Median Barrier", fill=(255, 255, 255))

        elif category == "incident" or category == "anpr":
            # Draw speeding offender car + ANPR Plate Highlight
            cx, cy = int(img_w * 0.38), int(img_h * 0.48)
            cw, ch = 340, 220
            # Car body
            draw.rectangle([cx, cy + 60, cx + cw, cy + ch], fill=(20, 20, 25), outline=(100, 100, 110), width=2)
            draw.polygon([(cx + 40, cy + 60), (cx + 90, cy), (cx + cw - 90, cy), (cx + cw - 40, cy + 60)], fill=(30, 30, 35))
            # Rear lights
            draw.rectangle([cx + 15, cy + 85, cx + 55, cy + 110], fill=(255, 0, 0))
            draw.rectangle([cx + cw - 55, cy + 85, cx + cw - 15, cy + 110], fill=(255, 0, 0))
            # License Plate
            plate_text = metadata.get("plate", "DL-3C-CN-9428")
            draw.rectangle([cx + 90, cy + 130, cx + cw - 90, cy + 175], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
            draw.text((cx + 105, cy + 145), plate_text, fill=(0, 0, 0))

            # Incident Bounding Box in Alert Crimson
            draw.rectangle([cx - 20, cy - 20, cx + cw + 20, cy + ch + 20], outline=(255, 23, 68), width=4)
            draw.rectangle([cx - 20, cy - 65, cx + 480, cy - 20], fill=(255, 23, 68))
            draw.text((cx - 10, cy - 58), f"CRITICAL INCIDENT: {title.upper()}", fill=(255, 255, 255))
            # ANPR Readout sub-box
            draw.rectangle([cx + 80, cy + ch + 30, cx + cw - 60, cy + ch + 75], fill=(0, 0, 0), outline=(0, 229, 255), width=2)
            draw.text((cx + 90, cy + ch + 42), f"ANPR: {plate_text} (Conf: 97.4%)", fill=(0, 229, 255))

        elif category == "pedestrian_school":
            # School children walking with backpacks
            sx, sy = int(img_w * 0.22), int(img_h * 0.48)
            for p in range(3):
                px = sx + (p * 70)
                draw.ellipse([px + 15, sy, px + 45, sy + 30], fill=(230, 190, 160)) # head
                draw.rectangle([px + 10, sy + 30, px + 50, sy + 110], fill=(25, 60, 120)) # school uniform
                draw.rectangle([px + 5, sy + 40, px + 20, sy + 80], fill=(220, 50, 50)) # backpack
            draw.rectangle([sx - 15, sy - 15, sx + 240, sy + 130], outline=(255, 214, 0), width=3)
            draw.rectangle([sx - 15, sy - 50, sx + 390, sy - 15], fill=(255, 214, 0))
            draw.text((sx - 5, sy - 44), f"SAFETY ALERT: School Children Crossing Zone", fill=(0, 0, 0))

        # Render Top HUD Bar & Edge AI Diagnostics
        draw.rectangle([0, 0, img_w, 45], fill=(10, 14, 22, 220))
        hud_text = f"S.T.R.I.D.E EDGE AI NODE | UNIT: {self.bus_id} ({self.plate}) | CAM: FRONT-4K-AI | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+05:30')}"
        draw.text((15, 12), hud_text, fill=(0, 229, 255))

        # Bottom HUD Bar
        draw.rectangle([0, img_h - 45, img_w, img_h], fill=(10, 14, 22, 220))
        bottom_hud = f"GPS: {self.lat:.6f}, {self.lng:.6f} | SPEED: {self.speed_kmh:.1f} KM/H | ROAD: {self.road_name} | EDGE INFERENCE: 28.4ms (35.2 FPS)"
        draw.text((15, img_h - 32), bottom_hud, fill=(200, 220, 240))

        # Save snapshot to file
        filename = f"evidence_{self.bus_id}_{category}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = EVIDENCE_DIR / filename
        img.save(filepath, "JPEG", quality=88)
        return f"/api/evidence/{filename}"

    def trigger_defect_event(self, defect_type: str, severity: str = "Severe") -> dict:
        meta = DEFECT_TYPES.get(defect_type, DEFECT_TYPES["pothole"])
        defect_id = f"DEF-2026-{random.randint(1000, 9999)}"
        conf = round(random.uniform(0.91, 0.985), 3)
        snapshot_url = self.generate_evidence_image(
            title=meta["label"],
            category=defect_type,
            label=f"{meta['label']} ({severity})",
            metadata={"confidence": conf, "severity": severity}
        )

        cost_map = {
            "pothole": 8500.0,
            "damaged_road": 18000.0,
            "missing_divider": 32000.0,
            "missing_zebra_crossing": 6500.0,
            "damaged_traffic_sign": 4200.0,
            "missing_traffic_sign": 5800.0,
            "waterlogging": 16500.0,
            "debris_hazard": 4500.0
        }

        defect_record = {
            "id": defect_id,
            "bus_id": self.bus_id,
            "defect_type": defect_type,
            "label": f"{meta['label']} - {severity}",
            "severity": severity,
            "confidence": conf,
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "road_name": self.road_name,
            "zone": "Central Metropolitan Zone",
            "detected_at": datetime.now().isoformat(),
            "snapshot_url": snapshot_url,
            "bounding_box": [0.38, 0.58, 0.24, 0.22],
            "status": "Detected",
            "assigned_team": None,
            "estimated_repair_cost": cost_map.get(defect_type, 7500.0),
            "verification_notes": f"Detected automatically by onboard Mobile Edge-AI Vision Unit on {self.bus_id}."
        }

        db_save_defect(defect_record)
        return defect_record

    def trigger_incident_event(self, incident_type: str = "Hit-and-Run Collision & Speeding Offender") -> dict:
        inc_id = f"INC-2026-{random.randint(1000, 9999)}"
        plates = ["DL-01-AX-9921", "HR-26-CB-3044", "UP-16-EK-7182", "DL-3C-NY-8012", "CH-01-BM-5509"]
        selected_plate = random.choice(plates)
        makes = [
            {"make": "Hyundai", "model": "Creta Dark Edition", "type": "Compact SUV", "color": "Abyss Black"},
            {"make": "Mahindra", "model": "Scorpio-N", "type": "Full SUV", "color": "Deep Forest"},
            {"make": "Maruti Suzuki", "model": "Brezza ZXi", "type": "SUV", "color": "Magma Grey"},
            {"make": "Tata", "model": "Harrier Dark", "type": "SUV", "color": "Oberon Black"}
        ]
        veh_info = random.choice(makes)
        anpr_conf = round(random.uniform(94.5, 98.9), 1)
        speed = round(random.uniform(72.0, 95.0), 1)

        snapshot_url = self.generate_evidence_image(
            title=incident_type,
            category="anpr",
            label=f"ANPR: {selected_plate} ({anpr_conf}%)",
            metadata={"plate": selected_plate, "confidence": anpr_conf, "speed": speed}
        )

        incident_record = {
            "id": inc_id,
            "incident_type": incident_type,
            "bus_id": self.bus_id,
            "timestamp": datetime.now().isoformat(),
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "road_name": self.road_name,
            "offender_vehicle": veh_info,
            "license_plate": selected_plate,
            "anpr_confidence": anpr_conf,
            "estimated_speed_kmh": speed,
            "trajectory_vector": f"Heading North-East at {self.bearing:.0f} deg away from collision locus",
            "snapshot_url": snapshot_url,
            "video_clip_url": None,
            "status": "Active Investigation",
            "police_fir_number": f"FIR-METRO-{random.randint(10000, 99999)}",
            "law_enforcement_notified": True
        }

        db_save_incident(incident_record)
        return incident_record

    def trigger_pedestrian_event(self, alert_type: str = "School Children Crossing Zone") -> dict:
        alert_id = f"PED-2026-{random.randint(1000, 9999)}"
        conf = round(random.uniform(0.92, 0.98), 3)
        snapshot_url = self.generate_evidence_image(
            title="School Zone Vulnerable Pedestrians",
            category="pedestrian_school",
            label="School Children Crossing",
            metadata={"confidence": conf}
        )

        ped_alert = {
            "id": alert_id,
            "bus_id": self.bus_id,
            "timestamp": datetime.now().isoformat(),
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "road_name": self.road_name,
            "alert_type": alert_type,
            "vulnerability_level": "Critical",
            "pedestrian_count": random.randint(3, 8),
            "confidence": conf,
            "snapshot_url": snapshot_url,
            "driver_notified": True
        }

        db_save_pedestrian_alert(ped_alert)
        return ped_alert


class FleetEdgeEngine:
    def __init__(self):
        self.buses: Dict[str, BusEdgeSimulator] = {}
        for b_cfg in BUS_FLEET:
            self.buses[b_cfg["bus_id"]] = BusEdgeSimulator(b_cfg)

    def tick(self, dt_seconds: float = 1.0):
        for bus in self.buses.values():
            bus.update_telemetry(dt_seconds)

    def get_fleet_telemetry(self) -> List[dict]:
        output = []
        for bus in self.buses.values():
            output.append({
                "bus_id": bus.bus_id,
                "route_id": bus.route_id,
                "route_name": bus.route_name,
                "route_color": bus.route_color,
                "driver": bus.driver,
                "plate": bus.plate,
                "model": bus.model,
                "lat": round(bus.lat, 6),
                "lng": round(bus.lng, 6),
                "speed_kmh": round(bus.speed_kmh, 1),
                "bearing": round(bus.bearing, 1),
                "passenger_count": bus.passenger_count,
                "edge_cpu": round(bus.edge_cpu, 1),
                "bandwidth_kbps": round(bus.bandwidth_kbps, 1),
                "road_name": bus.road_name,
                "active_detections": bus.active_detections,
                "cameras": {
                    "front": {"status": "ACTIVE_4K", "fps": bus.edge_fps["front"]},
                    "rear": {"status": "ACTIVE_1080P", "fps": bus.edge_fps["rear"]},
                    "left_kerb": {"status": "ACTIVE_1080P", "fps": bus.edge_fps["left_kerb"]},
                    "right_kerb": {"status": "ACTIVE_1080P", "fps": bus.edge_fps["right_kerb"]}
                }
            })
        return output

    def get_bus(self, bus_id: str) -> Optional[BusEdgeSimulator]:
        return self.buses.get(bus_id)

fleet_engine = FleetEdgeEngine()
