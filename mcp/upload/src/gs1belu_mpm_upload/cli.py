"""Console entry point: `gs1belu-mpm-upload-mcp` — launches the standalone Upload
server over stdio."""

from __future__ import annotations

from .config import ServerConfig
from .server import build_upload_server
from .specs import load_effective_spec


def main() -> None:
    config = ServerConfig.from_env()
    upload_spec = load_effective_spec("upload", config.api_version, path_override_env="GS1BELU_UPLOAD_SPEC_PATH")
    server = build_upload_server(upload_spec=upload_spec, config=config)
    server.run()


if __name__ == "__main__":
    main()
