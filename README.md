# data780-group-project
## Data

`data/processed/` holds the Caravan subset used in this project (US `camels`, Great Britain `camelsgb`, Australia `camelsaus`; 1760 basins, daily 1981-2014), built from the Caravan v1.6 CSV release by `src/build_subset.py`.

- `attributes.parquet`: static attributes for the kept basins (index `gauge_id`, column `subset`)
- `basin_list.csv`, `quality_report.csv`: which basins were kept and why others were dropped
- `timeseries/<subset>/part-N.parquet`: daily forcing + streamflow, sharded by gauge so each file stays under GitHub's 100 MB limit

Load a whole region with:

```python
import sys; sys.path.insert(0, "src")
from combine_shards import load_timeseries
us = load_timeseries("camels")  # sorted by (gauge_id, date)
```

or run `python src/combine_shards.py` to write one parquet per region to `data/combined/` (git-ignored).
