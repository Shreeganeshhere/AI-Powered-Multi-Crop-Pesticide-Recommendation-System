# backend/model_utils.py

import tensorflow as tf
from tensorflow.keras import models
from tensorflow.keras.preprocessing import image
import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import io
import os
import json

# --- 1. DEFINE PATHS AND (NEW) IMAGE SIZES ---
BASE_PATH = os.path.join("backend", "Models")

MODEL_PATHS = {
    "tomato": os.path.join(BASE_PATH, "tomato_disease_model_v1.h5"),
    "capsicum": os.path.join(BASE_PATH, "capsicum_disease_model.pth"),
    "eggplant": os.path.join(BASE_PATH, "eggplant_disease_model.h5")
}

CLASS_JSON_PATHS = {
    "tomato": os.path.join(BASE_PATH, "tomato_class_indices.json"),
    "capsicum": os.path.join(BASE_PATH, "capsicum_class_indices.json"),
    "eggplant": os.path.join(BASE_PATH, "eggplant_class_indices.json")
}

# --- NEW: Define model-specific image sizes ---
# Based on the errors, 'tomato' needs 256, and 'eggplant' needs 224
MODEL_IMG_SIZES = {
    "tomato": (256, 256),    
    "capsicum": (224, 224),  
    "eggplant": (224, 224)   
}

# --- 2. IMAGE PREPROCESSING (Updated) ---

# --- REMOVED global pytorch_transform ---

# --- UPDATED preprocess_image function ---
def preprocess_image(image_bytes, model_type, img_size): # Added img_size argument
    """
    Takes image bytes and preprocesses for TF or PyTorch
    using the specific image size.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    
    if model_type == 'tf':
        # TensorFlow/Keras preprocessing
        img = img.resize(img_size) # Use the passed-in img_size
        img_array = image.img_to_array(img)
        img_array = img_array / 255.0  # Normalize
        img_batch = np.expand_dims(img_array, axis=0)
        return img_batch
        
    elif model_type == 'torch':
        # Create the PyTorch transform on-the-fly
        pytorch_transform = transforms.Compose([
            transforms.Resize(img_size), # Use the passed-in img_size
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        img_tensor = pytorch_transform(img)
        img_batch = img_tensor.unsqueeze(0)
        return img_batch

# --- 3. MODEL AND CLASS LOADING (No Changes) ---
def load_all_models_and_classes():
    # ... (This function remains exactly the same as before) ...
    loaded_models = {}
    class_mappings = {}
    try:
        # ... (loading models logic) ...
        loaded_models["tomato"] = models.load_model(MODEL_PATHS["tomato"])
        loaded_models["eggplant"] = models.load_model(MODEL_PATHS["eggplant"])
        loaded_models["capsicum"] = torch.load(MODEL_PATHS["capsicum"], weights_only=False)
        loaded_models["capsicum"].eval()

        print("All models loaded successfully.")

        # --- NEW: Load and Invert Class JSONs ---
        for plant_type, json_path in CLASS_JSON_PATHS.items():
            with open(json_path, 'r') as f:
                # Load the file (e.g., {"healthy": 0, "early_blight_low": 1})
                name_to_index_map = json.load(f)
                
                # Invert the map to be {0: "healthy", 1: "early_blight_low"}
                # We also convert the index (which is a string in JSON) to an integer
                index_to_name_map = {int(k): v for k, v in name_to_index_map.items()}
                
                class_mappings[plant_type] = index_to_name_map
                
        print("All class mappings loaded and inverted successfully.")
        
    except Exception as e:
        print(f"Error loading models or classes: {e}")
        print("Please check all file paths and JSON file contents.")

    return loaded_models, class_mappings

# --- 4. PREDICTION FUNCTION (Updated) ---
# --- UPDATED predict_disease function ---
def predict_disease(model, image_bytes, model_type, class_map, img_size): # Added img_size
    """
    Runs prediction on a single image.
    """
    # Preprocess the image using the correct size
    processed_image = preprocess_image(image_bytes, model_type, img_size) # Pass img_size
    
    if model_type == 'tf':
        prediction = model.predict(processed_image)
        predicted_index = np.argmax(prediction, axis=1)[0]
        
    elif model_type == 'torch':
        with torch.no_grad():
            prediction = model(processed_image)
            predicted_index = torch.argmax(prediction, dim=1).item()
            
    # Map index to class name
    predicted_class_name = class_map.get(
        predicted_index, 
        f"Unknown (Index: {predicted_index})"
    )
    
    return predicted_class_name