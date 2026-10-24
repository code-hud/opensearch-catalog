# Hud Integration

[Hud](https://hud.io) is a runtime code sensor. Its SDK reports function-level and endpoint-level telemetry (invocations, durations, errors, exceptions) from production services as OpenTelemetry metrics, and records an investigation log for each failing or unusually slow request.

This integration ships six dashboards over that data: **service overview**, **endpoints**, **endpoint**, **functions**, **function** and **investigations**. See [info/README.md](info/README.md) for what each one shows.

![Hud: service overview](static/dashboard-service-overview.png)

## Data flow

```mermaid
flowchart LR
  SDK[Hud SDK, OTLP mode] -->|metrics| P[(Prometheus or Amazon Managed Service for Prometheus)]
  SDK -->|investigation logs| DP[Data Prepper or OpenSearch Ingestion] --> OS[(OpenSearch logs-otel-v1-*)]
  P -->|PromQL, direct query hud_prometheus| OSD[OpenSearch Dashboards or OpenSearch UI]
  OS -->|PPL| OSD
```

- **Metrics** (`hud_function_*`, `hud_http_endpoint_*`) go to Prometheus or Amazon Managed Service for Prometheus (AMP) as native histograms and counters, and are read through a Prometheus direct-query data source named `hud_prometheus`. The metric and label names listed in [info/README.md](info/README.md#metrics-prometheus) are the contract the dashboards depend on.
- **Investigation logs** (`attributes.event.name = 'hud.investigation'`) are indexed by Data Prepper or OpenSearch Ingestion into `logs-otel-v1-*`. Their fields are described by [schemas/logs_hud-1.0.0.mapping.json](schemas/logs_hud-1.0.0.mapping.json), with examples in [data/sample.json](data/sample.json).

## Requirements

- OpenSearch Dashboards 3.9 or later, with Explore and dashboard variables (`dashboard.variables.enabled`) enabled, or an Observability workspace in OpenSearch UI on Amazon OpenSearch Service.
- A Prometheus direct-query data source named `hud_prometheus`, backed by a Prometheus 2.40 or later with native histograms enabled, or by an AMP workspace.
- Hud investigation logs in `logs-otel-v1-*`.

## Setup

For Amazon OpenSearch Service with AMP, follow [info/README.md](info/README.md#amazon-opensearch-service-and-amazon-managed-service-for-prometheus) instead of step 1.

1. Create the Prometheus data source, for example with the SQL plugin's data source API:

   ```
   POST _plugins/_query/_datasources
   {
     "name": "hud_prometheus",
     "connector": "prometheus",
     "properties": { "prometheus.uri": "http://prometheus:9090" }
   }
   ```

2. Install **Hud** from **Integrations**, entering `logs-otel-v1*` as the data source. Alternatively, import `assets/hud-shared-1.0.0.ndjson` and then the dashboard bundles under **Dashboards Management > Saved objects**. The links between dashboards open dashboards by saved object id. Manual import keeps the ids, so the links work. After an install from **Integrations** the links do not resolve until the dashboards-observability installer rewrites the ids inside them; see [Installation](info/README.md#installation).
3. Open **Hud: service overview** and pick a service.

## Contents

| Path | Contents |
| --- | --- |
| `hud-1.0.0.json` | Integration config |
| `assets/hud-shared-1.0.0.ndjson` | `logs-otel-v1*` index pattern and a panel used by several dashboards |
| `assets/hud-*-1.0.0.ndjson` | One saved-object bundle per dashboard |
| `schemas/logs_hud-1.0.0.mapping.json` | Mapping for Hud investigation logs |
| `data/sample.json` | Sample investigation records |
| `static/` | Logo and dashboard screenshots |
