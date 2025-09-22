"""
Central Node Control Layer - Scheduler Module
Handles scheduling decisions, load balancing, and request routing
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import time
from enum import Enum

from config import Config

from central_node.control_layer.scheduler_module.gap_solver import GAPSolver, GAPConfig
from central_node.control_layer.models import EdgeNodeInfo, UserNodeInfo, NodeMetrics


class SchedulingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    GEOGRAPHIC = "geographic"
    PREDICTIVE = "predictive"
    GAP_BASELINE = "gap_baseline"

@dataclass
class SchedulingDecision:
    target_node_id: str
    execution_time_estimate: float
    confidence: float
    reasoning: str

class Scheduler:
    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.edge_nodes: Dict[str, EdgeNodeInfo] = {}
        self.central_node = {
            "node_id": "central_node",
            "endpoint": "localhost:8000",
            "location": {"x": 600, "y": 400}, # default location
            "coverage": 0 # default coverage
        }
        self.user_nodes: Dict[str, UserNodeInfo] = {}
        self.round_robin_index = 0
        self.logger = logging.getLogger(__name__)
        
        # Initialize GAP solver
        self.gap_solver = GAPSolver(GAPConfig(debug_logging=True))
        self.simulation = False
        self.current_dataset = None
        self.current_step_id = None

        # Assignment runtime config (overridable via API)
        self.handoff_min_dwell_seconds: float = getattr(Config, 'HANDOFF_MIN_DWELL_SECONDS', 1.0)
        self.handoff_improvement_threshold: float = getattr(Config, 'HANDOFF_IMPROVEMENT_THRESHOLD', 0.1)
        self.assignment_scan_interval: float = getattr(Config, 'ASSIGNMENT_SCAN_INTERVAL', 0.5)
        self.load_aware_alpha: float = getattr(Config, 'LOAD_AWARE_ALPHA', 1.0)
        self.handoff_penalty: float = getattr(Config, 'PREDICTIVE_HANDOFF_COST', 0.05)

        # Handoff event log (recent)
        self.handoff_log: List[Dict[str, Any]] = []
        self.max_handoff_log = 200

        # Optional trajectory predictor and per-user history (injected by controller)
        self.trajectory_predictor = None
        self._user_history: Dict[str, List[Tuple[float, float]]] = {}

    def start_simulation(self):
        self.simulation = True
        
    def stop_simulation(self):
        self.simulation = False

    def get_edge_node(self, node_id: str) -> Optional[EdgeNodeInfo]:
        return self.edge_nodes.get(node_id)
    
    def update_edge_node(self, new_edge_node: EdgeNodeInfo):
        if new_edge_node.node_id not in self.edge_nodes:
            return
        self.edge_nodes[new_edge_node.node_id] = new_edge_node
        
    def update_user_node(self, user_id: str, new_location: Dict[str, float]) -> bool:
        if user_id not in self.user_nodes:
            return False

        user = self.user_nodes[user_id]
        user.location = new_location

        # Keep current assignment unless it's invalid/out of coverage.
        nearest_id, nearest_dist_m = self._node_assignment(new_location)
        current_id = user.assigned_node_id or None
        if not current_id:
            # First-time assignment
            user.assigned_node_id = nearest_id
            user.latency.distance = nearest_dist_m
        else:
            # Validate coverage for current edge; if invalid, fall back to nearest
            if current_id == 'central_node':
                # Distance to central for latency
                dist_px = self._calculate_distance(new_location, self.central_node["location"])
                user.latency.distance = dist_px * Config.DEFAULT_PIXEL_TO_METERS
            else:
                curr_node = self.edge_nodes.get(current_id)
                if not curr_node:
                    user.assigned_node_id = nearest_id
                    user.latency.distance = nearest_dist_m
                else:
                    dist_px = self._calculate_distance(new_location, curr_node.location)
                    # If out of coverage, switch immediately to nearest
                    if dist_px > curr_node.coverage:
                        user.assigned_node_id = nearest_id
                        user.latency.distance = nearest_dist_m
                    else:
                        user.latency.distance = dist_px * Config.DEFAULT_PIXEL_TO_METERS
        user.last_updated = time.time()
        # Append to trajectory history
        try:
            hist = self._user_history.get(user_id, [])
            hist.append((new_location['x'], new_location['y']))
            if len(hist) > 10:
                hist = hist[-10:]
            self._user_history[user_id] = hist
        except Exception:
            pass
        
        return True
    
    def get_central_node_info(self) -> Dict[str, Any]:
        return self.central_node
    
    def set_scheduling_strategy(self, strategy: SchedulingStrategy):
        """Change the scheduling strategy"""
        # Allow string input for convenience
        if isinstance(strategy, str):
            try:
                strategy = SchedulingStrategy(strategy)
            except Exception:
                self.logger.warning(f"Unknown strategy '{strategy}', fallback to round_robin")
                strategy = SchedulingStrategy.ROUND_ROBIN
        self.strategy = strategy
        self.logger.info(f"Scheduling strategy changed to: {self.strategy.value}")
        
    def get_scheduling_strategy(self) -> str:
        """Get current scheduling strategy"""
        return self.strategy.value

    def set_assignment_config(self, **kwargs):
        """Update handoff/assignment runtime parameters."""
        if 'handoff_min_dwell_seconds' in kwargs:
            self.handoff_min_dwell_seconds = float(kwargs['handoff_min_dwell_seconds'])
        if 'handoff_improvement_threshold' in kwargs:
            self.handoff_improvement_threshold = float(kwargs['handoff_improvement_threshold'])
        if 'assignment_scan_interval' in kwargs:
            self.assignment_scan_interval = float(kwargs['assignment_scan_interval'])
        if 'load_aware_alpha' in kwargs:
            self.load_aware_alpha = float(kwargs['load_aware_alpha'])
        self.logger.info(
            f"Assignment config updated: dwell={self.handoff_min_dwell_seconds}s, "
            f"threshold={self.handoff_improvement_threshold}, scan={self.assignment_scan_interval}s, "
            f"alpha={self.load_aware_alpha}"
        )

    
    def create_user_node(self, user_node: UserNodeInfo):
        self.user_nodes[user_node.user_id] = user_node
        # initialize last_updated if missing
        if not getattr(user_node, 'last_updated', None):
            user_node.last_updated = time.time()
        if not getattr(user_node, 'last_handoff', None):
            user_node.last_handoff = user_node.created_at
        # initialize history with current location
        try:
            self._user_history[user_node.user_id] = [(user_node.location['x'], user_node.location['y'])]
        except Exception:
            self._user_history[user_node.user_id] = []

    def register_edge_node(self, node_info: EdgeNodeInfo):
        if node_info.node_id in self.edge_nodes:
            raise Exception(f"Node {node_info.node_id} is already registered")
        self.edge_nodes[node_info.node_id] = node_info
        self.logger.info(f"Registered edge node: {node_info.node_id}")
        
    def unregister_edge_node(self, node_id: str):
        if node_id in self.edge_nodes:
            del self.edge_nodes[node_id]
            self.logger.info(f"Unregistered edge node: {node_id}")

    def update_node_metrics(self, node_id: str, new_metrics: NodeMetrics, system_info: Dict[str, Any], endpoint: str):
        if node_id in self.edge_nodes:
            self.edge_nodes[node_id].metrics_info = new_metrics
            self.edge_nodes[node_id].system_info = system_info
            self.edge_nodes[node_id].last_heartbeat = time.time()
        else:
            self.register_edge_node(EdgeNodeInfo(
                node_id=node_id,
                endpoint=endpoint,
                location={"x": 0.0, "y": 0.0},
                system_info=system_info,
                last_heartbeat=time.time(),
                metrics_info=new_metrics,
                coverage=300.0
            ))

    def schedule_request(self, request_data: Dict[str, Any]) -> Optional[SchedulingDecision]:
        """Schedule a request to the best available edge node"""
        available_nodes = []
        
        if not available_nodes:
            self.logger.warning("No healthy edge nodes available")
            return None
            
        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._schedule_round_robin(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.LEAST_LOADED:
            return self._schedule_least_loaded(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.GEOGRAPHIC:
            return self._schedule_geographic(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.PREDICTIVE:
            return self._schedule_predictive(available_nodes, request_data)
        elif self.strategy == SchedulingStrategy.GAP_BASELINE:
            return self._schedule_gap_baseline(available_nodes, request_data)
        else:
            return self._schedule_round_robin(available_nodes, request_data)

    def _schedule_round_robin(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Round robin scheduling"""
        if self.round_robin_index >= len(nodes):
            self.round_robin_index = 0
            
        selected_node = nodes[self.round_robin_index]
        self.round_robin_index += 1
        
        return SchedulingDecision(
            target_node_id=selected_node.node_id,
            execution_time_estimate=1.0,  # Default estimate
            confidence=0.8,
            reasoning="Round robin selection"
        )
        
    def _schedule_least_loaded(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Least loaded scheduling"""
        selected_node = min(nodes, key=lambda n: n.current_load)
        
        return SchedulingDecision(
            target_node_id=selected_node.node_id,
            execution_time_estimate=1.0 / (1.0 - selected_node.current_load),
            confidence=0.9,
            reasoning=f"Least loaded node (load: {selected_node.current_load:.2f})"
        )
        
    def _schedule_geographic(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Geographic-based scheduling"""
        # For now, just use least loaded
        # TODO: Implement actual geographic distance calculation
        return self._schedule_least_loaded(nodes, request_data)
        
    def _schedule_predictive(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """Predictive scheduling using ML models"""
        # For now, just use least loaded
        # TODO: Integrate with prediction module
        return self._schedule_least_loaded(nodes, request_data)
    
    def _classify_nodes(self):
        classified_nodes = {
            "healthy": set(),
            "warning": set(),
            "unhealthy": set()
        }

        for node in self.edge_nodes.values():
            if node.metrics_info.cpu_usage < Config.EDGE_NODE_WARNING_CPU_THRESHOLD and \
               node.metrics_info.memory_usage < Config.EDGE_NODE_WARNING_CPU_THRESHOLD:
                classified_nodes["healthy"].add(node.node_id)
            elif node.metrics_info.cpu_usage < Config.EDGE_NODE_UNHEALTHY_CPU_THRESHOLD and \
                 node.metrics_info.memory_usage < Config.EDGE_NODE_UNHEALTHY_MEMORY_THRESHOLD:
                classified_nodes["warning"].add(node.node_id)
            else:
                classified_nodes["unhealthy"].add(node.node_id)

        return classified_nodes
        
    def get_cluster_status(self) -> Dict[str, Any]:
        current_time = time.time()
        total_load = sum(node.metrics_info.cpu_usage for node in self.edge_nodes.values())
        average_load = total_load / len(self.edge_nodes) if self.edge_nodes else 0
        all_nodes_info = []
        
        classified_nodes = self._classify_nodes()

        for node in self.edge_nodes.values():
            last_seen = current_time - node.last_heartbeat
            node_status = "unidentified"
            if node.node_id in classified_nodes["healthy"]:
                node_status = "healthy"
            elif node.node_id in classified_nodes["warning"]:
                node_status = "warning"
            else:
                node_status = "unhealthy"
            node_info = {
                "node_id": node.node_id,
                "system_info": node.system_info,
                "location": node.location,
                "last_seen": last_seen,
                "endpoint": node.endpoint,
                "metrics": node.metrics_info,
                "coverage": node.coverage,
                "status": node_status
            }
            
            all_nodes_info.append(node_info)
            
        return {
            "total_nodes": len(self.edge_nodes),
            "average_load": average_load,
            "edge_nodes_info": all_nodes_info,
            "healthy_node_count": len(classified_nodes["healthy"]),
            "healthy_node_list": list(classified_nodes["healthy"]),
            "unhealthy_node_count": len(classified_nodes["unhealthy"]),
            "unhealthy_node_list": list(classified_nodes["unhealthy"]),
            "warning_node_count": len(classified_nodes["warning"]),
            "warning_node_list": list(classified_nodes["warning"]),
        }
    
    def _node_assignment(self, user_location: Dict[str, float]) -> Tuple[str, float]:
        min_distance = self._calculate_distance(user_location, self.central_node["location"])
        nearest_node_id = "central_node"  # default to central node
        
        # Check all edge nodes
        for node_id, edge_node in self.edge_nodes.items():
            distance = self._calculate_distance(user_location, edge_node.location)
            if distance < min_distance and distance <= edge_node.coverage:
                min_distance = distance
                nearest_node_id = node_id

        return nearest_node_id, min_distance * Config.DEFAULT_PIXEL_TO_METERS

    def _calculate_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        """Calculate Euclidean distance between two locations"""
        dx = location1["x"] - location2["x"]
        dy = location1["y"] - location2["y"]
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def _schedule_gap_baseline(self, nodes: List[EdgeNodeInfo], request_data: Dict[str, Any]) -> SchedulingDecision:
        """GAP-based scheduling using utility optimization"""
        user_id = request_data.get('user_id', 'unknown_user')
        user_location = request_data.get('user_location', {'x': 0, 'y': 0})
        
        try:
            # Prepare data for GAP solver
            users = {
                user_id: {
                    'location': user_location,
                    'data_size': request_data.get('data_size', 300)  # MB
                }
            }
            
            # Convert edge nodes to GAP format
            edge_nodes = {}
            for node in nodes:
                edge_nodes[node.node_id] = {
                    'node_id': node.node_id,
                    'location': node.location,
                    'endpoint': node.endpoint,
                    'metrics': node.metrics_info.__dict__ if node.metrics_info else {}
                }
            
            # Run GAP solver
            assignments = self.gap_solver.solve_gap(users, edge_nodes, self.central_node)
            
            if assignments and len(assignments) > 0:
                assignment = assignments[0]  # Get assignment for our user
                
                # Log GAP statistics
                stats = self.gap_solver.get_assignment_stats(assignments)
                self.logger.info(f"GAP assignment stats: {stats}")
                
                return SchedulingDecision(
                    target_node_id=assignment.target_node_id,
                    execution_time_estimate=assignment.estimated_latency / 1000.0,  # Convert to seconds
                    confidence=0.9,  # High confidence in GAP optimization
                    reasoning=assignment.reasoning
                )
            else:
                # Fallback to round robin if GAP fails
                self.logger.warning("GAP assignment failed, falling back to round robin")
            return self._schedule_round_robin(nodes, request_data)
            
        except Exception as e:
            self.logger.error(f"GAP scheduling error: {e}")
            # Fallback to round robin
            return self._schedule_round_robin(nodes, request_data)

    # --- Online assignment / handoff helpers ---
    def _score_node_distance(self, user_location: Dict[str, float], node: Optional[EdgeNodeInfo]) -> float:
        # Lower is better
        if node is None:
            # central node
            dist = self._calculate_distance(user_location, self.central_node["location"])
            return dist
        return self._calculate_distance(user_location, node.location)

    def _score_node_load_aware(self, user_location: Dict[str, float], node: Optional[EdgeNodeInfo]) -> float:
        # Lower is better; include CPU load factor
        base = self._score_node_distance(user_location, node)
        if node is None:
            load = 0.5  # arbitrary for central
        else:
            try:
                load = (node.metrics_info.cpu_usage or 0) / 100.0
            except Exception:
                load = 0.0
        return base * (1.0 + self.load_aware_alpha * load)

    def _estimate_available_memory_mb(self, node: Optional[EdgeNodeInfo]) -> float:
        if node is None:
            return float('inf')
        metrics = getattr(node, 'metrics_info', None)
        if not metrics:
            return float('inf')
        try:
            total_bytes = float(getattr(metrics, 'memory_total', 0) or 0)
            usage_percent = float(getattr(metrics, 'memory_usage', 0) or 0) / 100.0
            if total_bytes <= 0:
                return float('inf')
            available_bytes = total_bytes * max(0.0, 1.0 - usage_percent)
            return available_bytes / (1024 * 1024)
        except Exception:
            return float('inf')

    def _estimate_warm_probability(self, node: Optional[EdgeNodeInfo]) -> float:
        if node is None:
            return getattr(Config, 'PREDICTIVE_WARM_BASE_PROB', 0.2)
        metrics = getattr(node, 'metrics_info', None)
        if not metrics:
            return getattr(Config, 'PREDICTIVE_WARM_BASE_PROB', 0.2)
        try:
            warm = float(getattr(metrics, 'warm_container', 0) or 0)
            running = float(getattr(metrics, 'running_container', 0) or 0)
            total = warm + running
            if total <= 0:
                return getattr(Config, 'PREDICTIVE_WARM_BASE_PROB', 0.2)
            return max(0.0, min(1.0, warm / total))
        except Exception:
            return getattr(Config, 'PREDICTIVE_WARM_BASE_PROB', 0.2)

    def _compute_expected_latency(self, user: UserNodeInfo, node: Optional[EdgeNodeInfo], predicted_location: Dict[str, float]) -> Dict[str, float]:
        data_size = getattr(user.latency, 'data_size', None)
        if not data_size:
            data_size = getattr(Config, 'PREDICTIVE_DEFAULT_DATA_SIZE_BYTES', 512 * 1024)
        bandwidth = getattr(user.latency, 'bandwidth', None)
        if not bandwidth:
            bandwidth = 500.0  # bytes per ms fallback
        try:
            bandwidth = float(bandwidth)
        except Exception:
            bandwidth = 500.0
        metrics = getattr(node, 'metrics_info', None) if node else None
        if metrics:
            try:
                cpu_usage = float(getattr(metrics, 'cpu_usage', 0) or 0) / 100.0
                bandwidth *= max(0.1, 1.0 - 0.5 * cpu_usage)
            except Exception:
                pass
        distance_px = self._calculate_distance(predicted_location, node.location if node else self.central_node["location"])
        distance_m = distance_px * Config.DEFAULT_PIXEL_TO_METERS
        propagation_speed = getattr(Config, 'DEFAULT_PROPAGATION_SPEED_IN_METERS', 3 * 10**8)
        try:
            propagation_delay = (distance_m / max(propagation_speed, 1)) * 1000.0
        except Exception:
            propagation_delay = 0.0
        transmission_delay = data_size / max(bandwidth, 1.0)
        warm_prob = self._estimate_warm_probability(node)
        base_proc = getattr(user.latency, 'computation_delay', 0.0)
        if base_proc <= 0:
            base_proc = data_size / 1024.0  # approx ms
        cold_penalty = getattr(Config, 'PREDICTIVE_COLD_START_MS', 300)
        processing_delay = warm_prob * base_proc + (1.0 - warm_prob) * (cold_penalty + base_proc)
        total_latency = propagation_delay + transmission_delay + processing_delay
        return {
            'total_latency': total_latency,
            'communication_delay': propagation_delay + transmission_delay,
            'processing_delay': processing_delay,
            'warm_probability': warm_prob,
            'distance_meters': distance_m,
            'transmission_delay': transmission_delay
        }

    def _predictive_candidate_scores(self, user: UserNodeInfo, predicted_location: Dict[str, float]) -> List[Dict[str, Any]]:
        required_mem_mb = getattr(user, 'memory_requirement', Config.PREDICTIVE_DEFAULT_MEMORY_REQUIREMENT_MB * 1024 * 1024)
        try:
            required_mem_mb = float(required_mem_mb) / (1024 * 1024)
        except Exception:
            required_mem_mb = Config.PREDICTIVE_DEFAULT_MEMORY_REQUIREMENT_MB

        cloud_metrics = self._compute_expected_latency(user, None, predicted_location)
        cloud_latency = cloud_metrics['total_latency']

        candidates: List[Dict[str, Any]] = []
        current_node_id = user.assigned_node_id or 'central_node'

        def build_candidate(node_id: str, node: Optional[EdgeNodeInfo], node_type: str) -> Optional[Dict[str, Any]]:
            available_mb = self._estimate_available_memory_mb(node)
            if available_mb < required_mem_mb - 1e-6 and node_id != current_node_id:
                return None
            metrics = self._compute_expected_latency(user, node, predicted_location)
            utility = cloud_latency - metrics['total_latency']
            cpu_penalty = 0.0
            if node and getattr(node, 'metrics_info', None):
                cpu = float(getattr(node.metrics_info, 'cpu_usage', 0) or 0) / 100.0
                cpu_penalty = self.load_aware_alpha * cpu
            handoff_penalty = 0.0
            if node_id != (user.assigned_node_id or 'central_node'):
                handoff_penalty = self.handoff_penalty
            score = (utility / max(required_mem_mb, 1.0)) - cpu_penalty - handoff_penalty
            return {
                'node_id': node_id,
                'node_type': node_type,
                'score': score,
                'utility': utility,
                'latency': metrics['total_latency'],
                'memory_required_mb': required_mem_mb,
                'memory_available_mb': available_mb,
                'cpu_penalty': cpu_penalty,
                'handoff_penalty': handoff_penalty,
                'details': metrics,
                'cloud_latency': cloud_latency
            }

        for node_id, node in self.edge_nodes.items():
            candidate = build_candidate(node_id, node, 'edge')
            if candidate:
                candidates.append(candidate)

        # Include central node as fallback
        central_candidate = build_candidate('central_node', None, 'central')
        if central_candidate:
            candidates.append(central_candidate)

        candidates.sort(key=lambda item: item['score'], reverse=True)
        return candidates

    def _best_node_for_user(self, user: UserNodeInfo, user_location: Dict[str, float], strategy: SchedulingStrategy) -> Tuple[str, float]:
        # returns (node_id, score). central node id is 'central_node'
        if strategy == SchedulingStrategy.PREDICTIVE:
            candidates = self._predictive_candidate_scores(user, user_location)
            if not candidates:
                return 'central_node', float('inf')
            best = candidates[0]
            return best['node_id'], best['score']
        if strategy in (SchedulingStrategy.GEOGRAPHIC, SchedulingStrategy.ROUND_ROBIN, SchedulingStrategy.PREDICTIVE, SchedulingStrategy.GAP_BASELINE, SchedulingStrategy.LEAST_LOADED):
            # Implement two simple strategies: geographic (distance) and load-aware
            best_id = 'central_node'
            if strategy == SchedulingStrategy.LEAST_LOADED:
                best_score = self._score_node_load_aware(user_location, None)
            else:
                best_score = self._score_node_distance(user_location, None)

            for node_id, node in self.edge_nodes.items():
                # Only consider nodes within coverage
                if self._calculate_distance(user_location, node.location) > node.coverage:
                    continue
                score = self._score_node_load_aware(user_location, node) if strategy == SchedulingStrategy.LEAST_LOADED else self._score_node_distance(user_location, node)
                if score < best_score:
                    best_score = score
                    best_id = node_id
            return best_id, best_score
        # default fallback
        return 'central_node', self._score_node_distance(user_location, None)

    def maybe_reassign_user(self, user: UserNodeInfo) -> bool:
        """Re-evaluate assignment based on current strategy and location.
        Returns True if re-assigned.
        """
        try:
            now = time.time()
            # Dwell time to avoid thrashing
            last_handoff = getattr(user, 'last_handoff', user.created_at)
            if now - last_handoff < self.handoff_min_dwell_seconds:
                return False

            # Use predicted next location for PREDICTIVE strategy
            loc_for_assignment = user.location
            if self.strategy == SchedulingStrategy.PREDICTIVE and self.trajectory_predictor is not None:
                hist = self._user_history.get(user.user_id, [])
                if hist:
                    try:
                        px, py = self.trajectory_predictor.predict_next(hist)
                        loc_for_assignment = {'x': px, 'y': py}
                    except Exception:
                        loc_for_assignment = user.location

            current_id = user.assigned_node_id or 'central_node'

            if self.strategy == SchedulingStrategy.PREDICTIVE:
                candidates = self._predictive_candidate_scores(user, loc_for_assignment)
                if not candidates:
                    return False
                best_candidate = candidates[0]
                current_candidate = next((c for c in candidates if c['node_id'] == current_id), None)
                if current_candidate is None:
                    # Compute score for current node manually to compare
                    current_node = None if current_id == 'central_node' else self.edge_nodes.get(current_id)
                    metrics = self._compute_expected_latency(user, current_node, loc_for_assignment)
                    cloud_metrics = self._compute_expected_latency(user, None, loc_for_assignment)
                    utility = cloud_metrics['total_latency'] - metrics['total_latency']
                    cpu_penalty = 0.0
                    if current_node and getattr(current_node, 'metrics_info', None):
                        cpu = float(getattr(current_node.metrics_info, 'cpu_usage', 0) or 0) / 100.0
                        cpu_penalty = self.load_aware_alpha * cpu
                    base_mem = getattr(user, 'memory_requirement', Config.PREDICTIVE_DEFAULT_MEMORY_REQUIREMENT_MB * 1024 * 1024)
                    base_mem_mb = float(base_mem) / (1024 * 1024)
                    current_candidate = {
                        'node_id': current_id,
                        'score': (utility / max(base_mem_mb, 1.0)) - cpu_penalty,
                        'latency': metrics['total_latency'],
                        'details': metrics
                    }
                improvement = best_candidate['score'] - current_candidate['score']
                relative = improvement / max(abs(current_candidate['score']), 1e-6)
                if best_candidate['node_id'] != current_id and relative > self.handoff_improvement_threshold:
                    user.assigned_node_id = best_candidate['node_id']
                    target_id = best_candidate['node_id']
                    if target_id == 'central_node':
                        dist_px = self._calculate_distance(user.location, self.central_node["location"])
                    else:
                        dist_px = self._calculate_distance(user.location, self.edge_nodes[target_id].location)
                    user.latency.distance = dist_px * Config.DEFAULT_PIXEL_TO_METERS
                    user.latency.total_turnaround_time = best_candidate['latency']
                    user.latency.computation_delay = best_candidate['details']['processing_delay']
                    user.latency.transmission_delay = best_candidate['details']['transmission_delay']
                    user.latency.container_status = 'warm' if best_candidate['details']['warm_probability'] > 0.5 else 'cold'
                    user.predictive_debug = best_candidate
                    user.last_handoff = now
                    self.handoff_log.append({
                        'ts': now,
                        'user_id': user.user_id,
                        'from': current_id,
                        'to': target_id,
                        'improvement': relative,
                    })
                    if len(self.handoff_log) > self.max_handoff_log:
                        self.handoff_log = self.handoff_log[-self.max_handoff_log:]
                    self.logger.info(
                        f"User {user.user_id} predictive handoff: {current_id} -> {target_id} (relative_gain={relative:.2f})"
                    )
                    return True
                return False

            target_id, target_score = self._best_node_for_user(user, loc_for_assignment, self.strategy)
            current_node = None if current_id == 'central_node' else self.edge_nodes.get(current_id)
            if self._calculate_distance(user.location, self.central_node["location"]) > 1e9:  # defensive
                return False
            if self.strategy == SchedulingStrategy.LEAST_LOADED:
                current_score = self._score_node_load_aware(loc_for_assignment, current_node)
            else:
                current_score = self._score_node_distance(loc_for_assignment, current_node)
            improved = (current_score - target_score) / max(current_score, 1e-6)
            if target_id != current_id and improved > self.handoff_improvement_threshold:
                user.assigned_node_id = target_id
                if target_id == 'central_node':
                    dist_px = self._calculate_distance(user.location, self.central_node["location"])
                else:
                    dist_px = self._calculate_distance(user.location, self.edge_nodes[target_id].location)
                user.latency.distance = dist_px * Config.DEFAULT_PIXEL_TO_METERS
                user.last_handoff = now
                self.handoff_log.append({
                    'ts': now,
                    'user_id': user.user_id,
                    'from': current_id,
                    'to': target_id,
                    'improvement': improved,
                })
                if len(self.handoff_log) > self.max_handoff_log:
                    self.handoff_log = self.handoff_log[-self.max_handoff_log:]
                self.logger.info(f"User {user.user_id} handoff: {current_id} -> {target_id} (improvement={improved:.2f})")
                return True
            return False
        except Exception as e:
            self.logger.error(f"maybe_reassign_user error: {e}")
            return False
