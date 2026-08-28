"""
Pulls the latest NASA / NOAA / OWID climate data, re-runs the tipping point
analysis from the notebook, and writes the results to docs/data/ as JSON.
Run manually with `python scripts/update_data.py`, or let the GitHub Action
run it on a schedule.
"""
import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'docs' / 'data'
OUT_DIR.mkdir(parents=True, exist_ok=True)

GISTEMP_URL = 'https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv'
CO2_URL = 'https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv'
ICE_URL = ("https://ourworldindata.org/grapher/monthly-sea-ice-extent-in-the-arctic.csv"
           "?v=1&csvType=full&useColumnShortNames=false")

TIPPING_POINTS = {
    'Greenland Ice Sheet': {'code': 'GrIS', 'category': 'Global core', 'threshold': 1.5,
        'threshold_min': 0.8, 'threshold_max': 3.0,
        'consequence': 'Up to 7m sea level rise over millennia'},
    'W. Antarctic Ice Sheet': {'code': 'WAIS', 'category': 'Global core', 'threshold': 1.5,
        'threshold_min': 1.0, 'threshold_max': 3.0,
        'consequence': 'Up to 5m additional sea level rise'},
    'Labrador Sea Convection': {'code': 'LABC', 'category': 'Global core', 'threshold': 1.8,
        'threshold_min': 1.1, 'threshold_max': 3.8,
        'consequence': 'Regional cooling -3C, disrupted ocean circulation'},
    'E. Antarctic Subglacial Basins': {'code': 'EASB', 'category': 'Global core', 'threshold': 3.0,
        'threshold_min': 2.0, 'threshold_max': 6.0,
        'consequence': 'Significant additional sea level rise'},
    'Amazon Rainforest': {'code': 'AMAZ', 'category': 'Global core', 'threshold': 3.5,
        'threshold_min': 2.0, 'threshold_max': 6.0,
        'consequence': 'Dieback releases 30-75 GtC, regional rainfall collapse'},
    'Boreal Permafrost': {'code': 'PFTP', 'category': 'Global core', 'threshold': 4.0,
        'threshold_min': 3.0, 'threshold_max': 6.0,
        'consequence': '125-250 GtC released, +0.2-0.4C additional warming'},
    'AMOC Collapse': {'code': 'AMOC', 'category': 'Global core', 'threshold': 4.0,
        'threshold_min': 1.4, 'threshold_max': 8.0,
        'consequence': '-4 to -10C regional cooling, monsoon disruption'},
    'Arctic Winter Sea Ice': {'code': 'AWSI', 'category': 'Global core', 'threshold': 6.3,
        'threshold_min': 4.5, 'threshold_max': 8.7,
        'consequence': '+0.6C global warming, +0.6-1.2C regional'},
    'E. Antarctic Ice Sheet': {'code': 'EAIS', 'category': 'Global core', 'threshold': 7.5,
        'threshold_min': 5.0, 'threshold_max': 10.0,
        'consequence': '+0.6C global, +2C regional warming'},
    'Low-latitude Coral Reefs': {'code': 'REEF', 'category': 'Regional impact', 'threshold': 1.5,
        'threshold_min': 1.0, 'threshold_max': 2.0,
        'consequence': 'Die-off, 500M people lose coastal protection and food'},
    'Boreal Permafrost (abrupt thaw)': {'code': 'PFAT', 'category': 'Regional impact', 'threshold': 1.5,
        'threshold_min': 1.0, 'threshold_max': 2.3,
        'consequence': 'Adds 50% to gradual thaw, 10 GtC/C by 2100'},
    'Barents Sea Ice': {'code': 'BARI', 'category': 'Regional impact', 'threshold': 1.6,
        'threshold_min': 1.5, 'threshold_max': 1.7,
        'consequence': 'Abrupt Arctic sea ice loss, regional climate shift'},
    'Mountain Glaciers': {'code': 'GLCR', 'category': 'Regional impact', 'threshold': 2.0,
        'threshold_min': 1.5, 'threshold_max': 3.0,
        'consequence': '+0.08C global, freshwater loss for millions'},
    'Sahel & W. African Monsoon': {'code': 'SAHL', 'category': 'Regional impact', 'threshold': 2.8,
        'threshold_min': 2.0, 'threshold_max': 3.5,
        'consequence': 'Greening of Sahel, major rainfall pattern shift'},
    'Boreal Forest (dieback)': {'code': 'BORF', 'category': 'Regional impact', 'threshold': 4.0,
        'threshold_min': 1.4, 'threshold_max': 5.0,
        'consequence': '-0.18C global, -0.5 to -2C regional cooling'},
    'Boreal Forest (expansion)': {'code': 'TUND', 'category': 'Regional impact', 'threshold': 4.0,
        'threshold_min': 1.5, 'threshold_max': 7.2,
        'consequence': '+0.14C global, +0.5-1.0C regional warming'},
}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'tipping-tracker/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_temperature():
    raw = fetch(GISTEMP_URL)
    df = pd.read_csv(pd.io.common.BytesIO(raw), skiprows=1, na_values=['***'])
    df = df[['Year'] + MONTHS]
    long = df.melt(id_vars='Year', var_name='Month', value_name='anomaly_C')
    long['date'] = pd.to_datetime(long['Year'].astype(str) + '-' + long['Month'], format='%Y-%b')
    return long.dropna().sort_values('date').reset_index(drop=True)


