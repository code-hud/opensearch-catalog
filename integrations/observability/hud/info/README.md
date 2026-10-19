# Hud Integration

## What is Hud?

[Hud](https://hud.io) is a runtime code sensor that reports function-level and endpoint-level telemetry (invocations, durations, errors, exceptions) from production services, and captures forensics for failing requests ("investigations").

## What is the Hud Integration?

An integration is a bundle of pre-canned assets which are bundled together in a meaningful manner.

The Hud integration includes the following dashboards:

- **Hud: service overview**: KPIs, invocation rate, duration percentiles, error rate, exceptions by type, and the service's flows and functions.
- **Hud: endpoints**: firing alerts and endpoints ranked by requests, 5xx count and rate, and average / p90 / p99 latency.
- **Hud: functions**: functions ranked by invocations, error count and rate, and average / p90 / p99 duration.
- **Hud: function**: a single function's rate, errors, duration percentiles, per-version breakdowns, callers and callees.
- **Hud: investigations**: investigations over time by trigger, exceptions in failed requests, throwing functions and the latest investigations.

## Data sources

- **Metrics** panels use PromQL against a Prometheus direct-query data source named `lifey_o11y_stack_prometheus`. Rename the data source in the panels to match your own Prometheus connection after installing.
- **Investigation** panels use the `logs-otel-v1*` index pattern with `time` as the time field. This is where Data Prepper writes OTel logs in the OpenSearch observability stack.

## Installation

Install the integration from **Integrations** in OpenSearch Dashboards, or import any of the `assets/*.ndjson` files (one per dashboard) directly via **Dashboards Management > Saved objects > Import**.
