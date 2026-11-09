#!/usr/bin/env python3
"""Generate assets/hud-1.0.0.ndjson from the Hud dashboards in hud-o11y-resources.

    python3 integrations/observability/hud/scripts/generate-assets.py --resources <hud-o11y-resources checkout>

Runs the resources dashboard loader on opensearch-ui/dashboards/hud-all-dashboards.ndjson
(--target osd --links version-neutral --logs-layout otel --prometheus-connection hud_amp),
then applies the catalog-specific steps the loader does not do yet:

1. replaces Data Prepper's flattened serviceName, which the otel layout does not have,
   with resource.attributes.service.name;
2. adds the forensic panels (summary, exception, call chain, request context, outbound
   calls, machine metrics) to "Hud: 5. Investigation Details";
3. declares every dashboard a panel links to as a link_<target> reference, so the
   integrations installer rewrites the link when it gives the dashboards new ids;
4. makes every PPL query also read the index "Try with sample data" creates
   (ss4o_logs_hud-*-sample); where that index doesn't exist, the results are unchanged.

The result is one saved-object bundle with all the dashboards, written over
assets/hud-1.0.0.ndjson. Only the Python standard library is used.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "assets" / "hud-1.0.0.ndjson"
SOURCE = "opensearch-ui/dashboards/hud-all-dashboards.ndjson"
LOADER = "opensearch-ui/scripts/dashboard-loader.py"
LOADER_ARGS = [
    "--target", "osd",
    "--links", "version-neutral",
    "--logs-layout", "otel",
    "--prometheus-connection", "hud_amp",
]

INDEX_PATTERN_ID = "hud-logs-otel-v1"
INVESTIGATION_DASHBOARD = "hud-investigation-details-dashboard"
SERVICE_FIELD = "resource.attributes.service.name"

INVESTIGATION = (
    "source = logs-otel-v1* | where _id = '$investigation' or `attributes.issue.fingerprint` = '$investigation'"
    " | sort - time | head 1"
)
FUNCTION_ARGS = '["code.function.name"]'


def link(link_id, title, dashboard, variable, field):
    return {
        "id": link_id,
        "title": title,
        "url": f"/app/dashboards#/view/{dashboard}?_a=(variables:!((id:{variable},current:!('${{__value.text}}'))))",
        "openInNewTab": False,
        "fields": [field],
    }


FORENSIC_PANELS = [
    {
        "id": "hud-inv-summary",
        "title": "Summary (click the flow or the function for its page)",
        "h": 5,
        "links": [
            link("open-endpoint-flow", "Open flow", "hud-endpoint-dashboard", "endpoint", "Flow"),
            link("open-function-function", "Open function", "hud-function-dashboard", "function", "Function"),
        ],
        "query": INVESTIGATION
        + " | eval `Duration ms` = round(cast(json_extract(body, '$.duration') as double) / 1000000, 1),"
        " `Threshold ms` = json_extract(body, '$.durationThreshold'), Trigger = json_extract(body, '$.triggerType')"
        " | parse `attributes.hud.issue.sources` '^\\\\[?(?<Error>[^@]+)@(?<File>[^:]+):(?<Function>.*?)\\\\]?$'"
        " | eval Error = if(isnull(Error) or Error = '', json_extract(body, '$.exceptions[0].name'), Error),"
        " Error = if(isnull(Error), json_extract(body, '$.context.response_body.error'), Error),"
        " Error = if(isnull(Error), `attributes.hud.issue.framework_result`, Error),"
        " Function = if(isnull(Function) or Function = '', json_extract(body, '$.exceptions[0].executionFlow[0].function"
        + FUNCTION_ARGS
        + "'), Function)"
        " | rename `resource.attributes.service.name` as Service, `attributes.code.flow.name` as Flow,"
        " `attributes.hud.forensic.type` as Type, `attributes.http.response.status_code` as Status,"
        " `attributes.issue.fingerprint` as Fingerprint, `attributes.hud.issue.caught` as Caught,"
        " `attributes.hud.issue.framework_result` as Result, traceId as `Trace id`"
        " | fields time, Service, Flow, Type, Trigger, Status, `Duration ms`, `Threshold ms`, Fingerprint, Error,"
        " Function, Caught, Result, `Trace id`",
    },
    {
        "id": "hud-inv-exception",
        "title": "Exception",
        "h": 6,
        "links": [],
        "query": INVESTIGATION
        + " | eval Exception = json_extract(body, '$.exceptions[0].name'), Message = json_extract(body, '$.exceptions[0].message'),"
        " `Stack trace` = json_extract(body, '$.exceptions[0].stackTrace'), Caught = json_extract(body, '$.exceptions[0].caught'),"
        " `Total exceptions` = json_extract(body, '$.totalExceptionsCount')"
        " | fields Exception, Message, `Stack trace`, Caught, `Total exceptions`",
    },
    {
        "id": "hud-inv-chain",
        "title": "Call chain (the throwing function and its caller; click one for its page)",
        "h": 5,
        "links": [
            link("open-function-function", "Open function", "hud-function-dashboard", "function", "Function"),
            link("open-function-caller", "Open caller", "hud-function-dashboard", "function", "Caller"),
        ],
        "query": INVESTIGATION
        + " | eval Function = json_extract(body, '$.exceptions[0].executionFlow[0].function" + FUNCTION_ARGS + "'),"
        " `Function file` = json_extract(body, '$.exceptions[0].executionFlow[0].function[\"code.file.path\"]'),"
        " Version = json_extract(body, '$.exceptions[0].executionFlow[0].function[\"hud.function.content_hash\"]'),"
        " Caller = json_extract(body, '$.exceptions[0].executionFlow[0].caller" + FUNCTION_ARGS + "'),"
        " `Caller file` = json_extract(body, '$.exceptions[0].executionFlow[0].caller[\"code.file.path\"]'),"
        " `Error breakdown` = json_extract(body, '$.errorBreakdown.errors')"
        " | fields Function, `Function file`, Version, Caller, `Caller file`, `Error breakdown`",
    },
    {
        "id": "hud-inv-request",
        "title": "Request context",
        "h": 6,
        "links": [],
        "query": INVESTIGATION
        + " | eval Route = json_extract(body, '$.context.route'), Method = json_extract(body, '$.context.method'),"
        " Params = json_extract(body, '$.context.params'), Query = json_extract(body, '$.context.query'),"
        " `Request body` = json_extract(body, '$.context.request_body'), `Response body` = json_extract(body, '$.context.response_body'),"
        " Headers = json_extract(body, '$.context.extra_headers'), `Session id` = json_extract(body, '$.context.session_id')"
        " | fields Method, Route, Params, Query, `Request body`, `Response body`, Headers, `Session id`",
    },
    {
        "id": "hud-inv-outbounds",
        "title": "Outbound calls",
        "h": 5,
        "links": [],
        "query": INVESTIGATION
        + " | eval `Total outbounds` = json_extract(body, '$.totalOutboundsCount'), Aggregation = json_extract(body, '$.outboundAggregation'),"
        " Outbounds = json_extract(body, '$.outbounds')"
        " | fields `Total outbounds`, Aggregation, Outbounds",
    },
    {
        "id": "hud-inv-machine",
        "title": "Machine metrics",
        "h": 5,
        "links": [],
        "query": INVESTIGATION
        + " | eval `CPU user %` = round(cast(json_extract(body, '$.context.machine_metrics.cpu_usage.user_percent_of_limit') as double), 1),"
        " `CPU system %` = round(cast(json_extract(body, '$.context.machine_metrics.cpu_usage.system_percent_of_limit') as double), 1),"
        " `CPU limit (cores)` = json_extract(body, '$.context.machine_metrics.cpu_usage.limit'),"
        " `RSS MB` = round(cast(json_extract(body, '$.context.machine_metrics.memory_usage.rss') as double) / 1048576, 1),"
        " `Heap used MB` = round(cast(json_extract(body, '$.context.machine_metrics.memory_usage.heap_used') as double) / 1048576, 1),"
        " `Heap total MB` = round(cast(json_extract(body, '$.context.machine_metrics.memory_usage.heap_total') as double) / 1048576, 1),"
        " `Event loop utilization` = round(cast(json_extract(body, '$.context.machine_metrics.event_loop_utilization') as double), 3),"
        " Pod = json_extract(body, '$.context.system_info.pod_name')"
        " | fields `CPU user %`, `CPU system %`, `CPU limit (cores)`, `RSS MB`, `Heap used MB`, `Heap total MB`, `Event loop utilization`, Pod",
    },
]

INVESTIGATION_DESCRIPTION = (
    "One investigation (a failed or slow request, from the hud.forensic logs): summary, exception, call chain, "
    "request context, outbound calls, machine metrics, and the full forensic record. Open it from an Investigation id, "
    "or from an issue Fingerprint (shows the latest investigation with it)."
)

SERVICE_NAME = re.compile(r"(?<![\w.`@])serviceName(?![\w`])")
VIEW_LINK = re.compile(r"#/view/([\w-]+)")
PPL_SOURCE = "source = logs-otel-v1*"
PPL_SOURCES = "source = logs-otel-v1*,ss4o_logs_hud-*-sample"


def run_loader(resources, workdir):
    subprocess.run(
        [sys.executable, str(resources / LOADER), *LOADER_ARGS, "--out", str(workdir), str(resources / SOURCE)],
        check=True,
    )
    with open(workdir / "hud.ndjson") as f:
        return [json.loads(line) for line in f if line.strip()]


def fix_service_name(obj):
    attrs = obj["attributes"]
    for key in ("visualization", "variablesJSON"):
        if key in attrs:
            attrs[key] = SERVICE_NAME.sub(f"`{SERVICE_FIELD}`", attrs[key])
    meta = attrs.get("kibanaSavedObjectMeta")
    if meta:
        meta["searchSourceJSON"] = SERVICE_NAME.sub(f"`{SERVICE_FIELD}`", meta["searchSourceJSON"])
    if "columns" in attrs:
        attrs["columns"] = [SERVICE_FIELD if c == "serviceName" else c for c in attrs["columns"]]


def add_sample_source(obj):
    attrs = obj["attributes"]
    if "variablesJSON" in attrs:
        attrs["variablesJSON"] = attrs["variablesJSON"].replace(PPL_SOURCE, PPL_SOURCES)
    meta = attrs.get("kibanaSavedObjectMeta")
    if meta:
        meta["searchSourceJSON"] = meta["searchSourceJSON"].replace(PPL_SOURCE, PPL_SOURCES)


def forensic_panel(panel):
    search = {
        "query": {
            "query": panel["query"],
            "language": "PPL",
            "dataset": {"id": INDEX_PATTERN_ID, "title": "logs-otel-v1*", "type": "INDEX_PATTERN", "timeFieldName": "time"},
        },
        "filter": [],
        "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index",
    }
    visualization = {
        "title": "",
        "chartType": "table",
        "params": {
            "pageSize": 10,
            "globalAlignment": "left",
            "showColumnFilter": False,
            "showFooter": False,
            "dataLinks": panel["links"],
        },
    }
    return {
        "type": "explore",
        "id": panel["id"],
        "attributes": {
            "title": panel["title"],
            "description": "",
            "hits": 0,
            "columns": ["_source"],
            "sort": [],
            "type": "logs",
            "version": 1,
            "uiState": json.dumps({"activeTab": "explore_visualization_tab"}),
            "visualization": json.dumps(visualization),
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(search)},
        },
        "references": [
            {"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": INDEX_PATTERN_ID}
        ],
    }


def add_forensic_panels(objects):
    index = next(i for i, o in enumerate(objects) if o["id"] == INVESTIGATION_DASHBOARD)
    dashboard = objects[index]
    attrs = dashboard["attributes"]
    existing = json.loads(attrs["panelsJSON"])
    refs = {r["name"]: r for r in dashboard["references"]}

    panels, references, y = [], [], 0
    for p in FORENSIC_PANELS:
        panels.append((p["id"], {"x": 0, "y": y, "w": 48, "h": p["h"]}, "explore"))
        y += p["h"]
    for p in existing:
        grid = dict(p["gridData"], y=p["gridData"]["y"] + y)
        panels.append((refs[p["panelRefName"]]["id"], grid, refs[p["panelRefName"]]["type"]))

    panels_json = []
    for n, (panel_id, grid, kind) in enumerate(panels):
        panels_json.append({
            "version": "3.6.0",
            "panelIndex": panel_id,
            "gridData": dict(grid, i=panel_id),
            "embeddableConfig": {},
            "panelRefName": f"panel_{n}",
        })
        references.append({"name": f"panel_{n}", "type": kind, "id": panel_id})
    attrs["panelsJSON"] = json.dumps(panels_json)
    attrs["description"] = INVESTIGATION_DESCRIPTION
    dashboard["references"] = references

    objects[index:index] = [forensic_panel(p) for p in FORENSIC_PANELS]


def add_link_references(objects):
    dashboards = {o["id"] for o in objects if o["type"] == "dashboard"}
    for obj in objects:
        targets = sorted(set(VIEW_LINK.findall(obj["attributes"].get("visualization", ""))))
        for target in targets:
            if target not in dashboards:
                sys.exit(f"{obj['id']}: link to missing dashboard {target}")
            name = "link_" + target.removeprefix("hud-").replace("-", "_")
            if not any(r["name"] == name for r in obj["references"]):
                obj["references"].append({"name": name, "type": "dashboard", "id": target})


def check(objects):
    ids = {(o["type"], o["id"]) for o in objects}
    problems = []
    for obj in objects:
        for ref in obj.get("references", []):
            if (ref["type"], ref["id"]) not in ids:
                problems.append(f"{obj['id']}: dangling reference {ref['name']} -> {ref['type']}:{ref['id']}")
    text = "\n".join(json.dumps(o) for o in objects)
    for pattern in (r"\bserviceName\b", r"\$__all", r"/w/[\w-]+/app", r"source = logs-otel-v1\*(?!,)"):
        if re.search(pattern, text):
            problems.append(f"output still matches {pattern}")
    if problems:
        sys.exit("\n".join(problems))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resources", type=Path, required=True, help="checkout of code-hud/hud-o11y-resources")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output file (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        objects = run_loader(args.resources.resolve(), Path(tmp))
    for obj in objects:
        fix_service_name(obj)
    add_forensic_panels(objects)
    for obj in objects:
        add_sample_source(obj)
    add_link_references(objects)
    check(objects)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for obj in objects:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    links = sum(1 for o in objects for r in o["references"] if r["name"].startswith("link_"))
    print(f"wrote {args.out}: {len(objects)} objects, {links} link_ references")


if __name__ == "__main__":
    main()
