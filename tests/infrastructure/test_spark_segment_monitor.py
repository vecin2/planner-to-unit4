from datetime import datetime
from uuid import uuid4

import pytest


try:
    from pyspark.sql import SparkSession
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    SparkSession = None

from planner_to_unit4.infrastructure.spark_segment_monitor import SparkSegmentMonitor


@pytest.mark.spark
def test_spark_segment_monitor_records_submission() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = SparkSession.builder.master("local[1]").appName("segment-monitor-test").getOrCreate()
    database_name = f"segment_monitoring_test_{uuid4().hex}"
    table_name = f"{database_name}.segment_monitoring"
    submitted_at = datetime(2026, 4, 12, 13, 0, 0)
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")

    monitor = SparkSegmentMonitor(spark=spark, table_name=table_name)
    monitor.record_submitted(
        pipeline_run_id="fabric-run-123",
        snapshot_path="snapshot-123",
        segment_index=1,
        segment_size=2,
        order_no="order-456",
        http_status=200,
        message=None,
        submitted_at_utc=submitted_at,
    )

    row = spark.table(table_name).collect()[0].asDict()
    assert row == {
        "pipeline_run_id": "fabric-run-123",
        "snapshot_path": "snapshot-123",
        "segment_index": 1,
        "segment_size": 2,
        "order_no": "order-456",
        "http_status": 200,
        "message": None,
        "submitted_at_utc": submitted_at,
    }

    spark.sql(f"DROP TABLE IF EXISTS {table_name}")
    spark.sql(f"DROP DATABASE IF EXISTS {database_name}")
    spark.stop()
