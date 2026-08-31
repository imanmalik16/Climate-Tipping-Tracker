# Climate Tipping Point Tracker

A live dashboard that tracks how close 16 major climate systems are to published global warming thresholds. It combines data from NASA, NOAA, and NSIDC with Monte Carlo simulation and temperature forecasting. Data updates automatically each week through GitHub Actions.

**Live dashboard:** [imanmalik16.github.io/Climate-Tipping-Tracker](https://imanmalik16.github.io/Climate-Tipping-Tracker/)

## Key features

* Tracks current warming relative to a pre-industrial baseline
* Compares atmospheric CO2 levels with global temperature
* Calculates proximity scores and remaining warming for 16 climate tipping elements
* Estimates the probability of crossing each threshold by 2050 and 2100 using 20,000 Monte Carlo simulations
* Backtests linear trend and ridge regression temperature forecasts
* Refreshes the dashboard weekly with an automated data pipeline

## Tools

Python, Jupyter Notebook, HTML, CSS, JavaScript, statistical modeling, Monte Carlo simulation, and GitHub Actions.

## Methodology

Tipping thresholds come from Armstrong McKay et al. (2022) and are expressed as global mean surface temperature above the 1850-1900 baseline. NASA GISTEMP uses a 1951-1980 baseline, so the temperature series is adjusted using the earliest available GISTEMP period, 1880-1899, before comparison.

### Proximity scores

Each score measures how much of a tipping element's estimated temperature threshold has been reached:

```text
proximity score = current warming / threshold × 100
```

A score of 70 means current warming is 70% of the way to the threshold. It does not mean the element has a 70% probability of tipping.

### Crossing probabilities

The Monte Carlo analysis runs 20,000 simulations per tipping element. Each simulation:

1. Samples a threshold from a triangular distribution using the published low, central, and high estimates.
2. Samples a warming rate from a normal distribution around the post-1980 trend.
3. Calculates whether the sampled threshold is crossed by 2050 or 2100.

Newey-West standard errors are used to account for autocorrelation in annual temperature residuals.

### Forecast validation

`2_temperature_forecast.ipynb` tests whether a linear trend is a reasonable basis for estimating future crossing dates. It compares:

* A linear temperature trend
* A persistence baseline
* Ridge regression with lagged ENSO data

The models are evaluated with expanding-window backtesting, so each prediction uses only information available at that time.

Ridge regression performs slightly better at 1-year and 10-year horizons. The linear model predicts about six years too early at the 10-year horizon. This difference is small relative to the wider uncertainty in published tipping thresholds, so it does not materially change the dashboard results.

## Repository structure

```text
notebooks/
  1_climate_tipping.ipynb
    Data loading, exploratory analysis, proximity scores,
    Monte Carlo simulation, and limitations

  2_temperature_forecast.ipynb
    Forecast model comparison and backtesting

scripts/
  update_data.py
    Downloads current data, reruns the analysis, and writes
    the dashboard JSON files

docs/
  index.html
    Static dashboard

  data/
    Generated JSON files used by the dashboard

.github/workflows/
  update.yml
    Runs the update script weekly and commits refreshed data
```

## Limitations

* Converting between temperature baselines introduces a small offset.
* Current warming estimates depend on the selected averaging period.
* Global mean temperature is used as the control variable for every tipping element, although some systems respond more directly to regional or ocean temperatures.
* Crossing probabilities represent threshold exceedance, not the probability or timing of the physical tipping process itself.

## Data sources

* [NASA GISS Surface Temperature Analysis, GISTEMP v4](https://data.giss.nasa.gov/gistemp/)
* [NOAA Global Monitoring Laboratory, Mauna Loa CO2](https://gml.noaa.gov/ccgg/trends/)
* [NSIDC Arctic sea ice extent via Our World in Data](https://ourworldindata.org/grapher/monthly-sea-ice-extent-in-the-arctic)
* [Armstrong McKay et al. (2022), *Science*](https://doi.org/10.1126/science.abn7950)

## Troubleshooting scheduled updates

`update_data.py` validates incoming data before writing new dashboard files. If NASA, NOAA, or Our World in Data changes a file format, the script stops instead of publishing invalid results. Check the GitHub Actions log to identify the failed validation.
