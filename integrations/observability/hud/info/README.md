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

## Requirements

- **OpenSearch Dashboards 3.x with Explore enabled.** All panels are `explore` saved objects (PromQL and PPL); they do not load on 2.x or on Dashboards without Explore.
- **A Prometheus direct-query data source named `hud_prometheus`.** The service, endpoint and function panels query it with PromQL. Create it under **Data sources** before installing, using exactly that name.
- **Hud investigation logs in `logs-otel-v1*`.** The investigation panels run PPL over `logs-otel-v1*` (the Data Prepper default for OTel logs), using `time` as the time field. The index name is part of each PPL query (`source = logs-otel-v1*`), so the index selected while installing the integration does not change it. If your logs are written elsewhere, edit the panel queries after installing.

## Installation

Install the integration from **Integrations** in OpenSearch Dashboards.

To import the assets manually instead, import `assets/hud-shared-1.0.0.ndjson` first, then any of the dashboard bundles, via **Dashboards Management > Saved objects > Import**. The shared bundle holds the index pattern and a panel that more than one dashboard uses.
