from __future__ import annotations

from datetime import datetime

from planner_to_unit4.infrastructure.segment_monitor import SegmentMonitor


class SparkSegmentMonitor(SegmentMonitor):
    def __init__(self, spark, table_name: str) -> None:
        self.spark = spark
        self.table_name = table_name

    def record_submitted(
        self,
        pipeline_run_id: str,
        snapshot_path: str,
        segment_index: int,
        segment_size: int,
        order_no: str,
        http_status: int | None,
        message: str | None,
        submitted_at_utc: datetime,
    ) -> None:
        record = {
            "pipeline_run_id": pipeline_run_id,
            "snapshot_path": snapshot_path,
            "segment_index": segment_index,
            "segment_size": segment_size,
            "status": "SUBMITTED",
            "order_no": order_no,
            "http_status": http_status,
            "message": _truncate_message(message),
            "submitted_at_utc": submitted_at_utc,
        }
        self._write_record(record)

    def record_failed(
        self,
        pipeline_run_id: str,
        snapshot_path: str,
        segment_index: int,
        segment_size: int,
        http_status: int | None,
        message: str | None,
        submitted_at_utc: datetime,
    ) -> None:
        record = {
            "pipeline_run_id": pipeline_run_id,
            "snapshot_path": snapshot_path,
            "segment_index": segment_index,
            "segment_size": segment_size,
            "status": "FAILED",
            "order_no": None,
            "http_status": http_status,
            "message": _truncate_message(message),
            "submitted_at_utc": submitted_at_utc,
        }
        self._write_record(record)

    def _write_record(self, record: dict[str, object]) -> None:
        from pyspark.sql.types import (
            IntegerType,
            StringType,
            StructField,
            StructType,
            TimestampType,
        )

        schema = StructType(
            [
                StructField("pipeline_run_id", StringType(), nullable=False),
                StructField("snapshot_path", StringType(), nullable=False),
                StructField("segment_index", IntegerType(), nullable=False),
                StructField("segment_size", IntegerType(), nullable=False),
                StructField("status", StringType(), nullable=False),
                StructField("order_no", StringType(), nullable=True),
                StructField("http_status", IntegerType(), nullable=True),
                StructField("message", StringType(), nullable=True),
                StructField("submitted_at_utc", TimestampType(), nullable=False),
            ]
        )
        dataframe = self.spark.createDataFrame([record], schema=schema)
        dataframe.write.mode("append").saveAsTable(self.table_name)


def _truncate_message(message: str | None, limit: int = 4000) -> str | None:
    if message is None:
        return None
    if len(message) <= limit:
        return message
    return f"{message[:limit]}... (truncated)"
