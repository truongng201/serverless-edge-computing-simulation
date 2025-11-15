"""
T-Drive Phase A data preparation pipeline
========================================

Purpose
-------
Prepare the raw T-Drive taxi trajectories (text logs) into a uniform, per-minute
sequence dataset with engineered features suitable for Phase A modeling (free-space
GRU without map-matching).

High-level steps
----------------
1) Load raw files (taxi_id, timestamp, lon, lat) and sort/deduplicate by
   (taxi_id, ts).
2) Convert WGS84 coordinates to a local planar CRS (UTM Zone 50N) for metric
   distances in meters.
3) Segment trajectories into trips using an idle gap threshold (configurable,
   default 15 minutes). This creates contiguous sequences for modeling; it does
   NOT correspond to passenger trips.
4) Filter speed outliers (>160 km/h instantaneous) to remove obvious GPS spikes.
5) Resample each trip to a strict 60-second grid using time-based interpolation.
   We take the union of original timestamps and the target grid to preserve the
   original points as anchors, then slice back to the grid.
6) Compute kinematic and temporal features (v, a, delta_heading, stop/dwell,
   time-of-day, day-of-week, rush-hour flags).
7) Split by calendar day: train = 2–6 Feb, val = 7 Feb, test = 8 Feb (2008).
8) Fit per-feature standardization on train only, apply to val/test.
9) Persist artifacts (train/val/test pickles, scaler.pkl, meta.json).

Notes
-----
- Phase A deliberately does NOT perform map-matching or use OSM; positions are
  interpolated in planar UTM space (“free-space” assumption).
- The splitter threshold can be tuned via --max-idle-gap-min depending on how
  sparse the sampling is for selected taxis.
- Dwell time is computed within each trip as cumulative seconds with near-zero
  speed (v < 0.5 m/s), resetting when movement resumes.

CLI usage (from predict-model-with-taxi/)
----------------------------------------
- Prepare (50 taxis, 15-minute idle gap):
  python -m tdrive_predictor.cli prepare \
      --tdrive-root ".\T-drive Taxi Trajectories\release\taxi_log_2008_by_id" \
      --num-taxis 50 --max-idle-gap-min 15 --out-dir tdrive_predictor_artifacts\phase_a
- Train:
  python -m tdrive_predictor.cli train --data-dir tdrive_predictor_artifacts\phase_a
- Evaluate:
  python -m tdrive_predictor.cli eval --data-dir tdrive_predictor_artifacts\phase_a

Outputs
-------
out_dir/
  train.pkl, val.pkl, test.pkl   # feature tables per split
  scaler.pkl                     # dict[str,(mu,sigma)] for feature normalization
  meta.json                      # metadata (CRS, horizons, lookback, thresholds)
  (model ckpt is written by train.py)
"""

import os
import re
import math
import time
import sys
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd

from .utils import wgs84_to_utm, heading_from_dxdy
from .osm.loader import load_graph
from .mapmatch.hmm import CandidateGenerator, HMMMapMatcher


def _list_taxi_files(root: str) -> List[str]:
    """Return list of taxi .txt files sorted by numeric taxi ID from filenames.

    Filenames are expected to be like "<id>.txt" (e.g., 123.txt). Only the first
    `num_taxis` files will be consumed downstream.
    """
    files = []
    for name in os.listdir(root):
        if name.endswith('.txt'):
            files.append(os.path.join(root, name))
    # sort by numeric id from filename
    def key_fn(p):
        m = re.match(r"(\d+)\.txt$", os.path.basename(p))
        return int(m.group(1)) if m else 0

    files.sort(key=key_fn)
    return files


