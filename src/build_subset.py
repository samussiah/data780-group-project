"""Extract a manageable Caravan subset from the 29 GB Zenodo CSV release.

Caravan-csv.tar.gz is one gzip stream, so individual files can't be fetched. This script makes a
single streaming pass over it (nothing like 29 GB is written to disk):

  1. attributes for the chosen sub-datasets are saved to <raw>/attributes/ (they come first in the
     archive, which also tells us which gauge ids to expect),
  2. each wanted time series is trimmed to the chosen columns + date window and cached as a small
     float32 parquet file in <interim>/<subset>/,
  3. the stream stops as soon as every expected gauge has been seen.

A second stage then runs on the local cache only (no network) and writes EVERY extracted gauge, unfiltered:
  <out>/attributes.parquet            merged attributes (index gauge_id, col subset)
  <out>/timeseries/<subset>/part-N.parquet   long format (gauge_id, date, ...), sharded by gauge so each file
                                      stays under GitHub's 100 MB limit; read a whole region with
                                      pd.read_parquet('<out>/timeseries/<subset>/')

No quality filtering happens here. notebooks/02_preprocessing.ipynb computes the per-gauge quality report,
applies the record-length / missingness filters and writes <out>/quality_report.csv and <out>/basin_list.csv,
so the thresholds can change without touching the committed data.

Re-running skips gauges already cached. Rewrite the outputs from the cache alone with --skip-pull.
If you already have the archive locally, pass --archive PATH.

Usage:
    python src/build_subset.py                                        # stream from Zenodo
    python src/build_subset.py --archive ~/Downloads/Caravan-csv.tar.gz
    python src/build_subset.py --skip-pull                            # rewrite outputs from the cache
"""
from __future__ import annotations

import argparse
import io
import sys
import tarfile
import time
from pathlib import Path

import pandas as pd
import requests
import urllib3

ZENODO_URL = "https://zenodo.org/records/15530022/files/Caravan-csv.tar.gz?download=1"
ROOT = "Caravan-csv"
REPO = Path(__file__).resolve().parents[1]

# camels = US (CAMELS), camelsgb = Great Britain, camelsaus = Australia (most water-limited sub-dataset:
# median ERA5-Land aridity PET/P ~6, and the record spans the Millennium Drought).
DEFAULT_SUBSETS = ["camels", "camelsgb", "camelsaus"]
DEFAULT_COLUMNS = [
    "streamflow",
    "total_precipitation_sum",
    "temperature_2m_min", "temperature_2m_mean", "temperature_2m_max",
    "potential_evaporation_sum_ERA5_LAND",
    "snow_depth_water_equivalent_mean",
    "dewpoint_temperature_2m_mean",
    "surface_net_solar_radiation_mean", "surface_net_thermal_radiation_mean",
    "surface_pressure_mean",
    "u_component_of_wind_10m_mean", "v_component_of_wind_10m_mean",
    "volumetric_soil_water_layer_1_mean", "volumetric_soil_water_layer_2_mean",
    "volumetric_soil_water_layer_3_mean", "volumetric_soil_water_layer_4_mean",
]
ATTR_KINDS = ("caravan", "hydroatlas", "other")


# --------------------------------------------------------------------------- stage 1: stream & cache
class _Progress:
    """File-like wrapper around a urllib3 response that tracks compressed bytes read."""

    def __init__(self, raw, total):
        self.raw, self.total, self.n, self._t = raw, total, 0, time.time()

    def read(self, size=-1):
        b = self.raw.read(size)
        self.n += len(b)
        return b

    def status(self):
        pct = f"{100 * self.n / self.total:4.1f}%" if self.total else "  ?  "
        return f"{self.n / 1e9:6.2f} GB {pct} {self.n / 1e6 / max(time.time() - self._t, 1e-6):5.1f} MB/s"


def _open_stream(archive: Path | None):
    if archive:
        f = open(archive, "rb")
        return f, _Progress(f, archive.stat().st_size)
    r = requests.get(ZENODO_URL, stream=True, timeout=60)
    r.raise_for_status()
    prog = _Progress(r.raw, int(r.headers.get("Content-Length", 0)))
    return r, prog


def _trim(csv_file, columns, start, end) -> pd.DataFrame:
    df = pd.read_csv(csv_file, parse_dates=["date"], index_col="date")
    df = df.loc[start:end]
    keep = [c for c in columns if c in df.columns]
    return df[keep].astype("float32")


