import time
import random
import math
import re

from shared import InvalidDataException
from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.models import EdgeNodeInfo, NodeMetrics
from config import Config


class RegisterEdgeNodeController:
    """
    Controller for registering edge nodes with the scheduler.
    
    Edge node placement strategies:
    1. Grid-based (default): Divide map into grid cells, place node at cell center
    2. Circle-based: Evenly space nodes in a circle around central node
    3. Random: Legacy random placement
    """
    
    # Map dimensions in pixels (from TaxiD viewport config)
    MAP_WIDTH_PX = getattr(Config, 'TAXID_VIEWPORT_WIDTH_PX', 1800)
    MAP_HEIGHT_PX = getattr(Config, 'TAXID_VIEWPORT_HEIGHT_PX', 1200)
    MARGIN_PX = getattr(Config, 'TAXID_VIEWPORT_MARGIN_PX', 80)
    
    def __init__(self, scheduler: Scheduler, node_data: dict):
        self.scheduler = scheduler
        self.node_data = node_data
        self.node_metrics = None
        self.edge_node_info = None
        self._validate_node_data()

    def _validate_node_data(self):
        if not self.node_data or "node_id" not in self.node_data or "endpoint" not in self.node_data:
            raise InvalidDataException("Invalid node data")
    
    def _get_edge_index_from_id(self, node_id: str) -> int:
        """Extract numeric index from node_id like 'edge_001' -> 0, 'edge_002' -> 1"""
        match = re.search(r'(\d+)', node_id)
        if match:
            return int(match.group(1)) - 1  # 0-indexed
        return len(self.scheduler.edge_nodes)  # Fallback: use current count
    
    def _grid_based_location(self, node_id: str, total_nodes: int = 10):
        """
        Distribute edge nodes in a grid pattern across the map.
        
        Strategy:
        - Calculate optimal grid dimensions (cols x rows) for total_nodes
        - Generate all cell center positions
        - Pick cells using a farthest-point strategy (max-min distance) to ensure
          early nodes are well-separated (avoids clumping near one area).
        - Anchor the first cell near the current central node location (if known),
          otherwise use the map center as anchor.
        
        Example for 8 nodes:
        - Node 1: near central node
        - Node 2..N: progressively cover farthest remaining areas
        
        This is deterministic and produces a much more even spatial distribution
        for arbitrary N (including when EXPECTED_EDGE_NODES is not perfectly set).
        """
        idx = self._get_edge_index_from_id(node_id)
        
        # Calculate grid dimensions based on total nodes
        aspect_ratio = self.MAP_WIDTH_PX / self.MAP_HEIGHT_PX  # ~1.5
        rows = max(1, round(math.sqrt(total_nodes / aspect_ratio)))
        cols = max(1, math.ceil(total_nodes / rows))
        
        while rows * cols < total_nodes:
            cols += 1
        
        # Calculate cell dimensions (usable area excludes margins)
        usable_width = self.MAP_WIDTH_PX - 2 * self.MARGIN_PX
        usable_height = self.MAP_HEIGHT_PX - 2 * self.MARGIN_PX
        
        cell_width = usable_width / cols
        cell_height = usable_height / rows
        
        # Anchor: use current central node location if available; else map center.
        # NOTE: scheduler.central_node is a dict (see Scheduler.__init__), so we
        # must use item access, not attribute access. The previous getattr-based
        # check silently fell through to map center every time.
        map_center_x = self.MAP_WIDTH_PX / 2
        map_center_y = self.MAP_HEIGHT_PX / 2
        anchor_x = map_center_x
        anchor_y = map_center_y
        try:
            central = getattr(self.scheduler, "central_node", None)
            loc = None
            if isinstance(central, dict):
                loc = central.get("location")
            elif central is not None:
                loc = getattr(central, "location", None)
            if isinstance(loc, dict):
                anchor_x = float(loc.get("x", anchor_x))
                anchor_y = float(loc.get("y", anchor_y))
        except Exception:
            anchor_x, anchor_y = map_center_x, map_center_y
        
        # Generate all cell positions
        cells = []  # (x, y)
        for r in range(rows):
            for c in range(cols):
                cx = self.MARGIN_PX + c * cell_width + cell_width / 2
                cy = self.MARGIN_PX + r * cell_height + cell_height / 2
                cells.append((cx, cy))

        def dist(p1, p2):
            return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

        # Choose up to total_nodes representative cells using farthest-point sampling.
        # 1) start near anchor (central node)
        # 2) iteratively pick the point maximizing min-distance to already chosen points
        remaining = cells[:]
        start = min(remaining, key=lambda p: dist(p, (anchor_x, anchor_y)))
        chosen = [start]
        remaining.remove(start)

        while remaining and len(chosen) < total_nodes:
            def score(p):
                return min(dist(p, q) for q in chosen)

            # Deterministic tie-break: prefer lower x then lower y
            next_p = max(remaining, key=lambda p: (score(p), -p[0], -p[1]))
            chosen.append(next_p)
            remaining.remove(next_p)

        # Get position for this node index
        if idx < len(chosen):
            x, y = chosen[idx]
        else:
            x, y = anchor_x, anchor_y
        
        return {'x': x, 'y': y}
    
    def _random_location_around_central(self, central_node_location, min_distance=100, max_distance=500):
        """Legacy random placement (not recommended for experiments)"""
        angle = random.uniform(0, 2 * math.pi)
        
        min_radius_squared = min_distance * min_distance
        max_radius_squared = max_distance * max_distance
        
        radius_squared = random.uniform(min_radius_squared, max_radius_squared)
        radius = math.sqrt(radius_squared)

        x = central_node_location.get('x', 0) + radius * math.cos(angle)
        y = central_node_location.get('y', 0) + radius * math.sin(angle)
        
        return {'x': x, 'y': y}

    def _mapping_node_data(self):
        self.node_metrics = NodeMetrics(
            node_id=self.node_data.get("node_id"),
            cpu_usage=0.0,
            memory_usage=0.0,
            memory_total=0,
            running_container=0,
            warm_container=0,
            active_requests=0,
            total_requests=0,
            response_time_avg=0.0,
            energy_consumption=0.0,
            load_average=[],
            network_io={},
            disk_io={},
            timestamp=0,
            uptime=0
        )
        node_id = self.node_data.get('node_id')

        # Dynamic total_nodes: Config.EXPECTED_TOTAL_EDGE_NODES is evaluated once at
        # module import, so it cannot reflect env changes made after the central
        # process started (e.g. run_experiments.py setting EXPECTED_EDGE_NODES for
        # its own process). We take the max of the configured hint and the
        # currently-registered fleet size (+1 for the node being added) so the
        # grid always has enough cells for `idx` to fall inside `chosen`.
        # For taxiD datasets `_spread_existing_edge_nodes` will re-place everyone
        # using the real count after dataset load anyway, but using a sensible
        # value here keeps registration-time placement coherent for non-taxiD
        # datasets and for any code that inspects locations pre-dataset.
        current_count = len(getattr(self.scheduler, "edge_nodes", {}) or {})
        total_nodes = max(
            int(getattr(Config, "EXPECTED_TOTAL_EDGE_NODES", 10)),
            current_count + (0 if node_id in (self.scheduler.edge_nodes or {}) else 1),
        )
        
        # Use GRID-BASED placement for even distribution across map
        # Each edge node covers approximately equal area
        self.edge_node_info = EdgeNodeInfo(
            node_id=node_id,
            endpoint=self.node_data.get("endpoint"),
            location=self._grid_based_location(node_id, total_nodes=total_nodes),
            system_info=self.node_data.get("system_info", {}),
            last_heartbeat=time.time(),
            metrics_info=self.node_metrics,
            coverage=self.node_data.get("coverage", 300.0)
        )
        
    def _register_edge_node(self):
        self.scheduler.register_edge_node(self.edge_node_info)

    def execute(self):
        self._mapping_node_data()
        self._register_edge_node()
