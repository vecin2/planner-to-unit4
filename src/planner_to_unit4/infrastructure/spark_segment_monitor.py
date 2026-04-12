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
        from pyspark.sql.types import (
            IntegerType,
            StringType,
            StructField,
            StructType,
            TimestampType,
        )

        record = {
            "pipeline_run_id": pipeline_run_id,
            "snapshot_path": snapshot_path,
            "segment_index": segment_index,
            "segment_size": segment_size,
            "order_no": order_no,
            "http_status": http_status,
            "message": message,
            "submitted_at_utc": submitted_at_utc,
        }
        schema = StructType(
            [
                StructField("pipeline_run_id", StringType(), nullable=False),
                StructField("snapshot_path", StringType(), nullable=False),
                StructField("segment_index", IntegerType(), nullable=False),
                StructField("segment_size", IntegerType(), nullable=False),
                StructField("order_no", StringType(), nullable=False),
                StructField("http_status", IntegerType(), nullable=True),
                StructField("message", StringType(), nullable=True),
                StructField("submitted_at_utc", TimestampType(), nullable=False),
            ]
        )
        dataframe = self.spark.createDataFrame([record], schema=schema)
        dataframe.write.mode("append").saveAsTable(self.table_name)
