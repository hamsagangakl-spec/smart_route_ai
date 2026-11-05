// Smart Route AI - Client Application Logic

let map;
let routeLayers = [];
let markerStart = null;
let markerDest = null;
let currentRoutes = [];
let activeRouteIndex = 0;
let currentAssistantLang = 'en';
let checkinTimerInterval = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initTheme();
    initDefaultTime();
    loadFavourites();
    loadHistory();
    loadSafetyCheckins();
    renderAssistantChips();

    // Start live countdown timer loop for safety check-ins
    checkinTimerInterval = setInterval(updateCheckinTimers, 1000);

    // Initial automated calculation for Bangalore to Mysore
    setTimeout(() => {
        calculateSmartRoute();
    }, 500);
});

// ==================== 1. MAP INITIALIZATION ====================

function initMap() {
    // Center initially around Karnataka / South India
    map = L.map('map').setView([12.9716, 77.5946], 8);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18
    }).addTo(map);
}

function fitMapBounds() {
    if (routeLayers.length > 0) {
        const group = new L.featureGroup(routeLayers);
        map.fitBounds(group.getBounds(), { padding: [40, 40] });
    }
}

let isSatellite = false;
let satelliteLayer = null;

function toggleMapTiles() {
    if (!satelliteLayer) {
        satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        });
    }

    if (!isSatellite) {
        map.addLayer(satelliteLayer);
        isSatellite = true;
    } else {
        map.removeLayer(satelliteLayer);
        isSatellite = false;
    }
}

// ==================== 2. THEME & DEFAULTS ====================

function initTheme() {
    const savedTheme = localStorage.getItem('smart_route_theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        document.getElementById('themeToggleBtn').innerText = '☀️ Light';
    }

    document.getElementById('themeToggleBtn').addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        localStorage.setItem('smart_route_theme', isLight ? 'light' : 'dark');
        document.getElementById('themeToggleBtn').innerText = isLight ? '☀️ Light' : '🌙 Dark';
    });
}

function initDefaultTime() {
    // Set safety check-in expected arrival to 3.5 hours from current time
    const now = new Date();
    now.setMinutes(now.getMinutes() + 210);
    const tzoffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now.getTime() - tzoffset)).toISOString().slice(0, 16);
    const arrivalInput = document.getElementById('chkArrivalTime');
    if (arrivalInput) {
        arrivalInput.value = localISOTime;
    }
}

function autoAdjustMileage() {
    const vType = document.getElementById('vehicleType').value;
    const mileageInput = document.getElementById('mileageInput');
    const unitSpan = document.getElementById('mileageUnit');

    if (vType === 'bike') {
        mileageInput.value = '48.0';
        unitSpan.innerText = 'km/L';
    } else if (vType === 'diesel_car') {
        mileageInput.value = '19.5';
        unitSpan.innerText = 'km/L';
    } else if (vType === 'ev') {
        mileageInput.value = '7.5';
        unitSpan.innerText = 'km/kWh';
    } else if (vType === 'suv') {
        mileageInput.value = '12.0';
        unitSpan.innerText = 'km/L';
    } else {
        // Petrol car
        mileageInput.value = '16.0';
        unitSpan.innerText = 'km/L';
    }
}

function loadPreset(start, dest) {
    document.getElementById('startPlace').value = start.charAt(0).toUpperCase() + start.slice(1);
    document.getElementById('destPlace').value = dest.charAt(0).toUpperCase() + dest.slice(1);
    calculateSmartRoute();
}

function detectCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude.toFixed(4);
                const lon = pos.coords.longitude.toFixed(4);
                document.getElementById('startPlace').value = `GPS (${lat}, ${lon})`;
                alert(`Current location detected: ${lat}, ${lon}`);
            },
            (err) => {
                alert('GPS location permission denied or unavailable. Using entered city name.');
            }
        );
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}

// ==================== 3. ROUTE CALCULATION ====================

async function geocodePlace(name) {
    try {
        const resp = await fetch(`/api/geocode?q=${encodeURIComponent(name)}`);
        const data = await resp.json();
        return data;
    } catch (e) {
        console.error('Geocode error:', e);
        return { lat: 12.9716, lon: 77.5946, display_name: name };
    }
}

