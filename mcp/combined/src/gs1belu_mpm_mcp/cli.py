"""Console entry point: `gs1belu-mpm-mcp` — launches the composed server over stdio."""

from __future__ import annotations

from .config import ServerConfig
from .server import build_server
from .specs import load_effective_spec


def main() -> None:
    config = ServerConfig.from_env()
    upload_spec = load_effective_spec("upload", config.api_version, path_override_env="GS1BELU_UPLOAD_SPEC_PATH")
    download_spec = load_effective_spec("download", config.api_version, path_override_env="GS1BELU_DOWNLOAD_SPEC_PATH")
    server = build_server(upload_spec=upload_spec, download_spec=download_spec, config=config)
    server.run()


if __name__ == "__main__":
    main()
