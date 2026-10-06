"""
Hotel Booking Demand warehouse - full-refresh orchestration DAG.

Unlike project 1's daily-incremental DAG, this dataset is a fixed
historical extract (2015-2017 arrivals, published once in 2019) - there's
no new data landing each day. The honest orchestration pattern here is
idempotent full-refresh: truncate + reload raw, rebuild every dbt model,
run tests. Scheduled weekly mainly to demonstrate that the pipeline is
safely re-runnable end to end, not because the source data changes.

Pipeline:
    1. Load the static CSV into raw.bookings (full truncate + reload).
    2. Run dbt models: staging -> intermediate -> marts.
    3. Run dbt tests.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

DBT_PROJECT_DIR = "/opt/airflow/dbt/hotel_booking_demand"
DBT_PROFILES_DIR = "/opt/airflow/dbt"

default_args = {
    "owner": "sedar",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _load_raw_data(**context):
    import sys

    sys.path.append("/opt/airflow")
    from scripts.load_raw_data import main

    main()


with DAG(
    dag_id="hotel_booking_demand_pipeline",
    description="Full-refresh ELT: static hotel booking CSV -> raw -> dbt transform + test",
    default_args=default_args,
    schedule_interval="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["hotel", "dbt", "analytics", "full-refresh"],
) as dag:

    load_raw_data = PythonOperator(
        task_id="load_raw_data",
        python_callable=_load_raw_data,
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt deps --profiles-dir {DBT_PROFILES_DIR}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --profiles-dir {DBT_PROFILES_DIR} --full-refresh",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --profiles-dir {DBT_PROFILES_DIR}",
    )

    load_raw_data >> dbt_deps >> dbt_run >> dbt_test
