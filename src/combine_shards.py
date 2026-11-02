"""Recombine the sharded Caravan time series in data/processed/timeseries/<subset>/part-*.parquet.

The shards exist only to keep every committed file under GitHub's 100 MB limit.

In code:
    from combine_shards import load_timeseries
    us = load_timeseries("camels")            # one DataFrame, sorted by (gauge_id, date)
    us = load_timeseries("camels", columns=["streamflow", "total_precipitation_sum"])

From the command line (writes one parquet per sub-dataset to data/combined/, which is git-ignored):
    python src/combine_shards.py                    # all sub-datasets found
    python src/combine_shards.py camels camelsaus   # just these
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "data" / "processed"
COMBINED = REPO / "data" / "combined"


def available_subsets(processed_dir: Path = PROCESSED) -> list[str]:
    return sorted(p.name for p in (processed_dir / "timeseries").iterdir() if p.is_dir())


def load_timeseries(subset: str, processed_dir: Path = PROCESSED, columns: list[str] | None = None) -> pd.DataFrame:
    """All kept basins of one sub-dataset as a single long DataFrame (gauge_id, date, ...)."""
    shard_dir = processed_dir / "timeseries" / subset
    files = sorted(shard_dir.glob("part-*.parquet"))
    if not files:
        raise FileNotFoundError(f"no shards in {shard_dir}")
    cols = None if columns is None else ["gauge_id", "date", *columns]
    df = pd.concat((pd.read_parquet(f, columns=cols) for f in files), ignore_index=True)
    return df.sort_values(["gauge_id", "date"], ignore_index=True)


def main(subsets: list[str]):
    COMBINED.mkdir(parents=True, exist_ok=True)
    for s in subsets or available_subsets():
        df = load_timeseries(s)
        out = COMBINED / f"{s}.parquet"
        df.to_parquet(out, index=False)
        print(f"{s}: {df.gauge_id.nunique()} basins, {len(df):,} rows -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
