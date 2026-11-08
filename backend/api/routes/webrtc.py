"""FastAPI WebRTC signaling and frame-processing endpoint."""

import asyncio
import logging
import time
from fractions import Fraction

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from fastapi import APIRouter, HTTPException, Request

from ..schemas.workout import WebRTCAnswer, WebRTCOffer
from ..services.workout_access import get_request_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


class ProcessedVideoTrack(VideoStreamTrack):
    """Return frames processed by the existing MediaPipe video processor."""

    def __init__(self, source, processor, session) -> None:
        super().__init__()
        self.source = source
        self.processor = processor
        self.session = session
        self._source_frames = asyncio.Queue(maxsize=1)
        self._frames = asyncio.Queue(maxsize=1)
        self._reader = None
        self._processor = None
        self._timestamp_origin = time.monotonic()

    async def recv(self):
        if self._reader is None:
            self._reader = asyncio.create_task(self._read_frames())
            self._processor = asyncio.create_task(self._process_frames())
        return await self._frames.get()

    async def _read_frames(self):
        while True:
            frame = await self.source.recv()
            if self._source_frames.full():
                self._source_frames.get_nowait()
            await self._source_frames.put(frame)

    async def _process_frames(self):
        while True:
            frame = await self._source_frames.get()
            if self.session.status == "running":
                frame = await asyncio.to_thread(self.processor.recv, frame)
            frame.pts = int((time.monotonic() - self._timestamp_origin) * 90_000)
            frame.time_base = Fraction(1, 90_000)
            if self._frames.full():
                self._frames.get_nowait()
            await self._frames.put(frame)

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

    peer_connection = RTCPeerConnection()
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
