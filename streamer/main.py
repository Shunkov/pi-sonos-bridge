"""Entry point: start the encoder, then serve the control API/UI."""
from __future__ import annotations

import signal

from .config import Config
from .manager import StreamManager
from .server import serve


def main() -> None:
    cfg = Config.from_env()
    if cfg.icecast_source_password == "changeme":
        print("WARNING: ICECAST_SOURCE_PASSWORD is still 'changeme' — set a real one (see .env.example)")
    manager = StreamManager(cfg)
    manager.start()

    def _shutdown(signum, frame):  # clean stop on SIGTERM (systemd)
        manager.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    serve(cfg, manager)


if __name__ == "__main__":
    main()