def _pull_once(subsets, columns, start, end, raw_dir, interim_dir, archive):
    """One pass over the archive. Returns (expected_ids, done_ids)."""
    expected: dict[str, set[str]] = {}
    done: set[str] = set()
    warned_missing: set[str] = set()
    stream, prog = _open_stream(archive)
    last_print = 0.0
    try:
        with tarfile.open(fileobj=prog, mode="r|gz") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                parts = m.name.split("/")  # Caravan-csv/<attributes|timeseries>/...
                if len(parts) >= 4 and parts[1] == "attributes" and parts[2] in subsets:
                    dest = raw_dir / "attributes" / parts[2] / parts[3]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(tf.extractfile(m).read())
                    if parts[3] == f"attributes_other_{parts[2]}.csv":
                        ids = pd.read_csv(dest, usecols=["gauge_id"])["gauge_id"]
                        expected[parts[2]] = set(ids)
                        print(f"[attributes] {parts[2]}: {len(ids)} basins")
                elif len(parts) == 5 and parts[1] == "timeseries" and parts[2] == "csv" and parts[3] in subsets:
                    subset, gid = parts[3], parts[4].removesuffix(".csv")
                    if subset not in expected:
                        sys.exit(f"time series for {subset} reached before its attributes; unexpected archive order")
                    out = interim_dir / subset / f"{gid}.parquet"
                    if not out.exists():
                        df = _trim(io.BytesIO(tf.extractfile(m).read()), columns, start, end)
                        missing = [c for c in columns if c not in df.columns]
                        if missing and subset not in warned_missing:
                            warned_missing.add(subset)
                            print(f"[warn] {subset}: columns not found: {missing}")
                        out.parent.mkdir(parents=True, exist_ok=True)
                        df.to_parquet(out)
                    done.add(gid)
                    if time.time() - last_print > 5:
                        last_print = time.time()
                        print(f"[stream] {prog.status()}  gauges cached: {len(done)}/{sum(map(len, expected.values()))}")
                    if len(expected) == len(subsets) and done >= set().union(*expected.values()):
                        print("[stream] all expected gauges found; stopping early")
                        break
    finally:
        stream.close()
    return expected, done


def pull(subsets, columns, start, end, raw_dir, interim_dir, archive, retries):
    for attempt in range(1, retries + 2):
        try:
            expected, done = _pull_once(subsets, columns, start, end, raw_dir, interim_dir, archive)
            break
        except (requests.RequestException, urllib3.exceptions.HTTPError, tarfile.TarError, EOFError, OSError) as e:
            if attempt > retries:
                raise
            print(f"[retry {attempt}/{retries}] stream failed ({e!r}); restarting (cached gauges are skipped)")
            time.sleep(10)
    for s in subsets:
        if s not in expected:
            print(f"[warn] no attributes found for sub-dataset '{s}' (check the name)")
        else:
            gone = expected[s] - done
            if gone:
                print(f"[warn] {s}: {len(gone)} attribute rows have no time series file")


# --------------------------------------------------------------------------- stage 2: write outputs
def combine(subsets, raw_dir, interim_dir, out_dir, shards):
    """Write every cached gauge (no filtering) as sharded long-format parquet plus merged attributes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "timeseries").mkdir(exist_ok=True)

    all_ids = []
    for s in subsets:
        files = sorted((interim_dir / s).glob("*.parquet"))
        if not files:
            print(f"[warn] no cached time series for {s}")
            continue
        sub_dir = out_dir / "timeseries" / s
        sub_dir.mkdir(parents=True, exist_ok=True)
        for old in sub_dir.glob("part-*.parquet"):
            old.unlink()
        for i in range(shards):
            part = files[i::shards]  # interleave so shards have similar size
            long = pd.concat({f.stem: pd.read_parquet(f) for f in part}, names=["gauge_id"]).reset_index()
            long.to_parquet(sub_dir / f"part-{i}.parquet", index=False, compression="zstd", compression_level=9)
        all_ids += [f.stem for f in files]
        print(f"[write] {s}: {len(files)} gauges -> {sub_dir}")

    # attributes: merge the three files per subset, keep gauges that have a time series, stack subsets
    frames = []
    for s in subsets:
        parts = [pd.read_csv(raw_dir / "attributes" / s / f"attributes_{k}_{s}.csv", index_col="gauge_id")
                 for k in ATTR_KINDS if (raw_dir / "attributes" / s / f"attributes_{k}_{s}.csv").exists()]
        if parts:
            a = pd.concat(parts, axis=1)
            a = a.loc[a.index.intersection(all_ids)].assign(subset=s)
            frames.append(a)
    attrs = pd.concat(frames)
    attrs.to_parquet(out_dir / "attributes.parquet")
    print(f"wrote {len(all_ids)} gauges; attributes {attrs.shape}; to {out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subsets", nargs="+", default=DEFAULT_SUBSETS)
    ap.add_argument("--columns", nargs="+", default=DEFAULT_COLUMNS, help="time series columns to keep")
    ap.add_argument("--start", default="1981-01-01", help="first day of the stored time series")
    ap.add_argument("--end", default="2014-12-31", help="last day of the stored time series")
    ap.add_argument("--out-dir", type=Path, default=REPO / "data" / "processed")
    ap.add_argument("--raw-dir", type=Path, default=REPO / "data" / "raw")
    ap.add_argument("--interim-dir", type=Path, default=REPO / "data" / "interim")
    ap.add_argument("--archive", type=Path, help="local Caravan-csv.tar.gz instead of streaming from Zenodo")
    ap.add_argument("--shards", type=int, default=5, help="time series files per sub-dataset (keeps each under GitHub's 100 MB limit)")
    ap.add_argument("--retries", type=int, default=20)
    ap.add_argument("--skip-pull", action="store_true", help="only rewrite the outputs from already cached data")
    a = ap.parse_args()

    if not a.skip_pull:
        pull(a.subsets, a.columns, a.start, a.end, a.raw_dir, a.interim_dir, a.archive, a.retries)
    combine(a.subsets, a.raw_dir, a.interim_dir, a.out_dir, a.shards)


if __name__ == "__main__":
    main()
