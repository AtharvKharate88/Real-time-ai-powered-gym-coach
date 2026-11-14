"""Build WebRTC ICE server configuration from backend environment settings."""


def build_ice_servers(
    stun_url: str,
    turn_url: str = "",
    turn_username: str = "",
    turn_credential: str = "",
) -> list[dict[str, str | list[str]]]:
    """Return browser/aiortc-compatible ICE servers without partial TURN credentials."""
    ice_servers: list[dict[str, str | list[str]]] = []
    stun_urls = [url.strip() for url in stun_url.split(",") if url.strip()]
    if stun_urls:
        ice_servers.append({"urls": stun_urls if len(stun_urls) > 1 else stun_urls[0]})

    turn_urls = [url.strip() for url in turn_url.split(",") if url.strip()]
    turn_values = (bool(turn_urls), bool(turn_username.strip()), bool(turn_credential))
    if any(turn_values) and not all(turn_values):
        raise ValueError("TURN_URL, TURN_USERNAME, and TURN_CREDENTIAL must be configured together.")
    if turn_urls:
        ice_servers.append({
            "urls": turn_urls if len(turn_urls) > 1 else turn_urls[0],
            "username": turn_username,
            "credential": turn_credential,
        })
    return ice_servers
