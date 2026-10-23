# Hud Integration

## What is Hud?

[Hud](https://hud.io) is a runtime code sensor that reports function-level and endpoint-level telemetry (invocations, durations, errors, exceptions) from production services, and captures forensics for failing requests ("investigations").

## What is the Hud Integration?

An integration is a bundle of pre-canned assets which are bundled together in a meaningful manner.

The Hud integration includes the following dashboards:

- **Hud: service overview**: KPIs, invocation rate, duration percentiles, error rate, exceptions by type, and the service's flows and functions.
- **Hud: endpoints**: firing alerts and endpoints ranked by requests, 5xx count and rate, and average / p90 / p99 latency.
- **Hud: endpoint**: a single endpoint's request rate, 5xx rate, duration percentiles, requests by status code, and its exceptions and latest investigations.
- **Hud: functions**: functions ranked by invocations, error count and rate, and average / p90 / p99 duration.
- **Hud: function**: a single function's rate, errors, duration percentiles, per-version breakdowns, callers and callees.
- **Hud: investigations**: investigations over time by trigger, exceptions in failed requests, throwing functions and the latest investigations.

![Hud: service overview](../static/dashboard-service-overview.png)

![Hud: endpoint](../static/dashboard-endpoint.png)

![Hud: investigations](../static/dashboard-investigations.png)

## Requirements

- **OpenSearch Dashboards 3.7 or later, with Explore and dashboard variables enabled.** All panels are `explore` saved objects (PromQL and PPL), and every dashboard has a variable (service, endpoint or function). Dashboard variables (`variablesJSON`) were added in 3.7; on 3.8 and later they are controlled by `dashboard.variables.enabled` (default `true`). On older versions, or with variables disabled, the dashboards are not created.
- **A Prometheus direct-query data source named `hud_prometheus`.** The service, endpoint and function panels query it with PromQL. Create it under **Data sources** before installing, using exactly that name. The Prometheus server must store native histograms (`hud_function_duration` and `hud_http_endpoint_duration`) and support the `@` modifier.
- **Hud investigation logs in `logs-otel-v1-*`.** The investigation panels run PPL over `logs-otel-v1*` (the Data Prepper default for OTel logs), using `time` as the time field. The index name is part of each panel's query and dataset, so the index selected while installing the integration does not change it. If your logs are written elsewhere, edit the panel queries after installing.

## Data

### Metrics (Prometheus)

| Metric | Type | Labels used by the dashboards |
| --- | --- | --- |
| `hud_http_endpoint_requests_total` | counter | `service_name`, `service_endpoint`, `endpoint_method`, `endpoint_path`, `status_code` |
| `hud_http_endpoint_duration` | native histogram (ns) | `service_name`, `service_endpoint`, `endpoint_method`, `endpoint_path` |
| `hud_function_invocations_total` | counter | `service_name`, `service_instance_id`, `service_function_key`, `service_caller_function_key`, `function_name`, `function_file`, `function_version` |
| `hud_function_exceptions_total` | counter | as above, plus `exception_type` |
| `hud_function_duration` | native histogram (ns) | as `hud_function_invocations_total` |

The **Alerts in this time range** panel on **Hud: endpoints** reads `ALERTS{alertstate="firing", endpoint_page!=""}` and stays empty unless Hud's Prometheus alerting rules are installed.

### Investigation logs (OpenSearch)

Each investigation is one log record with `attributes.event.name = 'hud.investigation'`. The fields the dashboards use are described by [`schemas/logs_hud-1.0.0.mapping.json`](../schemas/logs_hud-1.0.0.mapping.json), and [`data/sample.json`](../data/sample.json) has example records.

## Installation

Install the integration from **Integrations** in OpenSearch Dashboards. When asked for the data source, enter `logs-otel-v1*`.

Installing from **Integrations** gives every saved object a new id. The links between dashboards (clicking an endpoint or a function in a table) open dashboards by id, so after an install from **Integrations** they show "Could not locate that dashboard". To keep the links working, import the assets manually instead.

To import the assets manually, import `assets/hud-shared-1.0.0.ndjson` first, then the dashboard bundles, via **Dashboards Management > Saved objects > Import**. The shared bundle holds the index pattern and a panel that more than one dashboard uses. Manual import keeps the saved object ids, so the links between dashboards work.
