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

## Data overview

The subset has three parts: daily time series (17 variables per basin), static attributes (216 columns per basin), and bookkeeping files. The modelling work uses US and AUS only; GB basins (588) are still in the files but are excluded by the splits in `data/processed/splits/`.

### Daily time series (`timeseries/<subset>/`)

Daily, 1981-01-01 to 2014-12-31. Besides `gauge_id` and `date`, each row has streamflow plus 16 catchment-averaged ERA5-Land weather and land-surface variables:

| Group | Columns |
| --- | --- |
| **Target** | `streamflow` (mm/day, i.e. already normalised by catchment area) |
| Precipitation | `total_precipitation_sum` |
| Temperature | `temperature_2m_min`, `_mean`, `_max`; `dewpoint_temperature_2m_mean` |
| Evaporative demand | `potential_evaporation_sum_ERA5_LAND` |
| Radiation | `surface_net_solar_radiation_mean`, `surface_net_thermal_radiation_mean` |
| Wind and pressure | `u_component_of_wind_10m_mean`, `v_component_of_wind_10m_mean`, `surface_pressure_mean` |
| Land-surface states | `snow_depth_water_equivalent_mean`; `volumetric_soil_water_layer_1` to `_4_mean` (four soil depths) |

The snow and soil-water columns are ERA5-Land model states, not observations. They are legitimate inputs and likely useful for slow snowmelt and groundwater behaviour.

### Static attributes (`attributes.parquet`)

216 columns per basin. A few are metadata (`gauge_name`, `country`, `gauge_lat`, `gauge_lon`, `area`, `area_fraction_used_for_aggregation`, `subset`). The rest come from two sources.

**Caravan climate indices (about 15 columns)**, computed from the ERA5-Land forcing: `p_mean`, `pet_mean_*`, `aridity_*`, `moisture_index_*`, `seasonality_*`, `frac_snow`, `high_prec_freq/dur`, `low_prec_freq/dur`.

**HydroATLAS attributes (about 195 columns).** Names follow `variable_unit_stat`. In the stat suffix, `s` is the whole catchment, `u` upstream and `p` the pour point; `av`/`mn`/`mx`/`yr` are mean, min, max and annual; `01` to `12` are months; `se` is percent of area; `mj` is the majority class.

| Category | Examples |
| --- | --- |
| Climate | `pre_mm` (precip), `tmp_dc` (temp), `pet_mm`, `aet_mm`, `cmi_ix` (moisture index), `ari_ix` (aridity), `snw_pc` (snow cover); most as 12 monthly columns plus an annual one |
| Physiography | `ele_mt` (elevation), `slp_dg` (slope), `sgr_dk` (stream gradient) |
| Hydrology | `dis_m3` (discharge), `run_mm` (runoff), `gwt_cm` (groundwater depth), `inu_pc` (inundation), `lka_pc`/`lkv_mc` (lakes), `rev_mc`/`dor_pc` (reservoirs, degree of regulation), `ria_ha`/`riv_tc` (river area and volume), `gla_pc` (glaciers), `prm_pc` (permafrost), `wet_pc` (wetlands) |
| Soils and geology | `cly`/`slt`/`snd_pc` (clay, silt, sand), `soc_th` (organic carbon), `swc_pc` (soil water, monthly), `kar_pc` (karst), `ero_kh` (erosion), `lit_cl` (lithology) |
| Land cover | `glc_pc_s01` to `s22` (22 land-cover classes), `pnv_pc` (potential vegetation), `for_pc`, `crp_pc`, `pst_pc`, `ire_pc` (irrigated), `urb_pc`, `pac_pc` (protected) |
| Classifications | `clz_cl` (climate zone), `cls_cl`, `tbi_cl` (biome), `tec_cl`, `fmh_cl`, `fec_cl` (eco-regions) |
| Human influence | `hft_ix` (human footprint), `nli_ix` (night lights), `pop_ct`, `ppd_pk` (population), `rdd_mk` (roads), `gdp_ud`, `hdi_ix` |

Caveats for the attribute audit:
- `dis_m3_*` and `run_mm_syr` are **modelled flow**; the proposal excludes flow-derived attributes.
- The Caravan climate indices are computed over the **full record, test years included**; recompute them from training-period forcing.
- The `*_cl_*` columns are category codes, not numbers, and the monthly columns are highly redundant with each other.

### Bookkeeping files (`data/processed/`)

- `quality_report.csv`: every gauge pulled from the archive, including dropped ones: record length, missing fraction, first and last valid dates, negative-flow count, and the `keep` flag.
- `basin_list.csv`: kept gauge ids (makes the subset reproducible).
- `splits/`: the train/test split design written by `notebooks/02_preprocessing.ipynb`:
  - `basins.csv`: spatial block, fold, and valid years in the train and test periods for each basin.
  - `fold_roles.csv`: `test`/`train`/`buffer` per fold and basin, plus each training basin's distance to the nearest test basin.
  - `config.json`: periods and parameters.

`data/combined/` (one parquet per region) and `data/raw/` are git-ignored caches.
