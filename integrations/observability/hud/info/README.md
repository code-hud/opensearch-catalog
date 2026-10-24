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

- **OpenSearch Dashboards 3.9 or later, with Explore and dashboard variables enabled, or OpenSearch UI on Amazon OpenSearch Service.** All panels are `explore` saved objects (PromQL and PPL), and every dashboard has a variable (service, endpoint or function) whose values come from a Prometheus label-values lookup. Dashboard variables were added in 3.7, but the PromQL query type for variables was added in 3.9. On 3.8 and later, variables are controlled by `dashboard.variables.enabled` (default `true`). On Amazon OpenSearch Service, use an **Observability workspace** in OpenSearch UI: Discover Metrics, PromQL panels and dashboard variables are not available in the OpenSearch Dashboards hosted on a domain.
- **A Prometheus direct-query data source named `hud_prometheus`.** The service, endpoint and function panels query it with PromQL. Create it before installing, using exactly that name. It can be a self-managed Prometheus (2.40 or later, with native histograms enabled) or an Amazon Managed Service for Prometheus (AMP) workspace; see [Amazon OpenSearch Service and Amazon Managed Service for Prometheus](#amazon-opensearch-service-and-amazon-managed-service-for-prometheus).
- **Native histograms.** `hud_function_duration` and `hud_http_endpoint_duration` must be stored as Prometheus native histograms. The panels read them with `histogram_quantile`, `histogram_avg`, `histogram_sum` and `histogram_count` over the bare metric name, and use the `@ end()` modifier. AMP supports both.
- **Hud investigation logs in `logs-otel-v1-*`.** The investigation panels run PPL over `logs-otel-v1*` (the Data Prepper and OpenSearch Ingestion default for OTel logs), using `time` as the time field. The index name is part of each panel's query and dataset, so the index selected while installing the integration does not change it. If your logs are written elsewhere, edit the panel queries after installing.

## Data

### Metrics (Prometheus)

The metric names and labels in this table are the contract the dashboards depend on: the panel queries and dashboard variables use them verbatim. `service_name` and `service_instance_id` come from the OTel resource attributes `service.name` and `service.instance.id`, so the OTLP path into Prometheus must turn resource attributes into labels (Prometheus `otlp.promote_resource_attributes`, or `resource_to_telemetry_conversion` on the OpenTelemetry Collector `prometheusremotewrite` exporter). The other labels are data-point attributes the Hud SDK sets. The metric names must arrive without a unit suffix.

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

The links between dashboards (clicking an endpoint or a function in a table) open dashboards by id. Installing from **Integrations** gives every saved object a new id, and the installer does not yet rewrite the ids inside those links, so after an install from **Integrations** they show "Could not locate that dashboard". The links need a fix in the dashboards-observability integrations installer that rewrites the old ids in panel links to the new ones. Until that fix ships, import the assets manually to keep the links working.

To import the assets manually, import `assets/hud-shared-1.0.0.ndjson` first, then the dashboard bundles, via **Dashboards Management > Saved objects > Import**. The shared bundle holds the index pattern and a panel that more than one dashboard uses. Manual import keeps the saved object ids, so the links between dashboards work. In an OpenSearch UI workspace, import from **Assets > Import** and choose **Check for existing assets**: the default, **Create new assets with unique IDs**, gives the objects new ids and breaks the links. Importing through the saved objects API with a `dataSourceId` parameter also renames every object to `<dataSourceId>_<id>`, which breaks the links in the same way.

## Amazon OpenSearch Service and Amazon Managed Service for Prometheus

On AWS, metrics go to an Amazon Managed Service for Prometheus (AMP) workspace, investigation logs go to an OpenSearch Service domain, and the dashboards run in an OpenSearch UI Observability workspace.

1. **Send metrics to AMP as native histograms.** Use an OpenTelemetry Collector (or the AWS Distro for OpenTelemetry) with the `prometheusremotewrite` exporter and the `sigv4auth` extension, pointed at `https://aps-workspaces.<region>.amazonaws.com/workspaces/<workspace-id>/api/v1/remote_write`. That exporter writes OTel exponential histograms as native histograms, and AMP stores and queries them with no workspace setting. Enable `resource_to_telemetry_conversion` so `service_name` becomes a label. The collector's credentials need `aps:RemoteWrite`. Don't route the metrics through the OpenSearch Ingestion `prometheus` sink: it writes histograms as separate `_bucket`, `_sum` and `_count` series, which these panels can't read.

   ```yaml
   extensions:
     sigv4auth:
       region: <region>
       service: aps
   exporters:
     prometheusremotewrite:
       endpoint: https://aps-workspaces.<region>.amazonaws.com/workspaces/<workspace-id>/api/v1/remote_write
       auth:
         authenticator: sigv4auth
       resource_to_telemetry_conversion:
         enabled: true
   service:
     extensions: [sigv4auth]
     pipelines:
       metrics:
         receivers: [otlp]
         exporters: [prometheusremotewrite]
   ```

2. **Connect AMP as the `hud_prometheus` data source.** In the OpenSearch Service console, open **Central management > Connected data sources > Connect new data source**, choose **Amazon Managed Service for Prometheus**, and name it `hud_prometheus`. OpenSearch Service queries AMP with an IAM role that it assumes, and signs the requests with SigV4 itself, so no credentials are stored in OpenSearch. Let the console create the role, or pass your own:

   ```
   aws opensearch add-direct-query-data-source \
     --data-source-name hud_prometheus \
     --data-source-type 'Prometheus={RoleArn=arn:aws:iam::<account>:role/<role>,WorkspaceArn=arn:aws:aps:<region>:<account>:workspace/<workspace-id>}'
   ```

   The role's trust policy must allow `directquery.opensearchservice.amazonaws.com` to call `sts:AssumeRole`, scoped with `aws:SourceArn` = `arn:aws:opensearch:<region>:<account>:datasource/hud_prometheus` and `aws:SourceAccount`. For these dashboards the role needs `aps:QueryMetrics`, `aps:GetLabels`, `aps:GetSeries` and `aps:GetMetricMetadata` on the workspace. The OpenSearch Service documentation lists the full policy, which adds the alerting and rule-group actions that OpenSearch UI's alerting pages use.

3. **Use an Observability workspace.** AMP data sources are only available in Observability workspaces of OpenSearch UI. Associate both the `hud_prometheus` data connection and the OpenSearch domain that holds `logs-otel-v1-*` with the workspace, then import the assets there as described in [Installation](#installation).

Limits that apply on AMP: a query times out after 30 seconds, and each query counts against the workspace's Query Samples Processed quota. Panels that aggregate over the whole time range (`[$__range] @ end()`) read more samples the longer the range, so keep dashboard ranges to hours or a few days.
