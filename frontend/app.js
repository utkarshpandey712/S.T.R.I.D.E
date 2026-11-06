/**
 * S.T.R.I.D.E - Smart Transit Real-time Infrastructure & Defect Evaluator
 * Frontend Application Controller
 */

class StrideApp {
    constructor() {
        this.socket = null;
        this.map = null;
        this.busMarkers = {};
        this.defectMarkers = {};
        this.incidentMarkers = {};
        this.routeLayers = {};
        this.fleetData = [];
        this.selectedBusId = "STRIDE-BUS-01";
        this.showBoundingBoxes = true;
        this.activeEmergencyIncident = null;
        this.hourlyTrafficChart = null;
        this.vehicleBreakdownChart = null;

        // Active filters
        this.layerVisibility = {
            buses: true,
            defects: true,
            incidents: true,
            routes: true
        };

        // Sim modal state
        this.simModalState = {
            category: "defect",
            type: "pothole",
            severity: "Severe"
        };
    }

    init() {
        this.initLiveClock();
        this.initTabs();
        this.initMap();
        this.initWebSocket();
        this.initCameraRenderLoops();
        this.loadDefectsAndWorkOrders();
        this.loadTrafficAnalytics();
        this.loadIncidents();
        this.loadRqiScorecards();
    }

    /* ================= Live Clock ================= */
    initLiveClock() {
        const clockEl = document.getElementById("system-live-clock");
        const update = () => {
            const now = new Date();
            if (clockEl) {
                clockEl.textContent = now.toLocaleTimeString() + " UTC+05:30";
            }
        };
        setInterval(update, 1000);
        update();
    }

