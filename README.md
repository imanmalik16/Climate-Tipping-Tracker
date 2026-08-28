# Climate Tipping Point Tracker

A live dashboard tracking how close Earth's major climate systems are to the
warming thresholds identified in Armstrong McKay et al. (2022, *Science*).
Current warming, tipping point proximity scores, and Monte Carlo crossing
probabilities, pulled from NASA, NOAA, and NSIDC and refreshed automatically
every week.

**Live site:** https://imanmalik16.github.io/Climate-Tipping-Tracker/

## What it shows

- Current global warming against a pre-industrial baseline, and the rate
  it's rising at
- Atmospheric CO2 and how it tracks with temperature
- A proximity score for each of 16 tipping elements (Greenland ice sheet,
  AMOC, Amazon dieback, coral reefs, and others), how far each sits from its
  threshold in degrees
- A 20,000-run Monte Carlo simulation giving the probability each element
  crosses its threshold by 2050 and by 2100, accounting for uncertainty in
  both the threshold itself and the warming rate

## Repository structure

```
notebooks/
  1_climate_tipping.ipynb        the full analysis: data loading, EDA,
                                  proximity scores, Monte Carlo, limitations
  2_temperature_forecast.ipynb   backtests whether a better forecasting
                                  model beats the linear trend notebook 1
                                  extrapolates from (see Methodology below)
scripts/
  update_data.py                 re-runs the notebook 1 analysis against
                                  live data and writes docs/data/*.json
docs/
  index.html                     the dashboard (static, no build step)
  data/                          generated JSON the dashboard reads
.github/workflows/
  update.yml                     runs update_data.py weekly and commits
                                  the refreshed numbers
```

## Methodology

Thresholds are from Table 1 of Armstrong McKay et al. (2022), expressed as
global mean surface temperature above the 1850-1900 baseline. NASA's
GISTEMP series uses a 1951-1980 baseline, so it's re-referenced to
1880-1899 (the earliest window GISTEMP covers) before comparison.

**Proximity score** = current warming / threshold x 100. It's a distance
measure, not a probability, an element scoring 70 is 70% of the way there in
degrees, not 70% likely to tip.

**Crossing probabilities** come from a Monte Carlo simulation: each
element's threshold is drawn from a triangular distribution over its
published low/best/high estimate, the warming rate is drawn from a normal
distribution around the post-1980 trend (with Newey-West standard errors,
since annual temperature residuals are autocorrelated), and the two are
combined 20,000 times per element.

`2_temperature_forecast.ipynb` checks the load-bearing assumption in
notebook 1: that a straight line through the post-1980 trend is a
reasonable way to extrapolate crossing dates. It backtests a linear trend
against a persistence baseline and a ridge regression with lagged ENSO,
using an expanding window so each prediction only sees data available at
that point in time. Result: ridge modestly beats the linear trend at 1-year
and 10-year horizons, and the linear trend runs about 6 years low on a
10-year forecast. That's small next to the decades-to-centuries spread in
the Monte Carlo's threshold uncertainty, so it doesn't change the
dashboard's headline numbers, but it's the honest caveat on where they come
from.

Known limitations (also documented in the notebook): the baseline
conversion introduces a small offset, current warming is sensitive to the
choice of averaging window, and using global mean temperature as a single
control parameter for every tipping element is a simplification, some
respond to regional or ocean-specific temperatures rather than the global
mean.

## Data sources

- [NASA GISS Surface Temperature Analysis (GISTEMP v4)](https://data.giss.nasa.gov/gistemp/)
- [NOAA Global Monitoring Laboratory, Mauna Loa CO2](https://gml.noaa.gov/ccgg/trends/)
- [NSIDC Arctic sea ice extent, via Our World in Data](https://ourworldindata.org/grapher/monthly-sea-ice-extent-in-the-arctic)
- Armstrong McKay, D.I. et al. (2022). Exceeding 1.5C global warming could
  trigger multiple climate tipping points. *Science*, 377(6611), eabn7950.
  [doi:10.1126/science.abn7950](https://doi.org/10.1126/science.abn7950)

### If a scheduled run fails

`update_data.py` raises an error rather than writing bad data if NASA,
NOAA, or OWID change their file formats (it carries over the same assert
checks the notebook uses). Check the Actions log for the specific
assertion that failed.