def load_raw_tdrive(root: str, num_taxis: int) -> pd.DataFrame:
    """Load up to `num_taxis` raw T-Drive files and return a single DataFrame.

    Columns: [taxi_id:int, ts:datetime64[ns], lon:float, lat:float]
    Data is sorted by (taxi_id, ts) and duplicate timestamps (per-taxi) are
    removed, keeping the first occurrence.
    """
    files = _list_taxi_files(root)[:num_taxis]
    rows = []
    # progress over files if tqdm available
    try:
        from tqdm import tqdm  # type: ignore
        file_iter = tqdm(files, desc='[Prepare] Reading files', unit='file')
    except (ImportError, ModuleNotFoundError):
        file_iter = files
    for fp in file_iter:
        with open(fp, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) != 4:
                    continue
                taxi_id = int(parts[0])
                ts = pd.to_datetime(parts[1])
                lon = float(parts[2])
                lat = float(parts[3])
                rows.append((taxi_id, ts, lon, lat))
    df = pd.DataFrame(rows, columns=['taxi_id', 'ts', 'lon', 'lat'])
    # sort and deduplicate
    df = df.sort_values(['taxi_id', 'ts']).drop_duplicates(subset=['taxi_id', 'ts'], keep='first')
    return df.reset_index(drop=True)


def _compute_xy(df: pd.DataFrame) -> pd.DataFrame:
    """Append planar coordinates (x,y in meters) using UTM Zone 50N.

    Uses pyproj transformers via utils.wgs84_to_utm. This step converts lon/lat
    to metric coordinates to simplify resampling and feature computation.
    """
    x, y = wgs84_to_utm(df['lon'].to_numpy(), df['lat'].to_numpy())
    df = df.copy()
    df['x'] = x
    df['y'] = y
    return df


def _segment_trips(df: pd.DataFrame, max_idle_gap_sec: int = 480) -> pd.DataFrame:
    """Segment by idle gap threshold in seconds within each taxi.

    A new trip starts when the elapsed time from the previous point exceeds the
    threshold, or when the taxi changes. This is a modeling convenience to form
    contiguous sequences; it is not a passenger trip boundary.
    """
    df = df.copy()
    # compute dt within taxi
    df['dt'] = df.groupby('taxi_id')['ts'].diff().dt.total_seconds().fillna(0)
    # start a new trip when dt > threshold or taxi changes
    new_trip = (df['dt'] > max_idle_gap_sec) | (df['dt'] == 0)
    df['trip_index'] = new_trip.groupby(df['taxi_id']).cumsum().astype(int)
    # uniquely identify trip
    df['trip_id'] = df['taxi_id'].astype(str) + '_' + df['trip_index'].astype(str)
    return df


def _filter_speed_outliers(df: pd.DataFrame, max_speed_kmh: float = 160.0) -> pd.DataFrame:
    """Remove points that imply unrealistic instantaneous speeds.

    We estimate instantaneous speed between consecutive points within the same
    trip using UTM distances and timestamps. If speed exceeds `max_speed_kmh`,
    we drop the later point and re-segment trips since gaps may increase.
    """
    df = df.copy()
    # compute instantaneous speed between consecutive points (m/s)
    df['dx'] = df.groupby('trip_id')['x'].diff()
    df['dy'] = df.groupby('trip_id')['y'].diff()
    df['dt'] = df.groupby('trip_id')['ts'].diff().dt.total_seconds()
    v = np.sqrt((df['dx'].to_numpy() ** 2) + (df['dy'].to_numpy() ** 2)) / df['dt'].to_numpy()
    v[np.isnan(v)] = 0.0
    df['v_inst'] = v
    max_ms = max_speed_kmh / 3.6
    # drop rows where instantaneous speed exceeds threshold (drop the later point)
    mask = (df['v_inst'] <= max_ms) | (~np.isfinite(df['v_inst']))
    df = df[mask].copy()
    df = df.drop(columns=['dx', 'dy', 'dt', 'v_inst'])
    # re-segment trips as gaps may appear
    df = df.sort_values(['taxi_id', 'ts'])
    df = _segment_trips(df)
    return df.reset_index(drop=True)


