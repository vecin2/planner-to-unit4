from typing import List

from planner_to_unit4.infrastructure.budget_variance_reader import BudgetVarianceReader


class SparkBudgetVarianceReader:
    def __init__(self, spark, table_name: str):
        self.spark = spark
        self.table_name = table_name

    def read_rows(self) -> List[dict]:
        df = self.spark.table(self.table_name)
        return [row.asDict() for row in df.collect()]
