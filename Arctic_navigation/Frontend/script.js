
// ==========================================
// GLOBAL VARIABLES FOR LEAFLET MAP
// ==========================================
let map;
let routeLayer;
let pointsLayer;
let userLocationMarker;

// ==========================================
// INITIALIZATION ON PAGE LOAD
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // Initialize Leaflet Map centered on an Arctic region
    map = L.map('map-container').setView([70.0, 20.0], 4);

    // Use a dark-themed map tile (CartoDB Dark Matter) to match the UI
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors & CartoDB',
        maxZoom: 19
    }).addTo(map);

    // Create layer groups to easily clear old routes when a new one is searched
    routeLayer = L.layerGroup().addTo(map);
    pointsLayer = L.layerGroup().addTo(map);

    // Start tracking the user's live device location
    startLiveTracking();

    // Attach click event to the Analyze button
    document.getElementById("analyze-btn").addEventListener("click", handleRouteAnalysis);
});

// ==========================================
// LIVE LOCATION TRACKING (BLUE DOT)
// ==========================================
function startLiveTracking() {
    if (!navigator.geolocation) {
        console.warn("Geolocation is not supported by this browser.");
        return;
    }

    // Custom CSS for the glowing blue dot (Google Maps style)
    const blueDotIcon = L.divIcon({
        className: 'live-location-dot',
        html: `<div style="width: 14px; height: 14px; background-color: #2563eb; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px #2563eb;"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });

    // Watch the user's position continuously
    navigator.geolocation.watchPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            // If marker exists, update position. Otherwise, create it.
            if (userLocationMarker) {
                userLocationMarker.setLatLng([lat, lng]);
            } else {
                userLocationMarker = L.marker([lat, lng], { icon: blueDotIcon, zIndexOffset: 1000 }).addTo(map);
                userLocationMarker.bindPopup("<b>Your Live Location</b>");
            }
        },
        (error) => {
            console.warn("Location tracking error or permission denied:", error.message);
        },
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
    );
}

// ==========================================
// QUICK EXAMPLES FILLER
// ==========================================
function fillExample(start, end) {
    document.getElementById("start-location").value = start;
    document.getElementById("end-location").value = end;
}

// ==========================================
// RISK CATEGORY STYLING HELPER
// ==========================================
function getRiskStyle(percentage) {
    if (percentage >= 56) {
        return { color: "#ef4444", alertClass: "high-risk", icon: "fa-triangle-exclamation" }; // Red
    } else if (percentage >= 36) {
        return { color: "#eab308", alertClass: "medium-risk", icon: "fa-circle-exclamation" }; // Yellow
    } else {
        return { color: "#22c55e", alertClass: "low-risk", icon: "fa-circle-check" }; // Green
    }
}

// ==========================================
// ==========================================
// MAIN API CALL & UI UPDATE
// ==========================================
async function handleRouteAnalysis() {
    const startLoc = document.getElementById("start-location").value.trim();
    const endLoc = document.getElementById("end-location").value.trim();
    const btn = document.getElementById("analyze-btn");

    if (!startLoc || !endLoc) {
        alert("Please enter both Start and End locations.");
        return;
    }

    // Set Loading State
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...`;
    btn.disabled = true;

    try {
        // Call the FastAPI Backend using relative path for Render
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                start_location: startLoc,
                end_location: endLoc
            })
        });

        const data = await response.json();

        if (response.ok) {
            updateDashboard(data);
            plotRouteOnMap(data);
        } else {
            alert(`Error: ${data.detail || 'Failed to analyze route.'}`);
        }
    } catch (error) {
        console.error("API Call Failed:", error);
        alert("Cannot connect to the backend server. Is FastAPI running?");
    } finally {
        // Reset Button State
        btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Analyze Route`;
        btn.disabled = false;
    }
}
// ==========================================
// UPDATE DASHBOARD UI
// ==========================================
function updateDashboard(data) {
    const riskPct = data.overall_max_risk;
    const styleInfo = getRiskStyle(riskPct);

    // Update the Large Alert Box
    const alertBox = document.getElementById("risk-alert");
    const riskIcon = document.getElementById("risk-icon");
    const riskText = document.getElementById("risk-text-display");
    
    alertBox.className = `risk-alert ${styleInfo.alertClass}`;
    riskIcon.className = `fa-solid ${styleInfo.icon}`;
    riskText.textContent = data.overall_category.toUpperCase();

    // Update Percentage and Progress Bar
    document.getElementById("risk-percentage").textContent = `${riskPct}%`;
    const progressBar = document.getElementById("risk-progress");
    progressBar.style.width = `${riskPct}%`;
    progressBar.style.backgroundColor = styleInfo.color;

    // Update Details Rows
    document.getElementById("lbl-start").textContent = document.getElementById("start-location").value;
    document.getElementById("lbl-end").textContent = document.getElementById("end-location").value;
    
    const categorySpan = document.getElementById("lbl-category");
    categorySpan.textContent = data.overall_category;
    categorySpan.style.color = styleInfo.color;
}

// ==========================================
// PLOT ROUTE & POINTS ON LEAFLET MAP
// ==========================================
function plotRouteOnMap(data) {
    // Clear previous results
    routeLayer.clearLayers();
    pointsLayer.clearLayers();

    // 1. Draw the full continuous route line (OSRM returns [lon, lat], Leaflet needs [lat, lon])
    const routeLatLngs = data.full_route.map(coord => [coord[1], coord[0]]);
    const polyline = L.polyline(routeLatLngs, { color: '#3b82f6', weight: 4, opacity: 0.7 }).addTo(routeLayer);

    // 2. Plot the analyzed points with risk colors
    data.analyzed_points.forEach(point => {
        const styleInfo = getRiskStyle(point.risk_percentage);
        
        const circle = L.circleMarker([point.lat, point.lon], {
            radius: 5,
            fillColor: styleInfo.color,
            color: "#ffffff", // White border
            weight: 1,
            opacity: 1,
            fillOpacity: 0.9
        });

        // Add tooltip on hover showing exact risk percentage
        circle.bindTooltip(`<b>Risk:</b> ${point.risk_percentage}%<br><b>Zone:</b> ${point.risk_category}`);
        circle.addTo(pointsLayer);
    });

    // 3. Add Start and End Markers
    const startCoord = [data.start_coords[1], data.start_coords[0]];
    const endCoord = [data.end_coords[1], data.end_coords[0]];

    L.marker(startCoord).bindPopup("<b>Start</b>").addTo(routeLayer);
    L.marker(endCoord).bindPopup("<b>End</b>").addTo(routeLayer);

    // Automatically zoom and center the map to fit the entire route
    map.fitBounds(polyline.getBounds(), { padding: [50, 50] });
}