async function calculateSmartRoute() {
    const btn = document.getElementById('btnCalculate');
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ Calculating Routes & Forecasts...</span>';

    const startPlace = document.getElementById('startPlace').value.trim();
    const destPlace = document.getElementById('destPlace').value.trim();
    const personality = document.getElementById('routePersonality').value;
    const vehicleType = document.getElementById('vehicleType').value;
    const mileage = parseFloat(document.getElementById('mileageInput').value) || 16.0;
    const fuelPrice = parseFloat(document.getElementById('fuelPriceInput').value) || 102.5;
    const passengers = parseInt(document.getElementById('passengersInput').value) || 1;

    try {
        // Step 1: Geocode starting & destination points
        const startGeo = await geocodePlace(startPlace);
        const destGeo = await geocodePlace(destPlace);

        // Step 2: Request route calculation from backend
        const payload = {
            start_place: startPlace,
            dest_place: destPlace,
            start_lat: startGeo.lat,
            start_lon: startGeo.lon,
            dest_lat: destGeo.lat,
            dest_lon: destGeo.lon,
            personality: personality,
            vehicle_type: vehicleType,
            mileage: mileage,
            fuel_price: fuelPrice,
            passengers: passengers
        };

        const res = await fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            currentRoutes = data.routes;
            renderMapRoutes(data.routes, startGeo, destGeo);
            renderRouteCards(data.routes, data.recommendation_reason, passengers);
            renderWeather(data.weather);
            renderRiskScore(data.routes[0].risk);
            loadHistory(); // refresh history table
        } else {
            alert('Failed to calculate route: ' + (data.message || 'Unknown error'));
        }
    } catch (err) {
        console.error('Route calculation error:', err);
        alert('Route Calculation encountered an error. Check server logs.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🔍 Find & Compare Smart Routes</span>';
    }
}

// Render polylines & markers on map
function renderMapRoutes(routes, startGeo, destGeo) {
    // Clear previous layers
    routeLayers.forEach(l => map.removeLayer(l));
    routeLayers = [];
    if (markerStart) map.removeLayer(markerStart);
    if (markerDest) map.removeLayer(markerDest);

    // Add Start Marker (Green circle icon)
    markerStart = L.circleMarker([startGeo.lat, startGeo.lon], {
        radius: 9,
        fillColor: '#10b981',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 0.95
    }).addTo(map).bindPopup(`<b>Start:</b> ${startGeo.display_name}`).openPopup();

    // Add Destination Marker (Red circle icon)
    markerDest = L.circleMarker([destGeo.lat, destGeo.lon], {
        radius: 9,
        fillColor: '#ef4444',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 0.95
    }).addTo(map).bindPopup(`<b>Destination:</b> ${destGeo.display_name}`);

    // Colors for Primary vs Alternative routes
    const colors = ['#3b82f6', '#10b981', '#f59e0b'];

    routes.forEach((route, idx) => {
        const isPrimary = (idx === 0);
        const polyline = L.polyline(route.coordinates, {
            color: colors[idx % colors.length],
            weight: isPrimary ? 6 : 4,
            opacity: isPrimary ? 0.9 : 0.65,
            dashArray: isPrimary ? null : '6, 8'
        }).addTo(map);

        polyline.bindTooltip(`<b>${route.name}</b><br>${route.distance_km} km | ${route.duration_text}`, {
            sticky: true
        });

        polyline.on('click', () => {
            selectRouteCard(idx);
        });

        routeLayers.push(polyline);
    });

    fitMapBounds();
}

