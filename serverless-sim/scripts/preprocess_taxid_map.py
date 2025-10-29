#!/usr/bin/env python3
"""
Preprocess TaxiD map data:
 - Build/load a drivable GraphML (projected)
 - Extract filtered road polylines
 - Convert meters -> pixels using DEFAULT_PIXEL_TO_METERS
 - Save compressed JSON (roads.json.gz) for fast UI consumption

Usage examples:
  # From bbox (north, south, east, west)
  python serverless-sim/scripts/preprocess_taxid_map.py --bbox 40.084 39.756 116.813 116.127 \
      --graphml predict-model-with-taxi/osm/beijing_taxid.graphml \
      --roads-json predict-model-with-taxi/osm/beijing_taxid_roads.json.gz

  # From existing OSM XML
  python serverless-sim/scripts/preprocess_taxid_map.py --xml predict-model-with-taxi/planet_116.127,39.756_116.813,40.084.osm/planet_116.127,39.756_116.813,40.084.osm \
      --graphml predict-model-with-taxi/osm/beijing_taxid.graphml \
      --roads-json predict-model-with-taxi/osm/beijing_taxid_roads.json.gz
"""

import argparse
import gzip
import json
import os
from typing import List, Tuple

try:
    import osmnx as ox  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("Please install osmnx: pip install osmnx shapely pyproj rtree networkx")


def load_graph(xml_path: str | None, graphml_path: str | None, bbox: Tuple[float, float, float, float] | None):
    G = None
    if graphml_path and os.path.exists(graphml_path):
        G = ox.load_graphml(graphml_path)
    elif xml_path and os.path.exists(xml_path):
        G = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True)
        if graphml_path:
            os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
            ox.save_graphml(G, graphml_path)
    elif bbox is not None:
        north, south, east, west = bbox
        try:
            G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
        except TypeError:
            G = ox.graph_from_bbox(north, south, east, west, network_type="drive")
        if graphml_path:
            os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
            ox.save_graphml(G, graphml_path)
    else:
        raise RuntimeError("No source provided (graphml, xml, or bbox)")

    # Project to metric CRS for accurate geometry
    if not G.graph.get("crs_is_projected", False):
        G = ox.project_graph(G)
        G.graph["crs_is_projected"] = True
    return G


def to_pixel_transform(G):
    xs = [d["x"] for _, d in G.nodes(data=True)]
    ys = [d["y"] for _, d in G.nodes(data=True)]
    minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)

    px_per_m = 1.0 / 10.0  # match Config.DEFAULT_PIXEL_TO_METERS = 10

    def to_px(xm: float, ym: float) -> Tuple[float, float]:
        return (xm - minx) * px_per_m, (maxy - ym) * px_per_m

    bounds = {
        "minX": 0.0,
        "minY": 0.0,
        "maxX": (maxx - minx) * px_per_m,
        "maxY": (maxy - miny) * px_per_m,
    }
    center = {
        "x": ((minx + maxx) / 2 - minx) * px_per_m,
        "y": (maxy - (miny + maxy) / 2) * px_per_m,
    }
    return to_px, bounds, center, px_per_m


def extract_roads(G, simplify: bool = True, allowed=None, quantize: float | None = 0.1):
    if allowed is None:
        allowed = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified"}
    to_px, bounds, center, px_per_m = to_pixel_transform(G)
    roads: List[List[List[float]]] = []
    for u, v, data in G.edges(data=True):
        h = data.get("highway")
        hw = set(h if isinstance(h, list) else [h]) if h else set()
        if hw and not (hw & allowed):
            continue
        if "geometry" in data and data["geometry"] is not None:
            coords = list(data["geometry"].coords)
        else:
            coords = [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
        poly = []
        for xm, ym in coords:
            x, y = to_px(float(xm), float(ym))
            if quantize:
                x = round(x / quantize) * quantize
                y = round(y / quantize) * quantize
            poly.append([x, y])
        roads.append(poly)
    return {"bounds": bounds, "center": center, "pixel_per_meter": px_per_m, "roads": roads}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", type=str, default=None, help="Path to OSM XML")
    ap.add_argument("--graphml", type=str, default=None, help="Path to GraphML (load/save cache)")
    ap.add_argument("--roads-json", type=str, required=True, help="Output gzipped JSON path")
    ap.add_argument("--bbox", nargs=4, type=float, default=None, help="north south east west")
    args = ap.parse_args()

    bbox = tuple(args.bbox) if args.bbox else None
    G = load_graph(args.xml, args.graphml, bbox)
    data = extract_roads(G)

    os.makedirs(os.path.dirname(args.roads_json), exist_ok=True)
    with gzip.open(args.roads_json, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Wrote {args.roads_json} | roads={len(data['roads'])}")


if __name__ == "__main__":
    main()

