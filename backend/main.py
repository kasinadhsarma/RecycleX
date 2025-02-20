from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tensorflow as tf
import numpy as np
import cv2
import os
import logging
import shutil
from datetime import datetime
from io import BytesIO
from PIL import Image
import base64
from video_processor import process_video

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Application configuration"""
    API_VERSION = "1.0.0"
    API_TITLE = "RecycleX API"
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app = FastAPI(
    title=Config.API_TITLE,
    version=Config.API_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORIES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

def validate_file(file: UploadFile, allowed_extensions: set) -> tuple[bool, str]:
    """Validate uploaded file format and size"""
    if not file.filename:
        return False, "No filename provided"
    
    file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > Config.MAX_FILE_SIZE:
            return False, f"File size exceeds maximum limit of {Config.MAX_FILE_SIZE/1024/1024}MB"
        
        if size == 0:
            return False, "File is empty"
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        return False, f"Error validating file: {str(e)}"
    
    return True, ""

def draw_detection(image: np.ndarray, class_name: str, confidence: float) -> np.ndarray:
    """Draw detection box and label on image"""
    height, width = image.shape[:2]
    
    # Calculate coordinates for centered box (80% of image size)
    box_size = min(width, height) * 0.8
    x1 = int((width - box_size) / 2)
    y1 = int((height - box_size) / 2)
    x2 = int(x1 + box_size)
    y2 = int(y1 + box_size)

    # Draw green rectangle
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)

    # Prepare label text
    label = f"{class_name}: {confidence:.1%}"
    
    # Get text size
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    (label_width, label_height), baseline = cv2.getTextSize(
        label, font, font_scale, thickness
    )

    # Draw filled background for text
    cv2.rectangle(
        image,
        (x1, y1 - label_height - 10),
        (x1 + label_width + 10, y1),
        (0, 255, 0),
        -1
    )

    # Draw white text
    cv2.putText(
        image,
        label,
        (x1 + 5, y1 - 5),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA
    )

    return image

async def process_image(image: np.ndarray) -> dict:
    """Process image and return detection results"""
    try:
        # Store original image for drawing
        original_image = image.copy()

        # Preprocess image for model
        image = cv2.resize(image, (224, 224))
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = tf.keras.applications.efficientnet.preprocess_input(image)
        image = np.expand_dims(image, axis=0)

        # Make prediction
        prediction = model.predict(image, verbose=0)
        predicted_class = CATEGORIES[np.argmax(prediction[0])]
        confidence = float(np.max(prediction[0]))

        # Draw detection on original image
        result_image = draw_detection(original_image, predicted_class, confidence)

        # Convert to base64
        _, buffer = cv2.imencode('.jpg', result_image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "status": "success",
            "predicted_class": predicted_class,
            "confidence": confidence,
            "processed_image": f"data:image/jpeg;base64,{image_base64}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/predict/live")
async def predict_live(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                img_bytes = base64.b64decode(data.split(',')[1])
                img = Image.open(BytesIO(img_bytes))
                image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                # Process frame
                result = await process_image(image)
                await websocket.send_json(result)
                
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                continue
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    logger.info("WebSocket connection closed")

@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    """Process uploaded image with detection visualization"""
    try:
        # Validate file
        is_valid, error_message = validate_file(file, Config.ALLOWED_IMAGE_EXTENSIONS)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        content = await file.read()
        image = cv2.imdecode(
            np.frombuffer(content, np.uint8),
            cv2.IMREAD_COLOR
        )
        if image is None:
            raise HTTPException(status_code=400, detail="Could not read image")
        
        result = await process_image(image)
        return JSONResponse(status_code=200, content=result)
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/video")
async def predict_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Process uploaded video with frame-by-frame detection"""
    try:
        # Validate file
        is_valid, error_message = validate_file(file, Config.ALLOWED_VIDEO_EXTENSIONS)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Save file temporarily
        content = await file.read()
        temp_path = os.path.join(Config.UPLOAD_FOLDER, f"temp_{file.filename}")
        with open(temp_path, "wb") as f:
            f.write(content)

        # Process video
        result = process_video(
            temp_path,
            model,
            tf.keras.applications.efficientnet.preprocess_input,
            CATEGORIES
        )

        # Schedule cleanup
        background_tasks.add_task(lambda: os.remove(temp_path))

        return JSONResponse(status_code=200, content=result)
    
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        if 'temp_path' in locals():
            background_tasks.add_task(lambda: os.remove(temp_path))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": Config.API_VERSION
    }

# Load the model
print("Loading model...")
try:
    img_size = 224
    base_model = tf.keras.applications.EfficientNetB4(
        weights='imagenet', 
        include_top=False, 
        input_shape=(img_size, img_size, 3)
    )
    
    inputs = base_model.input
    x = base_model.output
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x1 = tf.keras.layers.Dense(1024, activation='relu')(x)
    x1 = tf.keras.layers.BatchNormalization()(x1)
    x1 = tf.keras.layers.Dropout(0.5)(x1)
    x2 = tf.keras.layers.Dense(512, activation='relu')(x1)
    x2 = tf.keras.layers.BatchNormalization()(x2)
    x2 = tf.keras.layers.Dropout(0.4)(x2)
    x2 = tf.keras.layers.Add()([x2, tf.keras.layers.Dense(512)(x1)])
    x3 = tf.keras.layers.Dense(256, activation='relu')(x2)
    x3 = tf.keras.layers.BatchNormalization()(x3)
    x3 = tf.keras.layers.Dropout(0.3)(x3)
    x3 = tf.keras.layers.Add()([x3, tf.keras.layers.Dense(256)(x2)])
    outputs = tf.keras.layers.Dense(len(CATEGORIES), activation='softmax')(x3)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    
    model_path = os.path.join(os.path.dirname(__file__), "TrashNet_Model.h5")
    if os.path.exists(model_path):
        model.load_weights(model_path)
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        print("Model loaded successfully")
    else:
        raise FileNotFoundError("Model file not found.")
except Exception as e:
    print(f"Error loading model: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