def _resample_trip_minutely(trip: pd.DataFrame) -> pd.DataFrame:
    """Resample a single trip to a strict 60s grid via time interpolation.

    Expects columns: ['taxi_id','trip_id','ts','x','y', ...]
    Strategy:
      - Build a per-minute DateTimeIndex from ceil(min ts) .. floor(max ts).
      - Take the union of original timestamps and the target grid to preserve
        original points as anchors for interpolation (critical for dense fills).
      - Interpolate with method='time' on the union, then slice back to grid.
      - ffill/bfill as a last safety (should be rare within the clipped range).
    Returns a DataFrame with ['taxi_id','trip_id','ts','x','y'].
    """
    if len(trip) < 2:
        return pd.DataFrame(columns=['taxi_id','trip_id','ts','x','y','lon','lat'])
    trip = trip.sort_values('ts').set_index('ts')
    # uniform 60s grid
    idx = pd.date_range(start=trip.index.min().ceil('min'), end=trip.index.max().floor('min'), freq='60s')
    if len(idx) == 0:
        return pd.DataFrame(columns=['taxi_id','trip_id','ts','x','y','lon','lat'])
    sub = trip[['x', 'y']].astype(float)
    # critical: keep original timestamps while inserting target grid, then interpolate, then slice grid
    union_idx = sub.index.union(idx)
    sub = sub.reindex(union_idx)
    sub[['x', 'y']] = sub[['x', 'y']].interpolate(method='time', limit_direction='both')
    sub = sub.reindex(idx)
    # safety fill
    sub[['x', 'y']] = sub[['x', 'y']].ffill().bfill()
    # restore identifiers
    sub['taxi_id'] = trip['taxi_id'].iloc[0]
    sub['trip_id'] = trip['trip_id'].iloc[0]
    sub['ts'] = sub.index
    # back to lon/lat for export if needed
    # We do not back-convert; keep lon/lat blank to avoid pyproj call again
    return sub.reset_index(drop=True)[['taxi_id', 'trip_id', 'ts', 'x', 'y']]


def _compute_features(resampled: pd.DataFrame) -> pd.DataFrame:
    """Compute kinematic and temporal features on a resampled dataset.

    Adds dx,dy,vx,vy,v,a, heading, delta_heading, delta_v, stop_flag, dw_time,
    tod_sin/cos, dow_sin/cos, rush_hour.
    """
    df = resampled.copy()
    # velocity components and speed (m/s)
    df['dx'] = df.groupby('trip_id')['x'].diff().fillna(0.0)
    df['dy'] = df.groupby('trip_id')['y'].diff().fillna(0.0)
    slot_sec = 60.0
    df['vx'] = df['dx'] / slot_sec
    df['vy'] = df['dy'] / slot_sec
    df['v'] = np.sqrt(df['vx']**2 + df['vy']**2)
    # acceleration (m/s^2)
    df['a'] = df.groupby('trip_id')['v'].diff().fillna(0.0) / slot_sec
    # heading and delta heading
    df['heading'] = np.arctan2(df['dy'], df['dx']).fillna(0.0)
    dhead = df.groupby('trip_id')['heading'].diff().fillna(0.0)
    # wrap angle to [-pi, pi)
    dhead = ((dhead + np.pi) % (2 * np.pi)) - np.pi
    df['delta_heading'] = dhead
    # delta_v
    df['delta_v'] = df.groupby('trip_id')['v'].diff().fillna(0.0)
    # stop flag and dwell time
    stop_thresh = 0.5  # m/s
    df['stop_flag'] = (df['v'] < stop_thresh).astype(int)
    # dwell time in seconds: cumulative seconds while stop_flag==1, reset to 0 otherwise.
    # Implement per-trip to avoid index misalignment from groupby.apply (which
    # would return a Series with a MultiIndex and break direct assignment).
    dw = np.zeros(len(df), dtype=np.float32)
    for trip_id, g in df.groupby('trip_id', sort=False):
        idx = g.index.values
        s = g['stop_flag'].to_numpy().astype(np.int32)
        r = np.zeros_like(s, dtype=np.float32)
        accum = 0.0
        for i in range(len(s)):
            if s[i] == 1:
                accum += slot_sec
                r[i] = accum
            else:
                accum = 0.0
                r[i] = 0.0
        dw[idx] = r
    df['dw_time'] = dw
    # temporal features
    t = df['ts']
    sec_day = t.dt.hour * 3600 + t.dt.minute * 60 + t.dt.second
    df['tod_sin'] = np.sin(2 * np.pi * sec_day / 86400)
    df['tod_cos'] = np.cos(2 * np.pi * sec_day / 86400)
    dow = t.dt.dayofweek
    df['dow_sin'] = np.sin(2 * np.pi * dow / 7)
    df['dow_cos'] = np.cos(2 * np.pi * dow / 7)
    df['rush_hour'] = ((t.dt.hour.between(7, 10)) | (t.dt.hour.between(17, 20))).astype(int)
    return df


