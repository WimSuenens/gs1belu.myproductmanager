"""Console entry point: `gs1belu-mpm-download-mcp` — launches the standalone Download
server over stdio."""

from __future__ import annotations

from .config import ServerConfig
from .server import build_download_server


def main() -> None:
    config = ServerConfig.from_env()
    server = build_download_server(config=config)
    server.run()


if __name__ == "__main__":
    main()
