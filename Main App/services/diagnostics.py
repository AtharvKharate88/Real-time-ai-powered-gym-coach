import logging
import os
import time

_LOGGER = logging.getLogger("gymcoach")
_configured = False
_last_webrtc_snapshot = None


def configure_logging():
    global _configured
    if _configured or _LOGGER.handlers:
        _configured = True
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(handler)
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "gymcoach.log"),
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _LOGGER.addHandler(file_handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
    _configured = True


def log(message):
    configure_logging()
    _LOGGER.info(message)


def log_webrtc_context(context, source="poll"):
    global _last_webrtc_snapshot
    if context is None:
        return
    state = getattr(context, "state", None)
    playing = getattr(state, "playing", None)
    signalling = getattr(state, "signalling", None)
    ice_gathering = ice_connection = peer_state = signaling = None
    candidate_count = 0
    uses_relay = False
    getter = getattr(context, "_get_worker", None)
    worker = getter() if callable(getter) else None
    pc = getattr(worker, "pc", None) if worker else None
    if pc is not None:
        ice_gathering = getattr(pc, "iceGatheringState", None)
        ice_connection = getattr(pc, "iceConnectionState", None)
        peer_state = getattr(pc, "connectionState", None)
        signaling = getattr(pc, "signalingState", None)
        local_description = getattr(pc, "localDescription", None)
        sdp = getattr(local_description, "sdp", "") or ""
        candidate_count = sdp.count("a=candidate:")
        uses_relay = " typ relay " in f" {sdp} "
    snapshot = (
        playing,
        signalling,
        ice_gathering,
        ice_connection,
        peer_state,
        signaling,
        candidate_count,
        uses_relay,
    )
    if snapshot == _last_webrtc_snapshot:
        return
    _last_webrtc_snapshot = snapshot
    log(
        f"[WEBRTC] source={source} playing={playing} signalling={signalling} "
        f"ice_gathering={ice_gathering} ice_connection={ice_connection} "
        f"peer={peer_state} signaling={signaling} candidates={candidate_count} "
        f"relay={uses_relay}"
    )
    if ice_connection in ("connected", "completed") or peer_state == "connected":
        log("[WEBRTC] Connection established")
    elif ice_connection == "failed" or peer_state == "failed":
        log("[WEBRTC] Connection failed")
    elif ice_connection == "closed" or peer_state == "closed":
        log("[WEBRTC] Connection closed")


class VideoStats:
    def __init__(self):
        self.processed = 0
        self.dropped = 0
        self.last_report_at = time.perf_counter()
        self.last_processed = 0
        self.last_dropped = 0
        self.infer_ms = 0.0
        self.detect_ms = 0.0
        self.recv_ms = 0.0

    def record(self, recv_ms, infer_ms, detect_ms, dropped):
        self.processed += 1
        self.dropped += dropped
        self.recv_ms = recv_ms
        self.infer_ms = infer_ms
        self.detect_ms = detect_ms
        now = time.perf_counter()
        elapsed = now - self.last_report_at
        if elapsed < 2.0:
            return
        frames = self.processed - self.last_processed
        dropped_delta = self.dropped - self.last_dropped
        fps = frames / elapsed if elapsed else 0.0
        log(
            f"[VIDEO] Incoming/processed FPS={fps:.1f} "
            f"recv={self.recv_ms:.0f}ms mediapipe={self.infer_ms:.0f}ms "
            f"detector={self.detect_ms:.0f}ms stale_dropped={dropped_delta} "
            f"total_dropped={self.dropped}"
        )
        self.last_report_at = now
        self.last_processed = self.processed
        self.last_dropped = self.dropped
