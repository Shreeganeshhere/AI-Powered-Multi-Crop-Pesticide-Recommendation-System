# main.py

import uvicorn
import requests
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from backend.model_utils import (
    load_all_models_and_classes, 
    predict_disease, 
    MODEL_IMG_SIZES 
)

# --- 2. Initialize App and Load Models/Classes (No Change) ---
app = FastAPI(title="AI Powered Pesticide Recommendation System for Tomato, Capsicum, and Brinjal")
MODELS, CLASS_MAPPINGS = load_all_models_and_classes()
# ... (rest of the startup code) ...if not MODELS or not CLASS_MAPPINGS:
#print("FATAL ERROR: Models or class mappings could not be loaded. Shutting down.")
    # In a real app, you might want to exit
    # exit()

# --- 3. API Key and Helper Functions (No Change) ---
OPENWEATHER_API_KEY = "347e7f996d0bf8ce6b23a60d5d6a076b"

def fetch_weather_data(lat, lon, api_key):
    """
    Calls OpenWeatherMap API to get current weather.
    """
    api_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"  # Gets temperature in Celsius
    }
    try:
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()  # Raises an error for bad responses
        data = response.json()
        
        # Extract only the data we need
        return {
            "temp": data.get('main', {}).get('temp'),
            "humidity": data.get('main', {}).get('humidity'),
            "wind_speed": data.get('wind', {}).get('speed'),  # meter/sec
            "description": data.get('weather', [{}])[0].get('description', 'N/A')
        }
    except requests.exceptions.RequestException as e:
        print(f"Weather API Error: {e}")
        # Return sensible defaults if API fails
        return {
            "temp": None, "humidity": None, "wind_speed": None, "description": "Weather data unavailable"
        }
def get_mock_recommendation(disease_name, severity, weather_data, land_size, land_unit):
    
    # --- Pesticide Logic (Hardcoded) ---
    pesticide = "Emamectin benzoate"
    if "Healthy" in disease_name:
        pesticide = "None"
    if "Early Blight" in disease_name:
        pesticide = "Azoxystrobin"
    elif "Bacterial Spot" in disease_name:
        pesticide = "Copper Oxychloride"
    elif "Leaf Hoppers" in disease_name:
        pesticide = "Imidacloprid"
    elif "Mosaic Virus" in disease_name:
        pesticide = "Chlorantraniliprole"

    # --- Dosage Logic (Calculated) ---
    if land_unit == "sqm":
        land_in_acres = land_size * 0.000247105
    else:
        land_in_acres = land_size
    
    base_dosage_per_acre = 150  # Mock value: 150 ml per acre
    total_dosage = base_dosage_per_acre * land_in_acres
    dosage_text = f"{total_dosage:.1f} ml for your {land_size} {land_unit} plot"

    # --- Weather Advice Logic (Real) ---
    app_advice = "Apply in early morning."
    temp = weather_data.get("temp")
    
    if temp and temp > 32:
        app_advice = f"ADVISORY: High heat ({temp}°C). Apply in late evening."
    elif temp and temp < 10:
        app_advice = f"ADVISORY: Too cold ({temp}°C). Wait for warmer weather."

    if "rain" in (weather_data.get("description") or ""):
         app_advice = "ADVISORY: Rain detected. Do not spray now."
         
    return {
        "pesticide_name": pesticide,
        "application_advice": app_advice,
        "dosage_text": dosage_text
    }

# --- 4. Main Prediction Endpoint (Updated) ---
@app.post("/predict_recommendation")
async def predict_recommendation(
    file: UploadFile = File(...),
    lat: float = Form(...),
    lon: float = Form(...),
    plant_type: str = Form(...), # e.g., "tomato"
    land_size: float = Form(...),
    land_unit: str = Form(...) 
):
    
    print(f"Received request for: {plant_type}")
    
    # Remap brinjal
    if plant_type == "brinjal":
        plant_type = "eggplant" 
    
    # --- UPDATED: Get model, class map, AND image size ---
    if plant_type not in MODELS:
        raise HTTPException(status_code=400, detail=f"No model available for plant type: {plant_type}")
    if plant_type not in CLASS_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"No class map available for plant type: {plant_type}")
    if plant_type not in MODEL_IMG_SIZES: # <-- NEW: Check for image size
        raise HTTPException(status_code=400, detail=f"No image size configured for plant type: {plant_type}")
        
    model = MODELS[plant_type]
    class_map = CLASS_MAPPINGS[plant_type]
    img_size = MODEL_IMG_SIZES[plant_type] # <-- NEW: Get the correct image size
    
    model_type = 'torch' if plant_type == 'capsicum' else 'tf'

    # --- STAGES 1, 2, & 3 (NOW REAL) ---
    image_contents = await file.read()
    
    try:
        # --- UPDATED: Pass the correct img_size ---
        prediction_name = predict_disease(
            model, 
            image_contents, 
            model_type, 
            class_map,
            img_size  # <-- NEW: Pass the size
        )
        print(f"Model prediction: {prediction_name}")
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        # Send the full, detailed error to the frontend
        raise HTTPException(status_code=500, detail=f"Model prediction failed: {e}")

   # --- Parse the prediction string (No Changes) ---
    if prediction_name == "healthy":
        disease_name = "Healthy"
        severity_level = "N/A"
    else:
        parts = prediction_name.split('__')
        if len(parts) < 2:
            disease_name = prediction_name.title()
            severity_level = "Unknown"
        else:
            disease_name = " ".join(parts[:-1]).title()
            severity_level = parts[-1].title()

    # --- STAGE 4 (Real): Fetch Weather Data (No Changes) ---
    print(f"Fetching weather for lat={lat}, lon={lon}")
    weather_data = fetch_weather_data(lat, lon, OPENWEATHER_API_KEY)

    # --- STAGE 5 (Mock Logic): Recommendation Engine (No Changes) ---
    recommendation_dict = {}
    if severity_level == "N/A":
       recommendation_dict = {
            "pesticide_name": "None",
            "application_advice": "No action needed. Plant is healthy.",
            "dosage_text": "0 ml"
        }
    else:
        recommendation_dict = get_mock_recommendation(
            disease_name, 
            severity_level,
            weather_data,
            land_size,
            land_unit
        )

    # --- STAGE 6: Return Structured JSON (No Changes) ---
    print("Sending response to frontend.")
    return {
        "disease_name": disease_name,
        "severity_level": severity_level,
        "severity_class": f"severity-{severity_level.lower()}",
        "pesticide_recommendation": recommendation_dict["pesticide_name"],
        "application_time": recommendation_dict["application_advice"],
        "dosage_amount": recommendation_dict["dosage_text"],
        "weather_info": weather_data
    }

# --- 7. Serve Your HTML/CSS/JS (MUST COME LAST) ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# --- 8. Run the Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)