// Render comparison cards in the grid
function renderRouteCards(routes, recReason, passengers) {
    const banner = document.getElementById('recommendationBanner');
    banner.innerText = recReason;

    const container = document.getElementById('routesGrid');
    container.innerHTML = '';

    routes.forEach((route, idx) => {
        const isRec = route.is_recommended;
        const card = document.createElement('div');
        card.className = `route-card ${idx === 0 ? 'is-active' : ''} ${isRec ? 'is-recommended' : ''}`;
        card.id = `routeCard_${idx}`;
        card.onclick = () => selectRouteCard(idx);

        card.innerHTML = `
            ${isRec ? '<div class="recommended-ribbon">⭐ AI Recommended</div>' : ''}
            <div class="route-card-title">
                <span>${route.name}</span>
                <span class="badge ${route.risk.badge_class}">${route.risk.level}</span>
            </div>
            
            <div class="route-metric-hero">
                <div class="metric-item">
                    <div class="metric-label">Distance</div>
                    <div class="metric-val">${route.distance_km} <span style="font-size:0.8rem">km</span></div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Travel Time</div>
                    <div class="metric-val">${route.duration_text}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Fuel Est.</div>
                    <div class="metric-val">₹${route.fuel.total_cost}</div>
                </div>
            </div>

            <div class="route-details-list">
                <div class="route-detail-row">
                    <span>Fuel Required</span>
                    <strong>${route.fuel.liters} L</strong>
                </div>
                <div class="route-detail-row">
                    <span>Cost Split (${passengers} Person${passengers > 1 ? 's' : ''})</span>
                    <strong class="split-pill">₹${route.fuel.cost_per_person} / head</strong>
                </div>
                <div class="route-detail-row">
                    <span>Trip Carbon Footprint</span>
                    <strong>${route.carbon.total_co2_kg} kg CO₂</strong>
                </div>
                <div class="route-detail-row">
                    <span>Emissions / Passenger</span>
                    <strong>${route.carbon.co2_per_person} kg CO₂</strong>
                </div>
                <div class="route-detail-row">
                    <span>Road Risk Rating</span>
                    <strong style="color: ${route.risk.color}">${route.risk.score} / 100 (${route.risk.level})</strong>
                </div>
            </div>
        `;

        container.appendChild(card);
    });
}

function selectRouteCard(index) {
    activeRouteIndex = index;
    const cards = document.querySelectorAll('.route-card');
    cards.forEach((c, idx) => {
        c.classList.toggle('is-active', idx === index);
    });

    // Highlight selected polyline
    routeLayers.forEach((layer, idx) => {
        if (idx === index) {
            layer.setStyle({ weight: 7, opacity: 1.0 });
            layer.bringToFront();
        } else {
            layer.setStyle({ weight: 4, opacity: 0.45 });
        }
    });

    // Update risk display to match selected route
    if (currentRoutes[index]) {
        renderRiskScore(currentRoutes[index].risk);
    }
}

// ==================== 4. WEATHER & ROAD RISK ====================

function renderWeather(w) {
    if (!w) return;
    document.getElementById('destTemp').innerText = w.temperature;
    document.getElementById('destCondition').innerText = w.condition;
    document.getElementById('destWind').innerText = `Wind: ${w.wind}`;
    document.getElementById('destAdvice').innerText = w.driving_advice;

    const badge = document.getElementById('weatherLiveBadge');
    if (w.is_live) {
        badge.className = 'badge badge-success';
        badge.innerText = 'Live Forecast (Open-Meteo)';
    } else {
        badge.className = 'badge badge-warning';
        badge.innerText = 'Offline Simulated Forecast';
    }
}

function renderRiskScore(risk) {
    if (!risk) return;
    document.getElementById('riskScoreVal').innerText = risk.score;
    document.getElementById('riskScoreVal').style.color = risk.color;

    const badge = document.getElementById('riskScoreBadge');
    badge.className = `badge ${risk.badge_class}`;
    badge.innerText = risk.level;

    document.getElementById('riskLevelTitle').innerText = `${risk.level} (${risk.score}/100)`;
    document.getElementById('riskSummaryText').innerText = risk.summary;
}

// ==================== 5. FAVOURITES & HISTORY ====================

async function loadFavourites() {
    try {
        const resp = await fetch('/api/favourites');
        const data = await resp.json();
        const list = document.getElementById('favouritesList');
        list.innerHTML = '';

        if (!data.favourites || data.favourites.length === 0) {
            list.innerHTML = '<div style="font-size:0.78rem; color:var(--text-muted);">No favourite journeys saved yet. Click "+ Save Current" to pin one!</div>';
            return;
        }

        data.favourites.forEach(fav => {
            const item = document.createElement('div');
            item.className = 'fav-item';
            item.innerHTML = `
                <div>
                    <strong class="fav-load-link" onclick="loadFavouriteRoute('${fav.start_place}', '${fav.destination}')">
                        ${fav.name}
                    </strong>
                    <div style="font-size:0.72rem; color:var(--text-muted);">${fav.start_place} ➔ ${fav.destination}</div>
                </div>
                <button class="fav-del-btn" onclick="deleteFavourite(${fav.id})" title="Delete">✕</button>
            `;
            list.appendChild(item);
        });
    } catch (e) {
        console.error('Error loading favourites:', e);
    }
}

