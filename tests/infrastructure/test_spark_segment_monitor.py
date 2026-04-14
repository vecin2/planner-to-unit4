from datetime import datetime

import pytest

from planner_to_unit4.infrastructure.spark_segment_monitor import (
    SparkSegmentMonitor,
    _truncate_message,
)
from tests.support.spark_test_utils import (
    SparkSession,
    cleanup_temp_table,
    create_spark_session,
    create_temp_table,
)


@pytest.mark.spark
def test_spark_segment_monitor_records_submission() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = create_spark_session("segment-monitor-test")
    database_name, table_name = create_temp_table(
        spark,
        database_prefix="segment_monitoring_test",
        table_name="segment_monitoring",
    )
    submitted_at = datetime(2026, 4, 12, 13, 0, 0)

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
        "status": "SUBMITTED",
        "order_no": "order-456",
        "http_status": 200,
        "message": None,
        "submitted_at_utc": submitted_at,
    }

    cleanup_temp_table(spark, table_name, database_name)


@pytest.mark.spark
def test_spark_segment_monitor_records_failure() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = create_spark_session("segment-monitor-test")
    database_name, table_name = create_temp_table(
        spark,
        database_prefix="segment_monitoring_test",
        table_name="segment_monitoring",
    )
    submitted_at = datetime(2026, 4, 12, 13, 30, 0)

    monitor = SparkSegmentMonitor(spark=spark, table_name=table_name)
    monitor.record_failed(
        pipeline_run_id="fabric-run-456",
        snapshot_path="snapshot-456",
        segment_index=2,
        segment_size=1,
        http_status=400,
        message="Bad request",
        submitted_at_utc=submitted_at,
    )

    row = spark.table(table_name).collect()[0].asDict()
    assert row == {
        "pipeline_run_id": "fabric-run-456",
        "snapshot_path": "snapshot-456",
        "segment_index": 2,
        "segment_size": 1,
        "status": "FAILED",
        "order_no": None,
        "http_status": 400,
        "message": "Bad request",
        "submitted_at_utc": submitted_at,
    }

    cleanup_temp_table(spark, table_name, database_name)


def test_truncate_message_limits_length() -> None:
    message = "a" * 4100

    truncated = _truncate_message(message, limit=4000)

    assert len(truncated) == 4000
    assert truncated.endswith("... (truncated)")
