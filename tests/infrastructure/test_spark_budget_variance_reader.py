import pytest

from planner_to_unit4.infrastructure.spark_budget_variance_reader import (
    SparkBudgetVarianceReader,
)
from tests.support.spark_test_utils import (
    SparkSession,
    cleanup_temp_table,
    create_spark_session,
    create_temp_table,
)


@pytest.mark.spark
def test_spark_budget_variance_reader_applies_rows_filter() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = create_spark_session("budget-variance-reader-test")
    database_name, table_name = create_temp_table(
        spark,
        database_prefix="budget_variance_test",
        table_name="budget_variance_rows",
    )

    expected_rows = [
        {
            "record_no": 2,
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
            "record_no": 1,
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
        rows_filter=lambda dataframe: dataframe.where("Description = 'Test 2'"),
    )
    rows = reader.read_rows()

    assert len(rows) == 1
    assert rows[0] == expected_rows[1]

    cleanup_temp_table(spark, table_name, database_name)


def test_spark_budget_variance_reader_rejects_non_callable_filter() -> None:
    with pytest.raises(TypeError, match="budget_variance_rows_filter must be callable"):
        SparkBudgetVarianceReader(spark=None, table_name="table", rows_filter="invalid")


@pytest.mark.spark
def test_spark_budget_variance_reader_orders_by_record_no_when_no_filter() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = create_spark_session("budget-variance-reader-test")
    database_name, table_name = create_temp_table(
        spark,
        database_prefix="budget_variance_test",
        table_name="budget_variance_rows",
    )

    dataframe = spark.createDataFrame(
        [
            {"record_no": 3, "Client": "BI"},
            {"record_no": 1, "Client": "BI"},
            {"record_no": 2, "Client": "BI"},
        ]
    )
    dataframe.write.mode("overwrite").saveAsTable(table_name)

    reader = SparkBudgetVarianceReader(spark=spark, table_name=table_name)

    rows = reader.read_rows()

    assert [row["record_no"] for row in rows] == [1, 2, 3]

    cleanup_temp_table(spark, table_name, database_name)


@pytest.mark.spark
def test_spark_budget_variance_reader_rejects_non_dataframe_filter_result() -> None:
    if SparkSession is None:
        pytest.skip("pyspark is not installed")

    spark = create_spark_session("budget-variance-reader-test")
    database_name, table_name = create_temp_table(
        spark,
        database_prefix="budget_variance_test",
        table_name="budget_variance_rows",
    )

    dataframe = spark.createDataFrame([{"record_no": 1, "Client": "BI"}])
    dataframe.write.mode("overwrite").saveAsTable(table_name)

    reader = SparkBudgetVarianceReader(
        spark=spark,
        table_name=table_name,
        rows_filter=lambda _dataframe: "invalid",
    )

    with pytest.raises(
        TypeError, match="budget_variance_rows_filter must return a Spark DataFrame"
    ):
        reader.read_rows()

    cleanup_temp_table(spark, table_name, database_name)