async function saveCurrentToFavourites() {
    const start = document.getElementById('startPlace').value.trim();
    const dest = document.getElementById('destPlace').value.trim();
    const name = prompt('Enter a friendly nickname for this journey:', `${start} to ${dest}`);
    if (!name) return;

    try {
        const resp = await fetch('/api/favourites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                start_place: start,
                destination: dest,
                notes: 'Saved from dashboard'
            })
        });
        const data = await resp.json();
        if (data.success) {
            loadFavourites();
        }
    } catch (e) {
        alert('Failed to save favourite: ' + e);
    }
}

async function deleteFavourite(favId) {
    if (!confirm('Remove this favourite journey?')) return;
    try {
        await fetch(`/api/favourites/${favId}`, { method: 'DELETE' });
        loadFavourites();
    } catch (e) {
        console.error(e);
    }
}

function loadFavouriteRoute(start, dest) {
    document.getElementById('startPlace').value = start;
    document.getElementById('destPlace').value = dest;
    calculateSmartRoute();
}

async function loadHistory() {
    try {
        const resp = await fetch('/api/history');
        const data = await resp.json();
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:1rem;">No recent journey history in database.</td></tr>';
            return;
        }

        data.history.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${item.start_place}</strong></td>
                <td><strong>${item.destination}</strong></td>
                <td>${item.distance_km} km</td>
                <td>${Math.round(item.duration_min)} min</td>
                <td><span class="badge badge-info">${item.selected_personality}</span></td>
                <td>${item.risk_score}</td>
                <td>₹${item.fuel_cost}</td>
                <td style="font-size:0.75rem; color:var(--text-muted);">${item.created_at_local}</td>
                <td>
                    <button class="btn-ghost-sm" onclick="loadFavouriteRoute('${item.start_place}', '${item.destination}')">Re-run</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('History load error:', e);
    }
}

async function clearSearchHistory() {
    if (!confirm('Clear all SQLite search records?')) return;
    try {
        await fetch('/api/history', { method: 'DELETE' });
        loadHistory();
    } catch (e) {
        alert('Error clearing history: ' + e);
    }
}

// ==================== 6. JOURNEY SAFETY CHECK-IN TRACKER ====================

async function submitSafetyCheckin() {
    const traveler = document.getElementById('chkTraveler').value.trim();
    const contact = document.getElementById('chkContact').value.trim();
    const phone = document.getElementById('chkPhone').value.trim();
    const arrivalTime = document.getElementById('chkArrivalTime').value;
    const dest = document.getElementById('destPlace').value.trim();

    if (!arrivalTime) {
        alert('Please choose an expected arrival time.');
        return;
    }

    try {
        const resp = await fetch('/api/safety-checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                traveler_name: traveler,
                emergency_contact: contact,
                contact_phone: phone,
                destination: dest,
                expected_arrival: arrivalTime
            })
        });

        const data = await resp.json();
        if (data.success) {
            alert('Safety Check-In Registered! Live countdown is now active.');
            loadSafetyCheckins();
        }
    } catch (e) {
        alert('Failed to register checkin: ' + e);
    }
}

let activeCheckins = [];

async function loadSafetyCheckins() {
    try {
        const resp = await fetch('/api/safety-checkins');
        const data = await resp.json();
        activeCheckins = data.checkins || [];
        renderSafetyCheckinList();
    } catch (e) {
        console.error('Failed to load checkins:', e);
    }
}

