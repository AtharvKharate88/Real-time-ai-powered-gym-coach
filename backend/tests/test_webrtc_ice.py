import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from api.services.ice_config import build_ice_servers  # noqa: E402


class IceConfigurationTests(unittest.TestCase):
    def test_stun_server_is_used_when_turn_is_not_configured(self) -> None:
        self.assertEqual(
            build_ice_servers("stun:stun.example.test:3478"),
            [{"urls": "stun:stun.example.test:3478"}],
        )

    def test_turn_configuration_is_added_for_both_peers(self) -> None:
        self.assertEqual(
            build_ice_servers(
                "stun:stun.example.test:3478",
                "turn:relay.example.test:3478,turns:relay.example.test:5349",
                "temporary-user",
                "temporary-credential",
            ),
            [
                {"urls": "stun:stun.example.test:3478"},
                {
                    "urls": [
                        "turn:relay.example.test:3478",
                        "turns:relay.example.test:5349",
                    ],
                    "username": "temporary-user",
                    "credential": "temporary-credential",
                },
            ],
        )

    def test_partial_turn_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be configured together"):
            build_ice_servers(
                "stun:stun.example.test:3478",
                "turn:relay.example.test:3478",
                "temporary-user",
                "",
            )


if __name__ == "__main__":
    unittest.main()
