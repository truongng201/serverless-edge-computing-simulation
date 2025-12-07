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
        Distribute edge nodes in a grid pattern across the map, CENTER-FIRST.
        
        Strategy:
        - Calculate optimal grid dimensions (cols x rows) for total_nodes
        - Generate all cell center positions
        - Sort cells by distance from map center (closest first)
        - Assign nodes to sorted cells (node 1 -> center, then spread outward)
        
        Example for 5 nodes on 1800x1200 map (3x2 grid):
        - Node 1: Center cell
        - Nodes 2-5: Spread outward from center
        
        This ensures central areas (higher traffic) get coverage first.
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
        
        # Map center
        map_center_x = self.MAP_WIDTH_PX / 2
        map_center_y = self.MAP_HEIGHT_PX / 2
        
        # Generate all cell positions and sort by distance from center
        cells = []
        for r in range(rows):
            for c in range(cols):
                cx = self.MARGIN_PX + c * cell_width + cell_width / 2
                cy = self.MARGIN_PX + r * cell_height + cell_height / 2
                dist = math.hypot(cx - map_center_x, cy - map_center_y)
                cells.append((dist, cx, cy, r, c))
        
        # Sort by distance from center (closest first)
        cells.sort(key=lambda x: x[0])
        
        # Take only the first total_nodes cells
        cells = cells[:total_nodes]
        
        # Get position for this node index
        if idx < len(cells):
            _, x, y, _, _ = cells[idx]
        else:
            # Fallback if index out of range
            x = map_center_x
            y = map_center_y
        
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
        
        # Estimate total nodes from node_id pattern (e.g., edge_005 suggests ~5 nodes)
        match = re.search(r'(\d+)', node_id)
        estimated_total = 5  # Default
        if match:
            idx = int(match.group(1))
            # Use the node index as estimate (e.g., edge_005 = 5 nodes total)
            estimated_total = max(idx, 5)
        
        # Use GRID-BASED placement for even distribution across map
        # Each edge node covers approximately equal area
        self.edge_node_info = EdgeNodeInfo(
            node_id=node_id,
            endpoint=self.node_data.get("endpoint"),
            location=self._grid_based_location(node_id, total_nodes=estimated_total),
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
