from __future__ import annotations

from typing import Any
from typing import Callable


class SparkBudgetVarianceReader:
    def __init__(
        self,
        spark,
        table_name: str,
        rows_filter: Callable[[Any], Any] | None = None,
    ):
        if rows_filter is not None and not callable(rows_filter):
            raise TypeError("budget_variance_rows_filter must be callable")

        self.spark = spark
        self.table_name = table_name
        self.rows_filter = rows_filter

    def read_rows(self) -> list[dict]:
        df = self.spark.table(self.table_name)
        if self.rows_filter is not None:
            filtered_df = self.rows_filter(df)
            if not _is_spark_dataframe(filtered_df):
                raise TypeError("budget_variance_rows_filter must return a Spark DataFrame")
            df = filtered_df
        else:
            df = df.orderBy("record_no")
        return [row.asDict() for row in df.collect()]


def _is_spark_dataframe(value: object) -> bool:
    try:
        from pyspark.sql import DataFrame
    except ModuleNotFoundError:
        return hasattr(value, "collect")

    return isinstance(value, DataFrame)
