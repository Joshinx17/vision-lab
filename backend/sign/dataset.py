import logging
LOG = logging.getLogger(__name__)
import os
import cv2
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from .config import IMG_SIZE, BATCH_SIZE, NUM_CLASSES, DATASET_PATH

def preprocess_image(image, target_size=(IMG_SIZE, IMG_SIZE)):
    """Preprocess image: resize and normalize pixel values to [0, 1]"""
    if image is None or image.size == 0:
        return None
    image_resized = cv2.resize(image, target_size)
    image_normalized = image_resized.astype(np.float32) / 255.0
    return image_normalized

def detect_and_crop_hand(image, hands, padding=20):
    """
    Detect hand landmarks using MediaPipe and crop the hand area.
    
    Args:
        image: Source BGR image
        hands: MediaPipe Hands object instance
        padding: Bounding box padding in pixels
        
    Returns:
        cropped_img: Cropped BGR hand image (or None if empty bounding box)
        bbox: Tuple (x_min, y_min, x_max, y_max) or None
        results: MediaPipe results object
    """
    if hands is None or image is None or image.size == 0:
        return None, None, None

    try:
        h, w, _ = image.shape
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)
        
        if results.multi_hand_landmarks:
            x_min, x_max, y_min, y_max = w, 0, h, 0
            for hand_landmarks in results.multi_hand_landmarks:
                for lm in hand_landmarks.landmark:
                    x, y = int(lm.x * w), int(lm.y * h)
                    x_min = min(x_min, x)
                    x_max = max(x_max, x)
                    y_min = min(y_min, y)
                    y_max = max(y_max, y)
            
            # Apply padding and clamp to image boundaries
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(w, x_max + padding)
            y_max = min(h, y_max + padding)
            
            cropped_img = image[y_min:y_max, x_min:x_max]
            if cropped_img.size > 0:
                return cropped_img, (x_min, y_min, x_max, y_max), results
    except Exception as e:
        LOG.info(f"Error in hand detection: {e}")
            
    return None, None, None

def prepare_dataset(dataset_path, letters, hands_processor):
    """
    Traverse dataset folders, extract cropped hand regions and prepare training datasets.
    
    Args:
        dataset_path: Path to dataset containing subfolders A-Z
        letters: List of letters (A-Z)
        hands_processor: MediaPipe Hands instance to crop hands
        
    Returns:
        X_train, X_test, y_train, y_test
    """
    if not os.path.exists(dataset_path):
        LOG.info(f"Dataset path '{dataset_path}' does not exist! Please create it.")
        return None, None, None, None
        
    images = []
    labels = []
    
    for letter_idx, letter in enumerate(letters):
        letter_path = os.path.join(dataset_path, letter)
        if not os.path.exists(letter_path):
            continue
            
        LOG.info(f"Processing images for letter '{letter}'...")
        count = 0
        for img_file in os.listdir(letter_path):
            if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(letter_path, img_file)
                image = cv2.imread(img_path)
                if image is None:
                    continue
                
                # Detect and crop hand; fallback to full image if hand not detected or processor is None
                cropped = None
                if hands_processor is not None:
                    try:
                        cropped, _, _ = detect_and_crop_hand(image, hands_processor)
                    except Exception:
                        pass
                        
                target_img = cropped if cropped is not None else image
                
                processed_img = preprocess_image(target_img)
                if processed_img is not None:
                    images.append(processed_img)
                    labels.append(letter_idx)
                    count += 1
        LOG.info(f"Loaded {count} samples for letter '{letter}'")
    
    if not images:
        LOG.info("No valid images found in the dataset!")
        return None, None, None, None
        
    images = np.array(images)
    labels = np.array(labels)

    counts = np.bincount(labels, minlength=NUM_CLASSES)
    if np.any(counts < 5):
        raise ValueError('At least 5 decodable images per A-Z class are required for the stratified split.')
    
    # Convert labels to one-hot encoding
    labels_one_hot = tf.keras.utils.to_categorical(labels, NUM_CLASSES)
    
    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        images, labels_one_hot, test_size=0.2, random_state=42, stratify=labels
    )
    
    LOG.info(f"Dataset prepared successfully!")
    LOG.info(f"Training samples: {len(X_train)} | Test samples: {len(X_test)}")
    return X_train, X_test, y_train, y_test


