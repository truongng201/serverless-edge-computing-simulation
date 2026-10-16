"""
Analytical warm-container pool for the simulated execution mode.

Models serverless container reuse with proper semantics:
- Pool is keyed by (node_id, function_id), not (user_id, node_id).
- Each entry has a TTL (keep-alive window). Entries past TTL are gone.
- Per-node capacity (MAX_WARM_PER_NODE) is enforced via LRU eviction.
- Central node has its own (much larger but finite) capacity.

A warm hit means: at the moment of invocation, there is a live, READY container
for (function_id) at (node_id) within TTL. A miss means cold start, which
inserts a fresh entry (subject to capacity).

Prewarming: `prewarm()` launches a container ahead of demand. It occupies a
slot immediately (and can evict an LRU entry) but only becomes usable at
`ready_step`, so a request in the same step as the launch decision cannot use
it. Every launch is counted (`prewarm_launches`) so its cost can be billed; an
entry is counted once as `prewarm_hits` when first used, or as
`prewarm_wasted` if it is evicted / expires without ever serving a request.

Clock: the pool is driven by the SIMULATION STEP, not wall-clock time. All
methods take `now` (defaulting to the last value given to set_now/begin_step).
TTL is therefore measured in steps.
"""

from __future__ import annotations

import threading
import zlib
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Optional

from config import Config


@dataclass
class _Entry:
    last_used: float          # step of the last use (or launch); drives TTL + LRU
    ready_step: float         # first step at which the container can serve
    prewarmed: bool = False   # launched by prewarm (not by a request)
    used: bool = False        # served at least one request since launch


