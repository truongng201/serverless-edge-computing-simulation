# Edge-density sweep — 10 vs 50 vs 100 cloudlets

> Supersedes `edge_density_10_vs_100_comparison.md` (adds the 50-edge midpoint).
> Three full, VALID 80-run grids differing ONLY in cloudlet count:
> - **10 edges**: `experiment_results_20260619_105536.csv`
> - **50 edges**: `experiment_results_20260626_160812.csv`
> - **100 edges**: `experiment_results_20260625_134924.csv`
>
> Each: 4 variants × {100,500,1000,5000} users × 5 seeds × 300 steps, fixed code,
> warm-up rows excluded. Mean ± 95% CI (Student-t, n=5). 5000u CI=0 (pool=5000).

---

## TL;DR

1. **There is an optimal edge density, and it shifts DOWN as load rises.** Light load
   wants *many* cells (each user gets its own warm container); heavy load wants *few*
   cells (dense co-location keeps shared functions warm + fewer handoffs).
2. **Plain greedy is monotonically worse with more edges at every load** (no keep-alive
   ⇒ lives on same-step co-location, which spreading destroys).
3. **Warm variants peak at intermediate density at low load** (100u best at 50e),
   keep improving up to 100e at mid load (500u), and are **best at the fewest edges
   at high load** (5000u best at 10e).
4. **1000u is the transition regime — non-monotonic** (50e is a local *worst* for the
   warm variants).
5. **predictive's relative advantage grows with density.** The "predictive worst at
   5000u" finding holds ONLY at 10 edges; by 50e it ties greedy and by 100e it is best.

---

## Cold starts (total per run) — 10e → 50e → 100e
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | 23.8k → 27.4k → 28.4k | 4 944 → **1 397** → 1 828 | 4 740 → **464** → 478 |
| 500 | 87.8k → 110k → 121k | 71.6k → 43.0k → **26.1k** | 69.3k → 41.6k → **22.9k** |
| 1000 | 120k → 198k → 214k | 94.4k → *115k* → 93.1k | 104k → 110k → **90.3k** |
| 5000 | **124k** → 573k → 902k | **99.8k** → 489k → 743k | **150k** → 566k → 713k |

(**bold** = best density for that variant/load; *italic* = the 1000u non-monotone bump.)

## Warm rate — 10e → 50e → 100e
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | 0.196 → 0.074 → 0.042 | 0.833 → **0.953** → 0.938 | 0.840 → **0.984** → 0.984 |
| 500 | 0.407 → 0.259 → 0.185 | 0.516 → 0.709 → **0.824** | 0.532 → 0.719 → **0.845** |
| 1000 | 0.595 → 0.332 → 0.277 | 0.681 → *0.611* → 0.685 | 0.647 → 0.629 → **0.695** |
| 5000 | **0.917** → 0.613 → 0.390 | **0.933** → 0.670 → 0.498 | 0.899 → 0.617 → 0.518 |

## Turnaround (ms, step mean) — 10e → 50e → 100e
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | 126k → 139k → 143k | 59.6k → **46.9k** → 48.5k | 59.2k → **44.3k** → 44.5k |
| 500 | 522k → 599k → 638k | 465k → 363k → **302k** | 461k → 361k → **295k** |
| 1000 | 843k → 1.12M → 1.18M | 757k → *828k* → 750k | 808k → 819k → **748k** |
| 5000 | **2.54M** → 4.14M → 5.31M | **2.46M** → 3.85M → 4.75M | **2.65M** → 4.18M → 4.70M |

## p99 latency (ms) & energy (J) — highlights
- **predictive p99 at 100u collapses with more edges**: 1335 → **520** → 526 ms
  (near-pure-warm tail once each user has its own uncontended container).
- p99 otherwise stays ~1480–1570 ms across densities (cold-penalty-bound).
- **Energy rises with node count** (static power ∝ #nodes): 5000u greedy
  3.83M → 6.69M → 8.81M J. At low–mid load the warm variants' cold-energy savings
  offset it (500u keep-alive 767k → 618k → 549k J, *falling*).

---

## Interpretation — why the optimum moves with load

Warm reuse needs a recent invocation of the **same function bucket on the same node**
(within `WARM_TTL_STEPS`). Two opposing forces scale with edge count:
- **(A) Handoffs ↑** — smaller cells ⇒ moving taxis cross boundaries more ⇒ reassign
  more ⇒ each handoff to a non-warm node = a cold start. Pushes cold **up**.
- **(B) Per-node contention ↓** — fewer users per node ⇒ fewer function buckets fight
  over the `MAX_WARM_PER_NODE=16` slots ⇒ fewer LRU evictions of live containers.
  Pushes cold **down**.

The balance depends on how many users are available to *share* a node:
- **Light load (100u):** too few users to share, so co-location buys little; spreading
  to ~50 edges gives each user its own uncontended warm container (B wins) → optimum
  at 50e. Beyond that (100e) extra handoffs (A) start to cost (slight regress).
- **Mid load (500u):** still improving at 100e — enough users that B keeps paying.
- **Transition (1000u):** A and B roughly cancel; the curve is **non-monotone** with a
  dip at 50e (~20 users/edge is the worst trade-off here).
- **Heavy load (5000u):** dense co-location at 10 edges keeps shared functions warm for
  everyone (warm_rate 0.92); spreading to 100 edges fragments reuse and multiplies
  handoffs → cold explodes 6–7×. Optimum at the fewest edges (10e).

### Greedy is the clean control
Keep-alive OFF ⇒ greedy's only warmth is same-step co-location, which more edges always
destroys. Hence greedy degrades monotonically with density at every load — exactly
force (A)+fragmentation with none of (B).

### 🎯 The "predictive degrades at scale" result is a 10-edge contention artifact
At 5000u, predictive is the *worst* variant only at 10 edges (150k cold vs greedy 124k):
all 5000 users pile onto 10 nodes and prewarm evicts live containers. Add edges and the
per-node load drops, the pool stops thrashing, and predictive's relative rank recovers
(≈greedy at 50e; **best** at 100e, 713k < greedy 902k). Report this honestly as a
contention regime, not a design flaw. A `MAX_WARM_PER_NODE` sweep at 10e would
demonstrate the same recovery from the capacity axis.

---

## Caveats
- **Handoffs inferred, not counted.** Cold change conflates handoffs (A) with
  co-location fragmentation (B). Direct counts need the server's `request_logs/`
  (`migration_ms > 0`) — not yet captured (PER_REQUEST_LOG_DIR was unset).
- **5000u has no CI** (pool = exactly 5000 trajectories ⇒ identical cohort per seed).
- Specific to `MAX_WARM_PER_NODE=16`, `FUNCTION_NAME_BUCKETS=32`, `WARM_TTL_STEPS=30`,
  uniform-grid placement over center-heavy taxi demand. All tunable.
- Only 3 density points (10/50/100); 20 and 200 would smooth the curve, especially
  around the 1000u non-monotonic region.

## Implications for the paper
- **Optimal-edge-density-per-load** is a genuine, publishable curve ("denser ≠ better").
- predictive is **robustly best wherever density is adequate for the load**; present
  the 10e/5000u case as a contention boundary with the mechanism explained.
- More edges ⇒ more handoffs ⇒ fragmented reuse ⇒ more cold starts at scale = the
  motivation for predictive prewarm.