def load_co2():
    raw = fetch(CO2_URL)
    df = pd.read_csv(pd.io.common.BytesIO(raw), comment='#')
    df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
    df = df[['date', 'average']].rename(columns={'average': 'co2_ppm'})
    return df[df['co2_ppm'] > 0].reset_index(drop=True)


def load_ice():
    raw = fetch(ICE_URL)
    df = pd.read_csv(pd.io.common.BytesIO(raw))
    df = df.rename(columns={
        'Entity': 'year', 'Year': 'month',
        'Monthly sea ice extent in the Arctic': 'extent_mkm2'
    })
    df['month_name'] = df['month'].apply(lambda m: MONTHS[m - 1])
    return df


def main():
    temp_long = load_temperature()
    co2_df = load_co2()
    ice_df = load_ice()

    # re-reference GISS (1951-1980 baseline) to pre-industrial (1880-1899)
    pi_baseline = temp_long[temp_long['Year'].between(1880, 1899)]['anomaly_C'].mean()
    temp_long['anomaly_pi'] = temp_long['anomaly_C'] - pi_baseline

    month_counts = temp_long.groupby('Year').size()
    complete_years = month_counts[month_counts == 12].index
    annual_temp = (
        temp_long[temp_long['Year'].isin(complete_years)]
        .groupby('Year')['anomaly_pi'].mean().reset_index()
    )
    annual_temp.columns = ['year', 'anomaly_C']
    annual_temp['rolling_10yr'] = annual_temp['anomaly_C'].rolling(10, center=True).mean()

    window_years = 20
    current_temp = annual_temp['anomaly_C'].tail(window_years).mean()
    current_temp_2yr = annual_temp['anomaly_C'].tail(2).mean()
    current_co2 = co2_df['co2_ppm'].iloc[-1]

    # post-1980 warming trend, Newey-West (HAC) standard errors
    recent = annual_temp[annual_temp['year'] >= 1980]
    y_obs = recent['anomaly_C'].to_numpy(dtype=float)
    X_obs = sm.add_constant(recent['year'].to_numpy(dtype=float))
    ols = sm.OLS(y_obs, X_obs).fit()
    maxlags = int(np.floor(4 * (len(y_obs) / 100) ** (2 / 9)))
    hac = sm.OLS(y_obs, X_obs).fit(cov_type='HAC', cov_kwds={'maxlags': maxlags})
    intercept, slope = hac.params
    stderr = hac.bse[1]
    r2 = ols.rsquared

    def crossing_year(target):
        return (target - intercept) / slope

    # Arctic September sea ice linear trend
    sept_ice = ice_df[ice_df['month_name'] == 'Sep'].copy()
    t0 = int(sept_ice['year'].min())
    t = sept_ice['year'].to_numpy(dtype=float) - t0
    y_ice = sept_ice['extent_mkm2'].to_numpy(dtype=float)
    ice_lags = int(np.floor(4 * (len(y_ice) / 100) ** (2 / 9)))
    fit_lin = sm.OLS(y_ice, sm.add_constant(t)).fit(cov_type='HAC', cov_kwds={'maxlags': ice_lags})
    ice_rate = fit_lin.params[1] * 10  # per decade

    proj_years = np.arange(t0, 2090)
    b0, b1 = fit_lin.params
    proj_extent = np.clip(b0 + b1 * (proj_years - t0), 0, None)
    below = proj_years[proj_extent < 1.0]
    ice_free_year = int(below[0]) if len(below) else None

    # CO2 vs temperature correlation
    annual_co2 = co2_df.assign(year=co2_df['date'].dt.year).groupby('year')['co2_ppm'].mean().reset_index()
    merged = pd.merge(annual_temp, annual_co2, on='year').dropna()
    corr = merged['anomaly_C'].corr(merged['co2_ppm'])
    co2_recent = co2_df[co2_df['date'].dt.year >= co2_df['date'].dt.year.max() - 10]
    co2_rate = np.polyfit(co2_recent['date'].dt.year + co2_recent['date'].dt.month / 12,
                           co2_recent['co2_ppm'], 1)[0]

    # tipping point proximity scores
    results = []
    for name, info in TIPPING_POINTS.items():
        distance = round(info['threshold'] - current_temp, 2)
        score = round(min((current_temp / info['threshold']) * 100, 100), 1)
        score_low = round(min((current_temp / info['threshold_max']) * 100, 100), 1)
        score_high = round(min((current_temp / info['threshold_min']) * 100, 100), 1)
        years_left = round(distance / slope) if distance > 0 else 0
        results.append({
            'name': name, 'code': info['code'], 'category': info['category'],
            'threshold': info['threshold'], 'threshold_min': info['threshold_min'],
            'threshold_max': info['threshold_max'], 'distance': distance,
            'proximity_score': score, 'proximity_score_low': score_low,
            'proximity_score_high': score_high, 'years_remaining': years_left,
            'crossed': distance <= 0, 'consequence': info['consequence'],
        })
    results_df = pd.DataFrame(results).sort_values('distance').reset_index(drop=True)
    n_crossed = int(results_df['crossed'].sum())
    n_near = int(((results_df['distance'] > 0) & (results_df['distance'] <= 0.5)).sum())

    # Monte Carlo crossing probabilities
    rng = np.random.default_rng(42)
    n_sims = 20_000
    current_year = int(annual_temp['year'].max())
    horizon = 2200
    mc_records = []
    for name, info in TIPPING_POINTS.items():
        thresholds = rng.triangular(info['threshold_min'], info['threshold'], info['threshold_max'], n_sims)
        rates = rng.normal(slope, stderr, n_sims)
        gap = thresholds - current_temp
        with np.errstate(divide='ignore', invalid='ignore'):
            years_to = np.where(gap <= 0, 0.0, gap / rates)
        years_to = np.where((gap > 0) & (rates <= 0), np.inf, years_to)
        cross_yr = current_year + years_to
        q50 = np.percentile(np.minimum(cross_yr, horizon), 50)
        mc_records.append({
            'name': name, 'code': info['code'], 'category': info['category'],
            'p_already': round(float((gap <= 0).mean()), 3),
            'p_2050': round(float((cross_yr <= 2050).mean()), 3),
            'p_2100': round(float((cross_yr <= 2100).mean()), 3),
            'median_year': int(round(q50)),
        })
    mc_df = pd.DataFrame(mc_records).sort_values('p_2100', ascending=False).reset_index(drop=True)
    core_risk = mc_df[(mc_df['category'] == 'Global core') & (mc_df['p_2100'] >= 0.5)]
    soonest = mc_df.nsmallest(1, 'median_year').iloc[0]

    summary = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'current_year': current_year,
        'window_years': window_years,
        'current_temp': round(float(current_temp), 3),
        'current_temp_2yr': round(float(current_temp_2yr), 3),
        'warming_per_decade': round(float(slope * 10), 4),
        'stderr_per_decade': round(float(stderr * 10), 4),
        'r_squared': round(float(r2), 3),
        'current_co2': round(float(current_co2), 1),
        'co2_rate_per_year': round(float(co2_rate), 2),
        'co2_temp_corr': round(float(corr), 3),
        'ice_rate_per_decade': round(float(ice_rate), 3),
        'ice_free_year_extrapolated': ice_free_year,
        'n_total': len(results_df),
        'n_crossed': n_crossed,
        'n_near': n_near,
        'year_1p5': int(round(crossing_year(1.5))),
        'year_2p0': int(round(crossing_year(2.0))),
        'n_sims': n_sims,
        'n_core_risk_this_century': len(core_risk),
        'soonest_element': soonest['name'],
        'soonest_median_year': int(soonest['median_year']),
    }

    (OUT_DIR / 'summary.json').write_text(json.dumps(summary, indent=2))
    (OUT_DIR / 'proximity.json').write_text(results_df.to_json(orient='records', indent=2))
    (OUT_DIR / 'monte_carlo.json').write_text(mc_df.to_json(orient='records', indent=2))
    annual_out = annual_temp[['year', 'anomaly_C', 'rolling_10yr']].round(3)
    (OUT_DIR / 'annual_temp.json').write_text(annual_out.to_json(orient='records', indent=2))

    print(f"Updated data as of {date.today().isoformat()}: "
          f"+{current_temp:.2f}C, CO2 {current_co2:.0f} ppm, "
          f"{n_crossed}/{len(results_df)} thresholds crossed")


if __name__ == '__main__':
    main()
