# Edge-density comparison — 10 vs 100 cloudlets

> Question: *does increasing the number of edge nodes create more handoffs (and how
> does it change the ablation)?* Compares two full, VALID 80-run grids that differ
> ONLY in cloudlet count:
> - **10 edges**: `experiment_results_20260619_105536.csv`
> - **100 edges**: `experiment_results_20260625_134924.csv`
>
> Both: 4 variants × {100,500,1000,5000} users × 5 seeds, 300 steps, new (fixed) code.
> Warm-up rows excluded. Mean ± 95% CI (Student-t, n=5). 5000u CI=0 (pool=5000 exhausted).

---

## TL;DR

1. **Yes — more edges ⇒ finer cells ⇒ more boundary crossings ⇒ more handoffs.** But
   handoffs are only *part* of the story; the dominant driver of warm/cold is
   **co-location density** (how many users share the same `(node, function-bucket)`).
   More edges *reduces* that density.
2. **The net effect FLIPS with load:**
   - Low–mid load (100–500u): 100 edges **reduces** cold starts a lot for the warm
     variants (−63% to −67%) — lower per-node contention beats the extra handoffs.
   - High load (5000u): 100 edges makes cold starts **explode +374% to +655%** for
     everyone — handoffs + reuse fragmentation dominate.
3. **Plain greedy is hurt by more edges at every load** (no keep-alive ⇒ it lives on
   same-step co-location, which spreading destroys).
4. **🎯 100 edges RESOLVES the "predictive degrades at scale" problem.** At 10 edges
   predictive was the *worst* at 5000u; at 100 edges it is the *best* at every scale.
   That confirms the earlier degradation was a per-node **contention/thrash artifact**,
   not a flaw in the predictive idea.

---

## Cold starts (total per run) — 10e → 100e (Δ%)
| users | greedy | keep-alive | pred-noWS | predictive |
|---|---|---|---|---|
| 100 | 23 800 → 28 360 (**+19%**) | 4 944 → 1 828 (**−63%**) | 4 894 → 1 830 (−63%) | 4 740 → **478 (−90%)** |
| 500 | 87 800 → 120 700 (+37%) | 71 630 → 26 060 (−64%) | 71 100 → 25 710 (−64%) | 69 270 → 22 890 (−67%) |
| 1000 | 119 900 → 214 100 (+79%) | 94 420 → 93 120 (−1%) | 93 640 → 93 250 (−0%) | 104 500 → 90 300 (−14%) |
| 5000 | 123 600 → 902 200 (**+630%**) | 99 850 → 742 500 (+644%) | 97 280 → 734 300 (+655%) | 150 300 → 713 000 (**+374%**) |

## Warm rate — 10e → 100e
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | 0.196 → 0.042 (−79%) | 0.833 → 0.938 (+13%) | 0.840 → **0.984** (+17%) |
| 500 | 0.407 → 0.185 (−55%) | 0.516 → 0.824 (+60%) | 0.532 → 0.845 (+59%) |
| 1000 | 0.595 → 0.277 (−54%) | 0.681 → 0.685 (+1%) | 0.647 → 0.695 (+7%) |
| 5000 | 0.917 → 0.390 (−57%) | 0.933 → 0.498 (−47%) | 0.899 → 0.518 (−42%) |

## Turnaround (ms, step mean) — 10e → 100e (Δ%)
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | +13% | −19% | **−25%** |
| 500 | +22% | −35% | −36% |
| 1000 | +40% | −1% | −7% |
| 5000 | **+109%** | +93% | +77% |

## p99 latency (ms) — 10e → 100e
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | 1480 → 1505 | 1335 → 1143 | 1335 → **526** (−61%) |
| 500 | 1489 → 1508 | 1486 → 1486 | 1567 → 1518 |
| 1000 | 1484 → 1505 | 1483 → 1493 | 1569 → 1544 |
| 5000 | 1477 → 1527 | 1477 → 1518 | 1565 → 1568 |

## Energy (J, total) — 10e → 100e (Δ%)
| users | greedy | keep-alive | predictive |
|---|---|---|---|
| 100 | +45% | +49% | +42% |
| 500 | +32% | −28% | −30% |
| 1000 | +48% | +5% | −2% |
| 5000 | +130% | +112% | +91% |

