import unittest

from streamer.config import Config
from streamer.ffmpeg_cmd import build_ffmpeg_command


class FfmpegCmdTest(unittest.TestCase):
    def test_pipewire_mode_captures_virtual_sink_monitor(self):
        cmd = build_ffmpeg_command(Config(audio_mode="pipewire"))
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("pulse", cmd)
        self.assertIn("sonos_stream.monitor", cmd)
        self.assertIn("libmp3lame", cmd)
        self.assertTrue(cmd[-1].endswith("@127.0.0.1:8000/stream.mp3"))

    def test_direct_mode_uses_alsa_device(self):
        cmd = build_ffmpeg_command(Config(audio_mode="direct", alsa_device="hw:3,0"))
        self.assertIn("alsa", cmd)
        self.assertIn("hw:3,0", cmd)

    def test_test_tone_needs_no_hardware(self):
        cmd = build_ffmpeg_command(Config(audio_mode="test_tone"))
        joined = " ".join(cmd)
        self.assertIn("lavfi", joined)
        self.assertIn("sine=frequency=440", joined)
        self.assertIn("-re", cmd)  # lavfi must be realtime-paced for Icecast

    def test_bitrate_is_configurable(self):
        cmd = build_ffmpeg_command(Config(audio_mode="test_tone", bitrate_kbps=320))
        self.assertIn("320k", cmd)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            build_ffmpeg_command(Config(audio_mode="carrier-pigeon"))


if __name__ == "__main__":
    unittest.main()
