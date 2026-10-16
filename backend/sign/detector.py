import logging
LOG = logging.getLogger(__name__)
import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout

# Graceful import check for MediaPipe (unsupported in some python 3.13 setups)
try:
    import mediapipe as mp
    mp_sol = mp.solutions
    mp_hands = mp_sol.hands
    mp_drawing = mp_sol.drawing_utils
    HAS_MEDIAPIPE = True
except (ImportError, AttributeError, ModuleNotFoundError) as e:
    LOG.info(f"MediaPipe solutions not fully loaded: {e}. Bypassing skeleton tracking.")
    HAS_MEDIAPIPE = False
    mp = None
    mp_hands = None
    mp_drawing = None

from .config import IMG_SIZE, NUM_CLASSES, MODEL_PATH, LETTERS, BATCH_SIZE, EPOCHS
from .dataset import preprocess_image, detect_and_crop_hand

class SignLanguageDetector:
    def __init__(self, model_path=MODEL_PATH, static_image_mode=False):
        self.letters = LETTERS
        self.model_path = model_path
        self.model = None
        self.has_mediapipe = HAS_MEDIAPIPE
        self.hands = None
        
        # Initialize MediaPipe Hands if available
        if HAS_MEDIAPIPE:
            try:
                self.mp_hands = mp_hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=static_image_mode,
                    max_num_hands=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.mp_drawing = mp_drawing
            except Exception as e:
                LOG.info(f"Error initializing MediaPipe Hands: {e}. Bypassing skeleton tracking.")
                self.has_mediapipe = False
        else:
            LOG.info("MediaPipe is unavailable. Running in full-frame classification fallback mode.")
            
        # Load pre-trained model if available
        self.load_model()

    def load_model(self):
        """Load Keras model from self.model_path"""
        if os.path.exists(self.model_path):
            try:
                self.model = load_model(self.model_path, compile=False)
                LOG.info(f"Model loaded successfully from '{self.model_path}'")
                return True
            except Exception as e:
                LOG.exception("Error loading model from '%s'", self.model_path)
        else:
            LOG.info(f"No saved model found at '{self.model_path}'")
        self.model = None
        return False

    def build_new_model(self):
        """Create a CNN model for hand sign recognition"""
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Conv2D(128, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(128, activation='relu'),
            Dropout(0.5),
            Dense(NUM_CLASSES, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        self.model = model
        return model

    def train(self, X_train, X_test, y_train, y_test, epochs=EPOCHS, batch_size=BATCH_SIZE, callback_list=None):
        """
        Train the model on the prepared dataset.
        
        Args:
            X_train, X_test, y_train, y_test: Prepared split numpy datasets
            epochs: Number of training epochs
            batch_size: Mini-batch size
            callback_list: Optional list of Keras callbacks
            
        Returns:
            history: History object with accuracy/loss training logs
        """
        if self.model is None:
            self.build_new_model()
            
        # Data augmentation pipeline
        data_augmentation = tf.keras.Sequential([
            tf.keras.layers.RandomRotation(0.1),
            tf.keras.layers.RandomZoom(0.1),
            tf.keras.layers.RandomContrast(0.1),
        ])
        
        # Prepare tf.data pipelines for efficient augmented streaming
        train_ds = tf.data.Dataset.from_tensor_slices((X_train, y_train))
        train_ds = train_ds.map(lambda x, y: (data_augmentation(x, training=True), y))
        train_ds = train_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        
        # Callbacks
        callbacks = callback_list if callback_list is not None else []
        if not any(isinstance(c, tf.keras.callbacks.EarlyStopping) for c in callbacks):
            callbacks.append(
                tf.keras.callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=5,
                    restore_best_weights=True
                )
            )
            
        LOG.info("Starting training process...")
        history = self.model.fit(
            train_ds,
            epochs=epochs,
            validation_data=(X_test, y_test),
            callbacks=callbacks
        )
        
        # Save model weights
        self.model.save(self.model_path)
        LOG.info(f"Model successfully saved to '{self.model_path}'")
        return history

    def predict(self, image):
        """
        Detect hand, crop ROI, and predict ASL alphabet letter.
        
        Args:
            image: Source BGR image from frame or file
            
        Returns:
            dict: {
                "letter": Predicted letter (str),
                "confidence": Confidence percentage (float),
                "bbox": bounding box coordinates (x_min, y_min, x_max, y_max) or None,
                "landmarks": MediaPipe landmarks object,
                "cropped_hand": The cropped BGR hand image (or None)
            }
        """
        if self.model is None:
            raise ValueError("No model loaded or built. Please train a model first.")
            
        cropped_hand, bbox, landmarks = None, None, None
        
        # Detect and crop hand if MediaPipe is available
        if self.has_mediapipe and self.hands is not None:
            try:
                cropped_hand, bbox, landmarks = detect_and_crop_hand(image, self.hands)
            except Exception as e:
                LOG.info(f"Hand detection failed: {e}")
        
        # If hand detected, predict on hand crop, else fallback to full image
        target_img = cropped_hand if cropped_hand is not None else image
        processed = preprocess_image(target_img)
        
        if processed is None:
            return {"letter": "N/A", "confidence": 0.0, "bbox": None, "landmarks": None, "cropped_hand": None}
            
        # Reshape for single prediction batch
        input_data = np.expand_dims(processed, axis=0)
        prediction = self.model.predict(input_data, verbose=0)[0]
        predicted_idx = np.argmax(prediction)
        confidence = float(prediction[predicted_idx] * 100)
        predicted_letter = self.letters[predicted_idx]
        
        return {
            "letter": predicted_letter,
            "confidence": confidence,
            "bbox": bbox,
            "landmarks": landmarks,
            "cropped_hand": cropped_hand
        }
        
    def draw_prediction(self, image, prediction_result):
        """Draw landmarks, bounding box, and prediction overlays on BGR image"""
        output_image = image.copy()
        
        # Draw hand landmarks
        landmarks = prediction_result["landmarks"]
        if self.has_mediapipe and landmarks and landmarks.multi_hand_landmarks:
            for hand_landmarks in landmarks.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    output_image,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
                
        # Draw bounding box and prediction text
        bbox = prediction_result["bbox"]
        letter = prediction_result["letter"]
        confidence = prediction_result["confidence"]
        
        if bbox:
            x_min, y_min, x_max, y_max = bbox
            cv2.rectangle(output_image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            
            # Label background
            cv2.putText(
                output_image,
                f"Sign: {letter} ({confidence:.1f}%)",
                (x_min, y_min - 10 if y_min - 10 > 20 else y_min + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )
        else:
            # Draw elegant top-left banner fallback for non-bounding box predictions
            cv2.rectangle(output_image, (10, 10), (320, 60), (15, 23, 42), -1)
            cv2.rectangle(output_image, (10, 10), (320, 60), (192, 132, 252), 1)
            cv2.putText(
                output_image,
                f"Sign: {letter} ({confidence:.1f}%)",
                (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )
            
        return output_image