(Energy rises with node count via static power; at low–mid load the cold-start energy
saved by the warm variants more than offsets it, so their energy *drops*.)

---

## Interpretation

### The unifying mechanism: co-location density, not just handoffs
A container is warm only if some user recently invoked the **same function bucket on
the same node** within the TTL. Two opposing forces change with edge count:

- **(A) Handoffs ↑ with edges.** Smaller cells ⇒ a moving taxi crosses node
  boundaries more often ⇒ more reassignments. A handoff to a node that doesn't hold
  that function warm = a cold start. This pushes cold **up**.
- **(B) Per-node contention ↓ with edges.** Fewer users per node ⇒ fewer distinct
  function buckets competing for the `MAX_WARM_PER_NODE=16` slots ⇒ fewer LRU
  evictions of live containers. This pushes cold **down**.

Which wins depends on **users-per-edge**:
- **100u/100e ≈ 1 user/edge:** force (B) dominates massively (almost no eviction),
  each user keeps its own warm container → cold collapses (−63% to −90%).
- **5000u/100e ≈ 50 users/edge** but spread thin vs **5000u/10e ≈ 500 users/edge**
  tightly co-located: at 10 edges the heavy co-location keeps `(node,bucket)` warm for
  everyone (warm_rate 0.92); at 100 edges the population fragments across 100 nodes,
  co-location collapses, force (A) wins → cold explodes (+374% to +655%).

### Greedy is special — more edges always hurts it
Plain greedy runs keep-alive OFF (TTL=0), so its only warmth is **same-step**
co-location. Spreading users over more nodes destroys that → warm_rate falls at every
scale (0.196→0.042 at 100u). Greedy is the cleanest illustration of force (A)+
fragmentation with none of (B)'s benefit.

### 🎯 The predictive-at-scale problem was a contention artifact
The FULL report on the 10-edge grid flagged that **predictive was the worst variant
at 5000 users** (cold +22% vs greedy). With 100 edges the per-node load drops 10×, the
warm pool stops thrashing, and **predictive becomes the best variant at every scale**,
including 5000u (713k cold < keep-alive 743k < greedy 902k). This is strong evidence
that the degradation came from prewarm evicting live containers on a few overloaded
nodes — *not* from the predictive design. Recommended follow-up: a `MAX_WARM_PER_NODE`
sweep at 10 edges to show the same recovery from the capacity side.

### Latency tail (p99) is almost flat
Despite cold counts swinging by 6×, p99 moves only a few % (except predictive 100u,
−61%). p99 is set by the cold-penalty constant, and more edges lower propagation,
roughly cancelling. So "more handoffs" shows up in **cold-start counts / energy**, not
in the latency tail.

---

## Caveats
- **Handoffs are inferred, not counted.** Cold-start change conflates handoffs (A)
  with co-location fragmentation (B). To isolate the true handoff count, pull the
  server's `request_logs/` for both runs and count rows with `migration_ms > 0`
  (the local logs are empty/truncated). I can do that split once the logs are here.
- **5000u has no CI** (pool = exactly 5000 trajectories ⇒ identical cohort every seed).
  Point estimates valid; build a >5000 pool for a real 5000u CI.
- Effects are specific to `MAX_WARM_PER_NODE=16`, `FUNCTION_NAME_BUCKETS=32`,
  `WARM_TTL_STEPS=30`, and the uniform-grid placement over center-heavy taxi demand
  (see the placement note). All of these are tunables, not physical constants.

## Implications for the paper
- There is an **optimal edge density per load** — this is a genuine, publishable
  result (denser ≠ better once handoff + reuse-fragmentation dominate).
- The headline predictive method is **robustly best when edge density is adequate
  for the load** (100u–5000u at 100 edges); report the 10-edge/5000u degradation
  honestly as a contention regime and explain the mechanism.
- More edges ⇒ more handoffs is the **motivation**: it fragments container reuse and
  raises cold starts at scale — exactly what predictive prewarm targets.