def train_val_test_split_by_day(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by calendar day following the standard T-Drive week split.

    Dataset spans 2008-02-02 .. 2008-02-08.
      - train: days 2–6
      - val:   day 7
      - test:  day 8
    """
    day = df['ts'].dt.day
    train = df[day.isin([2, 3, 4, 5, 6])].copy()
    val = df[day == 7].copy()
    test = df[day == 8].copy()
    return train, val, test


def fit_scaler(train_df: pd.DataFrame, feature_cols: List[str]) -> Dict[str, Tuple[float, float]]:
    """Fit per-feature (mu, sigma) on the train split for standardization."""
    scaler = {}
    for c in feature_cols:
        mu = float(train_df[c].mean())
        sigma = float(train_df[c].std(ddof=0))
        if not np.isfinite(sigma) or sigma == 0:
            sigma = 1.0
        scaler[c] = (mu, sigma)
    return scaler


def apply_scaler(df: pd.DataFrame, scaler: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    """Apply a (mu, sigma) mapping to standardize feature columns in a DataFrame."""
    df = df.copy()
    for c, (mu, sigma) in scaler.items():
        if c in df.columns:
            df[c] = (df[c] - mu) / sigma
    return df


def prepare_phase_a(
    tdrive_root: str,
    out_dir: str,
    num_taxis: int = 500,
    resample_sec: int = 60,
    random_state: int = 42,
    max_idle_gap_min: int = 15,
) -> None:
    """End-to-end Phase A preparation.

    Parameters
    ----------
    tdrive_root : str
        Path to the directory containing T-Drive taxi text files (by_id folder).
    out_dir : str
        Output directory for artifacts (pickles and meta.json). Will be created.
    num_taxis : int
        Number of taxi files to load (sorted by numeric id).
    resample_sec : int
        Target resampling interval in seconds (currently 60, recorded in meta).
    random_state : int
        Placeholder for future randomness control (not used here).
    max_idle_gap_min : int
        Gap threshold in minutes to split trips (default 15).
    """
    os.makedirs(out_dir, exist_ok=True)
    # 1) load raw
    print(f"[Phase A] Prepare | root={tdrive_root} | num_taxis={num_taxis} | out={out_dir}", flush=True)
    t0 = time.time()
    raw = load_raw_tdrive(tdrive_root, num_taxis=num_taxis)
    print(f"[Phase A] Loaded rows={len(raw)} | taxis={raw['taxi_id'].nunique()}", flush=True)
    # 2) compute UTM x,y
    raw = _compute_xy(raw)
    # 3) segment trips by idle gap (configurable)
    raw = _segment_trips(raw, max_idle_gap_sec=int(max_idle_gap_min * 60))
    print(f"[Phase A] Segmented trips={raw['trip_id'].nunique()} | max_idle_gap_min={max_idle_gap_min}", flush=True)
    # 4) filter speed outliers
    raw = _filter_speed_outliers(raw, max_speed_kmh=160.0)
    # 5) resample per trip to 60s
    resampled_parts = []
    # progress over trips if tqdm available
    try:
        from tqdm import tqdm  # type: ignore
        n_trips = int(raw['trip_id'].nunique())
        trip_iter = raw.groupby('trip_id')
        is_tty = bool(getattr(sys.stderr, 'isatty', lambda: False)())
        pbar = tqdm(
            total=n_trips,
            desc='[Phase A] Resampling trips',
            unit='trip',
            leave=False,
            dynamic_ncols=True,
            mininterval=0.5,
            disable=(not is_tty),
        )
        for trip_id, trip in trip_iter:
            sub = _resample_trip_minutely(trip[['taxi_id', 'trip_id', 'ts', 'x', 'y']])
            if not sub.empty:
                resampled_parts.append(sub)
            pbar.update(1)
        pbar.close()
    except (ImportError, ModuleNotFoundError):
        for trip_id, trip in raw.groupby('trip_id'):
            sub = _resample_trip_minutely(trip[['taxi_id', 'trip_id', 'ts', 'x', 'y']])
            if not sub.empty:
                resampled_parts.append(sub)
    if not resampled_parts:
        raise RuntimeError("No trips after resampling. Check filters and input size.")
    resampled = pd.concat(resampled_parts, ignore_index=True)
    print(f"[Phase A] Resampled rows={len(resampled)}", flush=True)
    # final safety fill against any residual NaNs
    for col in ['x', 'y']:
        resampled[col] = resampled.groupby('trip_id')[col].transform(
            lambda s: s.interpolate().ffill().bfill()
        )
    resampled = resampled.dropna(subset=['x', 'y'])
    # 6) features
    feats = _compute_features(resampled)
    print(f"[Phase A] Features computed | columns={len(feats.columns)}", flush=True)
    # 7) split by day
    train_df, val_df, test_df = train_val_test_split_by_day(feats)
    print(f"[Phase A] Split sizes | train={len(train_df)} val={len(val_df)} test={len(test_df)}", flush=True)
    # 8) fit scaler on train
    feature_cols = [
        'v', 'a', 'delta_v', 'delta_heading', 'tod_sin', 'tod_cos',
        'dow_sin', 'dow_cos', 'rush_hour', 'stop_flag', 'dw_time'
    ]
    scaler = fit_scaler(train_df, feature_cols)
    # 9) apply scaler
    train_df_s = apply_scaler(train_df, scaler)
    val_df_s = apply_scaler(val_df, scaler)
    test_df_s = apply_scaler(test_df, scaler)
    # 10) save artifacts (pickle to avoid parquet dependency)
    train_df_s.to_pickle(os.path.join(out_dir, 'train.pkl'))
    val_df_s.to_pickle(os.path.join(out_dir, 'val.pkl'))
    test_df_s.to_pickle(os.path.join(out_dir, 'test.pkl'))
    pd.to_pickle(scaler, os.path.join(out_dir, 'scaler.pkl'))
    # save split info for reproducibility
    split = {
        'train_trip_ids': sorted(list(set(train_df['trip_id'].astype(str).unique()))),
        'val_trip_ids': sorted(list(set(val_df['trip_id'].astype(str).unique()))),
        'test_trip_ids': sorted(list(set(test_df['trip_id'].astype(str).unique()))),
    }
    pd.Series(split).to_json(os.path.join(out_dir, 'split.json'))
    # meta
    meta = {
        'num_taxis': int(num_taxis),
        'resample_sec': int(resample_sec),
        'feature_cols': feature_cols,
        'lookback_default': 20,
        'horizons_min': [1, 3, 5, 10],
        'crs': 'EPSG:32650',
        'max_idle_gap_min': int(max_idle_gap_min),
        'created': pd.Timestamp.utcnow().isoformat(),
    }
    pd.Series(meta).to_json(os.path.join(out_dir, 'meta.json'))
    print(f"[Phase A] Saved artifacts to {out_dir} | elapsed={time.time()-t0:.1f}s", flush=True)


def prepare_phase_b(
    tdrive_root: str,
    out_dir: str,
    num_taxis: int = 200,
    max_idle_gap_min: int = 15,
    graphml: str = None,
    place: str = None,
    bbox: Tuple[float, float, float, float] = None,
    overpass_endpoint: str = None,
    overpass_timeout: int = None,
    xml: str = None,
    candidate_radius_m: float = 50.0,
    k_candidates: int = 5,
    sigma_gps_m: float = 12.0,
    max_speed_kmh: float = 160.0,
    use_shortest_path: bool = False,
    use_road_resample: bool = False,
    beam_size: int = 10,
    turn_penalty: float = 0.0,
    speed_scale_mps: float = 20.0,
    adaptive_radius: Optional[Tuple[float, float, float, float]] = None,
) -> None:
    """Phase B: Map-matching + on-road resampling + features/splits.

    Loads/creates an OSM road graph, builds candidates and runs HMM map-matching
    per trip on raw (non-uniform) observations, then resamples to 60s on-road
    before computing features and splits.
    """
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    # 1) Load raw and project to UTM XY
    raw = load_raw_tdrive(tdrive_root, num_taxis=num_taxis)
    raw = _compute_xy(raw)
    raw = _segment_trips(raw, max_idle_gap_sec=int(max_idle_gap_min * 60))
    print(f"[Phase B] Segmented trips={raw['trip_id'].nunique()} | max_idle_gap_min={max_idle_gap_min}", flush=True)
    raw = _filter_speed_outliers(raw, max_speed_kmh=max_speed_kmh)
    # 2) Load OSM graph (projected)
    tG0 = time.time()
    G = load_graph(
        graphml_path=graphml,
        place=place,
        bbox=bbox,
        project=True,
        overpass_endpoint=overpass_endpoint,
        overpass_timeout=overpass_timeout,
        xml_path=xml,
    )
    gsrc = 'graphml' if graphml else ('xml' if xml else ('place/bbox' if (place or bbox) else 'unknown'))
    print(f"[Phase B] Graph loaded | source={gsrc} | elapsed={time.time()-tG0:.1f}s", flush=True)
    # Save graph meta
    try:
        import json
        nodes = getattr(G, 'number_of_nodes', lambda: None)()
        edges = getattr(G, 'number_of_edges', lambda: None)()
        xs = [d.get('x') for _, d in G.nodes(data=True) if 'x' in d]
        ys = [d.get('y') for _, d in G.nodes(data=True) if 'y' in d]
        bbox_m = None
        if xs and ys:
            bbox_m = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
        graph_meta = {
            'crs': 'EPSG:32650',
            'source': gsrc,
            'place': place,
            'bbox_param': list(bbox) if bbox is not None else None,
            'nodes': int(nodes) if nodes is not None else None,
            'edges': int(edges) if edges is not None else None,
            'bbox_m': bbox_m,
            'created': pd.Timestamp.utcnow().isoformat(),
        }
        with open(os.path.join(out_dir, 'graph.meta.json'), 'w', encoding='utf-8') as f:
            json.dump(graph_meta, f)
    except Exception:
        pass
    # 3) Build candidate generator + matcher
    cand_gen = CandidateGenerator(G, radius_m=candidate_radius_m, k=k_candidates)
    matcher = HMMMapMatcher(
        G,
        cand_gen,
        sigma_gps=sigma_gps_m,
        max_speed_kmh=max_speed_kmh,
        use_shortest_path=use_shortest_path,
        beam_size=beam_size,
        turn_penalty=turn_penalty,
        speed_scale_mps=speed_scale_mps,
        adaptive_radius=adaptive_radius,
    )
    print(f"[Phase B] HMM params | sigma={sigma_gps_m} | radius={candidate_radius_m} | K={k_candidates} | beam={beam_size} | turn_penalty={turn_penalty} | sp={use_shortest_path} | road_resample={use_road_resample}", flush=True)
    # 4) Map-match per trip, then resample to 60s (streaming + chunked flush)
    total_obs = 0
    total_nomatch = 0
    tmp_dir = os.path.join(out_dir, '_tmp_chunks')
    os.makedirs(tmp_dir, exist_ok=True)
    chunk_size = 200
    chunk_parts: List[pd.DataFrame] = []
    chunk_files: List[str] = []

    def _flush_chunk(parts: List[pd.DataFrame], idx: int) -> str:
        if not parts:
            return ''
        dfc = pd.concat(parts, ignore_index=True)
        for c in ['x', 'y']:
            dfc[c] = pd.to_numeric(dfc[c], errors='coerce')
            dfc[c] = dfc.groupby('trip_id')[c].transform(lambda s: pd.to_numeric(s, errors='coerce').interpolate().ffill().bfill())
        dfc = dfc.dropna(subset=['x', 'y'])
        dfc = dfc.sort_values(['trip_id', 'ts']).reset_index(drop=True)
        dx_ = dfc.groupby('trip_id')['x'].diff().astype('float64').fillna(0.0)
        dy_ = dfc.groupby('trip_id')['y'].diff().astype('float64').fillna(0.0)
        step_len_ = (dx_**2 + dy_**2).pow(0.5)
        dfc['s_glob'] = step_len_.groupby(dfc['trip_id']).cumsum().astype('float64')
        feats_c = _compute_features(dfc)
        fp = os.path.join(tmp_dir, f'feats_chunk_{idx:05d}.pkl')
        feats_c.to_pickle(fp)
        return fp

    try:
        from tqdm import tqdm  # type: ignore
        n_trips = int(raw['trip_id'].nunique())
        is_tty = bool(getattr(sys.stderr, 'isatty', lambda: False)())
        pbar = tqdm(
            total=n_trips,
            desc='[Phase B] Map-matching trips',
            unit='trip',
            leave=False,
            dynamic_ncols=True,
            mininterval=0.5,
            disable=(not is_tty),
        )
        iterator = raw.groupby('trip_id')
    except (ImportError, ModuleNotFoundError):
        pbar = None
        iterator = raw.groupby('trip_id')

    chunk_idx = 0
    for trip_id, trip in iterator:
        trip = trip.sort_values('ts')
        xs = trip['x'].tolist()
        ys = trip['y'].tolist()
        ts = trip['ts'].tolist()
        matched = matcher.match_trip(xs, ys, ts)
        total_obs += len(matched)
        total_nomatch += sum(1 for m in matched if m is None)
        if use_road_resample:
            try:
                from .resample.road_resample import resample_on_road
                rdf = resample_on_road(matched, ts, graph=G, dt_sec=60)
                if not rdf.empty:
                    rdf['taxi_id'] = trip['taxi_id'].iloc[0]
                    rdf['trip_id'] = trip_id
                    cols = ['taxi_id', 'trip_id', 'ts', 'x', 'y']
                    for c in ['edge', 's', 'edge_len']:
                        if c in rdf.columns:
                            cols.append(c)
                    sub = rdf.rename(columns={'ts': 'ts', 'x': 'x', 'y': 'y'})[cols]
                else:
                    sub = pd.DataFrame()
            except Exception:
                sub = pd.DataFrame()
        else:
            mx = []
            my = []
            for i, m in enumerate(matched):
                if m is None:
                    mx.append(xs[i]); my.append(ys[i])
                else:
                    fx, fy = m['foot_xy']; mx.append(fx); my.append(fy)
            mtrip = pd.DataFrame({
                'taxi_id': trip['taxi_id'].iloc[0],
                'trip_id': trip_id,
                'ts': trip['ts'].values,
                'x': mx,
                'y': my,
            })
            sub = _resample_trip_minutely(mtrip[['taxi_id', 'trip_id', 'ts', 'x', 'y']])
        if not sub.empty:
            chunk_parts.append(sub)
        if pbar is not None:
            pbar.update(1)
        if len(chunk_parts) >= chunk_size:
            fp = _flush_chunk(chunk_parts, chunk_idx)
            if fp:
                chunk_files.append(fp)
            chunk_parts.clear()
            chunk_idx += 1
    if chunk_parts:
        fp = _flush_chunk(chunk_parts, chunk_idx)
        if fp:
            chunk_files.append(fp)
        chunk_parts.clear()
    if pbar is not None:
        pbar.close()
    if not chunk_files:
        raise RuntimeError("No trips matched/resampled. Check OSM loader and parameters.")

    # Load feature chunks and split
    train_parts: List[pd.DataFrame] = []
    val_parts: List[pd.DataFrame] = []
    test_parts: List[pd.DataFrame] = []
    for fp in chunk_files:
        feats_c = pd.read_pickle(fp)
        tr_c, va_c, te_c = train_val_test_split_by_day(feats_c)
        if not tr_c.empty: train_parts.append(tr_c)
        if not va_c.empty: val_parts.append(va_c)
        if not te_c.empty: test_parts.append(te_c)
    train_df = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame()
    val_df = pd.concat(val_parts, ignore_index=True) if val_parts else pd.DataFrame()
    test_df = pd.concat(test_parts, ignore_index=True) if test_parts else pd.DataFrame()
    # cleanup chunks
    try:
        for fp in chunk_files:
            try:
                os.remove(fp)
            except Exception:
                pass
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass
    except Exception:
        pass
    # 5) Features already computed per-chunk; proceed to scaler/saves
    print(f"[Phase B] Split sizes | train={len(train_df)} val={len(val_df)} test={len(test_df)}", flush=True)
    feature_cols = [
        'v', 'a', 'delta_v', 'delta_heading', 'tod_sin', 'tod_cos',
        'dow_sin', 'dow_cos', 'rush_hour', 'stop_flag', 'dw_time'
    ]
    scaler = fit_scaler(train_df, feature_cols)
    train_df_s = apply_scaler(train_df, scaler)
    val_df_s = apply_scaler(val_df, scaler)
    test_df_s = apply_scaler(test_df, scaler)
    train_df_s.to_pickle(os.path.join(out_dir, 'train.pkl'))
    val_df_s.to_pickle(os.path.join(out_dir, 'val.pkl'))
    test_df_s.to_pickle(os.path.join(out_dir, 'test.pkl'))
    pd.to_pickle(scaler, os.path.join(out_dir, 'scaler.pkl'))
    # save split info for reproducibility
    split = {
        'train_trip_ids': sorted(list(set(train_df['trip_id'].astype(str).unique()))),
        'val_trip_ids': sorted(list(set(val_df['trip_id'].astype(str).unique()))),
        'test_trip_ids': sorted(list(set(test_df['trip_id'].astype(str).unique()))),
    }
    pd.Series(split).to_json(os.path.join(out_dir, 'split.json'))
    # map-matching fallback ratio (no candidate -> fallback to original xy)
    match_fallback_ratio = float(total_nomatch) / float(total_obs) if total_obs > 0 else None
    meta = {
        'num_taxis': int(num_taxis),
        'phase': 'B',
        'feature_cols': feature_cols,
        'lookback_default': 20,
        'horizons_min': [1, 3, 5, 10],
        'crs': 'EPSG:32650',
        'max_idle_gap_min': int(max_idle_gap_min),
        'sigma_gps_m': float(sigma_gps_m),
        'candidate_radius_m': float(candidate_radius_m),
        'k_candidates': int(k_candidates),
        'use_shortest_path': bool(use_shortest_path),
        'use_road_resample': bool(use_road_resample),
        'graph_source': 'graphml' if graphml else ('xml' if xml else ('place/bbox' if (place or bbox) else 'unknown')),
        'beam_size': int(beam_size),
        'turn_penalty': float(turn_penalty),
        'speed_scale_mps': float(speed_scale_mps),
        'adaptive_radius': list(adaptive_radius) if adaptive_radius is not None else None,
        'match_fallback_ratio': match_fallback_ratio,
        'created': pd.Timestamp.utcnow().isoformat(),
    }
    pd.Series(meta).to_json(os.path.join(out_dir, 'meta.json'))
    print(f"[Phase B] Saved artifacts to {out_dir} | fallback_ratio={match_fallback_ratio if match_fallback_ratio is not None else 'n/a'} | elapsed={time.time()-t0:.1f}s", flush=True)