function renderSafetyCheckinList() {
    const list = document.getElementById('activeCheckinList');
    list.innerHTML = '';

    if (activeCheckins.length === 0) {
        list.innerHTML = '<div style="font-size:0.8rem; color:var(--text-muted);">No active travel monitors right now.</div>';
        return;
    }

    activeCheckins.forEach(chk => {
        const item = document.createElement('div');
        const isOverdue = chk.is_overdue;
        const isCompleted = (chk.status === 'ARRIVED_SAFE');

        item.className = `checkin-card-item ${isOverdue ? 'is-overdue' : ''}`;
        item.id = `checkinCard_${chk.id}`;

        let statusBadge = `<span class="badge badge-success">On Schedule</span>`;
        if (isCompleted) {
            statusBadge = `<span class="badge badge-info">✅ Arrived Safe</span>`;
        } else if (isOverdue) {
            statusBadge = `<span class="badge badge-danger">⚠️ OVERDUE ALARM!</span>`;
        }

        item.innerHTML = `
            <div class="checkin-item-header">
                <span>👤 ${chk.traveler_name} ➔ ${chk.destination}</span>
                ${statusBadge}
            </div>
            <div style="font-size:0.75rem; color:var(--text-secondary);">
                Emergency Contact: <strong>${chk.emergency_contact} (${chk.contact_phone})</strong>
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted);">
                Expected by: ${chk.expected_arrival.replace('T', ' ')}
            </div>
            <div class="checkin-timer" id="timer_${chk.id}">
                ${isCompleted ? 'Journey Completed' : 'Calculating remaining time...'}
            </div>
            ${!isCompleted ? `
                <button class="btn-arrived" onclick="markArrivedSafe(${chk.id})">✅ Mark as Arrived Safe</button>
            ` : ''}
        `;

        list.appendChild(item);
    });
}

function updateCheckinTimers() {
    if (!activeCheckins || activeCheckins.length === 0) return;
    const now = new Date();

    activeCheckins.forEach(chk => {
        if (chk.status !== 'ACTIVE') return;

        const timerElem = document.getElementById(`timer_${chk.id}`);
        const cardElem = document.getElementById(`checkinCard_${chk.id}`);
        if (!timerElem) return;

        const target = new Date(chk.expected_arrival);
        const diffMs = target - now;

        if (diffMs > 0) {
            // Still on time
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            const diffSecs = Math.floor((diffMs % (1000 * 60)) / 1000);
            timerElem.innerText = `⏳ Due in: ${diffHours}h ${diffMins}m ${diffSecs}s`;
            if (cardElem) cardElem.classList.remove('is-overdue');
        } else {
            // Overdue!
            const overdueMs = Math.abs(diffMs);
            const ovHours = Math.floor(overdueMs / (1000 * 60 * 60));
            const ovMins = Math.floor((overdueMs % (1000 * 60 * 60)) / (1000 * 60));
            const ovSecs = Math.floor((overdueMs % (1000 * 60)) / 1000);
            timerElem.innerText = `🚨 OVERDUE BY: ${ovHours}h ${ovMins}m ${ovSecs}s! Notify ${chk.emergency_contact}`;
            if (cardElem) cardElem.classList.add('is-overdue');
        }
    });
}

