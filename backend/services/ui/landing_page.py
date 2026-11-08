import base64
import mimetypes
import re
from pathlib import Path

import streamlit as st


def _landing_page_root() -> Path:
    main_app_root = Path(__file__).resolve().parents[2]
    repository_root = main_app_root.parent
    for candidate in (main_app_root / "LandingPage", repository_root / "frontend"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("LandingPage directory was not found.")


def _load_landing_markup() -> str:
    landing_root = _landing_page_root()
    html = (landing_root / "index.html").read_text(encoding="utf-8")
    css = (landing_root / "style.css").read_text(encoding="utf-8")

    font_path = landing_root / "fonts" / "Averta.woff2"
    font_data = base64.b64encode(font_path.read_bytes()).decode("ascii")
    html = html.replace(
        'url("fonts/Averta.woff2")',
        f'url("data:font/woff2;base64,{font_data}")',
    )
    html = html.replace('<link rel="stylesheet" href="style.css" />', f"<style>{css}</style>")
    for image_number in range(1, 7):
        image_path = landing_root / "IMGs" / f"i{image_number}.png"
        if image_path.is_file():
            image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
            html = html.replace(
                f'src="./IMGs/i{image_number}.png"',
                f'src="data:image/png;base64,{image_data}"',
            )

    video_path = landing_root / "videos" / "video.mp4"
    if video_path.is_file():
        video_data = base64.b64encode(video_path.read_bytes()).decode("ascii")
        video_mime = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        html = html.replace(
            'src="videos/video.mp4"',
            f'src="data:{video_mime};base64,{video_data}"',
        )
    else:
        html = re.sub(
            r'<video src="videos/video\.mp4" controls playsinline></video>',
            '<div class="video-placeholder">DEMO VIDEO NOT AVAILABLE<br>'
            '<span>Add LandingPage/videos/video.mp4 to enable playback.</span></div>',
            html,
        )

    navigation_script = """
      <style>
        .video-placeholder {
          min-height: 420px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          color: #666;
          font: 11px var(--font-body);
          letter-spacing: 0.12em;
          text-align: center;
        }
        .video-placeholder span {
          color: #444;
          font-size: 10px;
          letter-spacing: 0.04em;
        }
      </style>
      <script>
        const cta = document.getElementById("cta-button");
        if (cta) {
          cta.addEventListener("click", (event) => {
            event.preventDefault();
            const url = new URL(window.parent.location.href);
            url.searchParams.set("view", "login");
              window.parent.location.assign(url.toString());
          });
        }
      </script>
    """
    return html.replace("</body>", f"{navigation_script}</body>")


def render_landing_page() -> None:
    st.html(_load_landing_markup(), unsafe_allow_javascript=True)
