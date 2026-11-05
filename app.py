import math
import os
import random
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import database

app = Flask(__name__)

# Initialize SQLite database on startup
database.init_db()

# Pre-cached popular cities for instantaneous response (especially useful during viva)
PRESET_CITIES = {
    "bengaluru": {"name": "Bengaluru (Bangalore)", "lat": 12.9716, "lon": 77.5946},
    "bangalore": {"name": "Bengaluru (Bangalore)", "lat": 12.9716, "lon": 77.5946},
    "mysuru": {"name": "Mysuru (Mysore)", "lat": 12.2958, "lon": 76.6394},
    "mysore": {"name": "Mysuru (Mysore)", "lat": 12.2958, "lon": 76.6394},
    "mangaluru": {"name": "Mangaluru (Mangalore)", "lat": 12.9141, "lon": 74.8560},
    "mangalore": {"name": "Mangaluru (Mangalore)", "lat": 12.9141, "lon": 74.8560},
    "hubballi": {"name": "Hubballi (Hubli)", "lat": 15.3647, "lon": 75.1240},
    "hubli": {"name": "Hubballi (Hubli)", "lat": 15.3647, "lon": 75.1240},
    "belagavi": {"name": "Belagavi (Belgaum)", "lat": 15.8497, "lon": 74.4977},
    "belgaum": {"name": "Belagavi (Belgaum)", "lat": 15.8497, "lon": 74.4977},
    "shivamogga": {"name": "Shivamogga (Shimoga)", "lat": 13.9299, "lon": 75.5681},
    "shimoga": {"name": "Shivamogga (Shimoga)", "lat": 13.9299, "lon": 75.5681},
    "udupi": {"name": "Udupi", "lat": 13.3409, "lon": 74.7421},
    "hassan": {"name": "Hassan", "lat": 13.0033, "lon": 76.1004},
    "davanagere": {"name": "Davanagere", "lat": 14.4644, "lon": 75.9218},
    "ballari": {"name": "Ballari (Bellary)", "lat": 15.1394, "lon": 76.9214},
    "tumakuru": {"name": "Tumakuru (Tumkur)", "lat": 13.3392, "lon": 77.1017},
    "goa": {"name": "Panaji (Goa)", "lat": 15.4909, "lon": 73.8278},
    "hyderabad": {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    "chennai": {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    "mumbai": {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    "pune": {"name": "Pune", "lat": 18.5204, "lon": 73.8567},
    "delhi": {"name": "New Delhi", "lat": 28.6139, "lon": 77.2090}
}

EMISSION_FACTORS = {
    "petrol_car": 0.170,  # kg CO2 per km
    "diesel_car": 0.165,
    "ev": 0.052,
    "bike": 0.075,
    "suv": 0.220
}

# Weather code descriptions from WMO Open-Meteo
WMO_CODES = {
    0: ("Clear sky", "Sunny and dry conditions. Excellent visibility."),
    1: ("Mainly clear", "Mild sunlight, good driving conditions."),
    2: ("Partly cloudy", "Comfortable temperature with periodic shadows."),
    3: ("Overcast", "Gray skies, watch for subtle light changes."),
    45: ("Foggy", "Reduced visibility. Keep fog lamps ON and drive at safe distance."),
    48: ("Depositing rime fog", "Severe fog warning! Reduce speed drastically."),
    51: ("Light drizzle", "Slightly wet roads, brake early."),
    61: ("Slight rain", "Slippery asphalt alert. Maintain 3-second gap."),
    63: ("Moderate rain", "Active windshield wipers needed. Watch hydroplaning."),
    65: ("Heavy rain", "Hazardous wet conditions! Avoid overtaking on single-lane roads."),
    71: ("Slight snow", "Cold pavement, reduced traction."),
    80: ("Rain showers", "Intermittent heavy bursts possible."),
    95: ("Thunderstorm", "High risk! Avoid parking under trees or power lines.")
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_fallback_polyline(lat1, lon1, lat2, lon2, curve_direction=1):
    """Generates realistic intermediate coordinates between two points."""
    points = []
    steps = 15
    mid_lat = (lat1 + lat2) / 2.0
    mid_lon = (lon1 + lon2) / 2.0
    # Add offset perpendicular to route to simulate an alternative highway curve
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    offset = 0.08 * curve_direction
    
    for i in range(steps + 1):
        t = i / float(steps)
        # Quadratic bezier curve
        curved_t = 4 * t * (1 - t) # peaks at t=0.5
        p_lat = (1 - t) * lat1 + t * lat2 + curved_t * (-dlon * offset)
        p_lon = (1 - t) * lon1 + t * lon2 + curved_t * (dlat * offset)
        points.append([round(p_lat, 5), round(p_lon, 5)])
    return points

def fetch_osrm_routes(start_coords, dest_coords):
    """Fetches real driving routes from OSRM or synthesizes fallbacks."""
    lat1, lon1 = start_coords
    lat2, lon2 = dest_coords
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson&alternatives=true"
    
    routes_data = []
    try:
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                for idx, r in enumerate(data["routes"]):
                    dist_km = round(r["distance"] / 1000.0, 1)
                    dur_min = round(r["duration"] / 60.0, 1)
                    # Coordinates in GeoJSON are [lon, lat], Leaflet expects [lat, lon]
                    leaflet_coords = [[pt[1], pt[0]] for pt in r["geometry"]["coordinates"]]
                    routes_data.append({
                        "id": f"route_{idx+1}",
                        "name": f"Route {chr(65+idx)}" + (" (Expressway / NH)" if idx == 0 else " (State Highway Alternate)"),
                        "distance_km": dist_km,
                        "duration_min": dur_min,
                        "duration_text": f"{int(dur_min // 60)}h {int(dur_min % 60)}m" if dur_min >= 60 else f"{int(dur_min)} mins",
                        "coordinates": leaflet_coords,
                        "source": "OSRM Live Routing Engine"
                    })
    except Exception as e:
        print(f"OSRM request fallback triggered: {e}")
        
    # If OSRM failed or returned only 1 route, build robust realistic alternative routes
    if not routes_data:
        direct_dist = haversine_distance(lat1, lon1, lat2, lon2)
        road_dist_1 = round(direct_dist * 1.22, 1)
        dur_1 = round((road_dist_1 / 65.0) * 60, 1) # ~65 km/h avg
        
        routes_data.append({
            "id": "route_1",
            "name": "Route A (NH 4-Lane Mainline)",
            "distance_km": road_dist_1,
            "duration_min": dur_1,
            "duration_text": f"{int(dur_1 // 60)}h {int(dur_1 % 60)}m" if dur_1 >= 60 else f"{int(dur_1)} mins",
            "coordinates": generate_fallback_polyline(lat1, lon1, lat2, lon2, 0.4),
            "source": "Smart Route Synthetic Simulator"
        })

    # Always ensure we provide a viable Route B alternative for comparison
    if len(routes_data) == 1:
        base = routes_data[0]
        alt_dist = round(base["distance_km"] * 1.12, 1)
        alt_dur = round(base["duration_min"] * 1.18, 1)
        routes_data.append({
            "id": "route_2",
            "name": "Route B (Scenic Bypass / Alternate)",
            "distance_km": alt_dist,
            "duration_min": alt_dur,
            "duration_text": f"{int(alt_dur // 60)}h {int(alt_dur % 60)}m" if alt_dur >= 60 else f"{int(alt_dur)} mins",
            "coordinates": generate_fallback_polyline(lat1, lon1, lat2, lon2, -0.6),
            "source": "Smart Route Alternative Engine"
        })

    return routes_data

def get_live_weather(lat, lon):
    """Fetches live meteorological data from Open-Meteo."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            cw = resp.json().get("current_weather", {})
            temp = cw.get("temperature", 28.0)
            wcode = cw.get("weathercode", 0)
            wind = cw.get("windspeed", 10.0)
            condition, advice = WMO_CODES.get(wcode, ("Clear conditions", "Normal safe driving rules apply."))
            return {
                "temperature": f"{temp}°C",
                "wind": f"{wind} km/h",
                "condition": condition,
                "driving_advice": advice,
                "code": wcode,
                "is_live": True
            }
    except Exception as e:
        print(f"Weather API fallback: {e}")
        
    return {
        "temperature": "27.5°C",
        "wind": "12 km/h",
        "condition": "Partly Cloudy",
        "driving_advice": "Dry tarmac and good ambient light. Standard speed limits recommended.",
        "code": 2,
        "is_live": False
    }

def calculate_road_risk_score(distance_km, weather_code, active_alerts_count, personality):
    """
    Computes an intelligent 0-100 road risk score based on:
    - Distance fatigue
    - Weather hazard severity
    - Matching active road alerts
    - Travel style
    """
    score = 15 # baseline road risk
    
    # Distance fatigue impact
    if distance_km > 300:
        score += 25
    elif distance_km > 150:
        score += 15
    elif distance_km > 75:
        score += 8

    # Weather impact
    if weather_code in [65, 80, 95]: # Heavy rain or thunderstorm
        score += 35
    elif weather_code in [45, 48]: # Fog
        score += 30
    elif weather_code in [61, 63, 51]: # Light/Mod rain
        score += 18

    # Alerts factor
    score += min(active_alerts_count * 8, 24)

    # Personality adjustment
    if personality == "safe":
        score = max(5, score - 15)
    elif personality == "fastest":
        score = min(98, score + 6)
    elif personality == "night":
        score = min(95, score + 12)

    score = min(max(score, 8), 96)
    
    if score < 35:
        level = "Low Risk"
        badge = "badge-success"
        color = "#10b981"
        desc = "Optimal highway condition with negligible hazards."
    elif score < 65:
        level = "Moderate Risk"
        badge = "badge-warning"
        color = "#f59e0b"
        desc = "Moderate caution advised due to distance or intermediate road conditions."
    else:
        level = "High Caution"
        badge = "badge-danger"
        color = "#ef4444"
        desc = "High caution! Adverse weather, long hours, or reported hazards detected."

    return {
        "score": score,
        "level": level,
        "badge_class": badge,
        "color": color,
        "summary": desc
    }

# ==================== WEB ROUTES ====================

@app.route('/')
def home():
    alerts = database.get_alerts()
    favourites = database.get_favourites()
    history = database.get_search_history(10)
    checkins = database.get_safety_checkins()
    return render_template('index.html', 
                           alerts=alerts, 
                           favourites=favourites, 
                           history=history, 
                           checkins=checkins)

# Geocode API endpoint
@app.route('/api/geocode', methods=['GET'])
def geocode():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({"error": "Empty search query"}), 400

    # 1. First check local presets
    for key, city in PRESET_CITIES.items():
        if key in query or query in key:
            return jsonify({
                "found": True,
                "display_name": city["name"],
                "lat": city["lat"],
                "lon": city["lon"]
            })

    # 2. Try Nominatim API
    try:
        headers = {'User-Agent': 'SmartRouteAI-FinalYearBCAMiniProject/1.0'}
        url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={query}"
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return jsonify({
                    "found": True,
                    "display_name": data[0]["display_name"],
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"])
                })
    except Exception as e:
        print(f"Geocode lookup exception: {e}")

    # Fallback default: Bengaluru center
    return jsonify({
        "found": False,
        "message": f"Place '{query}' not found online, defaulting to Bengaluru",
        "display_name": f"{query.title()} (Estimated Karnataka Coordinates)",
        "lat": 12.9716,
        "lon": 77.5946
    })

# Route Calculation & Comparison API
@app.route('/api/route', methods=['POST'])
def calculate_route():
    data = request.get_json() or {}
    start_place = data.get('start_place', 'Bengaluru')
    dest_place = data.get('dest_place', 'Mysuru')
    start_lat = float(data.get('start_lat', 12.9716))
    start_lon = float(data.get('start_lon', 77.5946))
    dest_lat = float(data.get('dest_lat', 12.2958))
    dest_lon = float(data.get('dest_lon', 76.6394))
    
    personality = data.get('personality', 'fastest').lower()
    mileage = float(data.get('mileage', 15.0))
    fuel_price = float(data.get('fuel_price', 102.5))
    passengers = max(1, int(data.get('passengers', 1)))
    vehicle_type = data.get('vehicle_type', 'petrol_car')

    # 1. Fetch routes
    routes = fetch_osrm_routes([start_lat, start_lon], [dest_lat, dest_lon])
    
    # 2. Fetch destination weather
    weather = get_live_weather(dest_lat, dest_lon)
    
    # 3. Fetch alerts
    all_alerts = database.get_alerts()
    matched_alerts = [a for a in all_alerts if a['severity'] in ['High', 'Medium']][:3]

    # 4. Enhance each route with Cost, Carbon, and Personality scoring
    emission_factor = EMISSION_FACTORS.get(vehicle_type, 0.170)
    
    for r in routes:
        dist = r["distance_km"]
        liters_needed = round(dist / mileage, 2)
        total_fuel_cost = round(liters_needed * fuel_price, 2)
        cost_per_passenger = round(total_fuel_cost / passengers, 2)
        
        # Carbon emissions
        total_co2_kg = round(dist * emission_factor, 2)
        co2_per_passenger = round(total_co2_kg / passengers, 2)
        
        # Risk score
        risk = calculate_road_risk_score(dist, weather["code"], len(matched_alerts), personality)
        
        r["fuel"] = {
            "liters": liters_needed,
            "total_cost": total_fuel_cost,
            "cost_per_person": cost_per_passenger,
            "currency": "₹"
        }
        r["carbon"] = {
            "total_co2_kg": total_co2_kg,
            "co2_per_person": co2_per_passenger,
            "vehicle_type": vehicle_type
        }
        r["risk"] = risk

    # 5. Determine recommended route based on chosen personality
    # Personalities: fastest, budget, eco, safe, scenic, night
    if personality == "fastest":
        recommended_route = min(routes, key=lambda x: x["duration_min"])
        rec_reason = "⚡ Fastest Route: Minimizes your in-transit travel time on prime expressways."
    elif personality == "budget":
        recommended_route = min(routes, key=lambda x: x["fuel"]["total_cost"])
        rec_reason = "💰 Budget Friendly: Shortest total distance translates directly to lowest fuel expenditure."
    elif personality == "eco":
        recommended_route = min(routes, key=lambda x: x["carbon"]["total_co2_kg"])
        rec_reason = "🌿 Eco-Friendly: Generates minimum CO2 emissions, preserving air quality."
    elif personality == "safe":
        recommended_route = min(routes, key=lambda x: x["risk"]["score"])
        rec_reason = "🛡️ Safest Route: Lowest road risk composite rating and avoids congested bottleneck sectors."
    elif personality == "night":
        # Prefers primary highway with best road markers
        recommended_route = routes[0]
        rec_reason = "🌙 Night Owl Choice: Direct major corridor with 24/7 rest stops and highway lighting."
    else: # scenic
        recommended_route = routes[-1] if len(routes) > 1 else routes[0]
        rec_reason = "🌅 Scenic Explorer: Pleasant detour along verdant terrain and cultural landmarks."

    # Mark recommended flag
    for r in routes:
        r["is_recommended"] = (r["id"] == recommended_route["id"])

    # 6. Record to SQLite Search History
    primary_route = routes[0]
    database.add_search_history(
        start_place=start_place,
        destination=dest_place,
        distance_km=primary_route["distance_km"],
        duration_min=primary_route["duration_min"],
        personality=personality,
        risk_score=primary_route["risk"]["score"],
        fuel_cost=primary_route["fuel"]["total_cost"]
    )

    return jsonify({
        "success": True,
        "start": {"name": start_place, "lat": start_lat, "lon": start_lon},
        "destination": {"name": dest_place, "lat": dest_lat, "lon": dest_lon},
        "personality": personality,
        "recommendation_reason": rec_reason,
        "routes": routes,
        "weather": weather,
        "alerts": matched_alerts
    })

# Favourites endpoints
@app.route('/api/favourites', methods=['GET', 'POST'])
def handle_favourites():
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', 'My Saved Journey')
        start = data.get('start_place', '')
        dest = data.get('destination', '')
        notes = data.get('notes', '')
        fav_id = database.add_favourite(name, start, dest, notes)
        return jsonify({"success": True, "id": fav_id, "message": "Saved to favourites!"})
    else:
        favs = database.get_favourites()
        return jsonify({"favourites": favs})

@app.route('/api/favourites/<int:fav_id>', methods=['DELETE'])
def remove_favourite(fav_id):
    database.delete_favourite(fav_id)
    return jsonify({"success": True, "message": "Favourite removed"})

# History endpoints
@app.route('/api/history', methods=['GET', 'DELETE'])
def handle_history():
    if request.method == 'DELETE':
        database.clear_search_history()
        return jsonify({"success": True, "message": "Search history cleared"})
    else:
        history = database.get_search_history(30)
        return jsonify({"history": history})

# Safety Check-In endpoints
@app.route('/api/safety-checkin', methods=['POST'])
def add_safety_checkin():
    data = request.get_json() or {}
    traveler = data.get('traveler_name', 'Student Traveler')
    contact = data.get('emergency_contact', 'Parent/Guardian')
    phone = data.get('contact_phone', '9876543210')
    destination = data.get('destination', 'College Campus')
    expected_arrival = data.get('expected_arrival', '')

    checkin_id = database.add_safety_checkin(traveler, contact, phone, destination, expected_arrival)
    return jsonify({"success": True, "id": checkin_id, "message": "Safety check-in registered successfully!"})

@app.route('/api/safety-checkins', methods=['GET'])
def get_safety_checkins():
    checkins = database.get_safety_checkins()
    now = datetime.now()
    
    # Evaluate overdue status dynamically
    for c in checkins:
        try:
            exp_time = datetime.fromisoformat(c['expected_arrival'])
            c['is_overdue'] = (now > exp_time and c['status'] == 'ACTIVE')
        except Exception:
            c['is_overdue'] = False
            
    return jsonify({"checkins": checkins})

@app.route('/api/safety-checkin/<int:checkin_id>/status', methods=['POST'])
def update_checkin_status(checkin_id):
    data = request.get_json() or {}
    new_status = data.get('status', 'ARRIVED_SAFE')
    database.update_safety_checkin_status(checkin_id, new_status)
    return jsonify({"success": True, "message": f"Status updated to {new_status}"})

# Kannada + English Assistant endpoint
@app.route('/api/assistant-faq', methods=['POST'])
def assistant_faq():
    data = request.get_json() or {}
    query = data.get('query', '').lower().strip()
    lang = data.get('lang', 'en')

    # Knowledge base in English and Kannada
    qa_pairs = [
        {
            "keys": ["emergency", "police", "help", "ambulance", "ತುರ್ತು", "ಪೊಲೀಸ್", "ಆಂಬ್ಯುಲೆನ್ಸ್"],
            "en": "🚨 National Emergency Number: 112. Karnataka Highway Patrol: 9480801000. Ambulance: 108. All toll expressways have dedicated SOS call boxes every 2 kilometers.",
            "kn": "🚨 ರಾಷ್ಟ್ರೀಯ ತುರ್ತು ಸಹಾಯವಾಣಿ ಸಂಖ್ಯೆ: 112. ಕರ್ನಾಟಕ ಹೆದ್ದಾರಿ ಗಸ್ತು: 9480801000. ಆಂಬ್ಯುಲೆನ್ಸ್: 108. ಪ್ರತಿ ಎಕ್ಸ್‌ಪ್ರೆಸ್‌ವೇಯಲ್ಲೂ 2 ಕಿಮೀಗೊಮ್ಮೆ ತುರ್ತು SOS ಕರೆ ಪೆಟ್ಟಿಗೆಗಳಿವೆ."
        },
        {
            "keys": ["fuel", "mileage", "save", "ಇಂಧನ", "ಮೈಲೇಜ್", "ಪೆಟ್ರೋಲ್"],
            "en": "⛽ Fuel Efficiency Tips: Maintain steady cruising speed between 65-80 km/h in top gear. Ensure correct tire pressure (+2 PSI for loaded cars). Avoid aggressive throttle bursts.",
            "kn": "⛽ ಇಂಧನ ಉಳಿಸುವ ಸೂತ್ರಗಳು: ಗಂಟೆಗೆ 65-80 ಕಿಮೀ ಸ್ಥಿರ ವೇಗದಲ್ಲಿ ವಾಹನ ಚಾಲನೆ ಮಾಡಿ. ಟೈರ್ ಪ್ರೆಶರ್ ಸರಿಯಾಗಿಡಿ. ಅನಗತ್ಯವಾಗಿ ವೇಗವರ್ಧಕ (ಆಕ್ಸಿಲರೇಟರ್) ಬಳಸಬೇಡಿ."
        },
        {
            "keys": ["rain", "monsoon", "fog", "weather", "ಮಳೆ", "ಮಳೆಗಾಲ", "ಹಿಮ", "ಹವಾಮಾನ"],
            "en": "🌧️ Weather Cautions: During rain, asphalt friction drops by 40%. Double your following distance to 6 seconds. Turn on low-beam headlights and defoggers.",
            "kn": "🌧️ ಮಳೆಗಾಲದ ಮುನ್ನೆಚ್ಚರಿಕೆ: ಮಳೆ ಬಂದಾಗ ಬ್ರೇಕ್ ದೂರ 40% ಹೆಚ್ಚಾಗುತ್ತದೆ. ಮುಂಭಾಗದ ವಾಹನದಿಂದ 6 ಸೆಕೆಂಡ್ ಅಂತರ ಕಾಯ್ದುಕೊಳ್ಳಿ. ಲೋ-ಬೀಮ್ ಹೆಡ್‌ಲೈಟ್ ಮತ್ತು ಡಿಫಾಗರ್ ಆನ್ ಮಾಡಿ."
        },
        {
            "keys": ["night", "dark", "sleep", "ರಾತ್ರಿ", "ಕತ್ತಲು", "ನಿದ್ರೆ"],
            "en": "🌙 Night Driving Tips: Use high beams only on divided empty corridors; dip lights when oncoming vehicles approach. Take a mandatory 15-minute break every 2 hours.",
            "kn": "🌙 ರಾತ್ರಿ ಚಾಲನೆ ಮಾರ್ಗದರ್ಶನ: ಎದುರಿನಿಂದ ವಾಹನ ಬಂದಾಗ ಡಿಪ್ಪರ್ ಬಳಸಿ. ನಿದ್ರೆ ಬರದಂತೆ ಪ್ರತಿ 2 ಗಂಟೆಗೊಮ್ಮೆ ಟೀ ಅಥವಾ ವಿಶ್ರಾಂತಿ ವಿರಾಮ ತೆಗೆದುಕೊಳ್ಳಿ."
        },
        {
            "keys": ["ghat", "shiradi", "charmadi", "hills", "ಘಾಟ್", "ಶಿರಾಡಿ", "ಚಾರ್ಮಾಡಿ"],
            "en": "⛰️ Ghat Road Rules: Uphill vehicles always have right-of-way! Never overtake on blind hairpin bends. Downshift to 2nd/3rd gear to utilize engine braking.",
            "kn": "⛰️ ಘಾಟ್ ರಸ್ತೆ ನಿಯಮ: ಮೇಲ್ಮುಖವಾಗಿ ಚಲಿಸುವ ವಾಹನಗಳಿಗೆ ಮೊದಲ ಆದ್ಯತೆ ನೀಡಿ. ಹೇರ್‌ಪಿನ್ ತಿರುವುಗಳಲ್ಲಿ ಎಂದಿಗೂ ಓವರ್‌ಟೇಕ್ ಮಾಡಬೇಡಿ. ಇಂಜಿನ್ ಬ್ರೇಕ್ ಬಳಸಲು ಕಡಿಮೆ ಗೇರ್ ಬಳಸಿ."
        },
        {
            "keys": ["fastag", "toll", "ಟೋಲ್", "ಫಾಸ್ಟ್ಯಾಗ್"],
            "en": "💳 FASTag & Toll Tips: Keep minimum ₹200 balance on your FASTag wallet. Non-FASTag lanes or deficient balance invites double standard toll penalty.",
            "kn": "💳 ಫಾಸ್ಟ್ಯಾಗ್ ಮಾಹಿತಿ: ನಿಮ್ಮ ಫಾಸ್ಟ್ಯಾಗ್ ವ್ಯಾಲೆಟ್‌ನಲ್ಲಿ ಕನಿಷ್ಠ ₹200 ಬ್ಯಾಲೆನ್ಸ್ ಇರಲಿ. ಫಾಸ್ಟ್ಯಾಗ್ ಇಲ್ಲದಿದ್ದರೆ ದ್ವಿಗುಣ ದಂಡ ಶುಲ್ಕ ವಿಧಿಸಲಾಗುತ್ತದೆ."
        },
        {
            "keys": ["carbon", "eco", "green", "ಹಸಿರು", "ಕಾರ್ಬನ್"],
            "en": "🌱 Carbon Footprint: Carpooling with 3 colleagues reduces your individual journey carbon emissions by up to 75%! EVs cut operational carbon by over 60%.",
            "kn": "🌱 ಕಾರ್ಬನ್ ಹೆಜ್ಜೆಗುರುತು: ಮೂವರು ಜೊತೆಯಾಗಿ ಕಾರ್‌ಪೂಲಿಂಗ್ ಮಾಡಿದರೆ ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಇಂಗಾಲದ ಹೊರಸೂಸುವಿಕೆ 75% ವರೆಗೆ ಕಡಿಮೆಯಾಗುತ್ತದೆ!"
        }
    ]

    for pair in qa_pairs:
        for k in pair["keys"]:
            if k in query:
                response_text = pair["kn"] if lang == "kn" else pair["en"]
                return jsonify({
                    "matched": True,
                    "answer": response_text,
                    "lang": lang
                })

    # Default response if no keyword matched
    if lang == "kn":
        default_ans = "ನಮಸ್ಕಾರ! ನೀವು ತುರ್ತು ಸಂಖ್ಯೆಗಳು (112), ಇಂಧನ ಉಳಿತಾಯ, ರಾತ್ರಿ ಚಾಲನೆ, ಘಾಟ್ ರಸ್ತೆ ನಿಯಮಗಳು ಅಥವಾ ಮಳೆಗಾಲದ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ ಕೇಳಬಹುದು."
    else:
        default_ans = "Hello! I am your Smart Route AI Travel Assistant. You can ask me about Emergency helplines (112), fuel efficiency tips, night driving, ghat safety, or monsoon precautions."

    return jsonify({
        "matched": False,
        "answer": default_ans,
        "lang": lang
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SMART ROUTE AI - Final Year BCA Mini Project")
    print("📍 Local Web Server running at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
