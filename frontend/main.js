// main.js

// Wait for the document to be fully loaded

document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. Get All DOM Elements ---
    const analysisForm = document.getElementById("analysis-form");
    const loadingScreen = document.getElementById("loading-screen");
    const inputSection = document.getElementById("input-section");
    const resultSection = document.getElementById("result-section");

    // Get all the individual result spans
    const resultSpans = {
        diseaseName: document.getElementById("disease-name"),
        severityLevel: document.getElementById("severity-level"),
        pesticide: document.getElementById("pesticide-recommendation"),
        appTime: document.getElementById("application-time"),
        dosage: document.getElementById("dosage-amount"),
        // This ID is for the new weather field
        weatherDetails: document.getElementById("weather-details") 
    };
    const fileInput = document.getElementById('leaf-image');
    const plantTypeSelect = document.getElementById('plant-type');
    const landSizeInput = document.getElementById('land-size');
    const landUnitSelect = document.getElementById('land-unit');
    
    // Find the span element where the text should go
    // .closest() finds the nearest parent with this class
    const wrapper = fileInput.closest('.file-upload-wrapper'); 
    const fileTextSpan = wrapper.querySelector('.file-text');

    // Add an event listener for 'change'
    fileInput.addEventListener('change', function() {
      // Check if any file is selected
      if (fileInput.files.length > 0) {
        // Get the name of the first selected file
        const fileName = fileInput.files[0].name;
        
        // Update the span's text
        fileTextSpan.textContent = fileName;
      } else {
        // Reset to default if no file is selected
        fileTextSpan.textContent = 'Choose Image';
      }
    });
    
    // --- 2. Add Form Submit Listener ---
    analysisForm.addEventListener("submit", (event) => {
        // Stop the default form browser submission
        event.preventDefault(); 
        
        // Show loading screen and hide form
        inputSection.classList.add("hidden");
        loadingScreen.classList.remove("hidden");
        
        // Start the analysis process (get location, then call API)
        getAnalysis();
    });

    // --- 3. Main Analysis Function ---
    async function getAnalysis() {
        try {
            // --- Step A: Get Geolocation ---
            const position = await getGeoLocation();
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            // --- Step B: Build FormData for backend /analyze ---
            const formData = new FormData();
            // Image (required)
            if (!fileInput.files || fileInput.files.length === 0) {
                throw new Error('Please choose an image.');
            }
            formData.append('image', fileInput.files[0]);
            // Plant type mapping to backend canonical values
            const plantRaw = (plantTypeSelect.value || '').toLowerCase();
            let plantCanonical = '';
            if (plantRaw === 'tomato') plantCanonical = 'Tomato';
            else if (plantRaw === 'eggplant') plantCanonical = 'Eggplant';
            // Treat capsicum as bell pepper
            else if (plantRaw === 'capsicum') plantCanonical = 'Bell_pepper';
            else plantCanonical = plantRaw; // fallback
            formData.append('plant_type', plantCanonical);
            // Land size (include unit for readability)
            const landSizeVal = landSizeInput.value;
            const landUnitVal = landUnitSelect.value;
            formData.append('land_size', `${landSizeVal} ${landUnitVal}`);
            
            // Add the location data to the FormData
            formData.append("lat", latitude);
            formData.append("lon", longitude);

            // --- Step C: Call the FastAPI Backend ---
            // Use /analyze endpoint that validates plant mismatch
            const response = await fetch("http://127.0.0.1:8000/analyze", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                // Expecting {detail: "..."}
                let message = 'Analysis failed';
                try {
                    const errorData = await response.json();
                    message = errorData.detail || message;
                } catch {}
                throw new Error(message);
            }

            const data = await response.json();

            // --- Step D: If backend returned ok=false (defensive), treat as error ---
            if (data && data.ok === false && data.message) {
                throw new Error(data.message);
            }

            // Populate results and show them (adjust according to your API response)
            populateResults(data);
            
            loadingScreen.classList.add("hidden");
            resultSection.classList.remove("hidden");

        } catch (error) {
            // --- Error Handling ---
            console.error("Error:", error);
            alert("Error: " + error.message);
            
            // Reset UI on failure
            loadingScreen.classList.add("hidden");
            inputSection.classList.remove("hidden");
        }
    }

    // --- 4. Helper: Geolocation Promise ---
    function getGeoLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error("Geolocation is not supported by your browser."));
            } else {
                // This triggers the browser prompt
                navigator.geolocation.getCurrentPosition(resolve, () => {
                    reject(new Error("Unable to retrieve location. Please grant permission."));
                });
            }
        });
    }

    // --- 5. Helper: Populate Result Card ---
    function populateResults(data) {
        // data is the JSON object from FastAPI
        resultSpans.diseaseName.textContent = data.disease_name;
        resultSpans.severityLevel.textContent = data.severity_level;
        resultSpans.pesticide.textContent = data.pesticide_recommendation;
        resultSpans.appTime.textContent = data.application_time;
        resultSpans.dosage.textContent = data.dosage_amount;
        
        // This block formats and displays the REAL weather data
        const weather = data.weather_info;
        if (weather && weather.temp !== null) {
            // Convert wind speed from m/s to km/h
            const wind_kmh = (weather.wind_speed * 3.6).toFixed(1); 
            
            // Create a clean summary string
            resultSpans.weatherDetails.textContent = 
                `${weather.temp.toFixed(1)}°C, ${weather.humidity}% Humidity, ${wind_kmh} km/h Wind`;
        } else {
            resultSpans.weatherDetails.textContent = "Weather data unavailable";
        }
        
        // Optional: Add dynamic styling for severity
        const severityClass = data.severity_class || 'severity-moderate';
        resultSpans.severityLevel.className = `result-value ${severityClass}`;
    }
});