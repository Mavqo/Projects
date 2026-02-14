"""Entry point for running Ralph Dashboard directly: python -m ralph_dashboard."""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ralph-dashboard",
        description="GUI Dashboard for Ralph-TUI AI Agent Orchestrator",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8420, help="Port to listen on (default: 8420)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    parser.add_argument("--projects-dir", default=None, help="Override projects directory path")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Override config if projects-dir specified
    if args.projects_dir:
        from .config import load_config, save_config
        cfg = load_config()
        cfg.projects_dir = args.projects_dir
        cfg.host = args.host
        cfg.port = args.port
        save_config(cfg)

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install with: pip install uvicorn", file=sys.stderr)
        sys.exit(1)

    print(f"Starting Ralph Dashboard at http://{args.host}:{args.port}")
    print(f"Press Ctrl+C to stop\n")

    uvicorn.run(
        "ralph_dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
