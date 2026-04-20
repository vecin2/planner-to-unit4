# planner-to-unit4

Pipeline support library for migrating planner data managed in Workday into Unit4.

## Initial scope
- register immutable snapshots
- orchestrate migration stages
- integrate with Fabric notebooks and pipelines

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

## Behavior Notes

- Submitter failures bubble as a single summarized exception message. The message includes up to 5 failed segments and is capped at 4000 characters.
- When `failed_request_fs` is provided, failed SOAP request payloads are written under the snapshot day folder in `failed_requests/`.
- Retention cleanup for monitor/archive logs warnings and continues processing if cleanup fails.
