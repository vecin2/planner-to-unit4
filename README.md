# planner-to-unit4

Pipeline support library for migrating planner data managed in Workday into Unit4.

## What This Library Does
- submit budget variance rows from Spark tables into Unit4 SOAP endpoints
- record per-segment submission outcomes in a monitoring table
- move source files into date-partitioned archive paths with optional retention cleanup

## Happy Path Flows

### `create_budget_variance_submitter`
- validates submitter config
- reads source rows (ordered by `record_no` when no row filter is provided)
- segments rows into SOAP requests and sends each segment to Unit4
- records each successful segment in the monitor table with `status=SUBMITTED`
- returns `COMPLETED` when all segments succeed

### `create_file_archiver`
- validates archive config
- moves one source file into a unique archive path under `yyyy=/mm=/dd=` partitions
- returns archive result with source and destination paths
- applies optional archive retention cleanup

## Configuration

### Budget Variance Submitter

Builder: `create_budget_variance_submitter`

Required config keys:

| Key | Type | Description |
| --- | --- | --- |
| `source_table_name` | `str` | Source Spark table with budget variance rows. |
| `version` | `str` | Value mapped to Unit4 `Version`. |
| `batch` | `str` | Value mapped to Unit4 `Batch`. |
| `endpoint` | `str` | SOAP endpoint URL. |
| `username` | `str` | Unit4 integration username. |
| `client` | `str` | Unit4 client code. |
| `password` | `str` | Unit4 integration password. |
| `segment_monitoring_table` | `str` | Spark table where segment monitoring rows are written. |

Optional config keys:

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `max_segment_size` | `int` | `12000` | Max rows per SOAP request segment. Must be `> 0`. |
| `timeout` | `int` | `90` | HTTP timeout in seconds. Must be `> 0`. |
| `segment_monitor_retention_days` | `int \| None` | `None` | Optional monitor retention window in days. Must be `> 0` when set. |

Runtime arguments (not in config):

| Argument | Type | Description |
| --- | --- | --- |
| `spark` | Spark session | Used for source table reads and monitor writes. |
| `log_fn` | `Callable[[str], None]` | Receives operational log lines. |
| `budget_variance_rows_filter` | `Callable[[DataFrame], DataFrame] \| None` | Optional filter/transform. If omitted, rows are ordered by `record_no`. |
| `failed_request_fs` | filesystem object \| `None` | Optional filesystem with `mkdirs` + `put` used to save failed SOAP requests. |

### File Archiver

Builder: `create_file_archiver`

Required config keys:

| Key | Type | Description |
| --- | --- | --- |
| `archive_root_path` | `str` | Root archive folder. Files are moved into date partitions. |

Optional config keys:

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `archive_retention_days` | `int \| None` | `None` | Optional archive retention window in days. Must be `> 0` when set. |

Runtime arguments (not in config):

| Argument | Type | Description |
| --- | --- | --- |
| `fs` | filesystem object | Used for `mkdirs`, `mv`, `ls`, and `rm`. |
| `log_fn` | `Callable[[str], None]` | Receives operational log lines. |

## Failure and Retention Behavior

- Submitter failures bubble as a single summarized exception message. The message includes up to 5 failed segments and is capped at 4000 characters.
- When `failed_request_fs` is provided, failed SOAP request payloads are written under the snapshot day folder in `failed_requests/`.
- Retention cleanup for monitor/archive logs warnings and continues processing if cleanup fails.

## Minimal Examples

### Submitter

```python
from planner_to_unit4 import create_budget_variance_submitter

submitter = create_budget_variance_submitter(
    spark=spark,
    config={
        "source_table_name": "Workday_Ingestion.fpa.Budget_Variance",
        "version": "ADJ",
        "batch": "WKD",
        "endpoint": "https://.../service.svc",
        "username": "...",
        "client": "bi",
        "password": "...",
        "segment_monitoring_table": "Workday_Ingestion.fpa.segment_monitoring",
    },
    log_fn=print,
)

submitter.run(pipeline_run_id="run-123", snapshot_path="Files/.../plan_data.json")
```

### Archiver

```python
from planner_to_unit4 import create_file_archiver

archiver = create_file_archiver(
    fs=notebookutils.fs,
    config={
        "archive_root_path": "Files/FPA_Ingestion_Test/archive",
        "archive_retention_days": 30,
    },
    log_fn=print,
)

result = archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")
print(result.archived_path)
```
