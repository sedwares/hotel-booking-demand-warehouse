# Hotel Booking Demand Warehouse

A dbt + Airflow + Postgres analytics warehouse built on **real, anonymized
PMS data** from two European hotels — not a synthetic dataset. The angle:
almost every public analysis of this dataset trains a classifier to predict
`is_canceled`. This instead treats cancellation, revenue, and room
assignment as **revenue-management reporting problems** — the tables an
actual hotel revenue manager would ask a data team to build.

## The dataset

**Antonio, N., de Almeida, A., & Nunes, L. (2019). "Hotel booking demand
datasets." *Data in Brief*, 22, 41-49.**

119,390 bookings from two real hotels — a resort (H1) and a city hotel
(H2) — arrivals between July 2015 and August 2017, hotel and guest
identifiers stripped for anonymization. Published specifically because
genuine business data is scarce for research and education. It carries the
fields revenue management actually runs on: lead time, market segment,
distribution channel, deposit type, reserved vs. assigned room type, days
on the waiting list, and the Transient / Transient-Party / Group / Contract
customer-type distinction.

**Honest framing, up front:** this is one of the most-used datasets on
Kaggle — thousands of notebooks exist against it, almost all doing
cancellation-prediction ML. The dataset itself isn't the differentiator
here; what's built on it is. It's also Portugal, 2015-2017 — a real,
representative hotel-ops dataset, not a stand-in for local-market analysis.

## Why this design is different from a typical Kaggle notebook on this data

- **A dbt warehouse, not a notebook.** Staged, tested, documented models —
  the way this data would actually get productionized, not a single
  `df.groupby()` chain.
- **Cancellation risk as a BI table, not an ML target.** `mart_cancellation_risk`
  segments cancellation rate by lead time, deposit type, market segment,
  and customer type — a report a revenue manager reads, not a model score.
- **An inferred capacity, defended in the open.** See below — this is the
  judgment call an ops background actually helps with.

## The capacity problem (the interesting part)

The dataset has no room-inventory count, so occupancy rate and RevPAR have
no ready-made denominator. `int_hotel_capacity` derives one: **the maximum
number of rooms occupied concurrently on any single night** across the full
2015-2017 window. A hotel cannot sell more rooms than it has, so the
observed peak is a hard floor on capacity.

That floor turns out to be well-behaved, not outlier-driven — the 99th
percentile of nightly occupied-room-counts sits within 1-3 rooms of the
max for both properties:

| Hotel | Assumed capacity (max concurrent) | 99th percentile | Avg nightly occupied |
|---|---|---|---|
| City Hotel | 226 | 225.0 | 169.2 |
| Resort Hotel | 187 | 184.0 | 148.7 |

That closeness means the hotel is genuinely near-full on dozens of nights,
not just one freak night — the kind of pattern a real property produces at
high season, not a data artifact.

**Stated limitation:** this is a floor, not a confirmed number. The
dataset only contains bookings that were actually made — if either hotel
sold out and turned guests away on a given night, that lost demand leaves
no row here, so true capacity could be somewhat higher than this estimate.
In a real analytics-engineering role this is exactly the kind of
assumption you'd flag to a stakeholder rather than quietly bake into a
number; it's documented in `int_hotel_capacity.sql` rather than buried as
a magic constant.

A second, smaller data-quality call: the raw data has one row with an ADR
of 5,400 (~50x the next-highest fare) and one with a negative ADR — both
look like PMS data-entry errors, not real rates. They're flagged
(`is_adr_outlier`) and excluded from revenue aggregations rather than
silently averaged in or silently dropped from the row set.

## What the marts actually found

Running the pipeline against the real data surfaced two things worth
flagging in a portfolio conversation:

