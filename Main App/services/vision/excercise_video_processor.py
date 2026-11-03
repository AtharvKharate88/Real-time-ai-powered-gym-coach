from streamlit_webrtc import VideoProcessorBase


import os
import cv2#Image processing and drawing
import av#Converts processed images into video frames
import numpy as np
import mediapipe as mp#Detects human body landmarks
import threading
from streamlit_webrtc import VideoProcessorBase#Base class for processing live WebRTC video
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from detectors.squat import SquatDetector
from detectors.pushup import PushUpDetector
from detectors.biceps_curl import BicepsCurlDetector
from detectors.shoulder_press import ShoulderPressDetector
from detectors.lunges import LungesDetector
from services.config.workout_config import POSE_CONNECTIONS


class VideoProcessorClass(VideoProcessorBase):
    def __init__(self):
        self._lock = threading.Lock()#prevent simultaneous updation
        self._latest_metrics = None#store latest excercise analysis
        self._exercise_type = "Squats"
        model_path = os.path.join(os.getcwd(), "ml_models", "pose_landmarker_full.task")
        base_option = python.BaseOptions(model_asset_path=model_path)#tell where pose_landmarker located
        options = vision.PoseLandmarkerOptions(
            base_options=base_option,
            running_mode=vision.RunningMode.VIDEO,#Processes video frames sequentially
            min_pose_detection_confidence=0.7,#Minimum confidence for detecting a pose
            min_pose_presence_confidence=0.7,#Minimum confidence that a detected pose is present
            min_tracking_confidence=0.7,#Minimum confidence for pose tracking
            output_segmentation_masks=False#Does not generate body segmentation masks
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

        self._detectors = {
            "Squats": SquatDetector(),
            "Push-ups": PushUpDetector(),
            "Biceps Curls (Dumbbell)": BicepsCurlDetector(),
            "Shoulder Press": ShoulderPressDetector(),
            "Lunges": LungesDetector(),
        }

        self._frame_timestamps_ms = 0
        #This variable tracks the timestamp of the video frames in milliseconds.
    #Stores a copy of the latest metrics.    
    def set_latest_metrics(self, metrics):
        with self._lock:
            self._latest_metrics = metrics.copy()
    #Returns a copy of the latest metrics.
    #Returning a copy prevents it from directly modifying the internal dictionary.
    def get_latest_metrics(self):
        with self._lock:
            return None if self._latest_metrics is None else self._latest_metrics.copy()
    #Changes the currently selected exercise.
    def set_exercise(self, exercise_type):
        with self._lock:
            self._exercise_type = exercise_type
    #Retrieves the selected exercise.
    def get_exercise(self):
        with self._lock:
            return self._exercise_type
        
    def _draw_skeleton(self, img, landmarks):
        h, w = img.shape[:2]

        for start_idx, end_idx in POSE_CONNECTIONS:
            p1 = landmarks[start_idx]
            p2 = landmarks[end_idx]

            if p1.visibility > 0.7 and p2.visibility > 0.7:
                #This draws a green line connecting two landmarks.
                cv2.line(
                    img,
                    (int(p1.x * w), int(p1.y * h)),#This converts normalized coordinates into actual pixel coordinates.
                    (int(p2.x * w), int(p2.y * h)),
                    (0, 255, 0),
                    8
                )
        
        for lm in landmarks:
            if lm.visibility > 0.7:
                #Draws a blue circle at each visible landmark.
                cv2.circle(
                    img, 
                    (int(lm.x * w), int(lm.y * h)),
                    8,
                    (255, 0, 0),
                    -1
                )
            
    def _draw_no_pose_warnings(self, img):
        #Drawing warnings when no pose is detected
        cv2.putText(
            img,
            "NO POSE DETECTED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            img,
            "PLEASE FACE THE CAMERA",
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    #show metric of excercise at bottom
    def _draw_overlays(self, img, metrics, ex_type):
        if ex_type == "Squats":
            self._draw_squats_overlays(img, metrics)
        elif ex_type == "Push-ups":
            self._draw_pushup_overlays(img, metrics)
        elif ex_type == "Biceps Curls (Dumbbell)":
            self._draw_curl_overlays(img, metrics)
        elif ex_type == "Shoulder Press":
            self._draw_press_overlays(img, metrics)
        elif ex_type == "Lunges":
            self._draw_lunge_overlays(img, metrics)


    def _draw_squats_overlays(self, img, metrics):
        h, _ = img.shape[:2]

        cv2.putText(
            img,
            f"DEPTH: {metrics['depth_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
    
    def _draw_pushup_overlays(self, img, metrics):
        h, _ = img.shape[:2]

        cv2.putText(
            img,
            f"BODY: {metrics['body_alignment']} | HIP: {metrics['hip_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_curl_overlays(self, img, metrics):
        h, _ = img.shape[:2]

        cv2.putText(
            img,
            f"SWING: {metrics['swing_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_press_overlays(self, img, metrics):
        h, _ = img.shape[:2]

        cv2.putText(
            img,
            f"EXT: {metrics['extension_status']} | BACK: {metrics['back_arch_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_lunge_overlays(self, img, metrics):
        h, _ = img.shape[:2]

        cv2.putText(
            img,
            f"BALANCE: {metrics['balance_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def recv(self, frame):
        #Receive and convert the frame
        image = np.asarray(
            cv2.flip(frame.to_ndarray(format="bgr24"), 1),
            dtype=np.uint8
        )
        #Convert the image for MediaPipe
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        )
        #Update timestamp
        self._frame_timestamps_ms += 30
        #Detect body landmarks
        result = self._landmarker.detect_for_video(mp_image, self._frame_timestamps_ms)
        #Check whether a pose exists
        if result.pose_landmarks:
            landmarks = result.pose_landmarks[0]
            #draw the skeleton
            self._draw_skeleton(image, landmarks)
            #get the selected exercise
            ex_type = self.get_exercise()
            #select detector
            detector = self._detectors.get(ex_type)

            if detector:
                #Analyze the exercise
                metrics = detector.process(landmarks)
                metrics["pose_detected"] = True
                #: Draw the feedback
                self._draw_overlays(image, metrics, ex_type)
                self.set_latest_metrics(metrics)
        else:
            #Handle missing pose
            self._draw_no_pose_warnings(image)
            latest_metrics = self.get_latest_metrics() or {}
            latest_metrics["pose_detected"] = False
            self.set_latest_metrics(latest_metrics)
        #Return the processed frame
        return av.VideoFrame.from_ndarray(image, format="bgr24")