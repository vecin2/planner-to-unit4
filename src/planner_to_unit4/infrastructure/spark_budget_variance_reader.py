from planner_to_unit4.infrastructure.budget_variance_reader import BudgetVarianceReader


class SparkBudgetVarianceReader:
    def __init__(self, spark, table_name: str, max_records: int | None = None):
        self.spark = spark
        self.table_name = table_name
        self.max_records = max_records

    def read_rows(self) -> list[dict]:
        df = self.spark.table(self.table_name)
        if self.max_records is not None:
            df = df.limit(self.max_records)
        return [row.asDict() for row in df.collect()]
