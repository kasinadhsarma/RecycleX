from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tensorflow as tf
import numpy as np
import cv2
from io import BytesIO
import PIL.Image as Image
import base64
import asyncio
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Categories
CATEGORIES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]

# Load the model
print("Loading model...")
try:
    # Custom objects to handle model loading
    custom_objects = {
        'FixedDropout': tf.keras.layers.Dropout,
        'efficientnet': tf.keras.applications.EfficientNetB4
    }
    
    # Load the model with custom objects
    model_path = os.path.join(os.path.dirname(__file__), "TrashNet_Model.h5")
    if os.path.exists(model_path):
        model = tf.keras.models.load_model(
            model_path,
            custom_objects=custom_objects,
            compile=False  # Don't compile the model for inference
        )
        # Compile the model with basic settings for inference
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        print("Model loaded successfully from TrashNet_Model.h5")
    else:
        raise FileNotFoundError("Model file not found.")
except Exception as e:
    print(f"Error loading model: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to load the model: {str(e)}")

def preprocess_image(image):
    """
    Preprocess the image for the EfficientNetB4 model.
    """
    try:
        # Resize and convert to RGB if needed
        image = cv2.resize(image, (224, 224))
        if len(image.shape) == 2:  # Grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:  # RGBA
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        
        # Convert BGR to RGB since OpenCV uses BGR
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Preprocess specifically for EfficientNetB4
        image = tf.keras.applications.efficientnet.preprocess_input(image)
        return np.expand_dims(image, axis=0)
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image format.")

def process_frame(frame):
    """
    Process a single frame and return predictions.
    """
    try:
        # Preprocess frame
        processed_frame = preprocess_image(frame)
        
        # Make prediction
        prediction = model.predict(processed_frame)
        
        # Get top prediction
        predicted_class = CATEGORIES[np.argmax(prediction[0])]
        confidence = float(np.max(prediction[0]))
        
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "class_probabilities": {
                category: float(prob) 
                for category, prob in zip(CATEGORIES, prediction[0])
            }
        }
    except Exception as e:
        print(f"Error processing frame: {e}")
        raise HTTPException(status_code=500, detail="Failed to process frame.")

@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    """
    Predict the class of an uploaded image.
    """
    try:
        # Read file
        content = await file.read()
        
        # Convert to numpy array
        image = np.array(Image.open(BytesIO(content)))
        
        return process_frame(image)
    except Exception as e:
        print(f"Error predicting image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file.")

@app.post("/predict/video")
async def predict_video(file: UploadFile = File(...)):
    """
    Predict the dominant class in an uploaded video.
    """
    try:
        # Read video file
        content = await file.read()
        temp_file = "temp_video.mp4"
        
        with open(temp_file, "wb") as f:
            f.write(content)
        
        # Process video
        results = []
        cap = cv2.VideoCapture(temp_file)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            result = process_frame(frame)
            results.append(result)
            
        cap.release()
        
        # Calculate overall prediction
        total_frames = len(results)
        class_counts = {category: 0 for category in CATEGORIES}
        
        for result in results:
            class_counts[result["predicted_class"]] += 1
        
        dominant_class = max(class_counts.items(), key=lambda x: x[1])[0]
        confidence = class_counts[dominant_class] / total_frames
        
        return {
            "predicted_class": dominant_class,
            "confidence": confidence,
            "frame_results": results
        }
    except Exception as e:
        print(f"Error predicting video: {e}")
        raise HTTPException(status_code=400, detail="Invalid video file.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@app.websocket("/predict/live")
async def predict_live(websocket: WebSocket):
    """
    Live prediction over WebSocket using base64-encoded frames.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive frame as base64 string
            data = await websocket.receive_text()
            
            try:
                # Convert base64 to image
                img_bytes = base64.b64decode(data.split(',')[1])
                image = np.array(Image.open(BytesIO(img_bytes)))
                
                # Process frame
                result = process_frame(image)
                
                # Send back result
                await websocket.send_json(result)
            except Exception as e:
                print(f"Error processing WebSocket frame: {e}")
                await websocket.send_json({"error": "Invalid frame data"})
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "model": "loaded"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