async function markArrivedSafe(checkinId) {
    try {
        await fetch(`/api/safety-checkin/${checkinId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'ARRIVED_SAFE' })
        });
        loadSafetyCheckins();
    } catch (e) {
        alert('Failed to update status: ' + e);
    }
}

// ==================== 7. KANNADA + ENGLISH TRAVEL ASSISTANT ====================

const chipsEn = [
    { label: "🚨 Emergency 112", query: "What are the emergency highway contacts and police numbers?" },
    { label: "⛽ Fuel Saving", query: "Give me fuel efficiency and mileage saving tips" },
    { label: "🌧️ Monsoon Driving", query: "How to drive safely during heavy monsoon rain and fog?" },
    { label: "⛰️ Ghat Road Rules", query: "What are the essential safety rules for Shiradi and Charmadi ghats?" },
    { label: "🌙 Night Driving", query: "Tips for safe night highway driving and sleep avoidance" },
    { label: "💳 FASTag Rules", query: "What are the toll gate and FASTag wallet rules?" }
];

const chipsKn = [
    { label: "🚨 ತುರ್ತು ಸಂಖ್ಯೆಗಳು 112", query: "ರಾಷ್ಟ್ರೀಯ ತುರ್ತು ಸಹಾಯವಾಣಿ ಮತ್ತು ಹೆದ್ದಾರಿ ಗಸ್ತು ಸಂಖ್ಯೆಗಳು ಯಾವುವು?" },
    { label: "⛽ ಇಂಧನ ಉಳಿತಾಯ", query: "ಹೆಚ್ಚು ಮೈಲೇಜ್ ಪಡೆಯಲು ಮತ್ತು ಇಂಧನ ಉಳಿಸಲು ಸೂತ್ರಗಳನ್ನು ನೀಡಿ" },
    { label: "🌧️ ಮಳೆಗಾಲದ ಚಾಲನೆ", query: "ಮಳೆ ಮತ್ತು ಹಿಮದ ಸಮಯದಲ್ಲಿ ವಾಹನ ಚಾಲನೆ ಮಾಡುವ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು" },
    { label: "⛰️ ಘಾಟ್ ರಸ್ತೆ ನಿಯಮ", query: "ಶಿರಾಡಿ ಘಾಟ್ ಮತ್ತು ಚಾರ್ಮಾಡಿ ಘಾಟ್ ರಸ್ತೆಗಳಲ್ಲಿ ಚಾಲನಾ ನಿಯಮಗಳು" },
    { label: "🌙 ರಾತ್ರಿ ಪ್ರಯಾಣ", query: "ರಾತ್ರಿ ವೇಳೆ ಹೆದ್ದಾರಿಯಲ್ಲಿ ಸುರಕ್ಷಿತವಾಗಿ ಚಾಲನೆ ಮಾಡುವುದು ಹೇಗೆ?" },
    { label: "💳 ಫಾಸ್ಟ್ಯಾಗ್ ನಿಯಮ", query: "ಟೋಲ್ ಗೇಟ್ ಮತ್ತು ಫಾಸ್ಟ್ಯಾಗ್ ನಿಯಮಗಳು" }
];

function setAssistantLang(lang) {
    currentAssistantLang = lang;
    document.getElementById('langEnBtn').classList.toggle('active', lang === 'en');
    document.getElementById('langKnBtn').classList.toggle('active', lang === 'kn');

    const welcome = document.getElementById('assistantWelcome');
    const input = document.getElementById('assistantQueryInput');

    if (lang === 'kn') {
        welcome.innerText = "ನಮಸ್ಕಾರ! ತುರ್ತು ಸಂಪರ್ಕಗಳು (112), ಇಂಧನ ಉಳಿತಾಯ, ಘಾಟ್ ರಸ್ತೆ ಅಥವಾ ಮಳೆಗಾಲದ ಚಾಲನಾ ನಿಯಮಗಳ ಬಗ್ಗೆ ನನ್ನನ್ನು ಕೇಳಿ.";
        input.placeholder = "ಪ್ರಯಾಣ ಸುರಕ್ಷತೆ ಅಥವಾ ಮಾರ್ಗದ ಪ್ರಶ್ನೆ ಕೇಳಿ...";
    } else {
        welcome.innerText = "👋 Hello! Ask me about emergency contacts, fuel saving, Ghat road guidelines, or monsoon highway cautions.";
        input.placeholder = "Type a travel safety or route question...";
    }

    renderAssistantChips();
}

function renderAssistantChips() {
    const container = document.getElementById('assistantChips');
    container.innerHTML = '';
    const chips = (currentAssistantLang === 'kn') ? chipsKn : chipsEn;

    chips.forEach(c => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.innerText = c.label;
        btn.onclick = () => {
            document.getElementById('assistantQueryInput').value = c.query;
            sendAssistantQuery(c.query);
        };
        container.appendChild(btn);
    });
}

async function sendAssistantQuery(explicitQuery) {
    const input = document.getElementById('assistantQueryInput');
    const query = explicitQuery || input.value.trim();
    if (!query) return;

    const chatBox = document.getElementById('assistantChatBox');

    // Add user bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user-bubble';
    userBubble.innerText = query;
    chatBox.appendChild(userBubble);
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    // Fetch bot answer
    try {
        const resp = await fetch('/api/assistant-faq', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, lang: currentAssistantLang })
        });
        const data = await resp.json();

        const botBubble = document.createElement('div');
        botBubble.className = 'chat-bubble bot-bubble';
        botBubble.innerText = data.answer;
        chatBox.appendChild(botBubble);
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (e) {
        console.error('Assistant error:', e);
    }
}
