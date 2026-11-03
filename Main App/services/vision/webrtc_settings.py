import os

DEFAULT_STUN_URL = "stun:stun.l.google.com:19302"


def _setting(name):
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets and name in secrets:
            return str(secrets[name])
    except Exception:
        return ""
    return ""


def stun_ice_servers():
    stun_url = _setting("STUN_URL") or DEFAULT_STUN_URL
    return [{"urls": [stun_url]}]


def build_ice_servers():
    ice_servers = list(stun_ice_servers())
    turn_url = _setting("TURN_URL")
    turn_username = _setting("TURN_USERNAME")
    turn_credential = _setting("TURN_CREDENTIAL")
    if turn_url and turn_username and turn_credential:
        ice_servers.append(
            {
                "urls": [turn_url],
                "username": turn_username,
                "credential": turn_credential,
            }
        )
    return ice_servers


def frontend_rtc_configuration():
    # Both peers need the same ICE servers. TURN is included only when
    # TURN_URL / TURN_USERNAME / TURN_CREDENTIAL are set in env or Streamlit
    # secrets. Credentials are not hardcoded in frontend source files.
    return {"iceServers": build_ice_servers()}


def server_rtc_configuration():
    return {"iceServers": build_ice_servers()}


def rtc_configuration():
    return server_rtc_configuration()


def media_stream_constraints():
    return {
        "video": {
            "width": {"ideal": 640},
            "height": {"ideal": 480},
            "frameRate": {"ideal": 15, "max": 24},
        },
        "audio": False,
    }


def turn_configured():
    return any("username" in server for server in build_ice_servers())
