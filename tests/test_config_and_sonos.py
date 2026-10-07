import os
import unittest
from unittest.mock import patch

from streamer.config import Config
from tools.sonos_play import didl_for, soap_body


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.icecast_mount, "/stream.mp3")
        self.assertEqual(cfg.audio_mode, "pipewire")

    def test_env_overrides_and_mount_normalised(self):
        env = {"ICECAST_MOUNT": "live.mp3", "AUDIO_MODE": "direct", "ICECAST_PORT": "9000"}
        with patch.dict(os.environ, env):
            cfg = Config.from_env()
        self.assertEqual(cfg.icecast_mount, "/live.mp3")
        self.assertEqual(cfg.audio_mode, "direct")
        self.assertEqual(cfg.icecast_port, 9000)
        self.assertIn(":9000/live.mp3", cfg.icecast_source_url)


class SonosSoapTest(unittest.TestCase):
    def test_didl_points_at_stream(self):
        didl = didl_for("http://192.168.1.20:8000/stream.mp3")
        self.assertIn("http://192.168.1.20:8000/stream.mp3", didl)
        self.assertIn("audioBroadcast", didl)

    def test_didl_escapes_url(self):
        didl = didl_for("http://pi:8000/stream.mp3?a=1&b=2")
        self.assertIn("a=1&amp;b=2", didl)

    def test_soap_body_is_well_formed_envelope(self):
        body = soap_body("Play", "<InstanceID>0</InstanceID>").decode()
        self.assertIn("<u:Play", body)
        self.assertIn("AVTransport:1", body)


if __name__ == "__main__":
    unittest.main()
