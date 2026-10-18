
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import sqlite3
import requests
import numpy as np
import pandas as pd
import time
import os

# Initialize the FastAPI application
app = FastAPI()

# Enable CORS to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Replace this with your actual OpenWeather API Key
OPENWEATHER_API_KEY = "17d1849df01bb168a74f963e12235c00"

# Load the ML model
try:
    # Ensure the model file is in the same directory as main.py
    model = joblib.load('arctic_master_final_model_v3.pkl')
    print("Success: 'arctic_master_v3.pkl' loaded successfully.")
except Exception as e:
    model = None
    print("Warning: 'arctic_master_v3.pkl' not found. Predictions will be randomized for testing.")

# Initialize SQLite Database for the Admin Panel
DB_FILE = "database.db"

def init_db():
    # Use check_same_thread=False to avoid issues with FastAPI's async workers
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    # Create the route_logs table to track searches
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS route_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_location TEXT,
            end_location TEXT,
            avg_risk_percentage REAL,
            max_risk_category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Run database initialization on startup
init_db()

# Define the request structure for route analysis
class RouteRequest(BaseModel):
    start_location: str
    end_location: str

# Helper Function 1: Convert location name to coordinates using OpenWeather Geo API
def get_coordinates(location_name: str, api_key: str):
    if not api_key:
        raise ValueError("API Key is missing.")
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name}&limit=1&appid={api_key}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200 and len(resp.json()) > 0:
        data = resp.json()[0]
        return data['lon'], data['lat']
    return None, None

# Helper Function 2: Get driving route using OSRM public API
def get_route(start_coords, end_coords):
    lon1, lat1 = start_coords
    lon2, lat2 = end_coords
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        if 'routes' in data and len(data['routes']) > 0:
            return data['routes'][0]['geometry']['coordinates']
    return None

# Helper Function 3: Fetch robust live weather data with rate-limit protection
def get_live_weather_features(route_coords, api_key):
    # Sample up to 10 points along the route to prevent API rate limiting
    if len(route_coords) > 10:
        indices = np.linspace(0, len(route_coords)-1, 10, dtype=int)
        sampled_coords = [route_coords[i] for i in indices]
    else:
        sampled_coords = route_coords
        
    features_list = []
    
    for lon, lat in sampled_coords:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        try:
            resp = requests.get(url, timeout=10).json()
            
            # Check for valid API response
            if str(resp.get("cod")) == "200":
                main_data = resp.get('main', {})
                wind_data = resp.get('wind', {})
                
                temp = main_data.get('temp', 0)
                wind_kph = wind_data.get('speed', 0) * 3.6
                precip = resp.get('rain', {}).get('1h', 0)
                snow = resp.get('snow', {}).get('1h', 0)
                visibility = resp.get('visibility', 10000)
                pressure = main_data.get('pressure', 1013)
                
                is_freezing = 1 if temp <= 0 else 0
                black_ice = 1 if temp <= 2 and (precip > 0 or snow > 0) else 0
                severe = 1 if wind_kph > 50 or snow > 2 else 0
                
                # Append features required by the ML model
                features_list.append({
                    'temp': temp, 'snowfall': snow, 'precip': precip, 'wind': wind_kph,
                    'Wind_Chill': temp - 2 if wind_kph > 10 else temp,
                    'Is_Freezing': is_freezing, 'Severe_Weather': severe,
                    'Risk_Zone': 2 if severe else (1 if is_freezing else 0),
                    'Zone_Weather_Risk': wind_kph / 10, 'Is_Night': 0, 'Is_RushHour': 0,
                    'Visibility_m': visibility, 'Snow_Depth_m': snow / 10,
                    'Surface_Pressure_hPa': pressure, 'Black_Ice_Risk': black_ice
                })
            
            # Sleep for 0.3 seconds to avoid blocking by OpenWeather free tier
            time.sleep(0.3)
            
        except Exception as e:
            time.sleep(0.3)
            continue
            
    if not features_list:
        return None, None
    return pd.DataFrame(features_list), sampled_coords

# Helper Function 4: Categorize risk based on custom user thresholds
def get_risk_category(percentage):
    if percentage >= 56:
        return "High Risk"
    elif percentage >= 36:
        return "Medium Risk"
    else:
        return "Low Risk"

# API ENDPOINTS

@app.post("/api/analyze")
def analyze_route_endpoint(req: RouteRequest):
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="API Key is missing in backend.")
        
    try:
        # 1. Geocoding
        start_coords = get_coordinates(req.start_location, OPENWEATHER_API_KEY)
        end_coords = get_coordinates(req.end_location, OPENWEATHER_API_KEY)
        
        if not start_coords[0] or not end_coords[0]:
            raise HTTPException(status_code=404, detail="Locations could not be found.")
            
        # 2. Routing
        full_route = get_route(start_coords, end_coords)
        if not full_route:
            raise HTTPException(status_code=404, detail="No driving route found between locations.")
            
        # 3. Weather & Feature Extraction
        features_df, sampled_route = get_live_weather_features(full_route, OPENWEATHER_API_KEY)
        if features_df is None:
            raise HTTPException(status_code=500, detail="Failed to fetch weather data.")
            
        # 4. Model Prediction
        if model is not None:
            # Get probability for class 1 (Risk)
            probs = model.predict_proba(features_df)[:, 1]
        else:
            # Fallback random probabilities if model fails to load
            probs = np.random.uniform(0, 1, len(sampled_route))
            
        # 5. Process Results
        route_points_data = []
        max_risk_pct = 0
        sum_risk_pct = 0
        
        for i in range(len(sampled_route)):
            # Convert probability (0.0 to 1.0) to percentage (0 to 100)
            risk_pct = round(probs[i] * 100, 1)
            sum_risk_pct += risk_pct
            
            if risk_pct > max_risk_pct:
                max_risk_pct = risk_pct
                
            route_points_data.append({
                "lat": sampled_route[i][1],
                "lon": sampled_route[i][0],
                "risk_percentage": risk_pct,
                "risk_category": get_risk_category(risk_pct)
            })
            
        avg_risk_pct = round(sum_risk_pct / len(sampled_route), 1)
        overall_category = get_risk_category(max_risk_pct)
        
        # 6. Save log to SQLite Database for Admin Panel
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO route_logs (start_location, end_location, avg_risk_percentage, max_risk_category)
            VALUES (?, ?, ?, ?)
        ''', (req.start_location, req.end_location, avg_risk_pct, overall_category))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "start_coords": start_coords,
            "end_coords": end_coords,
            "full_route": full_route,
            "analyzed_points": route_points_data,
            "overall_max_risk": max_risk_pct,
            "overall_category": overall_category
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/logs")
def get_admin_logs():
    # Fetch logs from SQLite for the admin dashboard
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM route_logs ORDER BY timestamp DESC LIMIT 50')
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for row in rows:
        logs.append({
            "id": row[0],
            "start": row[1],
            "end": row[2],
            "avg_risk": row[3],
            "category": row[4],
            "time": row[5]
        })
    return {"status": "success", "logs": logs}

# HTML ROUTING (Serving Frontend Files)

@app.get("/")
def serve_main_dashboard():
    # Serves the main user interface
    file_path = os.path.join("frontend", "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "index.html not found. Please create the frontend folder."}

@app.get("/admin-panel")
def serve_hidden_admin_panel():
    # Serves the hidden admin dashboard
    file_path = os.path.join("frontend", "admin.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "admin.html not found."}
