# Stage‑1 — Future Position Prediction with T‑Drive (Detailed Spec, No Code Yet)

## 0) Scope & Goals

* Goal: predict each taxi’s future coordinates (x_hat_{t+h}, y_hat_{t+h}) (predicted lon/lat at time t+h) for horizons h ∈ {1,3,5,10} minutes.
* Data constraint: T‑Drive is sparsely sampled, so the pipeline must clean → map‑match → resample to 60 s before modeling.
* Deliverables: two baselines (CTRV‑Kalman, Markov on road segments) and the main road‑aware GRU model, with ADE/FDE/Hit@R metrics, ablations, artifacts. No MPC or cloudlet probability yet.

Notation will include an inline explanation on first use: Δ (slot length, 60 s), H (forecast horizon, minutes), L (look‑back window, minutes), σ_h (uncertainty std at step h), ADE (average displacement error), FDE (final displacement error), P[i][j]^{t+h} (probability user i will be served by cloudlet j at time t+h).

---

## 1) Data & Field Schema

Source: T‑Drive sample (one week; Beijing). Typical fields:

* taxi_id (vehicle identifier), timestamp (UTC or local), lon, lat (WGS84 coordinates). Some versions include speed and direction.
* If speed/direction are missing, compute them from the coordinate sequence.

Timezone: normalize to UTC; record timezone metadata in the standardized files.

---

## 2) General Preprocessing

### 2.1 Order & coarse filtering

* Sort by (taxi_id, timestamp); drop duplicate timestamps.
* Speed outliers: if inferred speed > 160 km/h, drop or replace the single point by interpolation.
* GPS jumps: if Haversine gap > 1 km between two consecutive minutes, split the trip.

### 2.2 Trip segmentation

* Split the trajectory at long idle gaps: if Δt > 15 minutes, start a new trip.
* Discard trips shorter than 10 resampled points.

### 2.3 Coordinate frame & normalization

* Convert to a local planar frame: ENU/UTM (easier distances/angles). WGS84 → ENU around a city‑center reference.
* Normalize continuous features using train‑set statistics; save the scaler to reuse for val/test.

---

## 3) Map‑Matching (HMM) & Uniform Resampling @ 60 s

### 3.1 Road graph

* Nodes: intersections; Edges: directed road segments with attributes (speed limit if available, length, class).

### 3.2 HMM with Viterbi decoding

* Observation o_t (GPS at time t).
* Hidden state s_t (road segment and curvilinear position along the segment at time t).
* Emission: p(o_t | s_t) based on perpendicular distance from GPS to segment.
* Transition: p(s_t | s_{t-1}) penalizes infeasible travel given the shortest‑path length and the actual time gap.
* Decode with Viterbi to obtain the most likely segment sequence.

### 3.3 Uniform resampling

* After map‑matching, resample to a uniform cadence Δ = 60 s (Δ: slot length) along the polyline. Output a per‑minute sequence with ENU position, speed v_t (speed at time t), acceleration a_t (acceleration at time t), heading ψ_t (heading angle at time t).

---

## 4) Input Features (per minute)

* Kinematics: v_t (m/s), a_t (m/s²), ψ_t (radians), Δv_t (speed delta), Δψ_t (heading change).
* Road semantics: road_id (segment ID), lane_count (if available), road class (arterial/local), speed limit.
* Temporal: tod_sin/cos (time‑of‑day), dow_sin/cos (day‑of‑week), rush‑hour flag.
* Stop state: stop_flag (near‑zero movement), dw_time (dwell time so far).
* Normalization: z‑score for continuous, embedding for road_id.

Look‑back window L ∈ [10, 20] minutes (L: look‑back length) → input tensor shape [L, F] (F: number of features).

---

## 5) Splits & Batching

* Time split: train = days 1–5; val = day 6; test = day 7 (prevents temporal leakage).
* Unit: whole trips (do not split trips across batches).
* Batching: pack multiple short trips; pad to max length and mask loss on padding.

---

## 6) Modeling (Stage‑1, no code yet)

### 6.1 Baseline #1 — CTRV‑Kalman

* Constant‑Turn‑Rate‑and‑Velocity state: [x, y, v, ω, ψ] (position, speed, yaw rate ω, heading ψ).
* Filter noise and predict 1,3,5,10 minutes; after each step, snap the predicted point back to the nearest road polyline.

### 6.2 Baseline #2 — Markov on road segments

* Build a time‑conditioned segment‑transition matrix; roll out h minutes; take the median point on the destination segment as the estimate.

### 6.3 Main model — Road‑aware GRU (lightweight)

* Architecture: 1–2 GRU layers (hidden size 64–128), dropout 0.1.
* Output: one‑minute displacement vector Δs_{t→t+1} (curvilinear displacement along the route). Roll out cumulatively to h minutes.
* Scheduled sampling: train 1‑step with teacher forcing, then gradually increase the chance of feeding the model’s own predictions.
* Road constraint: after each step, snap to the nearest polyline (prefer candidates contiguous to the current road_id).
* Optional uncertainty: also output σ_h (std at step h) and train with Gaussian NLL for calibrated uncertainty.

---

## 7) Loss Functions