    /* ================= Tab Switching ================= */
    initTabs() {
        const tabs = document.querySelectorAll(".nav-tab");
        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                const targetTab = tab.getAttribute("data-tab");
                tabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");

                document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
                const targetContent = document.getElementById(targetTab);
                if (targetContent) targetContent.classList.add("active");

                if (targetTab === "tab-map" && this.map) {
                    setTimeout(() => this.map.invalidateSize(), 200);
                }
                if (targetTab === "tab-traffic") {
                    this.renderTrafficCharts();
                }
            });
        });
    }

    /* ================= Interactive Leaflet GIS Map ================= */
    initMap() {
        const mapContainer = document.getElementById("gis-map");
        if (!mapContainer) return;

        // Initialize at central metropolis coordinate
        this.map = L.map("gis-map", {
            center: [28.6139, 77.2090],
            zoom: 12,
            zoomControl: true
        });

        // CartoDB Dark Matter GIS Tiles
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | S.T.R.I.D.E GIS Sensing Layer',
            maxZoom: 19,
            subdomains: 'abcd'
        }).addTo(this.map);

        this.drawTransitRoutes();
    }

    drawTransitRoutes() {
        const routes = [
            {
                id: "RT-101",
                name: "Connaught Hub - Outer Ring Expressway",
                color: "#00e5ff",
                coords: [
                    [28.6315, 77.2167], [28.6250, 77.2280], [28.6080, 77.2350],
                    [28.5900, 77.2400], [28.5700, 77.2300], [28.5600, 77.2050],
                    [28.5800, 77.1850], [28.6100, 77.1950], [28.6315, 77.2167]
                ]
            },
            {
                id: "RT-204",
                name: "North University - South Tech District",
                color: "#00e676",
                coords: [
                    [28.6850, 77.2100], [28.6600, 77.2200], [28.6300, 77.2150],
                    [28.5900, 77.2100], [28.5500, 77.2000], [28.5200, 77.1850],
                    [28.5500, 77.2000], [28.5900, 77.2100], [28.6300, 77.2150],
                    [28.6850, 77.2100]
                ]
            },
            {
                id: "RT-305",
                name: "East River Corridor - West Commercial Axis",
                color: "#ff9100",
                coords: [
                    [28.6200, 77.2800], [28.6180, 77.2500], [28.6150, 77.2100],
                    [28.6220, 77.1700], [28.6350, 77.1300], [28.6220, 77.1700],
                    [28.6150, 77.2100], [28.6180, 77.2500], [28.6200, 77.2800]
                ]
            },
            {
                id: "RT-412",
                name: "Heritage Old Quarter - Airport Link",
                color: "#e040fb",
                coords: [
                    [28.6550, 77.2350], [28.6350, 77.2200], [28.6050, 77.1900],
                    [28.5750, 77.1500], [28.5550, 77.0850], [28.5750, 77.1500],
                    [28.6050, 77.1900], [28.6350, 77.2200], [28.6550, 77.2350]
                ]
            },
            {
                id: "RT-509",
                name: "Medical Center - Industrial Outer Belt",
                color: "#ffd600",
                coords: [
                    [28.5680, 77.2100], [28.5400, 77.2400], [28.5100, 77.2600],
                    [28.4900, 77.2300], [28.5100, 77.1900], [28.5400, 77.1700],
                    [28.5680, 77.2100]
                ]
            }
        ];

        routes.forEach(r => {
            const line = L.polyline(r.coords, {
                color: r.color,
                weight: 3,
                opacity: 0.7,
                dashArray: '6, 6'
            }).addTo(this.map);
            line.bindTooltip(`<strong>${r.id}</strong>: ${r.name}`, { sticky: true });
            this.routeLayers[r.id] = line;
        });
    }

    centerMapOnCity() {
        if (this.map) {
            this.map.setView([28.6139, 77.2090], 12);
        }
    }

    toggleMapLayer(layerName) {
        const checkbox = document.getElementById(`layer-toggle-${layerName}`);
        if (!checkbox) return;
        const isVisible = checkbox.checked;
        this.layerVisibility[layerName] = isVisible;

        if (layerName === "buses") {
            Object.values(this.busMarkers).forEach(m => isVisible ? m.addTo(this.map) : this.map.removeLayer(m));
        } else if (layerName === "defects") {
            Object.values(this.defectMarkers).forEach(m => isVisible ? m.addTo(this.map) : this.map.removeLayer(m));
        } else if (layerName === "incidents") {
            Object.values(this.incidentMarkers).forEach(m => isVisible ? m.addTo(this.map) : this.map.removeLayer(m));
        } else if (layerName === "routes") {
            Object.values(this.routeLayers).forEach(l => isVisible ? l.addTo(this.map) : this.map.removeLayer(l));
        }
    }

    /* ================= WebSocket Telemetry Hub ================= */
    initWebSocket() {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/telemetry`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            const badge = document.getElementById("ws-status-badge");
            if (badge) {
                badge.innerHTML = '<span class="conn-dot"></span> LIVE SYNC';
                badge.style.color = 'var(--color-emerald)';
            }
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSocketMessage(data);
            } catch (err) {
                console.error("WS Parse Error:", err);
            }
        };

        this.socket.onclose = () => {
            const badge = document.getElementById("ws-status-badge");
            if (badge) {
                badge.innerHTML = '<span class="conn-dot" style="background:#ff1744"></span> RECONNECTING';
                badge.style.color = '#ff1744';
            }
            setTimeout(() => this.initWebSocket(), 2500);
        };
    }

    handleSocketMessage(data) {
        if (data.type === "INITIAL_SYNC" || data.type === "FLEET_UPDATE") {
            this.updateFleetState(data.fleet);
            if (data.summary) {
                this.updateGlobalKpis(data.summary);
            }
        } else if (data.type === "NEW_DEFECT_DETECTED") {
            this.handleNewDefect(data.defect);
        } else if (data.type === "CRITICAL_INCIDENT_ALARM") {
            this.handleCriticalIncident(data.incident);
        } else if (data.type === "PEDESTRIAN_SAFETY_ALERT") {
            this.handlePedestrianAlert(data.alert);
        } else if (data.type === "WORK_ORDER_CREATED" || data.type === "WORK_ORDER_STATUS_CHANGED" || data.type === "DEFECT_UPDATED") {
            this.loadDefectsAndWorkOrders();
        }
    }

    updateGlobalKpis(summary) {
        const kpiBuses = document.getElementById("kpi-buses-active");
        const kpiCameras = document.getElementById("kpi-cameras");
        if (kpiBuses) kpiBuses.textContent = `${summary.total_buses_active} Buses`;
        if (kpiCameras) kpiCameras.textContent = `${summary.total_cameras_streaming} Streams`;
    }

    updateFleetState(fleet) {
        this.fleetData = fleet;
        this.populateBusSelector(fleet);
        this.updateSidebarBusList(fleet);
        this.updateMapBusMarkers(fleet);

        // Update selected bus HUD stats
        const sel = fleet.find(b => b.bus_id === this.selectedBusId) || fleet[0];
        if (sel) {
            this.updateHudTelemetry(sel);
        }
    }

    populateBusSelector(fleet) {
        const select = document.getElementById("hud-bus-select");
        const modalSelect = document.getElementById("sim-modal-bus-select");
        if (!select || select.children.length > 0) return;

        fleet.forEach(b => {
            const opt = document.createElement("option");
            opt.value = b.bus_id;
            opt.textContent = `${b.bus_id} - ${b.route_name} (${b.plate})`;
            select.appendChild(opt);

            if (modalSelect) {
                const opt2 = opt.cloneNode(true);
                modalSelect.appendChild(opt2);
            }
        });
        select.value = this.selectedBusId;
    }

    updateSidebarBusList(fleet) {
        const container = document.getElementById("sidebar-bus-list");
        if (!container) return;

        container.innerHTML = fleet.map(b => {
            const isSelected = b.bus_id === this.selectedBusId ? "selected" : "";
            return `
                <div class="bus-card-item ${isSelected}" onclick="app.selectBus('${b.bus_id}')">
                    <div class="bus-item-header">
                        <span class="bus-item-id"><i class="fa-solid fa-bus"></i> ${b.bus_id}</span>
                        <span class="bus-item-speed mono text-cyan">${b.speed_kmh} km/h</span>
                    </div>
                    <div class="bus-item-route">${b.route_name}</div>
                    <div class="bus-item-tags">
                        <span class="badge-cam-status">4 CAMS ACTIVE</span>
                        <span class="text-muted"><i class="fa-solid fa-user-group"></i> ${b.passenger_count} Pax</span>
                        <span class="text-muted mono"><i class="fa-solid fa-microchip"></i> ${b.edge_cpu}% CPU</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    updateMapBusMarkers(fleet) {
        if (!this.map || !this.layerVisibility.buses) return;

        fleet.forEach(b => {
            if (this.busMarkers[b.bus_id]) {
                this.busMarkers[b.bus_id].setLatLng([b.lat, b.lng]);
            } else {
                const icon = L.divIcon({
                    className: 'leaflet-bus-marker',
                    html: `<div class="bus-marker-pin" style="border-color:${b.route_color}" title="${b.bus_id}"><i class="fa-solid fa-bus"></i></div>`,
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                });

                const marker = L.marker([b.lat, b.lng], { icon: icon }).addTo(this.map);
                marker.bindPopup(`
                    <div style="font-family:var(--font-main); min-width:200px; color:#0f172a;">
                        <strong style="color:#0098a6;"><i class="fa-solid fa-bus"></i> ${b.bus_id}</strong> (${b.plate})<br>
                        <small><b>Route:</b> ${b.route_name}</small><br>
                        <small><b>Driver:</b> ${b.driver}</small><br>
                        <small><b>Speed:</b> ${b.speed_kmh} km/h | <b>Edge CPU:</b> ${b.edge_cpu}%</small><br>
                        <small><b>Detections:</b> ${b.active_detections.length} objects</small><br>
                        <button onclick="app.jumpToHud('${b.bus_id}')" style="margin-top:8px; width:100%; background:#0098a6; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-weight:bold;">
                            <i class="fa-solid fa-video"></i> Open Live 4-Cam HUD
                        </button>
                    </div>
                `);
                this.busMarkers[b.bus_id] = marker;
            }
        });
    }

    selectBus(busId) {
        this.selectedBusId = busId;
        const sel = document.getElementById("hud-bus-select");
        if (sel) sel.value = busId;

        const bus = this.fleetData.find(b => b.bus_id === busId);
        if (bus && this.map) {
            this.map.panTo([bus.lat, bus.lng]);
            if (this.busMarkers[busId]) {
                this.busMarkers[busId].openPopup();
            }
        }
        this.updateSidebarBusList(this.fleetData);
    }

    jumpToHud(busId) {
        this.selectBus(busId);
        document.querySelector('[data-tab="tab-hud"]').click();
    }

    onHudBusChanged(busId) {
        this.selectBus(busId);
    }

    updateHudTelemetry(bus) {
        const routeEl = document.getElementById("hud-route-name");
        const speedEl = document.getElementById("hud-speed-val");
        const driverEl = document.getElementById("hud-driver-name");
        const paxEl = document.getElementById("hud-passengers");
        const fpsEl = document.getElementById("hud-fps");
        const bwEl = document.getElementById("hud-bandwidth");

        if (routeEl) routeEl.textContent = `${bus.route_id} (${bus.route_name})`;
        if (speedEl) speedEl.textContent = `${bus.speed_kmh} km/h`;
        if (driverEl) driverEl.textContent = bus.driver;
        if (paxEl) paxEl.textContent = `${bus.passenger_count} Pax`;
        if (fpsEl) fpsEl.textContent = `${bus.cameras.front.fps} FPS`;
        if (bwEl) bwEl.textContent = `${bus.bandwidth_kbps} KB/s`;
    }

    toggleBBoxes() {
        this.showBoundingBoxes = !this.showBoundingBoxes;
        const btnLabel = document.getElementById("btn-bbox-label");
        if (btnLabel) {
            btnLabel.textContent = this.showBoundingBoxes ? "Hide AI Bounding Boxes" : "Show AI Bounding Boxes";
        }
    }

    /* ================= 4-Camera Canvas Animation & Rendering ================= */
    initCameraRenderLoops() {
        let frameCount = 0;

        const render = () => {
            frameCount++;
            const bus = this.fleetData.find(b => b.bus_id === this.selectedBusId) || this.fleetData[0];
            
            this.renderFrontCamera(frameCount, bus);
            this.renderRearCamera(frameCount, bus);
            this.renderLeftKerbCamera(frameCount, bus);
            this.renderRightKerbCamera(frameCount, bus);

            requestAnimationFrame(render);
        };

        requestAnimationFrame(render);
    }

    renderFrontCamera(frame, bus) {
        const canvas = document.getElementById("canvas-cam-front");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width, h = canvas.height;

        // Background / Horizon
        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, "#10192e");
        grad.addColorStop(0.45, "#1e293b");
        grad.addColorStop(0.45, "#334155");
        grad.addColorStop(1, "#1e2430");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        // Perspective Road
        ctx.fillStyle = "#2b3240";
        ctx.beginPath();
        ctx.moveTo(w * 0.38, h * 0.45);
        ctx.lineTo(w * 0.62, h * 0.45);
        ctx.lineTo(w * 0.95, h);
        ctx.lineTo(w * 0.05, h);
        ctx.closePath();
        ctx.fill();

        // Moving Dash Lanes
        ctx.strokeStyle = "#ffd600";
        ctx.lineWidth = 3;
        ctx.setLineDash([12, 14]);
        ctx.lineDashOffset = -frame * 2.5;
        ctx.beginPath();
        ctx.moveTo(w * 0.5, h * 0.45);
        ctx.lineTo(w * 0.5, h);
        ctx.stroke();
        ctx.setLineDash([]);

        // Ahead Vehicles (Moving simulation)
        const vY = h * 0.58 + Math.sin(frame * 0.02) * 5;
        ctx.fillStyle = "#0284c7";
        ctx.fillRect(w * 0.42, vY, 60, 36);
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(w * 0.44, vY + 28, 10, 6);
        ctx.fillRect(w * 0.42 + 42, vY + 28, 10, 6);

        // Draw Bounding Boxes if enabled
        if (this.showBoundingBoxes && bus) {
            const frontDets = (bus.active_detections || []).filter(d => d.camera === "front");
            frontDets.forEach(det => {
                const bx = det.bbox[0] * w;
                const by = det.bbox[1] * h;
                const bw = det.bbox[2] * w;
                const bh = det.bbox[3] * h;

                ctx.strokeStyle = "#00e5ff";
                ctx.lineWidth = 2;
                ctx.strokeRect(bx, by, bw, bh);

                ctx.fillStyle = "rgba(0, 229, 255, 0.85)";
                ctx.fillRect(bx, by - 16, Math.min(bw + 40, 180), 16);
                ctx.fillStyle = "#000";
                ctx.font = "bold 10px Inter";
                ctx.fillText(`${det.label}`, bx + 4, by - 4);
            });
        }
    }

    renderRearCamera(frame, bus) {
        const canvas = document.getElementById("canvas-cam-rear");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width, h = canvas.height;

        ctx.fillStyle = "#111827";
        ctx.fillRect(0, 0, w, h);

        // Rear road perspective
        ctx.fillStyle = "#1f2937";
        ctx.beginPath();
        ctx.moveTo(w * 0.4, h * 0.42);
        ctx.lineTo(w * 0.6, h * 0.42);
        ctx.lineTo(w * 0.9, h);
        ctx.lineTo(w * 0.1, h);
        ctx.closePath();
        ctx.fill();

        // Following Van
        const vy = h * 0.52;
        ctx.fillStyle = "#475569";
        ctx.fillRect(w * 0.42, vy, 100, 70);
        ctx.fillStyle = "#38bdf8"; // headlights
        ctx.fillRect(w * 0.44, vy + 40, 14, 10);
        ctx.fillRect(w * 0.42 + 72, vy + 40, 14, 10);

        if (this.showBoundingBoxes) {
            ctx.strokeStyle = "#00e676";
            ctx.lineWidth = 2;
            ctx.strokeRect(w * 0.40, vy - 10, 110, 90);
            ctx.fillStyle = "#00e676";
            ctx.fillRect(w * 0.40, vy - 26, 150, 16);
            ctx.fillStyle = "#000";
            ctx.font = "bold 10px Inter";
            ctx.fillText("Following Van (14.2m)", w * 0.42, vy - 14);
        }
    }

    renderLeftKerbCamera(frame, bus) {
        const canvas = document.getElementById("canvas-cam-left");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width, h = canvas.height;

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(0, 0, w, h);

        // Sidewalk pavement
        ctx.fillStyle = "#334155";
        ctx.fillRect(0, h * 0.45, w, h * 0.55);

        // Bus stop shelter
        ctx.fillStyle = "#64748b";
        ctx.fillRect(w * 0.25, h * 0.35, 160, 90);
        ctx.fillStyle = "#00e5ff";
        ctx.fillRect(w * 0.25, h * 0.35, 160, 8);

        // Pedestrian silhouettes
        for (let i = 0; i < 3; i++) {
            const px = w * 0.3 + (i * 35);
            ctx.fillStyle = "#94a3b8";
            ctx.beginPath();
            ctx.arc(px + 8, h * 0.48, 7, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillRect(px, h * 0.56, 16, 32);
        }

        if (this.showBoundingBoxes) {
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 2;
            ctx.strokeRect(w * 0.24, h * 0.38, 120, 100);
            ctx.fillStyle = "#ffd600";
            ctx.fillRect(w * 0.24, h * 0.38 - 16, 170, 16);
            ctx.fillStyle = "#000";
            ctx.font = "bold 10px Inter";
            ctx.fillText("Pedestrians at Shelter (3)", w * 0.26, h * 0.38 - 4);
        }
    }

    renderRightKerbCamera(frame, bus) {
        const canvas = document.getElementById("canvas-cam-right");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width, h = canvas.height;

        ctx.fillStyle = "#0a0f1d";
        ctx.fillRect(0, 0, w, h);

        // Concrete median barrier
        ctx.fillStyle = "#475569";
        ctx.beginPath();
        ctx.moveTo(w * 0.45, h * 0.4);
        ctx.lineTo(w * 0.55, h * 0.4);
        ctx.lineTo(w * 0.8, h);
        ctx.lineTo(w * 0.3, h);
        ctx.closePath();
        ctx.fill();

        if (this.showBoundingBoxes) {
            ctx.strokeStyle = "#00e5ff";
            ctx.lineWidth = 2;
            ctx.strokeRect(w * 0.35, h * 0.45, 140, 120);
            ctx.fillStyle = "#00e5ff";
            ctx.fillRect(w * 0.35, h * 0.45 - 16, 160, 16);
            ctx.fillStyle = "#000";
            ctx.font = "bold 10px Inter";
            ctx.fillText("Median Barrier: Intact", w * 0.37, h * 0.45 - 4);
        }
    }

    /* ================= Synthetic Event Generator & Triggers ================= */
    async triggerSyntheticEvent(category, type, severity) {
        try {
            const res = await fetch("/api/simulate/trigger", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    bus_id: this.selectedBusId,
                    event_category: category,
                    event_type: type,
                    severity: severity
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                this.addDetectionFeedItem({
                    title: `Simulated: ${type}`,
                    loc: `${this.selectedBusId} | ${data.data.road_name || 'En Route'}`,
                    time: new Date().toLocaleTimeString(),
                    type: category
                });
            }
        } catch (err) {
            console.error("Simulation trigger failed:", err);
        }
    }

    openSimulationModal() {
        const modal = document.getElementById("modal-simulation");
        if (modal) modal.classList.remove("hidden");
    }

    closeSimulationModal() {
        const modal = document.getElementById("modal-simulation");
        if (modal) modal.classList.add("hidden");
    }

    selectSimModalOpt(btn, category, type, severity) {
        document.querySelectorAll(".btn-sim-opt").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.simModalState = { category, type, severity };
    }

    executeModalSimulation() {
        const modalBus = document.getElementById("sim-modal-bus-select").value || this.selectedBusId;
        this.selectedBusId = modalBus;
        this.triggerSyntheticEvent(this.simModalState.category, this.simModalState.type, this.simModalState.severity);
        this.closeSimulationModal();
    }

    /* ================= Alert Handlers ================= */
    handleNewDefect(defect) {
        this.addDetectionFeedItem({
            title: `DEFECT: ${defect.label}`,
            loc: `${defect.bus_id} @ ${defect.road_name}`,
            time: new Date().toLocaleTimeString(),
            type: "pothole"
        });

        // Add Marker on map
        if (this.map && this.layerVisibility.defects) {
            const icon = L.divIcon({
                className: 'leaflet-bus-marker',
                html: `<div class="defect-marker-pin" title="${defect.label}"><i class="fa-solid fa-road-circle-exclamation"></i></div>`,
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            });
            const marker = L.marker([defect.lat, defect.lng], { icon: icon }).addTo(this.map);
            marker.bindPopup(`
                <div style="min-width:220px; color:#0f172a;">
                    <strong style="color:#d97706;"><i class="fa-solid fa-triangle-exclamation"></i> ${defect.label}</strong><br>
                    <small><b>Location:</b> ${defect.road_name}</small><br>
                    <small><b>AI Confidence:</b> ${(defect.confidence * 100).toFixed(1)}%</small><br>
                    <img src="${defect.snapshot_url}" style="width:100%; border-radius:4px; margin-top:6px;"><br>
                    <button onclick="app.inspectDefect('${defect.id}')" style="margin-top:6px; width:100%; background:#0284c7; color:#fff; border:none; padding:4px; border-radius:4px; cursor:pointer;">
                        Inspect & Create Work Order
                    </button>
                </div>
            `);
            this.defectMarkers[defect.id] = marker;
        }

        this.loadDefectsAndWorkOrders();
    }

    handleCriticalIncident(incident) {
        this.activeEmergencyIncident = incident;
        const banner = document.getElementById("emergency-alert-banner");
        const titleEl = document.getElementById("emergency-title");
        const descEl = document.getElementById("emergency-desc");

        if (banner) {
            banner.classList.remove("hidden");
            if (titleEl) titleEl.textContent = `🚨 EMERGENCY ALERT: ${incident.incident_type.toUpperCase()}`;
            if (descEl) descEl.textContent = `Offender Plate: ${incident.license_plate} (Conf: ${incident.anpr_confidence}%) | Unit: ${incident.bus_id} @ ${incident.road_name}`;
        }

        // Play alert audio beep if allowed
        const audio = document.getElementById("audio-alarm");
        if (audio) {
            audio.play().catch(() => {});
        }

        // Add incident pin on map
        if (this.map && this.layerVisibility.incidents) {
            const icon = L.divIcon({
                className: 'leaflet-bus-marker',
                html: `<div class="incident-marker-pin" title="Offender: ${incident.license_plate}"><i class="fa-solid fa-car-burst"></i></div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            });
            const marker = L.marker([incident.lat, incident.lng], { icon: icon }).addTo(this.map);
            marker.bindPopup(`
                <div style="min-width:240px; color:#0f172a;">
                    <strong style="color:#dc2626;">🚨 CRITICAL INCIDENT</strong><br>
                    <small><b>Offender Plate:</b> ${incident.license_plate} (${incident.anpr_confidence}%)</small><br>
                    <small><b>Speed:</b> ${incident.estimated_speed_kmh} km/h</small><br>
                    <small><b>Trajectory:</b> ${incident.trajectory_vector}</small><br>
                    <button onclick="app.inspectIncident('${incident.id}')" style="margin-top:6px; width:100%; background:#dc2626; color:#fff; border:none; padding:6px; border-radius:4px; cursor:pointer; font-weight:bold;">
                        View Offender Dossier
                    </button>
                </div>
            `).openPopup();
            this.incidentMarkers[incident.id] = marker;
            this.map.panTo([incident.lat, incident.lng]);
        }

        this.loadIncidents();
    }

    handlePedestrianAlert(alert) {
        this.addDetectionFeedItem({
            title: `SAFETY: ${alert.alert_type}`,
            loc: `${alert.bus_id} @ ${alert.road_name}`,
            time: new Date().toLocaleTimeString(),
            type: "pedestrian"
        });
    }

    addDetectionFeedItem(item) {
        const feed = document.getElementById("sidebar-detection-feed");
        if (!feed) return;

        let cls = "feed-event-item";
        if (item.type === "pothole") cls += " feed-pothole";
        else if (item.type === "incident") cls += " feed-incident";
        else if (item.type === "waterlogging") cls += " feed-water";

        const div = document.createElement("div");
        div.className = cls;
        div.innerHTML = `
            <div class="feed-event-top">
                <span class="feed-event-title">${item.title}</span>
                <span class="feed-event-time mono">${item.time}</span>
            </div>
            <div class="feed-event-loc">${item.loc}</div>
        `;
        feed.insertBefore(div, feed.firstChild);
        if (feed.children.length > 20) feed.removeChild(feed.lastChild);
    }

    dismissEmergencyBanner() {
        const banner = document.getElementById("emergency-alert-banner");
        if (banner) banner.classList.add("hidden");
    }

    viewIncidentDetailFromBanner() {
        if (this.activeEmergencyIncident) {
            this.inspectIncident(this.activeEmergencyIncident.id);
        } else {
            document.querySelector('[data-tab="tab-incidents"]').click();
        }
        this.dismissEmergencyBanner();
    }

    /* ================= Road Maintenance & Work Orders ================= */
    async loadDefectsAndWorkOrders() {
        try {
            const [defRes, woRes] = await Promise.all([
                fetch("/api/defects"),
                fetch("/api/work-orders")
            ]);
            const defData = await defRes.json();
            const woData = await woRes.json();

            this.renderDefectsTable(defData.defects || []);
            this.renderWorkOrdersList(woData.work_orders || []);
            this.updateDefectsKpi(defData.defects || [], woData.work_orders || []);
        } catch (err) {
            console.error("Error loading maintenance data:", err);
        }
    }

    updateDefectsKpi(defects, workOrders) {
        const kpiDefects = document.getElementById("kpi-defects-count");
        const totalBadge = document.getElementById("defects-total-badge");
        const woBadge = document.getElementById("workorders-total-badge");
        const navWoBadge = document.getElementById("badge-wo-count");

        const activeDefects = defects.filter(d => d.status !== "Repaired").length;
        if (kpiDefects) kpiDefects.textContent = `${activeDefects} Active`;
        if (totalBadge) totalBadge.textContent = `${defects.length} Items`;
        if (woBadge) woBadge.textContent = `${workOrders.length} Active`;
        if (navWoBadge) navWoBadge.textContent = `${workOrders.length}`;
    }

    renderDefectsTable(defects) {
        const tbody = document.getElementById("defects-table-body");
        if (!tbody) return;

        tbody.innerHTML = defects.map(d => {
            const statusClass = `status-${d.status.toLowerCase().replace(/ /g, '-')}`;
            return `
                <tr>
                    <td class="mono"><strong>${d.id}</strong><br><small class="text-dim">${d.bus_id}</small></td>
                    <td>
                        <img src="${d.snapshot_url}" class="thumb-preview" onclick="app.inspectDefect('${d.id}')" title="Click to inspect high-res visual proof">
                    </td>
                    <td>
                        <strong>${d.label}</strong><br>
                        <span class="text-amber mono">${d.severity}</span>
                    </td>
                    <td>
                        ${d.road_name}<br>
                        <small class="text-dim mono">${d.lat.toFixed(4)}, ${d.lng.toFixed(4)}</small>
                    </td>
                    <td class="mono text-cyan">${(d.confidence * 100).toFixed(1)}%</td>
                    <td><span class="status-badge ${statusClass}">${d.status}</span></td>
                    <td>
                        <button class="btn btn-xs btn-outline" onclick="app.inspectDefect('${d.id}')">
                            <i class="fa-solid fa-magnifying-glass"></i> Audit
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    renderWorkOrdersList(workOrders) {
        const container = document.getElementById("work-orders-container");
        if (!container) return;

        container.innerHTML = workOrders.map(wo => {
            const materials = (wo.materials_required || []).join(", ");
            return `
                <div class="wo-card">
                    <div class="wo-card-header">
                        <span class="wo-id">${wo.id}</span>
                        <span class="status-badge status-dispatched">${wo.status}</span>
                    </div>
                    <div>
                        <strong>${wo.road_name}</strong>
                        <div class="wo-agency"><i class="fa-solid fa-building-shield"></i> ${wo.assigned_agency} | Crew: ${wo.assigned_crew || 'Standard Team'}</div>
                    </div>
                    <div class="wo-materials"><i class="fa-solid fa-cubes"></i> <strong>Materials:</strong> ${materials}</div>
                    <div class="wo-actions">
                        <button class="btn btn-xs btn-outline" onclick="app.openWorkOrderPrintModal('${wo.id}')">
                            <i class="fa-solid fa-print"></i> Dispatch Slip
                        </button>
                        ${wo.status !== 'Repaired' ? `
                            <button class="btn btn-xs btn-primary" onclick="app.markWorkOrderRepaired('${wo.id}', '${wo.defect_id}')">
                                <i class="fa-solid fa-check"></i> Mark Repaired
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join("");
    }

    async inspectDefect(defectId) {
        try {
            const res = await fetch("/api/defects");
            const data = await res.json();
            const defect = (data.defects || []).find(d => d.id === defectId);
            if (!defect) return;

            const modal = document.getElementById("modal-defect-inspect");
            const body = document.getElementById("modal-defect-body");
            if (!modal || !body) return;

            body.innerHTML = `
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                    <div>
                        <img src="${defect.snapshot_url}" style="width:100%; border-radius:8px; border:1px solid var(--border-color); box-shadow:var(--shadow-subtle);">
                        <div style="margin-top:10px; font-size:11px; color:var(--text-muted);">
                            <strong>Visual Watermark:</strong> Unit ${defect.bus_id} | GPS ${defect.lat}, ${defect.lng} | Detected at ${defect.detected_at}
                        </div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div>
                            <span class="status-badge status-${defect.status.toLowerCase().replace(/ /g, '-')}">${defect.status}</span>
                            <h3 style="color:#fff; margin-top:6px;">${defect.label}</h3>
                            <p style="color:var(--text-muted); font-size:12px;"><i class="fa-solid fa-location-dot"></i> ${defect.road_name} (${defect.zone})</p>
                        </div>
                        <div style="background:var(--bg-surface-elevated); padding:12px; border-radius:6px; font-size:12px;">
                            <div><strong>AI Confidence:</strong> <span class="text-cyan mono">${(defect.confidence * 100).toFixed(1)}%</span></div>
                            <div><strong>Estimated Repair Cost:</strong> <span class="text-amber mono">₹ ${defect.estimated_repair_cost.toLocaleString()}</span></div>
                            <div><strong>Notes:</strong> ${defect.verification_notes || 'Pending human engineering sign-off'}</div>
                        </div>

                        <!-- Work Order Dispatch Form -->
                        <div style="border-top:1px solid var(--border-subtle); padding-top:12px;">
                            <h4 style="color:#fff; margin-bottom:8px;"><i class="fa-solid fa-file-contract"></i> Dispatch Municipal Work Order</h4>
                            <div class="form-group" style="margin-bottom:8px;">
                                <label>Assigned Department:</label>
                                <select id="form-wo-agency" class="stride-select">
                                    <option value="PWD Central Division">PWD (Public Works Department) Central</option>
                                    <option value="Municipal Corporation Road Maintenance Dept">Municipal Corporation Road Division</option>
                                    <option value="NHAI Highway Rapid Response">NHAI Highway Response</option>
                                </select>
                            </div>
                            <div class="form-group" style="margin-bottom:8px;">
                                <label>Assigned Repair Crew:</label>
                                <input type="text" id="form-wo-crew" class="stride-select" value="Asphalt Strike Crew #4" />
                            </div>
                            <button class="btn btn-primary" style="width:100%; justify-content:center;" onclick="app.dispatchWorkOrderFromModal('${defect.id}', '${defect.defect_type}', '${defect.road_name}', '${defect.zone}', ${defect.lat}, ${defect.lng}, '${defect.severity}', ${defect.estimated_repair_cost})">
                                <i class="fa-solid fa-paper-plane"></i> Dispatch Work Order to Field Team
                            </button>
                        </div>
                    </div>
                </div>
            `;

            modal.classList.remove("hidden");
        } catch (err) {
            console.error("Inspect defect failed:", err);
        }
    }

    closeDefectModal() {
        const modal = document.getElementById("modal-defect-inspect");
        if (modal) modal.classList.add("hidden");
    }

    async dispatchWorkOrderFromModal(defectId, defectType, roadName, zone, lat, lng, severity, estCost) {
        const agency = document.getElementById("form-wo-agency").value;
        const crew = document.getElementById("form-wo-crew").value;

        try {
            const res = await fetch("/api/work-orders", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    defect_id: defectId,
                    defect_type: defectType,
                    road_name: roadName,
                    zone: zone,
                    lat: lat,
                    lng: lng,
                    priority: severity === "Critical" ? "Critical" : "High",
                    assigned_agency: agency,
                    assigned_crew: crew,
                    estimated_cost_inr: estCost,
                    materials_required: ["Standard Bituminous / Structural Mix", "Safety Barricades", "Plate Compactor"],
                    supervisor: "Engr. Rajesh Nair (PWD Zone Officer)",
                    notes: `Dispatched via S.T.R.I.D.E mobile sensing platform automated audit.`
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                this.closeDefectModal();
                this.loadDefectsAndWorkOrders();
            }
        } catch (err) {
            console.error("Dispatch WO failed:", err);
        }
    }

    async markWorkOrderRepaired(woId, defectId) {
        try {
            await fetch("/api/work-orders/status", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    work_order_id: woId,
                    defect_id: defectId,
                    status: "Repaired"
                })
            });
            this.loadDefectsAndWorkOrders();
        } catch (err) {
            console.error("Mark repaired failed:", err);
        }
    }

    async openWorkOrderPrintModal(woId) {
        try {
            const res = await fetch("/api/work-orders");
            const data = await res.json();
            const wo = (data.work_orders || []).find(w => w.id === woId);
            if (!wo) return;

            const modal = document.getElementById("modal-work-order-print");
            const body = document.getElementById("modal-wo-print-body");
            if (!modal || !body) return;

            body.innerHTML = `
                <div style="border:2px dashed var(--border-color); padding:20px; border-radius:8px; font-family:var(--font-main);">
                    <div style="display:flex; justify-content:space-between; border-bottom:2px solid #00e5ff; padding-bottom:10px;">
                        <div>
                            <h2 style="color:#00e5ff; margin:0;">MUNICIPAL PUBLIC WORKS DISPATCH ORDER</h2>
                            <small>S.T.R.I.D.E Automated Urban Infrastructure Management</small>
                        </div>
                        <div style="text-align:right;">
                            <strong class="mono" style="font-size:16px;">${wo.id}</strong><br>
                            <small>DATE: ${new Date(wo.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; font-size:13px;">
                        <div>
                            <strong>DEFECT CLASSIFICATION:</strong> ${wo.defect_type.toUpperCase()}<br>
                            <strong>LOCATION:</strong> ${wo.road_name}<br>
                            <strong>ZONE:</strong> ${wo.zone}<br>
                            <strong>GPS COORDS:</strong> ${wo.lat}, ${wo.lng}
                        </div>
                        <div>
                            <strong>AGENCY:</strong> ${wo.assigned_agency}<br>
                            <strong>CREW:</strong> ${wo.assigned_crew || 'Unit-1'}<br>
                            <strong>SUPERVISOR:</strong> ${wo.supervisor}<br>
                            <strong>TARGET COMPLETION:</strong> ${wo.target_completion_date}
                        </div>
                    </div>
                    <div style="margin-top:16px; background:rgba(0,0,0,0.3); padding:10px; border-radius:4px;">
                        <strong>DISPATCHED MATERIALS & EQUIPMENT:</strong>
                        <ul style="margin-left:20px; margin-top:4px;">
                            ${(wo.materials_required || []).map(m => `<li>${m}</li>`).join("")}
                        </ul>
                    </div>
                    <div style="margin-top:20px; display:flex; justify-content:space-between; padding-top:20px; border-top:1px solid #64748b;">
                        <div>SIGNATURE: ____________________<br><small>Field Inspection Officer</small></div>
                        <div>STAMP: ____________________<br><small>Municipal Engineering Authority</small></div>
                    </div>
                </div>
            `;

            modal.classList.remove("hidden");
        } catch (err) {
            console.error("Open print modal failed:", err);
        }
    }

    closeWorkOrderPrintModal() {
        const modal = document.getElementById("modal-work-order-print");
        if (modal) modal.classList.add("hidden");
    }

    /* ================= Traffic Flow & O-D Matrix Analytics ================= */
    async loadTrafficAnalytics() {
        try {
            const [trafficRes, odRes] = await Promise.all([
                fetch("/api/analytics/traffic"),
                fetch("/api/analytics/od-matrix")
            ]);
            const trafficData = await trafficRes.json();
            const odData = await odRes.json();

            this.trafficAnalyticsData = trafficData;
            this.odMatrixData = odData;

            this.renderTrafficCharts();
            this.renderODMatrixTable(odData.matrix || []);
            this.renderBottlenecksList(trafficData.active_bottleneck_corridors || []);
        } catch (err) {
            console.error("Error loading traffic analytics:", err);
        }
    }

    renderTrafficCharts() {
        if (!this.trafficAnalyticsData) return;

        // 1. Hourly Curve Chart
        const hourlyCanvas = document.getElementById("chart-traffic-hourly");
        if (hourlyCanvas && !this.hourlyTrafficChart) {
            const trend = this.trafficAnalyticsData.hourly_trend || [];
            this.hourlyTrafficChart = new Chart(hourlyCanvas.getContext("2d"), {
                type: 'line',
                data: {
                    labels: trend.map(t => t.hour),
                    datasets: [
                        {
                            label: 'Hourly Vehicle Volume (Veh/h)',
                            data: trend.map(t => t.volume),
                            borderColor: '#00e5ff',
                            backgroundColor: 'rgba(0, 229, 255, 0.15)',
                            fill: true,
                            tension: 0.4,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Avg Corridor Flow Speed (km/h)',
                            data: trend.map(t => t.speed),
                            borderColor: '#ffb300',
                            backgroundColor: 'transparent',
                            borderDash: [5, 5],
                            tension: 0.4,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { type: 'linear', position: 'left', grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#00e5ff' } },
                        y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#ffb300' } }
                    },
                    plugins: {
                        legend: { labels: { color: '#fff' } }
                    }
                }
            });
        }

        // 2. Vehicle Breakdown Doughnut
        const breakdownCanvas = document.getElementById("chart-vehicle-breakdown");
        if (breakdownCanvas && !this.vehicleBreakdownChart) {
            this.vehicleBreakdownChart = new Chart(breakdownCanvas.getContext("2d"), {
                type: 'doughnut',
                data: {
                    labels: ['Private Cars & Sedans (48%)', '2-Wheelers / Bikes (30%)', 'Transit Buses (12%)', 'Auto-Rickshaws (6%)', 'Freight Trucks (4%)'],
                    datasets: [{
                        data: [48, 30, 12, 6, 4],
                        backgroundColor: ['#00e5ff', '#00e676', '#ffb300', '#e040fb', '#ff1744'],
                        borderColor: '#0f172a',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } }
                    }
                }
            });
        }
    }

    renderODMatrixTable(matrix) {
        const tbody = document.getElementById("od-matrix-tbody");
        if (!tbody) return;

        tbody.innerHTML = matrix.map(m => {
            const congScore = m.congestion_score;
            let badgeClass = "status-emerald";
            let congLabel = "Smooth Flow";
            if (congScore > 0.8) { badgeClass = "text-red"; congLabel = "Severe Bottleneck"; }
            else if (congScore > 0.65) { badgeClass = "text-amber"; congLabel = "Moderate Congestion"; }

            return `
                <tr>
                    <td><strong>${m.origin}</strong></td>
                    <td><strong>${m.dest}</strong></td>
                    <td class="mono">${m.volume.toLocaleString()} veh/h</td>
                    <td class="mono ${badgeClass}">+${m.avg_delay_min.toFixed(1)} min</td>
                    <td><span class="status-badge ${badgeClass}">${congLabel}</span></td>
                </tr>
            `;
        }).join("");
    }

    renderBottlenecksList(bottlenecks) {
        const container = document.getElementById("bottleneck-container");
        if (!container) return;

        container.innerHTML = bottlenecks.map(b => `
            <div class="bottleneck-item">
                <div class="bottleneck-item-title">
                    <span>${b.corridor}</span>
                    <span class="text-red mono">+${b.delay_min} min delay</span>
                </div>
                <div class="bottleneck-item-cause"><i class="fa-solid fa-circle-exclamation text-amber"></i> Root Cause: ${b.cause}</div>
            </div>
        `).join("");
    }

    /* ================= Emergency ANPR & Incident Locker ================= */
    async loadIncidents() {
        try {
            const res = await fetch("/api/incidents");
            const data = await res.json();
            const incidents = data.incidents || [];

            const kpiInc = document.getElementById("kpi-incidents-count");
            const navBadge = document.getElementById("badge-inc-count");
            if (kpiInc) kpiInc.textContent = `${incidents.length} Alerts`;
            if (navBadge) navBadge.textContent = `${incidents.length}`;

            this.renderIncidentsList(incidents);
        } catch (err) {
            console.error("Error loading incidents:", err);
        }
    }

    renderIncidentsList(incidents) {
        const container = document.getElementById("incidents-container");
        if (!container) return;

        container.innerHTML = incidents.map(inc => {
            const veh = inc.offender_vehicle || {};
            return `
                <div class="incident-dossier-card">
                    <div class="dossier-header">
                        <span class="dossier-title"><i class="fa-solid fa-car-burst"></i> ${inc.incident_type}</span>
                        <span class="status-badge status-${inc.status.toLowerCase().replace(/ /g, '-')}">${inc.status}</span>
                    </div>
                    <div class="dossier-body">
                        <img src="${inc.snapshot_url}" class="dossier-img" onclick="app.inspectIncident('${inc.id}')" title="Click to view full ANPR evidence">
                        <div class="dossier-details">
                            <div class="anpr-plate-box">${inc.license_plate}</div>
                            <div><strong>ANPR OCR Confidence:</strong> <span class="text-cyan mono">${inc.anpr_confidence}%</span></div>
                            <div><strong>Offender Vehicle:</strong> ${veh.make || 'SUV'} ${veh.model || ''} (${veh.color || 'Dark'})</div>
                            <div><strong>Incident Speed:</strong> <span class="text-red mono">${inc.estimated_speed_kmh} km/h</span></div>
                            <div><strong>Escape Trajectory:</strong> <small class="text-muted">${inc.trajectory_vector}</small></div>
                            <div><strong>Location:</strong> ${inc.road_name} (Unit: ${inc.bus_id})</div>
                        </div>
                    </div>
                    <div class="dossier-actions">
                        ${inc.police_fir_number ? `
                            <span class="mono text-emerald" style="font-size:11px;"><i class="fa-solid fa-shield-check"></i> FIR: ${inc.police_fir_number}</span>
                        ` : `
                            <button class="btn btn-xs btn-primary" onclick="app.dispatchPoliceAlert('${inc.id}')">
                                <i class="fa-solid fa-shield-halved"></i> Dispatch Police FIR Alert
                            </button>
                        `}
                        <button class="btn btn-xs btn-outline" onclick="app.inspectIncident('${inc.id}')">
                            <i class="fa-solid fa-file-shield"></i> Full Dossier
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    }

    async inspectIncident(incidentId) {
        try {
            const res = await fetch("/api/incidents");
            const data = await res.json();
            const inc = (data.incidents || []).find(i => i.id === incidentId);
            if (!inc) return;

            const modal = document.getElementById("modal-incident-inspect");
            const body = document.getElementById("modal-incident-body");
            if (!modal || !body) return;

            const veh = inc.offender_vehicle || {};
            body.innerHTML = `
                <div style="display:grid; grid-template-columns: 1.2fr 1fr; gap:20px;">
                    <div>
                        <img src="${inc.snapshot_url}" style="width:100%; border-radius:8px; border:2px solid #ff1744; box-shadow:var(--shadow-red-glow);">
                        <div style="margin-top:10px; font-size:11px; color:var(--text-muted);">
                            <strong>Cryptographic Hash Watermark:</strong> SHA256:${inc.id}-VERIFIED-TAMPERPROOF | Timestamp: ${inc.timestamp}
                        </div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div>
                            <span class="status-badge status-dispatched">HIGH PRIORITY LAW ENFORCEMENT DISPATCH</span>
                            <h3 style="color:#ff5252; margin-top:6px;">${inc.incident_type}</h3>
                            <p style="color:var(--text-muted); font-size:12px;"><i class="fa-solid fa-location-dot"></i> ${inc.road_name} (Captured by ${inc.bus_id})</p>
                        </div>
                        <div class="anpr-plate-box" style="font-size:22px;">
                            ${inc.license_plate} <span style="font-size:12px; color:#00e5ff;">(OCR: ${inc.anpr_confidence}%)</span>
                        </div>
                        <div style="background:var(--bg-surface-elevated); padding:12px; border-radius:6px; font-size:12px; display:flex; flex-direction:column; gap:6px;">
                            <div><strong>Vehicle Make & Model:</strong> ${veh.make || 'SUV'} ${veh.model || ''}</div>
                            <div><strong>Body Type & Color:</strong> ${veh.type || 'SUV'}, ${veh.color || 'Dark'}</div>
                            <div><strong>Speed at Incident:</strong> <span class="text-red mono font-bold">${inc.estimated_speed_kmh} km/h</span></div>
                            <div><strong>Trajectory Vector:</strong> ${inc.trajectory_vector}</div>
                            <div><strong>FIR Reference:</strong> <span class="mono text-cyan">${inc.police_fir_number || 'Pending Law Enforcement Dispatch'}</span></div>
                        </div>
                        ${!inc.police_fir_number ? `
                            <button class="btn btn-primary" style="background:#ff1744; color:#fff;" onclick="app.dispatchPoliceAlert('${inc.id}')">
                                <i class="fa-solid fa-shield-halved"></i> Transmit Urgent FIR to Traffic Police PCR
                            </button>
                        ` : `
                            <div style="background:rgba(0,230,118,0.15); border:1px solid var(--color-emerald); padding:8px 12px; border-radius:6px; color:var(--color-emerald); font-weight:bold; font-size:12px;">
                                <i class="fa-solid fa-check-double"></i> Successfully Dispatched to Delhi Traffic Police PCR Control
                            </div>
                        `}
                    </div>
                </div>
            `;

            modal.classList.remove("hidden");
        } catch (err) {
            console.error("Inspect incident failed:", err);
        }
    }

    closeIncidentModal() {
        const modal = document.getElementById("modal-incident-inspect");
        if (modal) modal.classList.add("hidden");
    }

    async dispatchPoliceAlert(incidentId) {
        try {
            const res = await fetch("/api/incidents/notify-police", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ incident_id: incidentId })
            });
            const data = await res.json();
            if (data.status === "success") {
                this.loadIncidents();
                this.inspectIncident(incidentId);
            }
        } catch (err) {
            console.error("Dispatch police alert failed:", err);
        }
    }

    /* ================= Municipal RQI Scorecard ================= */
    async loadRqiScorecards() {
        try {
            const res = await fetch("/api/analytics/rqi-zones");
            const data = await res.json();
            const zones = data.rqi_zones || [];

            const kpiRqi = document.getElementById("kpi-rqi-score");
            if (kpiRqi) kpiRqi.textContent = `${data.city_average_rqi.toFixed(1)} / 100`;

            this.renderRqiZonesTable(zones);
        } catch (err) {
            console.error("Error loading RQI scorecards:", err);
        }
    }

    renderRqiZonesTable(zones) {
        const tbody = document.getElementById("rqi-zones-tbody");
        if (!tbody) return;

        tbody.innerHTML = zones.map(z => {
            let statusBadge = "status-fair";
            let color = "text-amber";
            if (z.rqi_score >= 85) { statusBadge = "status-repaired"; color = "text-emerald"; }
            else if (z.rqi_score < 75) { statusBadge = "status-detected"; color = "text-red"; }

            return `
                <tr>
                    <td><strong>${z.zone_name}</strong><br><small class="text-dim mono">${z.zone_id}</small></td>
                    <td class="mono font-bold ${color}" style="font-size:15px;">${z.rqi_score.toFixed(1)}</td>
                    <td class="mono">${z.pothole_count}</td>
                    <td class="mono">${z.missing_infrastructure_count}</td>
                    <td class="mono">${z.total_km_surveyed} km</td>
                    <td><span class="status-badge ${statusBadge}">${z.status}</span></td>
                    <td>
                        <button class="btn btn-xs btn-outline" onclick="document.querySelector('[data-tab=\\'tab-maintenance\\']').click()">
                            View Work Orders
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    }
}

// Global App Instance
const app = new StrideApp();
window.addEventListener("DOMContentLoaded", () => {
    app.init();
});
