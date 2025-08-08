"""
Central Node Control Layer - Migration Module
Handles container migration between edge nodes
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from config import Config

class MigrationReason(Enum):
    HIGH_LOAD = "high_load"
    RESOURCE_SHORTAGE = "resource_shortage"
    NETWORK_LATENCY = "network_latency"
    NODE_FAILURE = "node_failure"
    LOAD_BALANCING = "load_balancing"

@dataclass
class MigrationRequest:
    container_id: str
    source_node_id: str
    target_node_id: str
    reason: MigrationReason
    priority: int  # 1-10, 10 being highest
    estimated_downtime: float  # seconds
    request_time: float

@dataclass
class MigrationStatus:
    request_id: str
    status: str  # pending, in_progress, completed, failed
    progress: float  # 0.0 to 1.0
    start_time: Optional[float]
    end_time: Optional[float]
    error_message: Optional[str]

class MigrationManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_migrations: Dict[str, MigrationRequest] = {}
        self.active_migrations: Dict[str, MigrationStatus] = {}
        self.migration_history: List[MigrationStatus] = []
        self.migration_threshold = Config.MIGRATION_THRESHOLD
        
    def should_migrate_container(self, container_info: Dict[str, Any], node_metrics: Dict[str, Any]) -> Optional[MigrationReason]:
        """Determine if a container should be migrated"""
        cpu_usage = node_metrics.get('cpu_usage', 0.0)
        memory_usage = node_metrics.get('memory_usage', 0.0)
        
        # Check CPU threshold
        if cpu_usage > self.migration_threshold:
            return MigrationReason.HIGH_LOAD
            
        # Check memory threshold
        if memory_usage > 0.9:
            return MigrationReason.RESOURCE_SHORTAGE
            
        # Check if node is unhealthy
        if node_metrics.get('health_status') == 'unhealthy':
            return MigrationReason.NODE_FAILURE
            
        return None
        
    def request_migration(self, container_id: str, source_node_id: str, 
                         target_node_id: str, reason: MigrationReason, 
                         priority: int = 5) -> str:
        """Request container migration"""
        request_id = f"migration_{int(time.time())}_{container_id}"
        
        migration_request = MigrationRequest(
            container_id=container_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            reason=reason,
            priority=priority,
            estimated_downtime=self._estimate_downtime(container_id),
            request_time=time.time()
        )
        
        self.pending_migrations[request_id] = migration_request
        
        # Create initial status
        self.active_migrations[request_id] = MigrationStatus(
            request_id=request_id,
            status="pending",
            progress=0.0,
            start_time=None,
            end_time=None,
            error_message=None
        )
        
        self.logger.info(f"Migration requested: {request_id} - {container_id} from {source_node_id} to {target_node_id}")
        return request_id
        
    def execute_migration(self, request_id: str) -> bool:
        """Execute a migration request"""
        if request_id not in self.pending_migrations:
            self.logger.error(f"Migration request not found: {request_id}")
            return False
            
        migration_request = self.pending_migrations[request_id]
        status = self.active_migrations[request_id]
        
        try:
            # Update status
            status.status = "in_progress"
            status.start_time = time.time()
            status.progress = 0.1
            
            # Step 1: Prepare target node
            self.logger.info(f"Preparing target node {migration_request.target_node_id}")
            if not self._prepare_target_node(migration_request):
                raise Exception("Failed to prepare target node")
            status.progress = 0.3
            
            # Step 2: Create container on target
            self.logger.info(f"Creating container on target node")
            if not self._create_container_on_target(migration_request):
                raise Exception("Failed to create container on target")
            status.progress = 0.5
            
            # Step 3: Transfer state/data
            self.logger.info(f"Transferring container state")
            if not self._transfer_container_state(migration_request):
                raise Exception("Failed to transfer container state")
            status.progress = 0.7
            
            # Step 4: Start container on target
            self.logger.info(f"Starting container on target node")
            if not self._start_container_on_target(migration_request):
                raise Exception("Failed to start container on target")
            status.progress = 0.9
            
            # Step 5: Stop and remove from source
            self.logger.info(f"Cleaning up source node")
            if not self._cleanup_source_node(migration_request):
                self.logger.warning("Failed to cleanup source node")
            
            # Migration completed
            status.status = "completed"
            status.progress = 1.0
            status.end_time = time.time()
            
            # Move to history
            self.migration_history.append(status)
            del self.pending_migrations[request_id]
            del self.active_migrations[request_id]
            
            self.logger.info(f"Migration completed successfully: {request_id}")
            return True
            
        except Exception as e:
            # Migration failed
            status.status = "failed"
            status.error_message = str(e)
            status.end_time = time.time()
            
            self.logger.error(f"Migration failed: {request_id} - {e}")
            
            # Cleanup on failure
            self._rollback_migration(migration_request)
            
            return False
            
    def _estimate_downtime(self, container_id: str) -> float:
        """Estimate migration downtime"""
        # Simple estimation - in practice this would be more sophisticated
        return 5.0  # 5 seconds default
        
    def _prepare_target_node(self, migration_request: MigrationRequest) -> bool:
        """Prepare target node for migration"""
        # TODO: Implement actual API call to target node
        # This would involve checking resources, preparing environment
        return True
        
    def _create_container_on_target(self, migration_request: MigrationRequest) -> bool:
        """Create container on target node"""
        # TODO: Implement actual container creation on target
        return True
        
    def _transfer_container_state(self, migration_request: MigrationRequest) -> bool:
        """Transfer container state/data to target"""
        # TODO: Implement state transfer (volumes, memory, etc.)
        return True
        
    def _start_container_on_target(self, migration_request: MigrationRequest) -> bool:
        """Start container on target node"""
        # TODO: Implement container startup on target
        return True
        
    def _cleanup_source_node(self, migration_request: MigrationRequest) -> bool:
        """Cleanup container from source node"""
        # TODO: Implement source cleanup
        return True
        
    def _rollback_migration(self, migration_request: MigrationRequest):
        """Rollback failed migration"""
        # TODO: Implement rollback logic
        self.logger.info(f"Rolling back migration for container {migration_request.container_id}")
        
    def get_migration_status(self, request_id: str) -> Optional[MigrationStatus]:
        """Get status of a migration"""
        return self.active_migrations.get(request_id)
        
    def get_pending_migrations(self) -> List[MigrationRequest]:
        """Get list of pending migrations"""
        return list(self.pending_migrations.values())
        
    def cancel_migration(self, request_id: str) -> bool:
        """Cancel a pending migration"""
        if request_id in self.pending_migrations:
            del self.pending_migrations[request_id]
            
            if request_id in self.active_migrations:
                status = self.active_migrations[request_id]
                status.status = "cancelled"
                status.end_time = time.time()
                del self.active_migrations[request_id]
                
            self.logger.info(f"Migration cancelled: {request_id}")
            return True
        return False
        
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get migration statistics"""
        total_migrations = len(self.migration_history)
        successful_migrations = len([m for m in self.migration_history if m.status == "completed"])
        failed_migrations = len([m for m in self.migration_history if m.status == "failed"])
        
        avg_downtime = 0.0
        if successful_migrations > 0:
            successful_downtimes = [
                (m.end_time - m.start_time) for m in self.migration_history 
                if m.status == "completed" and m.start_time and m.end_time
            ]
            if successful_downtimes:
                avg_downtime = sum(successful_downtimes) / len(successful_downtimes)
        
        return {
            "total_migrations": total_migrations,
            "successful_migrations": successful_migrations,
            "failed_migrations": failed_migrations,
            "success_rate": successful_migrations / total_migrations if total_migrations > 0 else 0,
            "average_downtime": avg_downtime,
            "pending_migrations": len(self.pending_migrations),
            "active_migrations": len(self.active_migrations)
        }
