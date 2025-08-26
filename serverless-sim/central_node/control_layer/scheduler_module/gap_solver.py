"""
GAP (Generalized Assignment Problem) Solver for Serverless Assignment
Implementation of the baseline algorithm from mobility-aware edge computing paper.
"""

import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class GAPAssignment:
    """Result of GAP optimization"""
    user_id: str
    target_node_id: str
    node_type: str  # 'edge' or 'central'
    utility_gain: float
    estimated_latency: float
    reasoning: str

@dataclass
class GAPConfig:
    """Configuration for GAP solver"""
    # Latency parameters (ms)
    upload_size_mb: float = 300.0
    ap_to_ap_delay_per_mb: float = 0.6
    ap_to_cloud_delay_per_mb: float = 6.0
    edge_processing_rate: float = 1.0  # ms/MB
    cloud_processing_rate: float = 0.05  # ms/MB
    cold_start_penalty: float = 300.0  # ms
    
    # GAP solver options
    solver_method: str = 'greedy'  # 'greedy' or 'ilp'
    enable_memory_constraints: bool = False
    debug_logging: bool = False

class GAPSolver:
    """
    GAP-based assignment solver for edge/central nodes.
    Uses existing scheduler data structures but applies GAP optimization.
    """
    
    def __init__(self, config: GAPConfig = None):
        self.config = config or GAPConfig()
        self.logger = logging.getLogger(__name__)
        
    def calculate_latency(self, user_location: Dict[str, float], 
                         node_info: Dict[str, Any], 
                         node_type: str, 
                         is_warm_start: bool = False) -> float:
        """
        Calculate latency using simplified version of paper formula.
        Uses distance as proxy for network delay.
        """
        try:
            # Communication delay: s(u,t) * d(v_u,t, v)
            user_x, user_y = user_location.get('x', 0), user_location.get('y', 0)
            node_x, node_y = node_info.get('location', {}).get('x', 0), node_info.get('location', {}).get('y', 0)
            
            # Distance-based delay (simplified)
            distance = math.sqrt((user_x - node_x)**2 + (user_y - node_y)**2)
            
            if node_type == 'cloud':
                # Cloud: higher base delay, no cold start
                comm_delay = self.config.upload_size_mb * self.config.ap_to_cloud_delay_per_mb
                proc_delay = self.config.upload_size_mb * self.config.cloud_processing_rate
                cold_start = 0
            else:
                # Edge: distance-based delay + processing
                comm_delay = self.config.upload_size_mb * (self.config.ap_to_ap_delay_per_mb * (distance / 100.0 + 1))
                proc_delay = self.config.upload_size_mb * self.config.edge_processing_rate
                cold_start = 0 if is_warm_start else self.config.cold_start_penalty
            
            total_latency = comm_delay + proc_delay + cold_start
            return max(0, total_latency)
            
        except Exception as e:
            self.logger.error(f"Error calculating latency: {e}")
            return 1000.0  # High penalty for errors
    
    def build_profit_matrix(self, users: Dict[str, Any], 
                           edge_nodes: Dict[str, Any], 
                           central_node: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Build profit matrix H[u][v] = utility gain when assigning user u to node v.
        H[u][v] = D(u, cloud, t) - D(u, v, t)
        """
        profits = {}
        
        # Virtual cloud node for comparison
        cloud_node = {
            'location': {'x': 0, 'y': 0},
            'node_id': 'cloud'
        }
        
        for user_id, user_info in users.items():
            profits[user_id] = {}
            user_location = user_info.get('location', {'x': 0, 'y': 0})
            
            # Calculate cloud latency (baseline)
            cloud_latency = self.calculate_latency(user_location, cloud_node, 'cloud')
            
            # Calculate profit for each edge node
            for node_id, node_info in edge_nodes.items():
                edge_latency = self.calculate_latency(user_location, node_info, 'edge')
                profits[user_id][node_id] = max(0, cloud_latency - edge_latency)
            
            # Calculate profit for central node
            if central_node:
                central_latency = self.calculate_latency(user_location, central_node, 'central')
                profits[user_id]['central_node'] = max(0, cloud_latency - central_latency)
            
            # Cloud has 0 profit (baseline)
            profits[user_id]['cloud'] = 0
            
        return profits
    
    def solve_gap_greedy(self, users: Dict[str, Any], 
                        edge_nodes: Dict[str, Any], 
                        central_node: Dict[str, Any]) -> List[GAPAssignment]:
        """
        Greedy approximation for GAP.
        For each user, assign to node with maximum utility gain.
        """
        profits = self.build_profit_matrix(users, edge_nodes, central_node)
        assignments = []
        
        # All available nodes
        all_nodes = {}
        for node_id, node_info in edge_nodes.items():
            all_nodes[node_id] = {'info': node_info, 'type': 'edge'}
        if central_node:
            all_nodes['central_node'] = {'info': central_node, 'type': 'central'}
        all_nodes['cloud'] = {'info': {'location': {'x': 0, 'y': 0}}, 'type': 'cloud'}
        
        for user_id, user_info in users.items():
            best_node_id = None
            best_profit = -1
            best_type = None
            
            # Find node with maximum profit
            for node_id in all_nodes:
                profit = profits[user_id].get(node_id, 0)
                if profit > best_profit:
                    best_profit = profit
                    best_node_id = node_id
                    best_type = all_nodes[node_id]['type']
            
            if best_node_id:
                # Calculate final latency
                user_location = user_info.get('location', {'x': 0, 'y': 0})
                node_info = all_nodes[best_node_id]['info']
                estimated_latency = self.calculate_latency(user_location, node_info, best_type)
                
                assignment = GAPAssignment(
                    user_id=user_id,
                    target_node_id=best_node_id,
                    node_type=best_type,
                    utility_gain=best_profit,
                    estimated_latency=estimated_latency,
                    reasoning=f"GAP greedy: max utility gain {best_profit:.2f}ms"
                )
                assignments.append(assignment)
                
                if self.config.debug_logging:
                    self.logger.info(f"GAP assignment: {user_id} -> {best_node_id} "
                                   f"(profit: {best_profit:.2f}, latency: {estimated_latency:.2f})")
        
        return assignments
    
    def solve_gap(self, users: Dict[str, Any], 
                  edge_nodes: Dict[str, Any], 
                  central_node: Dict[str, Any] = None) -> List[GAPAssignment]:
        """
        Main GAP solver entry point.
        """
        if not users:
            return []
        
        if not edge_nodes and not central_node:
            self.logger.warning("No nodes available for GAP assignment")
            return []
        
        try:
            if self.config.solver_method == 'ilp':
                # TODO: Implement ILP solver (OR-Tools)
                self.logger.info("ILP solver not implemented, using greedy")
                return self.solve_gap_greedy(users, edge_nodes, central_node)
            else:
                return self.solve_gap_greedy(users, edge_nodes, central_node)
                
        except Exception as e:
            self.logger.error(f"GAP solver error: {e}")
            return []
    
    def get_assignment_stats(self, assignments: List[GAPAssignment]) -> Dict[str, Any]:
        """Calculate statistics for GAP assignments"""
        if not assignments:
            return {
                'total_users': 0,
                'assigned_users': 0,
                'total_utility': 0,
                'avg_latency': 0,
                'edge_assignments': 0,
                'central_assignments': 0,
                'cloud_assignments': 0
            }
        
        stats = {
            'total_users': len(assignments),
            'assigned_users': len(assignments),
            'total_utility': sum(a.utility_gain for a in assignments),
            'avg_latency': sum(a.estimated_latency for a in assignments) / len(assignments),
            'edge_assignments': sum(1 for a in assignments if a.node_type == 'edge'),
            'central_assignments': sum(1 for a in assignments if a.node_type == 'central'),
            'cloud_assignments': sum(1 for a in assignments if a.node_type == 'cloud')
        }
        
        return stats
