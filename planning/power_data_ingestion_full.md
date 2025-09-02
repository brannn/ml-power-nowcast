# Power Demand Data Ingestion for NYISO and CAISO

This document provides an **in-depth analysis** of the correct public
API endpoints and data sources for power demand data from NYISO and
CAISO. It also explains why your original approach had some pitfalls,
and gives recommended **drop-in code fixes** for your ingestion module.

------------------------------------------------------------------------

# Where to Get the Data

## NYISO (New York)

### 1. Real-time actual load (5-minute) -- "P-58B / pal" CSVs

-   NYISO publishes **daily CSVs** and **monthly ZIP archives** of
    5-minute "Real-Time Actual Load" by zone.\
-   Files look like:\
    `https://mis.nyiso.com/public/csv/pal/YYYYMMDDpal.csv`\
-   CSV has columns: **`Time Stamp, Name, PTID, Load`**\
-   These are **zonal values**, *not* statewide totals.\
-   ⚠️ Your current filter on PTID **61757** is incorrect: this PTID
    corresponds to the **CAPITL zone**, not statewide (NYCA).\
-   ✅ To get **statewide load (NYCA)**, **sum all zones** per
    timestamp.

### 2. Historical hourly actual load (easy one-stop)

-   The U.S. EIA maintains cleaned **annual CSVs** for NYISO Hourly
    Actual Load by zone.\
-   This is very convenient for building **multi-year training sets**
    without stitching hundreds of daily CSVs.

------------------------------------------------------------------------

## CAISO (California)

### 1. OASIS API (official, best for programmatic pulls)

-   Base: `https://oasis.caiso.com/oasisapi/SingleZip`\
-   Query parameters example:
    -   `queryname=SLD_FCST` (system demand forecast family)\
    -   `startdatetime=YYYYMMDDThh:mm-0000`\
    -   `enddatetime=YYYYMMDDThh:mm-0000`\
    -   `version=1`\
    -   `granularity=15MIN`\
    -   `market_run_id=ACTUAL`\
-   **Data retention:** about 39 months (per CAISO FAQ).\
-   ⚠️ Different reports have different **date range limits** (some
    allow only daily requests). Pull in small chunks.

### 2. Today's Outlook (quick CSVs, 5-minute)

-   Web dashboard with downloadable CSVs for **Demand** and **Net
    Demand**.\
-   Great for quickly grabbing **today's data** or the past day.\
-   But: CAISO itself warns this feed is **"for informational
    purposes"**; OASIS is the authoritative source.

> **Practical approach:**\
> • Use **OASIS** for durable, historical pulls (chunked weekly or
> daily).\
> • Use **Today's Outlook CSV** for "grab now" convenience, then
> backfill from OASIS later.

------------------------------------------------------------------------

# Drop-in Code Patches

## NYISO Fixer (sum zones, not PTID filter)

``` python
def fetch_nyiso_data(days: int = 365) -> pd.DataFrame:
    """
    NYISO statewide real-time actual load (5-min) via P-58B 'pal' CSVs.
    Sums all zones per timestamp to produce NYCA total.
    """
    from datetime import datetime, timedelta
    import requests
    from io import StringIO

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    day_list = pd.date_range(start=start_dt.date(), end=end_dt.date(), freq="D", tz="UTC")

    frames = []
    for d in day_list:
        url = f"https://mis.nyiso.com/public/csv/pal/{d.strftime('%Y%m%d')}pal.csv"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                continue
            df = pd.read_csv(StringIO(r.text))
            ts_col = 'Time Stamp' if 'Time Stamp' in df.columns else None
            if ts_col is None or 'Load' not in df.columns:
                continue
            # ✅ Sum all zones at each timestamp
            g = (df[[ts_col, 'Load']]
                 .assign(**{ts_col: pd.to_datetime(df[ts_col])})
                 .groupby(ts_col, as_index=False)['Load'].sum()
                 .rename(columns={ts_col: 'timestamp', 'Load': 'load'}))
            frames.append(g)
        except requests.RequestException:
            continue

    if not frames:
        raise RuntimeError("NYISO: no data retrieved; check P-58B availability or date range.")

    out = pd.concat(frames, ignore_index=True).dropna()
    out = out.sort_values('timestamp').reset_index(drop=True)
    out['region'] = 'NYISO'
    out['data_source'] = 'nyiso_p58b_pal'
    return out[['timestamp', 'load', 'region', 'data_source']]
```

**Why this change?**\
Because **61757 ≠ statewide**. Filtering by PTID 61757 only gives the
CAPITL zone. Summing all zones is the only way to reconstruct **NYCA
total**.

------------------------------------------------------------------------

## CAISO Fixer (chunked OASIS fetch + fallback)

``` python
def fetch_caiso_data(days: int = 365) -> pd.DataFrame:
    """
    CAISO system demand via OASIS SingleZip (official) with a fallback to Today's Outlook CSV.
    Returns a statewide time series (timestamp UTC, MW).
    """
    import requests, zipfile
    from io import BytesIO
    from datetime import datetime, timedelta, timezone

    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=days)
    base = "https://oasis.caiso.com/oasisapi/SingleZip"
    chunk_days = 7
    frames = []

    cur = start_utc
    while cur < end_utc:
        s, e = cur, min(cur + timedelta(days=chunk_days), end_utc)
        params = {
            "queryname": "SLD_FCST",
            "startdatetime": s.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": e.strftime("%Y%m%dT%H:%M-0000"),
            "version": "1",
            "granularity": "15MIN",
            "market_run_id": "ACTUAL",
        }
        try:
            r = requests.get(base, params=params, timeout=90)
            if r.status_code == 200 and r.content:
                with zipfile.ZipFile(BytesIO(r.content)) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".csv"):
                            with z.open(name) as f:
                                df = pd.read_csv(f)
                                if "INTERVALSTARTTIME_GMT" in df.columns and "MW" in df.columns:
                                    g = pd.DataFrame({
                                        "timestamp": pd.to_datetime(df["INTERVALSTARTTIME_GMT"]),
                                        "load": pd.to_numeric(df["MW"], errors="coerce")
                                    }).dropna()
                                    frames.append(g)
        except requests.RequestException:
            pass
        cur = e

    if not frames:
        raise RuntimeError("CAISO OASIS fetch returned no data. Consider Today's Outlook CSV.")

    out = pd.concat(frames, ignore_index=True).dropna()
    out = out.sort_values("timestamp").reset_index(drop=True)
    out["region"] = "CAISO"
    out["data_source"] = "caiso_oasis_sld"
    return out[["timestamp", "load", "region", "data_source"]]
```

------------------------------------------------------------------------

# Suggested CLI Improvements

-   Add a `--granularity` option (5-min vs hourly).\
-   Add a `--backfill` flag (to walk older months/years automatically).\
-   Normalize everything to **UTC timestamps**.\
-   Store a "source granularity" field (5m/hourly) so you can resample
    consistently.\
-   For NYISO, consider **EIA hourly CSVs** as a long-history fallback
    when `--days` is large.

------------------------------------------------------------------------

# Summary

-   **NYISO:** Use P-58B pal CSVs, **sum all zones** (don't filter PTID
    61757). For longer histories, EIA hourly CSVs are easier.\
-   **CAISO:** Use OASIS `SingleZip` with short time windows; retention
    \~39 months. Fallback to Today's Outlook CSVs for recent data.\
-   **Both:** Normalize to UTC, chunk long queries, and persist locally
    to avoid re-downloading.

This ensures you get **consistent, statewide demand series** that can
fuel your **power nowcasting ML POC** with accurate, well-structured
historical and current data.
