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
from typing import List, Tuple, Dict

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
    for fp in files:
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
    raw = load_raw_tdrive(tdrive_root, num_taxis=num_taxis)
    # 2) compute UTM x,y
    raw = _compute_xy(raw)
    # 3) segment trips by idle gap (configurable)
    raw = _segment_trips(raw, max_idle_gap_sec=int(max_idle_gap_min * 60))
    # 4) filter speed outliers
    raw = _filter_speed_outliers(raw, max_speed_kmh=160.0)
    # 5) resample per trip to 60s
    resampled_parts = []
    for trip_id, trip in raw.groupby('trip_id'):
        sub = _resample_trip_minutely(trip[['taxi_id', 'trip_id', 'ts', 'x', 'y']])
        if not sub.empty:
            resampled_parts.append(sub)
    if not resampled_parts:
        raise RuntimeError("No trips after resampling. Check filters and input size.")
    resampled = pd.concat(resampled_parts, ignore_index=True)
    # final safety fill against any residual NaNs
    for col in ['x', 'y']:
        resampled[col] = resampled.groupby('trip_id')[col].transform(
            lambda s: s.interpolate().ffill().bfill()
        )
    resampled = resampled.dropna(subset=['x', 'y'])
    # 6) features
    feats = _compute_features(resampled)
    # 7) split by day
    train_df, val_df, test_df = train_val_test_split_by_day(feats)
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
) -> None:
    """Phase B: Map-matching + on-road resampling + features/splits.

    Loads/creates an OSM road graph, builds candidates and runs HMM map-matching
    per trip on raw (non-uniform) observations, then resamples to 60s on-road
    before computing features and splits.
    """
    os.makedirs(out_dir, exist_ok=True)
    # 1) Load raw and project to UTM XY
    raw = load_raw_tdrive(tdrive_root, num_taxis=num_taxis)
    raw = _compute_xy(raw)
    raw = _segment_trips(raw, max_idle_gap_sec=int(max_idle_gap_min * 60))
    raw = _filter_speed_outliers(raw, max_speed_kmh=max_speed_kmh)
    # 2) Load OSM graph (projected)
    G = load_graph(
        graphml_path=graphml,
        place=place,
        bbox=bbox,
        project=True,
        overpass_endpoint=overpass_endpoint,
        overpass_timeout=overpass_timeout,
        xml_path=xml,
    )
    # 3) Build candidate generator + matcher
    cand_gen = CandidateGenerator(G, radius_m=candidate_radius_m, k=k_candidates)
    matcher = HMMMapMatcher(G, cand_gen, sigma_gps=sigma_gps_m, max_speed_kmh=max_speed_kmh,
                            use_shortest_path=use_shortest_path)
    # 4) Map-match per trip, then on-road resample to 60s using footpoints
    #    We reuse _resample_trip_minutely by feeding matched x,y at original ts
    matched_resampled = []
    for trip_id, trip in raw.groupby('trip_id'):
        trip = trip.sort_values('ts')
        xs = trip['x'].tolist()
        ys = trip['y'].tolist()
        ts = trip['ts'].tolist()
        matched = matcher.match_trip(xs, ys, ts)
        # build DataFrame with matched xy (fallback to original if None)
        mx = []
        my = []
        for i, m in enumerate(matched):
            if m is None:
                mx.append(xs[i])
                my.append(ys[i])
            else:
                fx, fy = m['foot_xy']
                mx.append(fx)
                my.append(fy)
        mtrip = pd.DataFrame({
            'taxi_id': trip['taxi_id'].iloc[0],
            'trip_id': trip_id,
            'ts': trip['ts'].values,
            'x': mx,
            'y': my,
        })
        sub = _resample_trip_minutely(mtrip[['taxi_id', 'trip_id', 'ts', 'x', 'y']])
        if not sub.empty:
            matched_resampled.append(sub)
    if not matched_resampled:
        raise RuntimeError("No trips matched/resampled. Check OSM loader and parameters.")
    resampled = pd.concat(matched_resampled, ignore_index=True)
    # final safety fill
    for col in ['x', 'y']:
        resampled[col] = resampled.groupby('trip_id')[col].transform(
            lambda s: s.interpolate().ffill().bfill()
        )
    resampled = resampled.dropna(subset=['x', 'y'])
    # 5) Features, splits, scaler as Phase A
    feats = _compute_features(resampled)
    train_df, val_df, test_df = train_val_test_split_by_day(feats)
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
        'created': pd.Timestamp.utcnow().isoformat(),
    }
    pd.Series(meta).to_json(os.path.join(out_dir, 'meta.json'))
