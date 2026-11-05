# Smart Route AI - Multimodal Journey Planning & Road Safety Assistant
**Final Year BCA Mini Project**

---

## 📌 1. Project Abstract
**Smart Route AI** is an intelligent multimodal travel planning and road safety web platform developed as a Final Year BCA mini-project. The application compares alternative driving routes in real-time, estimates vehicle fuel costs and passenger splits, calculates carbon footprint emissions ($kg\ CO_2$), forecasts weather conditions at destinations, computes a Smart Road Risk score, tracks journey safety check-ins with overdue alerts, and offers a bilingual travel assistant in both **Kannada** (ಕನ್ನಡ) and **English**.

The project uses Python (Flask), SQLite for persistent storage, Leaflet.js with OpenStreetMap for client-side spatial mapping, and Open-Meteo meteorological endpoints.

---

## 🎯 2. Core Modules & Point-to-Point Structure

### Module 1: Smart Route Comparison & Interactive Mapping
- **OpenStreetMap & Leaflet.js Integration**: Real-time rendering of driving routes using polyline GeoJSON layers.
- **Alternative Route Analysis**: Generates Primary (Expressway/NH) and Secondary (State Highway/Scenic Bypass) corridors.
- **Metrics Displayed**: Real road distance in kilometers, estimated duration in hours and minutes.
- **Map Controls**: Fit to bounds, satellite imagery toggle, custom coordinate geocoding.

### Module 2: AI Travel Cost & Passenger Split Calculator
- **Fuel Consumption Formula**:
  $$\text{Liters Needed} = \frac{\text{Distance (km)}}{\text{Vehicle Mileage (km/L)}}$$
- **Total Expenditure**:
  $$\text{Total Fuel Cost} = \text{Liters Needed} \times \text{Fuel Rate (₹/L)}$$
- **Passenger Cost Split**:
  $$\text{Cost Per Passenger} = \frac{\text{Total Fuel Cost}}{\text{Number of Passengers}}$$
- **Vehicle Profiles**: Petrol Car, Diesel Car, EV (km/kWh), Two-Wheeler / Bike, and SUV.

### Module 3: Carbon Footprint Calculator ($CO_2$)
- Computes vehicle operational greenhouse emissions based on standard emission factors:
  - Petrol Car: $0.170\ kg\ CO_2 / km$
  - Diesel Car: $0.165\ kg\ CO_2 / km$
  - Two-Wheeler: $0.075\ kg\ CO_2 / km$
  - Electric Vehicle: $0.052\ kg\ CO_2 / km$
  - SUV: $0.220\ kg\ CO_2 / km$
- Calculates individual passenger footprint to encourage carpooling.

### Module 4: Six Route Personalities / Profiles
1. **⚡ Fastest Route**: Selects corridor with minimum transit time.
2. **💰 Budget-Friendly**: Optimizes for lowest fuel consumption.
3. **🌿 Eco-Friendly**: Minimizes carbon footprint ($CO_2$).
4. **🛡️ Safest Corridor**: Recommends route with lowest composite risk score.
5. **🌅 Scenic Detour**: Paces route for pleasant detours and landmarks.
6. **🌙 Night Owl**: Prefers illuminated National Highway corridors with 24/7 emergency amenities.

### Module 5: Weather-Aware Route Assistant
- Real-time destination meteorological retrieval via Open-Meteo.
- Ambient temperature (°C), wind velocity (km/h), and WMO weather codes (Rain, Fog, Thunderstorm, Sunny).
- Weather-specific driving advice (e.g., maintaining 6-second stopping distance on wet asphalt).

### Module 6: Smart Road Risk Score (0 - 100)
- Weighted algorithmic risk model combining:
  - **Distance Fatigue Factor**: Higher risk penalties for trips $> 150\ km$ and $> 300\ km$.
  - **Weather Factor**: Heavy rain, thunderstorms, and fog add severity points.
  - **Active Hazards**: Highway construction, lane narrowing, or bad terrain.
  - **Route Personality**: Safe mode applies defensive routing discounts.
- Categorized as **Low Risk (Green)**, **Moderate Risk (Amber)**, or **High Caution (Red)**.

### Module 7: Route Alerts and Travel Tips
- Road closures, flyover maintenance, and weather advisories.
- Clearly tagged as **✅ Verified Highway Alert** or **🧪 Sample Demonstration** to maintain academic transparency during viva examinations.

### Module 8: Journey Safety Check-In (Overdue Alarm)
- Allows solo travelers to log their destination, emergency contact, phone number, and expected arrival time.
- Persistent in SQLite database.
- Active client-side countdown timer `[HH:MM:SS]`.
- If the current system time exceeds the scheduled arrival time without the user clicking **"Mark as Arrived Safe"**, the card pulses red with an overdue emergency notice.

### Module 9: Kannada + English Bilingual Travel Assistant
- Built-in FAQ assistant with instant language toggle (`English` / `ಕನ್ನಡ`).
- Covers Emergency Helplines (112, 108, Highway Patrol), Fuel Efficiency, Ghat Road Rules (Shiradi/Charmadi), Monsoon Driving, and FASTag regulations.

