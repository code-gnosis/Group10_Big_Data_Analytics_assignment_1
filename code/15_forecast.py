# Section 8 - forecast next day using previous-day baseline + regression model
import math
import json
import psycopg2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

# load hourly regional energy
conn = psycopg2.connect(
    host="127.0.0.1", port=5433, dbname="energy_grid",
    user="auca", password="gishushu"
)
cur = conn.cursor()
cur.execute("SET TIME ZONE 'Africa/Kigali'")
cur.execute("""
    SELECT date_trunc('hour', e.event_time) AS hour,
           m.region, SUM(e.energy_kwh)
    FROM energy_readings e JOIN meters m USING (meter_id)
    GROUP BY 1, m.region ORDER BY 1, m.region
""")
rows = cur.fetchall()
cur.close()
conn.close()

df = pd.DataFrame(rows, columns=["hour", "region", "energy_kwh"])
df["hour"] = pd.to_datetime(df["hour"]).dt.tz_localize(None)
df["energy_kwh"] = df["energy_kwh"].astype(float)
print("dataset rows:", len(df))

# pivot so each region is a column
piv = df.pivot(index="hour", columns="region", values="energy_kwh")
print("hours:", len(piv), "regions:", piv.shape[1])

# split dates
train_end = pd.Timestamp("2026-09-15")
val_end   = pd.Timestamp("2026-09-22")
test_end  = pd.Timestamp("2026-09-29")
print("train 2026-09-01 to", train_end.date())
print("val  ", train_end.date(), "to", val_end.date())
print("test ", val_end.date(), "to", test_end.date())

def mae(a, b):
    return float(np.mean(np.abs(a - b)))

def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))

baseline_actuals = []
baseline_preds   = []
model_actuals    = []
model_preds      = []
region_data = {}

for region in sorted(piv.columns):
    y = piv[region]

    # calendar + lag features
    features = pd.DataFrame(index=y.index)
    features["hour_of_day"] = y.index.hour
    features["day_of_week"] = y.index.dayofweek
    features["is_weekend"]  = (y.index.dayofweek >= 5).astype(int)
    features["lag_24h"]     = y.shift(24)
    features["lag_48h"]     = y.shift(48)
    features["lag_168h"]    = y.shift(168)
    features["rolling7"]    = y.shift(24).rolling(168).mean()
    features["y"] = y.values
    features = features.dropna()

    train = features.loc[features.index < train_end]
    val   = features.loc[(features.index >= train_end) & (features.index < val_end)]
    test  = features.loc[(features.index >= val_end)   & (features.index < test_end)]

    # baseline = previous day same hour (= lag_24h column)
    bp = test["lag_24h"].values
    ba = test["y"].values
    baseline_actuals.extend(ba)
    baseline_preds.extend(bp)

    # try two GB configs on validation, pick lowest MAE
    X_tr, y_tr = train.drop(columns=["y"]), train["y"]
    X_va, y_va = val.drop(columns=["y"]),   val["y"]
    X_te, y_te = test.drop(columns=["y"]),  test["y"]

    best = None
    best_mae = 1e18
    for cfg_name, params in [
        ("A", {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05}),
        ("B", {"n_estimators": 400, "max_depth": 5, "learning_rate": 0.03}),
    ]:
        m = GradientBoostingRegressor(random_state=42, **params)
        m.fit(X_tr, y_tr)
        p = m.predict(X_va)
        v = mae(y_va.values, p)
        if v < best_mae:
            best_mae = v
            best = m
            best_name = cfg_name

    tp = best.predict(X_te)
    model_actuals.extend(y_te.values)
    model_preds.extend(tp)
    region_data[region] = {
        "idx": test.index, "actual": y_te.values,
        "baseline": bp, "model": tp, "cfg": best_name
    }

baseline_actuals = np.array(baseline_actuals)
baseline_preds   = np.array(baseline_preds)
model_actuals    = np.array(model_actuals)
model_preds      = np.array(model_preds)

print()
print("test predictions:", len(baseline_preds))
print("baseline  MAE =", round(mae(baseline_actuals, baseline_preds), 3),
      " RMSE =", round(rmse(baseline_actuals, baseline_preds), 3))
print("GB model  MAE =", round(mae(model_actuals, model_preds), 3),
      " RMSE =", round(rmse(model_actuals, model_preds), 3))

print()
print("per-region MAE:")
print(f"{'region':<12} {'baseline':>10} {'model':>10}")
for region in sorted(piv.columns):
    bp = region_data[region]["baseline"]
    ba = region_data[region]["actual"]
    mp = region_data[region]["model"]
    print(f"{region:<12} {mae(ba, bp):>10.3f} {mae(ba, mp):>10.3f}")

# peak-hour errors
print()
print("peak hour errors per region:")
for region in sorted(piv.columns):
    d = region_data[region]
    i = int(np.argmax(d["actual"]))
    print(f"  {region} peak at {d['idx'][i]} actual={d['actual'][i]:.1f} "
          f"baseline_err={abs(d['actual'][i]-d['baseline'][i]):.1f} "
          f"model_err={abs(d['actual'][i]-d['model'][i]):.1f}")

# plot one region
r1 = region_data["Region 1"]
plt.figure(figsize=(11, 4))
plt.plot(r1["idx"], r1["actual"],   label="actual",   color="black")
plt.plot(r1["idx"], r1["baseline"], label="baseline (previous day)", alpha=0.7)
plt.plot(r1["idx"], r1["model"],    label="GB model", alpha=0.7)
plt.title("Region 1 - 7 test days")
plt.xlabel("CAT hour")
plt.ylabel("energy_kwh")
plt.legend()
plt.tight_layout()
plt.savefig("../outputs/fig_84_forecast_region1.png", dpi=120)
plt.close()

print()
print("figures saved to outputs/")
