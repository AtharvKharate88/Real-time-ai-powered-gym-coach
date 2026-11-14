"""FastAPI WebRTC signaling and frame-processing endpoint."""

import asyncio
import logging
import time

from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.sdp import candidate_from_sdp
from fastapi import APIRouter, HTTPException, Request

from ..schemas.workout import WebRTCAnswer, WebRTCIceCandidate, WebRTCOffer
from ..services.auth import current_user
from ..services.ice_config import build_ice_servers
from ..services.workout_access import get_request_session
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


def _ice_servers() -> list[dict[str, str | list[str]]]:
    return build_ice_servers(
        settings.stun_url,
        settings.turn_url,
        settings.turn_username,
        settings.turn_credential,
    )


@router.get("/ice-servers")
def get_ice_servers(request: Request) -> dict[str, list[dict[str, str | list[str]]]]:
    """Return ICE settings to the signed-in browser for the active WebRTC session."""
    current_user(request)
    try:
        return {"ice_servers": _ice_servers()}
    except ValueError as error:
        raise HTTPException(status_code=503, detail="TURN configuration is incomplete.") from error


class ProcessedVideoTrack(VideoStreamTrack):
    """Return frames processed by the existing MediaPipe video processor."""

    def __init__(self, source, processor, session) -> None:
        super().__init__()
        self.source = source
        self.processor = processor
        self.session = session
        self._source_frames = asyncio.Queue(maxsize=1)
        self._video_frames = asyncio.Queue(maxsize=1)
        self._reader = None
        self._processor = None
        self._dropped_frames = 0
        self._output_frames = 0
        self._output_report_at = time.monotonic()

    async def recv(self):
        if self._reader is None:
            self._reader = asyncio.create_task(self._read_frames())
            self._processor = asyncio.create_task(self._process_frames())
        frame = await self._video_frames.get()
        annotate = getattr(self.processor, "annotate_latest", None)
        output = annotate(frame) if callable(annotate) else frame
        self._output_frames += 1
        now = time.monotonic()
        elapsed = now - self._output_report_at
        if elapsed >= 5:
            logger.info("[VIDEO] Live output FPS=%.1f", self._output_frames / elapsed)
            self._output_frames = 0
            self._output_report_at = now
        return output

    async def _read_frames(self):
        while True:
            frame = await self.source.recv()
            if self._video_frames.full():
                self._video_frames.get_nowait()
                self._dropped_frames += 1
            await self._video_frames.put(frame)
            if self._source_frames.full():
                # Replace the queued frame with this newer one; inference must not build a backlog.
                self._source_frames.get_nowait()
                self._dropped_frames += 1
            await self._source_frames.put(frame)

    async def _process_frames(self):
        while True:
            frame = await self._source_frames.get()
            if self.session.status == "running":
                dropped = self._dropped_frames
                self._dropped_frames = 0
                await asyncio.to_thread(self.processor.recv, frame, dropped)

    def stop(self) -> None:
        for task in (self._reader, self._processor):
            if task is not None:
                task.cancel()
        self._reader = None
        self._processor = None
        self.source.stop()
        super().stop()


@router.post("/offer", response_model=WebRTCAnswer)
async def receive_offer(
    session_id: str, offer: WebRTCOffer, request: Request
) -> WebRTCAnswer:
    session = get_request_session(session_id, request)

    try:
        processor = session.ensure_processor()
        await asyncio.to_thread(processor.warm_up)
        session.start()
    except (ImportError, OSError) as error:
        logger.exception("Vision processor is unavailable")
        raise HTTPException(
            status_code=503,
            detail=(
                "Vision processing is unavailable. Use the project's Python 3.12 "
                "environment and install backend\\requirements.txt. "
                f"Cause: {error}"
            ),
        ) from error
    session.ensure_voice_pipeline()

    try:
        configured_servers = [
            RTCIceServer(**server) for server in _ice_servers()
        ]
    except ValueError as error:
        raise HTTPException(status_code=503, detail="TURN configuration is incomplete.") from error

    peer_connection = RTCPeerConnection(
        configuration=RTCConfiguration(iceServers=configured_servers)
    )
    processed_track = None
    session.peer_connection = peer_connection

    @peer_connection.on("track")
    def on_track(track) -> None:
        nonlocal processed_track
        if track.kind == "video":
            processed_track = ProcessedVideoTrack(
                track, processor, session
            )
            peer_connection.addTrack(processed_track)

        @track.on("ended")
        async def on_ended() -> None:
            logger.info("WebRTC video track ended for session %s", session_id)

    @peer_connection.on("connectionstatechange")
    async def on_connection_state_change() -> None:
        if peer_connection.connectionState in {"failed", "closed", "disconnected"}:
            if processed_track is not None:
                processed_track.stop()
            await peer_connection.close()
            session.peer_connection = None

    await peer_connection.setRemoteDescription(
        RTCSessionDescription(sdp=offer.sdp, type=offer.type)
    )
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)

    return WebRTCAnswer(
        sdp=peer_connection.localDescription.sdp,
        type=peer_connection.localDescription.type,
    )


@router.post("/candidate")
async def receive_candidate(
    session_id: str,
    candidate: WebRTCIceCandidate,
    request: Request,
) -> dict[str, bool]:
    session = get_request_session(session_id, request)
    peer_connection = session.peer_connection
    if not isinstance(peer_connection, RTCPeerConnection):
        raise HTTPException(status_code=409, detail="WebRTC offer is not ready for candidates.")

    if not candidate.candidate:
        await peer_connection.addIceCandidate(None)
        return {"accepted": True}

    candidate_line = candidate.candidate.removeprefix("candidate:")
    try:
        remote_candidate = candidate_from_sdp(candidate_line)
    except (AssertionError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid ICE candidate.") from error

    remote_candidate.sdpMid = candidate.sdpMid
    remote_candidate.sdpMLineIndex = candidate.sdpMLineIndex
    if remote_candidate.sdpMid is None and remote_candidate.sdpMLineIndex is None:
        raise HTTPException(status_code=400, detail="ICE candidate is missing its media section.")

    await peer_connection.addIceCandidate(remote_candidate)
    return {"accepted": True}
