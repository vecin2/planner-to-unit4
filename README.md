# planner-to-unit4

Pipeline support library for migrating planner data managed in Workday into Unit4.

## What This Library Does
- submit budget variance rows from Spark tables into Unit4 SOAP endpoints
- record per-segment submission outcomes in a monitoring table
- copy source files into date-partitioned archive paths with optional retention cleanup

## Happy Path Flows

### Budget Variance Submitter
- reads source rows (ordered by `record_no` when no row filter is provided)
- segments rows into SOAP requests and sends each segment to Unit4
- records each successful segment in the monitor table with `status=SUBMITTED`

### File Archiver
- copies one source file into a unique archive path under `yyyy=/mm=/dd=` partitions
- returns a standardized outcome with `status` (`COMPLETED` or `FAILED`) and `to_payload()`
- applies optional archive retention cleanup

## Failure and Retention Behavior

- Submitter `run(...)` always returns a standardized outcome with `status` (`COMPLETED` or `FAILED`).
- On failure, the outcome includes `to_payload()` fields for pipeline handoff, including `email_html_body`, `summary_text`, and segment counts.
- Archiver `run(...)` also returns a standardized outcome with `status` (`COMPLETED` or `FAILED`) and `to_payload()` for notebook exit payloads.
- On archive failure, `email_html_body` contains the exception details so it can be used directly in email activities.
- When `artifact_fs` is provided, artifact persistence is controlled by `artifact_save_mode` (`on_failure`, `always`, `never`) and files are written under the snapshot day folder in `requests/` and `reports/`, with state appended to filenames.
- Retention cleanup for monitor/archive logs warnings and continues processing if cleanup fails.

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
| `username` | `str` | Unit4 integration username used for SOAP authentication. |
| `client` | `str` | Authentication client context for the user (`bi` or `c1`). |
| `password` | `str` | Password for the integration user (authentication credential). |
| `segment_monitoring_table` | `str` | Spark table where segment monitoring rows are written. |

Optional config keys:

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `max_segment_size` | `int` | `12000` | Max rows per SOAP request segment. Must be `> 0`. |
| `timeout` | `int` | `90` | HTTP timeout in seconds. Must be `> 0`. |
| `segment_monitor_retention_days` | `int \| None` | `None` | Optional monitor retention window in days. Must be `> 0` when set. |
| `report_max_sample_rows` | `int` | `10` | Max number of failed rows to include as samples in failure reports. Must be `> 0`. |
| `artifact_save_mode` | `str` | `on_failure` | Controls artifact writes when `artifact_fs` is provided. Allowed: `on_failure`, `always`, `never`. |
| `soap_retry_retries` | `int` | `0` | Number of retry attempts after the first SOAP exception. Must be `>= 0`. Retries apply only to exceptions. |

Runtime arguments (not in config):

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `spark` | Spark session | - | Used for source table reads and monitor writes. |
| `log_fn` | `Callable[[str], None]` | - | Receives operational log lines. |
| `budget_variance_rows_filter` | `Callable[[DataFrame], DataFrame] \| None` | `None` | Optional filter/transform. If omitted, rows are ordered by `record_no`. |
| `artifact_fs` | filesystem object \| `None` | `None` | Optional filesystem with `mkdirs` + `put` used to save request and report artifacts based on `artifact_save_mode`. |

### File Archiver

Builder: `create_file_archiver`

Required config keys:

| Key | Type | Description |
| --- | --- | --- |
| `archive_root_path` | `str` | Root archive folder. Files are copied into date partitions by default. |

Optional config keys:

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `archive_retention_days` | `int \| None` | `None` | Optional archive retention window in days. Must be `> 0` when set. |
| `archive_write_mode` | `str` | `copy` | Archive transfer mode. Allowed: `copy`, `move`. |

Runtime arguments (not in config):

| Argument | Type | Description |
| --- | --- | --- |
| `fs` | filesystem object | Used for `mkdirs`, `cp`, `mv`, `ls`, and `rm`. |
| `log_fn` | `Callable[[str], None]` | Receives operational log lines. |

## Minimal Examples

### Submitter

```python
import json

from planner_to_unit4 import create_budget_variance_submitter

submitter = create_budget_variance_submitter(
    spark=spark,
    config={
        "source_table_name": "db.budget_variance_staging",
        "version": "v1",
        "batch": "b1",
        "endpoint": "https://example.com/soap",
        "username": "user",
        "client": "bi",
        "password": "secret",
        "segment_monitoring_table": "db.segment_monitoring",
        "artifact_save_mode": "on_failure",
    },
    log_fn=print,
    artifact_fs=notebookutils.fs,
)

outcome = submitter.run(pipeline_run_id="run-123", snapshot_path="Files/.../plan_data.json")
print(outcome.status)
# For notebook->pipeline handoff:
notebookutils.notebook.exit(json.dumps(outcome.to_payload()))
```

### Fabric Notebook -> Pipeline Exit Payload

```python
import json

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
        "max_segment_size": 15000,
        "timeout": 60,
    },
    log_fn=print,
    failed_request_fs=notebookutils.fs,
)

outcome = submitter.run(
    pipeline_run_id="run-123",
    snapshot_path=json_file_archive_path,
)

payload = outcome.to_payload()
print("Submission status:", payload["status"])

# Pipeline consumes this JSON string.
# If payload["status"] == "FAILED", use payload["email_html_body"]
# in the Outlook Send Email activity.
notebookutils.notebook.exit(json.dumps(payload))
```

### Archiver

```python
import json

from planner_to_unit4 import create_file_archiver

archiver = create_file_archiver(
    fs=notebookutils.fs,
    config={
        "archive_root_path": "Files/FPA_Ingestion_Test/archive",
        "archive_retention_days": 30,
        "archive_write_mode": "copy",
    },
    log_fn=print,
)

result = archiver.run("Files/FPA_Ingestion_Test/landing/Plan_Data.json")
payload = result.to_payload()
print(payload["status"])
print(payload["archived_path"])
print(payload["archived_path_relative"])  # use this with Copy activity root="Files"

# Pipeline consumes this JSON string.
notebookutils.notebook.exit(json.dumps(payload))
```
