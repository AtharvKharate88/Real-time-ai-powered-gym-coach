import os
import sys
import time
import inspect
import threading
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def _rss_mb():
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        try:
            import resource

            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except Exception:
            return None


def main():
    print("=== Checkpoint measurements ===")
    rss = _rss_mb()
    if rss is not None:
        print(f"Checkpoint 0 RSS before imports: {rss:.0f} MB")

    import streamlit_webrtc

    print(f"streamlit-webrtc {streamlit_webrtc.__version__}")
    signature = inspect.signature(streamlit_webrtc.webrtc_streamer)
    for name in (
        "queued_video_frames_callback",
        "rtc_configuration",
        "frontend_rtc_configuration",
        "server_rtc_configuration",
        "desired_playing_state",
        "on_change",
        "async_processing",
        "sendback_audio",
    ):
        print(f"webrtc_streamer supports {name}: {name in signature.parameters}")

    from streamlit_webrtc.models import VideoProcessorBase

    print(
        "VideoProcessorBase.recv_queued drops to latest by default:",
        "frames[-1]" in inspect.getsource(VideoProcessorBase.recv_queued),
    )

    import_started = time.perf_counter()
    from services.vision.excercise_video_processor import VideoProcessorClass

    print(f"VideoProcessorClass import: {(time.perf_counter() - import_started) * 1000:.0f}ms")
    rss = _rss_mb()
    if rss is not None:
        print(f"Checkpoint 0 RSS after MediaPipe import: {rss:.0f} MB")

    init_started = time.perf_counter()
    processor = VideoProcessorClass()
    init_ms = (time.perf_counter() - init_started) * 1000
    print(f"Checkpoint 1 VideoProcessorClass.__init__: {init_ms:.0f}ms (must stay << 10000)")

    import av
    import numpy as np

    image = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = av.VideoFrame.from_ndarray(image, format="bgr24")

    first_started = time.perf_counter()
    processor.recv(frame, dropped=0)
    first_ms = (time.perf_counter() - first_started) * 1000
    print(f"Checkpoint 1/2 first recv() including model load: {first_ms:.0f}ms")
    print(f"landmarker error={processor._landmarker_error}")
    rss = _rss_mb()
    if rss is not None:
        print(f"Checkpoint 0 RSS after PoseLandmarker: {rss:.0f} MB")

    times = []
    for _ in range(8):
        started = time.perf_counter()
        processor.recv(frame, dropped=0)
        times.append((time.perf_counter() - started) * 1000)
    print(f"Checkpoint 2 recv() ms: {[round(t) for t in times]}")
    print(f"Checkpoint 2 recv() average after warmup: {sum(times[1:]) / max(1, len(times) - 1):.0f}ms")

    async def drop_batch():
        frames = [frame, frame, frame, frame, frame]
        return await processor.recv_queued(frames)

    import asyncio

    dropped_result = asyncio.run(drop_batch())
    print(f"Checkpoint 2 recv_queued keeps latest only: returned={len(dropped_result)} of 5")

    slow_done = threading.Event()

    def slow_voice():
        time.sleep(5)
        slow_done.set()

    voice_thread = threading.Thread(target=slow_voice, name="fake-groq")
    voice_thread.start()
    concurrent = []
    while voice_thread.is_alive():
        started = time.perf_counter()
        processor.recv(frame, dropped=0)
        concurrent.append((time.perf_counter() - started) * 1000)
    voice_thread.join()
    print(
        f"Checkpoint 3 recv() during 5s fake Groq/TTS: "
        f"frames={len(concurrent)} avg={sum(concurrent)/len(concurrent):.0f}ms "
        f"max={max(concurrent):.0f}ms"
    )

    from detectors.shoulder_press import ShoulderPressDetector
    from detectors.biceps_curl import BicepsCurlDetector
    from detectors.squat import SquatDetector
    from detectors.pushup import PushUpDetector
    from detectors.lunges import LungesDetector

    print(
        "Detectors preserved:",
        ShoulderPressDetector.__name__,
        BicepsCurlDetector.__name__,
        SquatDetector.__name__,
        PushUpDetector.__name__,
        LungesDetector.__name__,
    )
    processor.on_ended()
    rss = _rss_mb()
    if rss is not None:
        print(f"Checkpoint 0 RSS after processor stop: {rss:.0f} MB")
    print("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
