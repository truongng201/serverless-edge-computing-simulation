"""
Analytical warm-container pool for the simulated execution mode.

Models serverless container reuse with proper semantics:
- Pool is keyed by (node_id, function_id), not (user_id, node_id).
- Each entry has a TTL (keep-alive window). Entries past TTL are cold.
- Per-node capacity (MAX_WARM_PER_NODE) is enforced via LRU eviction.
- Central node has its own (much larger but finite) capacity.

A warm hit means: at the moment of invocation, there is a live container for
(function_id) at (node_id) within TTL. A miss means cold start, which inserts
a fresh entry (subject to capacity).

Clock: the pool is driven by the SIMULATION STEP, not wall-clock time. The
scheduler sets `now` (via set_now) at the start of each execution step, and all
methods default to that step counter. TTL is therefore measured in steps. This
keeps warm/cold decisions deterministic and aligned with the prewarm lead time
(also expressed in steps).
"""

from __future__ import annotations

import threading
import zlib
from collections import OrderedDict
from typing import Dict, Optional

from config import Config


class WarmPoolManager:
    def __init__(
        self,
        ttl_steps: Optional[float] = None,
        max_warm_per_edge: Optional[int] = None,
        max_warm_central: Optional[int] = None,
    ):
        self._ttl = float(ttl_steps if ttl_steps is not None else getattr(Config, "WARM_TTL_STEPS", 30))
        self._cap_edge = int(
            max_warm_per_edge if max_warm_per_edge is not None
            else getattr(Config, "MAX_WARM_PER_NODE", 32)
        )
        self._cap_central = int(
            max_warm_central if max_warm_central is not None
            else getattr(Config, "CENTRAL_MAX_CONCURRENT", 1024)
        )
        # node_id -> OrderedDict[function_id, last_used_step]
        # OrderedDict preserves LRU order: oldest at the front.
        self._pool: Dict[str, "OrderedDict[str, float]"] = {}
        self._lock = threading.RLock()

        # Simulation-step clock; updated by the scheduler each execution step.
        self.now: float = 0.0

        self.cold_starts = 0
        self.warm_hits = 0
        self.evictions = 0
        self.rejections = 0

    # ------------------------------------------------------------------ config
    def set_ttl(self, ttl_steps: float) -> None:
        """Set the keep-alive window (in steps). 0 disables keep-alive."""
        self._ttl = max(0.0, float(ttl_steps))

    def set_now(self, now: float) -> None:
        """Advance the simulation-step clock used for TTL decisions."""
        self.now = float(now)

    def _resolve_now(self, now: Optional[float]) -> float:
        return float(now) if now is not None else self.now

    def _capacity_for(self, node_id: str) -> int:
        if node_id == "central_node":
            return self._cap_central
        return self._cap_edge

    def _purge_expired(self, node_id: str, now: float) -> None:
        bucket = self._pool.get(node_id)
        if not bucket:
            return
        ttl = self._ttl
        # Remove from front while expired (front is oldest in LRU order).
        stale = []
        for fn_id, ts in bucket.items():
            if now - ts > ttl:
                stale.append(fn_id)
            else:
                break
        for fn_id in stale:
            bucket.pop(fn_id, None)

    # ------------------------------------------------------------------ lookups
    def is_warm(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Return True iff a live (within TTL) entry exists for (node, function)."""
        if not node_id or not function_id:
            return False
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return False
            self._purge_expired(node_id, now)
            return function_id in bucket

    def lookup(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Same as is_warm, but on hit promotes the entry to MRU and refreshes its step."""
        if not node_id or not function_id:
            return False
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return False
            self._purge_expired(node_id, now)
            if function_id in bucket:
                bucket.move_to_end(function_id, last=True)
                bucket[function_id] = now
                self.warm_hits += 1
                return True
            return False

    # ------------------------------------------------------------------ admit
    def admit(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Insert (or refresh) an entry. Evicts LRU if over capacity.

        Returns True if the entry was admitted, False if it was rejected
        (capacity 0 / negative — should not happen in normal config).
        """
        if not node_id or not function_id:
            return False
        cap = self._capacity_for(node_id)
        if cap <= 0:
            self.rejections += 1
            return False
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.setdefault(node_id, OrderedDict())
            self._purge_expired(node_id, now)
            if function_id in bucket:
                bucket.move_to_end(function_id, last=True)
                bucket[function_id] = now
                return True
            while len(bucket) >= cap:
                # popitem(last=False) -> LRU
                bucket.popitem(last=False)
                self.evictions += 1
            bucket[function_id] = now
            return True

    def admit_cold(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Cold-start admission: count as cold start and insert into pool."""
        admitted = self.admit(node_id, function_id, now)
        if admitted:
            self.cold_starts += 1
        return admitted

    def has_capacity(self, node_id: str, function_id: Optional[str] = None) -> bool:
        """True if (node, function) is already warm OR there is room.

        With LRU eviction enabled, a positive-capacity node can always admit a
        new entry (by evicting its least-recently-used one), so this returns
        True whenever capacity > 0.
        """
        cap = self._capacity_for(node_id)
        if cap <= 0:
            return False
        if function_id is None:
            return True
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return True
            self._purge_expired(node_id, self.now)
            return function_id in bucket or len(bucket) < cap or cap > 0

    # ------------------------------------------------------------------ stats
    def size(self, node_id: str, now: Optional[float] = None) -> int:
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return 0
            self._purge_expired(node_id, now)
            return len(bucket)

    def utilization(self, node_id: str, now: Optional[float] = None) -> float:
        cap = self._capacity_for(node_id)
        if cap <= 0:
            return 0.0
        return self.size(node_id, now) / float(cap)

    def reset(self) -> None:
        with self._lock:
            self._pool.clear()
            self.now = 0.0
            self.cold_starts = 0
            self.warm_hits = 0
            self.evictions = 0
            self.rejections = 0

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {
                node_id: dict(bucket) for node_id, bucket in self._pool.items()
            }

    def function_id_for_user(self, user_id: str) -> str:
        """Hash user_id into one of FUNCTION_NAME_BUCKETS bucket function ids.

        Uses a stable hash (zlib.crc32) rather than Python's built-in hash(),
        which is randomized per process (PYTHONHASHSEED) and would break
        cross-run / cross-process reproducibility.

        This mirrors how a real workload has many users sharing a small
        catalogue of functions, so reuse becomes possible.
        """
        buckets = int(getattr(Config, "FUNCTION_NAME_BUCKETS", 0) or 0)
        if buckets <= 0:
            # Fall back to per-user (legacy): reuse only if same user re-invokes.
            return f"fn_user_{user_id}"
        h = zlib.crc32(str(user_id).encode("utf-8")) & 0xFFFFFFFF
        return f"fn_bucket_{h % buckets:04d}"