class WarmPoolManager:
    def __init__(
        self,
        ttl_steps: Optional[float] = None,
        max_warm_per_edge: Optional[int] = None,
        max_warm_central: Optional[int] = None,
    ):
        self._ttl = float(ttl_steps if ttl_steps is not None else getattr(Config, "WARM_TTL_STEPS", 10))
        self._cap_edge = int(
            max_warm_per_edge if max_warm_per_edge is not None
            else getattr(Config, "MAX_WARM_PER_NODE", 32)
        )
        self._cap_central = int(
            max_warm_central if max_warm_central is not None
            else getattr(Config, "CENTRAL_MAX_CONCURRENT", 1024)
        )
        # node_id -> OrderedDict[function_id, _Entry]
        # OrderedDict preserves LRU order: oldest at the front.
        self._pool: Dict[str, "OrderedDict[str, _Entry]"] = {}
        self._lock = threading.RLock()

        # Simulation-step clock.
        self.now: float = 0.0
        self._step_marker: Optional[float] = None

        self._zero_counters()

    def _zero_counters(self) -> None:
        # Cumulative counters (whole run).
        self.cold_starts = 0          # request-triggered container launches
        self.warm_hits = 0
        self.evictions = 0
        self.rejections = 0
        self.prewarm_launches = 0     # prewarm-triggered container launches
        self.prewarm_hits = 0         # prewarmed containers that served >= 1 request
        self.prewarm_wasted = 0       # prewarmed containers gone without serving
        # Per-step counters (reset by begin_step).
        self.step_prewarm_launches = 0
        self.step_prewarm_hits = 0
        self.step_prewarm_wasted = 0
        self.step_evictions = 0

    # ------------------------------------------------------------------ config
    def set_ttl(self, ttl_steps: float) -> None:
        """Set the keep-alive window (in steps). 0 disables keep-alive."""
        self._ttl = max(0.0, float(ttl_steps))

    def set_now(self, now: float) -> None:
        """Advance the simulation-step clock used for TTL decisions."""
        self.now = float(now)

    def begin_step(self, now: float) -> None:
        """Start a new simulation step: advance the clock and reset per-step counters.

        Idempotent within a step, so it is safe to call from several places.
        """
        now = float(now)
        self.now = now
        if self._step_marker == now:
            return
        self._step_marker = now
        self.step_prewarm_launches = 0
        self.step_prewarm_hits = 0
        self.step_prewarm_wasted = 0
        self.step_evictions = 0

    def _resolve_now(self, now: Optional[float]) -> float:
        return float(now) if now is not None else self.now

    def _capacity_for(self, node_id: str) -> int:
        if node_id == "central_node":
            return self._cap_central
        return self._cap_edge

    def _drop(self, entry: _Entry) -> None:
        if entry.prewarmed and not entry.used:
            self.prewarm_wasted += 1
            self.step_prewarm_wasted += 1

    def _purge_expired(self, node_id: str, now: float) -> None:
        bucket = self._pool.get(node_id)
        if not bucket:
            return
        ttl = self._ttl
        # Remove from front while expired (front is oldest in LRU order).
        stale = []
        for fn_id, entry in bucket.items():
            if now - entry.last_used > ttl:
                stale.append(fn_id)
            else:
                break
        for fn_id in stale:
            self._drop(bucket.pop(fn_id))

    def _make_room(self, bucket: "OrderedDict[str, _Entry]", cap: int) -> None:
        while len(bucket) >= cap:
            # popitem(last=False) -> LRU
            _, evicted = bucket.popitem(last=False)
            self._drop(evicted)
            self.evictions += 1
            self.step_evictions += 1

    # ------------------------------------------------------------------ lookups
    def is_warm(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Return True iff a live (within TTL) and ready entry exists for (node, function)."""
        if not node_id or not function_id:
            return False
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return False
            self._purge_expired(node_id, now)
            entry = bucket.get(function_id)
            return entry is not None and entry.ready_step <= now

    def is_live(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """True iff an entry exists (ready or still launching)."""
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
        """Request-time lookup: on a hit, promotes the entry to MRU and refreshes its step.

        An entry that is still launching (ready_step > now) is NOT a hit.
        """
        if not node_id or not function_id:
            return False
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return False
            self._purge_expired(node_id, now)
            entry = bucket.get(function_id)
            if entry is None or entry.ready_step > now:
                return False
            bucket.move_to_end(function_id, last=True)
            entry.last_used = now
            if entry.prewarmed and not entry.used:
                self.prewarm_hits += 1
                self.step_prewarm_hits += 1
            entry.used = True
            self.warm_hits += 1
            return True

    # ------------------------------------------------------------------ admit
    def admit(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Insert (or refresh) a ready entry. Evicts LRU if over capacity.

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
            entry = bucket.get(function_id)
            if entry is not None:
                if entry.prewarmed and not entry.used:
                    # A request arrived while the prewarmed container was still
                    # launching: it paid a cold start anyway, so the launch did
                    # not help.
                    self.prewarm_wasted += 1
                    self.step_prewarm_wasted += 1
                bucket.move_to_end(function_id, last=True)
                entry.last_used = now
                entry.ready_step = min(entry.ready_step, now)
                entry.used = True
                return True
            self._make_room(bucket, cap)
            bucket[function_id] = _Entry(last_used=now, ready_step=now, used=True)
            return True

    def admit_cold(self, node_id: str, function_id: str, now: Optional[float] = None) -> bool:
        """Request-triggered cold start: count it and insert a ready entry."""
        admitted = self.admit(node_id, function_id, now)
        if admitted:
            self.cold_starts += 1
        return admitted

    def prewarm(
        self,
        node_id: str,
        function_id: str,
        now: Optional[float] = None,
        ready_delay: Optional[float] = None,
    ) -> bool:
        """Launch a container ahead of demand.

        No-op (returns False) if (node, function) already has a live entry: the
        existing container already covers the forecast and refreshing it would
        give keep-alive for free. Otherwise launches a new entry (counted in
        prewarm_launches, may evict the LRU entry) that becomes usable at
        now + ready_delay. Returns True iff a container was launched.
        """
        if not node_id or not function_id:
            return False
        cap = self._capacity_for(node_id)
        if cap <= 0:
            self.rejections += 1
            return False
        now = self._resolve_now(now)
        if ready_delay is None:
            ready_delay = float(getattr(Config, "PREWARM_READY_DELAY_STEPS", 1))
        with self._lock:
            bucket = self._pool.setdefault(node_id, OrderedDict())
            self._purge_expired(node_id, now)
            if function_id in bucket:
                return False
            self._make_room(bucket, cap)
            bucket[function_id] = _Entry(
                last_used=now, ready_step=now + float(ready_delay), prewarmed=True, used=False
            )
            self.prewarm_launches += 1
            self.step_prewarm_launches += 1
            return True

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
        """Live containers on a node (ready or still launching)."""
        now = self._resolve_now(now)
        with self._lock:
            bucket = self._pool.get(node_id)
            if not bucket:
                return 0
            self._purge_expired(node_id, now)
            return len(bucket)

    def total_live(self, now: Optional[float] = None) -> int:
        """Live containers across all nodes (ready or still launching)."""
        now = self._resolve_now(now)
        with self._lock:
            return sum(self.size(node_id, now) for node_id in list(self._pool.keys()))

    def total_retained(self, now: Optional[float] = None) -> int:
        """Containers kept alive past the current step (what keep-alive is billed on).

        An entry is retained while now - last_used < TTL, i.e. it is billed for
        TTL steps after its last use (or launch). With TTL=0 a container exists
        only for the request itself, whose energy is already in E_exec, so
        nothing is retained.
        """
        now = self._resolve_now(now)
        ttl = self._ttl
        with self._lock:
            count = 0
            for node_id in list(self._pool.keys()):
                self._purge_expired(node_id, now)
                count += sum(1 for e in self._pool[node_id].values() if now - e.last_used < ttl)
            return count

    def utilization(self, node_id: str, now: Optional[float] = None) -> float:
        cap = self._capacity_for(node_id)
        if cap <= 0:
            return 0.0
        return self.size(node_id, now) / float(cap)

    def reset(self) -> None:
        with self._lock:
            self._pool.clear()
            self.now = 0.0
            self._step_marker = None
            self._zero_counters()

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {
                node_id: {fn: e.last_used for fn, e in bucket.items()}
                for node_id, bucket in self._pool.items()
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