1. **"Non Refund" deposits correlate with ~100% cancellation**, across
   nearly every segment that has meaningful volume — the opposite of what
   you'd expect from a deposit designed to lock guests in. This is a known
   quirk of this specific dataset (likely wholesaler/OTA block bookings
   using that deposit code, then being cancelled and rebooked), and it's
   exactly the kind of counterintuitive signal `mart_cancellation_risk` is
   built to surface rather than bury in an aggregate cancellation rate.
2. **Resort Hotel reassigns guests to a different room type 25.4% of the
   time** on honored stays, versus 14.7% at City Hotel — worth a follow-up
   conversation with ops about whether that's routine upgrading or a
   capacity-crunch pattern.

Headline numbers (city vs. resort, full window):

| | City Hotel | Resort Hotel |
|---|---|---|
| Bookings | 79,330 | 40,060 |
| Cancellation rate | 41.7% | 27.8% |
| Avg lead time | 109.7 days | 92.7 days |
| Avg ADR | €105.24 | €94.96 |
| Avg occupancy | 74.9% | 79.5% |
| Avg RevPAR | €79.71 | €76.98 |

## Architecture

```
 data/raw/hotel_bookings.csv  (static PMS extract, 119,390 rows)
              │
              ▼
      Postgres: raw.bookings          full-refresh load
              │                       (truncate + reload — see note below)
              ▼
    ┌──────────────────────┐
    │       Airflow          │   load raw → dbt run → dbt test
    └──────────┬────────────┘
               ▼
   ┌────────────────────────────────────────┐
   │           dbt: analytics.*              │
   │  staging → intermediate → marts          │
   │  dim_hotel, dim_date                     │
   │  fact_bookings, fact_room_nights          │
   │  mart_daily_metrics                       │
   │  mart_cancellation_risk                   │
   │  mart_hotel_comparison                    │
   │  mart_room_assignment_mismatch            │
   └──────────────────┬───────────────────────┘
                       ▼
            Streamlit Dashboard
```

### Why this DAG is full-refresh, not daily-incremental

This dataset is a fixed historical extract — published once, no new rows
ever land. Project 1's synthetic-hotel pipeline models a live PMS with a
daily-incremental DAG; that pattern would be dishonest here, since there's
nothing new to append each day. The right orchestration pattern for a
static source is an idempotent full-refresh: truncate `raw.bookings`,
reload the CSV, rebuild every dbt model, run tests — safely re-runnable
end to end. The DAG is scheduled weekly mainly to demonstrate that
re-runnability, not because the source changes.

## Data model

| Layer | Models | Purpose |
|---|---|---|
| Staging | `stg_bookings` | Clean, cast, derive arrival/departure dates, honored-stay flag, ADR-outlier flag |
| Intermediate | `int_booking_nights` | Explode honored stays into one row per night stayed |
| Intermediate | `int_hotel_capacity` | Infer room capacity per hotel (see above) |
| Marts | `dim_hotel`, `dim_date` | Conformed dimensions |
| Marts | `fact_bookings` | Booking grain, BI-ready, with lead-time buckets |
| Marts | `fact_room_nights` | Hotel × night grain — the occupancy/RevPAR foundation |
| Marts | `mart_daily_metrics` | Occupancy, ADR, RevPAR by hotel and day |
| Marts | `mart_cancellation_risk` | Cancellation rate by lead time, deposit type, market segment, customer type |
| Marts | `mart_hotel_comparison` | Resort vs. City, side by side |
| Marts | `mart_room_assignment_mismatch` | Reserved-vs-assigned room type analysis |

## Tech stack

Postgres 16 · dbt-postgres 1.8 · Apache Airflow 2.9 ·
Streamlit · Plotly · Docker Compose

Deliberately **zero external dbt packages** (no `dbt_utils`) — the date
spine and range-check tests are hand-written in `macros/` instead. This
was a real decision, not a style choice: `dbt_utils` requires reaching
`hub.getdbt.com` at `dbt deps` time, and that wasn't reachable while
building this in a network-restricted environment. Rather than leave a
dependency the project doesn't strictly need, it's written out entirely —
one less thing that can fail to install in a locked-down client environment
too.

