from __future__ import annotations

from uuid import uuid4


try:
    from pyspark.sql import SparkSession
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    SparkSession = None


def create_spark_session(app_name: str):
    if SparkSession is None:
        return None
    return SparkSession.builder.master("local[1]").appName(app_name).getOrCreate()


def create_temp_table(spark, database_prefix: str, table_name: str) -> tuple[str, str]:
    database_name = f"{database_prefix}_{uuid4().hex}"
    full_table_name = f"{database_name}.{table_name}"
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")
    return database_name, full_table_name


def cleanup_temp_table(spark, table_name: str, database_name: str) -> None:
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")
    spark.sql(f"DROP DATABASE IF EXISTS {database_name}")
    spark.stop()