* Geodesic loss: Haversine between prediction and ground truth (or L2 in ENU if you keep everything planar).
* Multi‑horizon objective:
  L = sum_{h ∈ {1,3,5,10}} w_h · Haversine(p_hat_{t+h}, p_{t+h}) + λ_smooth · SmoothL1(Δs_hat, Δs)
  with w_h (horizon weights) and λ_smooth (displacement smoothness strength).
* Off‑road penalty (optional): small penalty if the predicted point is >10 m away from a road polyline.
* Uncertainty (optional): Gaussian NLL with σ_h (std at step h).

---

## 8) Training Protocol

* Optimizer: Adam (lr 1e‑3, reduce‑on‑plateau ×0.5, patience 3), weight decay 1e‑5.
* Early stopping: by FDE@10′ on the validation day.
* Augmentation: light jitter on v_t, a_t, ψ_t; random‑drop 1–2 points in the look‑back window to simulate sparse sampling.
* Reproducibility: fixed seeds; log scaler/encoder versions.

---

## 9) Evaluation

### 9.1 Primary metrics

* ADE (average displacement error): mean distance error across all forecast steps.
* FDE (final displacement error): distance error at the farthest step (5′/10′).
* Hit@R: fraction of predictions within radius R ∈ {100,200,400} meters (R = 400 m aligns with a typical cloudlet coverage radius).

### 9.2 Slices for insight

* By sampling gap: Δt ∈ (0,120], (120,300], >300 s between original observations.
* By time‑of‑day: rush hours (7–10, 17–20) vs off‑peak.
* By area: urban core vs outer ring (use road‑node density heuristics).

### 9.3 Comparisons & ablations

* CTRV‑Kalman vs GRU: target ≥ 20–30% FDE@10′ reduction and ≥ +10 pp Hit@200 m for GRU.
* Ablations: remove map‑matching; remove scheduled sampling; drop temporal features.

---

## 10) Artifacts & Logging

* Model card: architecture, parameter count, split details, metrics.
* Predictions export: Parquet with (taxi_id, t, h, x_hat, y_hat, sigma_h?) (σ_h: std if modeling uncertainty), plus ground truth coordinates.
* Experiment logs: TensorBoard/W&B (loss, ADE/FDE/Hit@R), seed, data hash.

---

## 11) Risks & Mitigations

* GPS drift: HMM map‑matching + (optional) CTRV pre‑filtering.
* Long data gaps: split trips; for very large Δt, let the model decay to a low‑velocity prior.
* Leakage across time/vehicles: strict time split by days; don’t mix trips.
* Overfitting to time cues: regularize and cross‑day validation.

---

## 12) Suggested Timeline

* Week 1: preprocessing + HMM map‑matching + 60 s resampling; CTRV‑Kalman baseline.
* Week 2: road‑aware GRU (1 layer), light scheduled sampling; Haversine + SmoothL1 losses; evaluation.
* Week 3: ablations + uncertainty (σ_h); final Stage‑1 report (tables & ADE/FDE/Hit@R plots).

---

## 13) Bridge to Stage‑2 (from positions → cloudlet probabilities)

* Use (x_hat_{t+h}, y_hat_{t+h}) (predicted coordinates at t+h) to generate top‑K cloudlets by road distance.
* Train a ranking head to convert position to P[i][j]^{t+h} (probability user i will be served by cloudlet j at time t+h).
* Aggregate demand U_hat[k][j]^{t+h} = sum_i P[i][j]^{t+h} · 1[k(i)=k] (expected demand of service k at cloudlet j at time t+h) and feed MPC.

---

## 14) Hyperparameter Starters

* GRU hidden = 128; layers = 1; dropout = 0.1.
* Look‑back L = 20 minutes; horizons h = {1,3,5,10} minutes.
* Adam; lr = 1e‑3 (reduce‑on‑plateau factor 0.5, patience 3); batch = 64 trips.
* Horizon weights w_h: 1 → 0.5 → 0.5 → 1 (emphasize near & far steps).
* λ_smooth = 0.1.

---

## 15) Citations & Licensing Notes

* When publishing, cite the original T‑Drive papers and note: “Data usage: T‑Drive sample, one‑week Beijing taxi trajectories.”

---

## 16) Notation & Symbols (recap with inline meanings)

* Δ — slot length (60 s).
* H — forecast horizon (minutes ahead).
* L — look‑back window length (minutes of history).
* (x_hat_{t+h}, y_hat_{t+h}) — predicted coordinates at step h.
* v_t, a_t, ψ_t — speed, acceleration, heading at time t.
* ADE — average displacement error over all steps.
* FDE — displacement error at the final step.
* Hit@R — fraction within radius R meters.
* P[i][j]^{t+h} — probability user i is served by cloudlet j at time t+h.
* σ_h — standard deviation of the predictive distribution at step h (if uncertainty is modeled).

---

### Appendix: High‑level Pseudocode

1. Load & sort → filter outliers → segment trips.
2. HMM map‑matching → resample to Δ = 60 s.
3. Featureize each minute over look‑back L.
4. Train CTRV‑Kalman (baseline #1) and segment‑Markov (baseline #2).
5. Train road‑aware GRU with scheduled sampling.
6. Evaluate ADE/FDE/Hit@R (+ slices by Δt, time‑of‑day, area).
7. Export artifacts (Parquet) with (x_hat_{t+h}, y_hat_{t+h}), σ_h for h ∈ {1,3,5,10}.

— End of Stage‑1 Spec —