## Setup

### 1. Start the infrastructure

```bash
docker compose up -d
```

Postgres on `localhost:5433` (offset from project 1's 5432 so both can run
side by side), Airflow UI at `http://localhost:8081`. Get the auto-generated
admin password with `docker compose logs airflow | grep password`.

### 2. Load the raw data and build the warehouse

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/load_raw_data.py

cd dbt/hotel_booking_demand
dbt run --profiles-dir ..
dbt test --profiles-dir ..
cd ../..
```

(The checked-in `data/raw/hotel_bookings.csv` is used directly; run
`python scripts/download_data.py` first if you'd rather re-fetch it. No
`dbt deps` step — see the tech stack note above.)

**Troubleshooting:** if `dbt --version` reports something calling itself
"dbt-oss" or flags the postgres adapter as experimental, your environment
resolved a pre-release `dbt-core` 2.x ("Fusion") instead of the classic
engine `dbt-postgres==1.8.2` was built against. Fix with
`pip install "dbt-core<2.0" dbt-postgres==1.8.2`.

### 3. Turn on the pipeline in Airflow

Un-pause `hotel_booking_demand_pipeline` in the Airflow UI to see the
full-refresh DAG run end to end.

### 4. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

## Verification note

Every model was actually built and tested against a live Postgres 16
instance with the real 119,390-row dataset while writing this — `dbt run`
and `dbt test` both passing (11 models, 30 tests), not just SQL written and
assumed correct. The numbers in "what the marts actually found" above are
real query output.

Worth saying plainly: the first pass at this project used `dbt_utils` for
the date spine and range-check tests, and — because `hub.getdbt.com`
wasn't reachable in the environment this was built in — that first pass
was only verified by running the *compiled* SQL by hand outside the dbt
CLI, not through `dbt run` itself. Removing the `dbt_utils` dependency
(see the tech stack note above) made it possible to actually run the real
dbt CLI end to end, which caught a genuine bug the hand-run SQL had
missed: dbt's default schema-naming behavior concatenates the profile's
target schema with any model `+schema` config, so `analytics` +
`schema: marts` silently became a table living in `analytics_marts`, not
`analytics` — which would have made the dashboard's `select * from
analytics.mart_x` queries fail against a real `dbt run`. Fixed by dropping
the `+schema` overrides in `dbt_project.yml` (see the comment there) so
everything lands in the profile's target schema directly. Flagging this
here because "I ran it and it broke, so I fixed it" is a more honest
account of building this than pretending it worked the first time.

## Project structure

```
hotel-booking-demand-warehouse/
├── docker-compose.yml          # Postgres (5433) + Airflow (8081)
├── data/raw/hotel_bookings.csv # the dataset (checked in - static, ~17MB)
├── sql/init.sql                 # raw schema DDL
├── scripts/
│   ├── download_data.py         # re-fetch the CSV from a public mirror
│   ├── load_raw_data.py         # full-refresh load into raw.bookings
│   └── db.py                    # shared Postgres connection helper
├── dbt/
│   ├── profiles.yml
│   └── hotel_booking_demand/
│       ├── dbt_project.yml
│       └── models/{staging,intermediate,marts}/
├── airflow/dags/hotel_booking_demand_dag.py
└── dashboard/app.py             # Streamlit + Plotly
```

## Possible extensions

- Cross-reference `mart_cancellation_risk` findings with a stated
  cancellation-policy change (deposit terms) to see if the pattern shifts
  over the 2015-2017 window
- Add a `days_in_waiting_list` mart — an underused signal in most public
  analyses of this dataset
- Point the same dbt project at a Snowflake target to show both warehouses
  from one modeling layer

## Citation

Antonio, N., de Almeida, A., & Nunes, L. (2019). Hotel booking demand
datasets. *Data in Brief*, 22, 41-49. https://doi.org/10.1016/j.dib.2018.11.126
