"""Build the leg-level travel-time dataset from the Amazon Last Mile Routing Research Challenge.

One row per consecutive stop pair in the *driven* sequence (`actual_sequences.json`). The target is
`travel_time_sec` from Amazon's per-route travel-time matrix (`travel_times.json`).

Caveat (documented in the README): that matrix is Amazon's modelled stop-to-stop time, not GPS
actuals, and it is not time-dependent. The Food Delivery model provides the observed-outcome signal.

Every feature is known before the leg is driven: coordinates, zones, package counts/volume at the
destination, planned service time, the planned (not realised) clock time and position in sequence.
`route_score` is deliberately excluded - it is computed after execution.

Usage: python -m src.data_processing.build_amazon_legs [--max-routes N]
"""
import argparse
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.data_processing.json_stream import iter_routes
from src.paths import PROCESSED_DIR, RAW_DIR

logger = logging.getLogger(__name__)
RAW = RAW_DIR / "amazon_last_mile"
OUT = PROCESSED_DIR / "amazon_legs.parquet"


def _package_summary(max_routes):
    """route_id -> stop_id -> (n_packages, total_volume_cm3, service_seconds, n_with_time_window)."""
    out = {}
    for i, (rid, stops) in enumerate(iter_routes(RAW / "package_data.json")):
        if max_routes and i >= max_routes:
            break
        summary = {}
        for stop, pkgs in stops.items():
            vol = svc = tw = 0.0
            for p in pkgs.values():
                d = p.get("dimensions") or {}
                vol += (d.get("depth_cm") or 0) * (d.get("height_cm") or 0) * (d.get("width_cm") or 0)
                svc += p.get("planned_service_time_seconds") or 0
                tw += 1 if (p.get("time_window") or {}).get("start_time_utc") else 0
            summary[stop] = (len(pkgs), vol, svc, tw)
        out[rid] = summary
        if (i + 1) % 1000 == 0:
            logger.info("package_data: %d routes", i + 1)
    return out


def _haversine_km(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def build(max_routes=None) -> pd.DataFrame:
    logger.info("Loading route metadata and driven sequences...")
    meta = {}
    for i, (rid, r) in enumerate(iter_routes(RAW / "route_data.json")):
        if max_routes and i >= max_routes:
            break
        meta[rid] = r
    seqs = {rid: r["actual"] for rid, r in iter_routes(RAW / "actual_sequences.json") if rid in meta}
    pkgs = _package_summary(max_routes)

    rows = []
    done = 0
    for rid, tt in iter_routes(RAW / "travel_times.json"):
        if rid not in meta:
            if max_routes and done >= len(meta):
                break
            continue
        r, seq = meta[rid], seqs.get(rid)
        if not seq:
            continue
        stops = r["stops"]
        order = [s for s, _ in sorted(seq.items(), key=lambda kv: kv[1])]
        depart = datetime.strptime(f"{r['date_YYYY_MM_DD']} {r['departure_time_utc']}", "%Y-%m-%d %H:%M:%S")
        station = next((s for s in order if stops[s]["type"] == "Station"), order[0])
        st_lat, st_lng = stops[station]["lat"], stops[station]["lng"]
        clock = depart
        psum = pkgs.get(rid, {})
        for k in range(len(order) - 1):
            a, b = order[k], order[k + 1]
            target = tt.get(a, {}).get(b)
            if target is None:
                continue
            sa, sb = stops[a], stops[b]
            n_pkg, vol, _, tw = psum.get(b, (0, 0.0, 0.0, 0))
            _, _, svc_from, _ = psum.get(a, (0, 0.0, 0.0, 0))
            rows.append((
                rid, r["station_code"], clock, k, len(order),
                sa["lat"], sa["lng"], sb["lat"], sb["lng"],
                sa.get("zone_id") or "none", sb.get("zone_id") or "none",
                n_pkg, vol, tw, svc_from, r["executor_capacity_cm3"],
                _haversine_km(sb["lat"], sb["lng"], st_lat, st_lng), target,
            ))
            clock = clock + timedelta(seconds=target + svc_from)
        done += 1
        if done % 1000 == 0:
            logger.info("legs: %d routes, %d rows", done, len(rows))
        if max_routes and done >= max_routes:
            break

    df = pd.DataFrame(rows, columns=[
        "route_id", "station_code", "planned_depart_ts", "stop_idx", "n_stops",
        "from_lat", "from_lng", "to_lat", "to_lng", "from_zone", "to_zone",
        "to_n_packages", "to_volume_cm3", "to_n_time_windows", "from_service_sec", "capacity_cm3",
        "to_station_km", "travel_time_sec",
    ])
    df["route_date"] = pd.to_datetime(df["planned_depart_ts"]).dt.normalize()
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-routes", type=int, default=None)
    args = ap.parse_args()
    df = build(args.max_routes)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out = OUT if not args.max_routes else OUT.with_name("amazon_legs_sample.parquet")
    df.to_parquet(out, index=False)
    print(f"Saved {len(df):,} legs from {df.route_id.nunique():,} routes -> {out}")
    print(df.travel_time_sec.describe())
