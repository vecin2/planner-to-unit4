from uuid import uuid4

import pytest

try:
    from pyspark.sql import SparkSession
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    SparkSession = None

from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)


@pytest.mark.spark
def test_spark_budget_variance_reader_reads_rows() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = (
        SparkSession.builder.master("local[1]").appName("budget-variance-reader-test").getOrCreate()
    )
    database_name = f"budget_variance_test_{uuid4().hex}"
    table_name = f"{database_name}.budget_variance_rows"
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")

    expected_rows = [
        {
            "Client": "BI",
            "Description": "Test",
            "Account": "1000",
            "Dim2": "A1",
            "Dim3": "X",
            "Dim4": "B1",
            "Dim6": "C1",
            "Dim7": "ROM",
            "Currency": "USD",
            "Period": "202601",
            "CurAmount": 12.25,
        },
        {
            "Client": "BI",
            "Description": "Test 2",
            "Account": "2000",
            "Dim2": "A2",
            "Dim3": "Y",
            "Dim4": "B2",
            "Dim6": "C2",
            "Dim7": "ROM",
            "Currency": "USD",
            "Period": "202602",
            "CurAmount": 24.5,
        },
    ]

    dataframe = spark.createDataFrame(expected_rows)
    dataframe.write.mode("overwrite").saveAsTable(table_name)

    reader = SparkBudgetVarianceReader(
        spark=spark,
        table_name=table_name,
        max_records=1,
    )
    rows = reader.read_rows()

    assert len(rows) == 1
    assert rows[0] in expected_rows

    spark.sql(f"DROP TABLE IF EXISTS {table_name}")
    spark.sql(f"DROP DATABASE IF EXISTS {database_name}")
    spark.stop()