### Module 10: Favourite Places & SQLite Search History
- **Favourites**: Save frequently planned trips in SQLite and browser cache for 1-click execution.
- **Search History**: Records past queries (start, destination, distance, cost, risk, timestamp) in SQLite (`routes.db`) with clear and re-run options.

---

## 🏗️ 3. System Architecture

```mermaid
flowchart TD
    User([User / Web Browser]) -->|HTTP / JSON| FlaskServer[Flask Application Server (app.py)]
    
    subgraph Backend_Processing
        FlaskServer --> GeocodeEngine[Geocoding Engine (Presets & Nominatim)]
        FlaskServer --> RoutingEngine[Routing Engine (OSRM & Fallback Polyline)]
        FlaskServer --> WeatherAPI[Weather Engine (Open-Meteo API)]
        FlaskServer --> RiskEngine[Smart Road Risk Algorithm]
        FlaskServer --> CostEngine[Cost & Carbon Calculator]
        FlaskServer --> FAQEngine[Bilingual Kannada/English FAQ]
    end
    
    subgraph Database_Layer
        FlaskServer <--> SQLite[(SQLite Database: routes.db)]
        SQLite --> T1[search_history]
        SQLite --> T2[favourite_places]
        SQLite --> T3[safety_checkins]
        SQLite --> T4[road_alerts]
    end

    subgraph Client_Frontend
        FlaskServer -->|HTML, CSS, JS| UI[Modern Responsive Dashboard]
        UI --> LeafletMap[Leaflet.js + OpenStreetMap Polylines]
        UI --> OverdueAlarm[Live Safety Countdown Timer]
        UI --> AssistantChat[Bilingual Chat Assistant]
    end
```

---

## 🗄️ 4. SQLite Database Schema

| Table Name | Primary Columns | Description |
| :--- | :--- | :--- |
| `search_history` | `id, start_place, destination, distance_km, duration_min, selected_personality, risk_score, fuel_cost, created_at` | Logs every route calculation. |
| `favourite_places` | `id, name, start_place, destination, notes, created_at` | Saves pinned routes for quick lookup. |
| `safety_checkins` | `id, traveler_name, emergency_contact, contact_phone, destination, expected_arrival, status, created_at` | Tracks traveler arrival schedule and overdue alerts. |
| `road_alerts` | `id, route_zone, title, description, severity, alert_type, is_verified, created_at` | Highway hazard bulletins and demo feeds. |

---

## 🚀 5. How to Run on Your Laptop Right Now (Step-by-Step)

### Prerequisites:
- Python 3.8 or above installed on your Windows machine.

### Method A: One-Click Execution (Recommended)
1. Open the project folder: `c:\Users\hamsa\Desktop\project`.
2. Double-click the file named **`run.bat`**.
3. It will automatically check Python, install required packages (`Flask`, `requests`), open your web browser to `http://127.0.0.1:5000`, and start the server!

### Method B: Terminal / Command Prompt Execution
1. Open **Command Prompt** (`cmd`) or **PowerShell**.
2. Navigate to the project directory:
   ```powershell
   cd c:\Users\hamsa\Desktop\project
   ```
3. Install required libraries:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Start the Flask application:
   ```powershell
   python app.py
   ```
5. Open your browser and visit:
   ```
   http://127.0.0.1:5000
   ```

---

## 🎓 6. Viva Voce Questions & Answers (For BCA Project Viva)

**Q1: Why did you choose SQLite instead of MySQL or MongoDB for this mini project?**  
*Answer:* SQLite is serverless, zero-configuration, and self-contained within a single file (`routes.db`). It fulfills all ACID properties, integrates natively into Python without installing external database servers, and runs reliably on any testing laptop.

**Q2: How does the Smart Road Risk score calculate risk?**  
*Answer:* It uses a weighted multi-factor heuristic:
1. Base score of 15.
2. Distance penalty (+8 for $>75\ km$, +15 for $>150\ km$, +25 for $>300\ km$).
3. Adverse weather penalty (+18 for rain, +30 for fog, +35 for thunderstorms).
4. Road alert penalty (+8 points per reported hazard).
5. Personality tuning (-15 points discount for defensive "Safest" mode).

**Q3: How are the maps rendered without paid Google Maps API keys?**  
*Answer:* We utilize Leaflet.js paired with OpenStreetMap raster tiles and OSRM (Open Source Routing Machine). This provides an open-source, zero-cost mapping and routing solution with built-in mathematical curve fallbacks.

**Q4: How does the Safety Check-in Overdue alarm work?**  
*Answer:* When a traveler submits an expected arrival ISO timestamp, the server stores it in SQLite. A high-resolution JavaScript `setInterval` loop compares `new Date()` against the target timestamp every second. If the target time passes without being marked safe, the UI activates an animated emergency warning.
