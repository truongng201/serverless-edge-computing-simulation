#!/usr/bin/env python3
"""
Web deployment entry point for the Serverless Edge Computing Simulation.

Starts the central node in simulated mode (no Docker required) and
auto-registers virtual edge nodes so the system is ready to use
without running separate edge node processes.

Usage:
    python web_start.py
    PORT=8080 python web_start.py

Environment variables (all optional):
    PORT                     - HTTP port (default: 8000)
    EXECUTION_MODE           - forced to "simulated" by this script
    EXPECTED_EDGE_NODES      - number of virtual edge nodes to register (default: 10)
    TDRIVE_ARTIFACT_DIR      - path to GRU model artifacts
    LOG_LEVEL                - INFO | DEBUG | WARNING (default: INFO)
"""

import os
import sys
import time
import math
import logging

# ── Force simulated mode BEFORE any project imports ──────────────────────────
os.environ.setdefault("EXECUTION_MODE", "simulated")
os.environ.setdefault("EXPECTED_EDGE_NODES", "10")

# Add the serverless-sim directory to sys.path so imports resolve correctly
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Now import project code ───────────────────────────────────────────────────
from flask import Flask
from flask_cors import CORS

from central_node.control_layer.routes_module.central_route import (
    register_central_route,
    initialize_central_route,
    central_core_controller,
)
from central_node.control_layer.routes_module.central_route import central_core_controller as _get_controller
from central_node.control_layer.controller_module.register_edge_node_controller import RegisterEdgeNodeController
from config import Config


def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def _register_virtual_edge_nodes(scheduler, n: int):
    """
    Register N virtual edge nodes directly into the scheduler.

    These nodes have no real HTTP endpoints -- they exist only as
    in-memory scheduling targets.  The scheduler_agent health-check loop
    is disabled in simulated mode so they will never be evicted.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Registering {n} virtual edge nodes...")

    for i in range(1, n + 1):
        node_id = f"edge_{i:03d}"
        # Use a placeholder endpoint -- it is never called in simulated mode
        endpoint = f"virtual-edge-{i:03d}:0"

        try:
            controller = RegisterEdgeNodeController(
                scheduler,
                {
                    "node_id": node_id,
                    "endpoint": endpoint,
                    "coverage": 400.0,
                    "system_info": {
                        "platform": "virtual",
                        "cpu_count": 4,
                        "memory_total": 8 * 1024 * 1024 * 1024,  # 8 GB
                    },
                },
            )
            controller.execute()
            logger.debug(f"  Registered {node_id}")
        except Exception as e:
            logger.warning(f"  Failed to register {node_id}: {e}")

    logger.info(f"Virtual edge node registration complete: {len(scheduler.edge_nodes)} nodes active")


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    initialize_central_route()
    register_central_route(app)
    return app


def main():
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    port = int(os.environ.get("PORT", Config.CENTRAL_NODE_PORT))
    n_edges = int(os.environ.get("EXPECTED_EDGE_NODES", "10"))

    logger.info("=" * 60)
    logger.info("SERVERLESS EDGE COMPUTING SIMULATION  —  WEB MODE")
    logger.info("=" * 60)
    logger.info(f"Execution mode : {Config.EXECUTION_MODE}")
    logger.info(f"Virtual edges  : {n_edges}")
    logger.info(f"Port           : {port}")
    logger.info(f"Artifact dir   : {Config.TDRIVE_ARTIFACT_DIR}")
    logger.info("-" * 60)

    # Create Flask app (also initialises CentralCoreController / Scheduler)
    app = create_app()

    # Import module-level reference populated by initialize_central_route()
    from central_node.control_layer.routes_module.central_route import (
        central_core_controller as controller,
    )

    if controller is None:
        logger.error("CentralCoreController failed to initialise — aborting.")
        sys.exit(1)

    # Register virtual edge nodes now that the Scheduler singleton is ready
    _register_virtual_edge_nodes(controller.scheduler, n_edges)

    logger.info("-" * 60)
    logger.info(f"API base : http://0.0.0.0:{port}/api/v1/central")
    logger.info(f"Health   : http://0.0.0.0:{port}/api/v1/central/health")
    logger.info("=" * 60)

    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
