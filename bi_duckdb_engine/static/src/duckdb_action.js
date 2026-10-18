/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

let duckdbPromise = null;
async function getDuckDBConnection() {
    if (!duckdbPromise) {
        duckdbPromise = (async () => {
            const duckdb = await import("https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm");
            const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
            const workerUrl = URL.createObjectURL(
                new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
            );
            const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), new Worker(workerUrl));
            await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
            return { db, conn: await db.connect() };
        })();
    }
    return duckdbPromise;
}

export class DuckDBReportAction extends Component {
    static template = "bi_duckdb_engine.DuckDBReportAction";

    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("chartCanvas");
        this.chartInstance = null;
        this.rawObjects = [];

        const action = this.props.action || {};
        const params = action.params || {};
        const context = action.context || {};

        let initialReportId = params.report_id || context.active_id || context.report_id || context.default_report_id;
        if (!initialReportId && typeof action.res_id === "number" && action.res_id > 0) {
            initialReportId = action.res_id;
        }

        const initialParamNames = params.param_names || [];
        const defaultParams = {};
        for (const p of initialParamNames) {
            if (p.includes("date_from")) {
                const d = new Date();
                d.setDate(d.getDate() - 30);
                defaultParams[p] = d.toISOString().slice(0, 10);
            } else if (p.includes("date")) {
                defaultParams[p] = new Date().toISOString().slice(0, 10);
            } else {
                defaultParams[p] = "";
            }
        }

        const initialViews = params.views || [];
        const firstView = initialViews[0] || { id: 0, duckdb_sql: "SELECT * FROM raw_dataset LIMIT 100" };

        this.state = useState({
            reports: [],
            selectedReportId: initialReportId ? Number(initialReportId) : null,
            reportName: params.report_name || "",
            paramNames: initialParamNames,
            views: initialViews,
            paramValues: defaultParams,
            activeViewId: firstView.id,
            activeSql: firstView.duckdb_sql,
            chartType: "bar",
            columns: [],
            rows: [],
            loading: false,
            datasetLoaded: false,
            statusText: "Initializing DuckDB WASM...",
            error: null,
        });

        onWillStart(async () => {
            await Promise.all([loadBundle("web.chartjs_lib"), getDuckDBConnection()]);

            // 1. Fetch available reports for report switcher
            try {
                const reports = await this.orm.searchRead(
                    "bi.duckdb.report",
                    [],
                    ["id", "name"]
                );
                this.state.reports = reports;
                if (!this.state.selectedReportId && reports.length > 0) {
                    this.state.selectedReportId = reports[0].id;
                }
            } catch (err) {
                console.warn("Could not load reports list:", err);
            }

            // 2. Load report definition if views or params were not passed (e.g. page refresh / direct URL)
            if (this.state.selectedReportId) {
                if (!this.state.views.length || !this.state.reportName) {
                    await this.loadReportDefinition(this.state.selectedReportId);
                }
                await this.loadServerDataset();
            } else {
                this.state.statusText = "No report configuration found.";
            }
        });

        onWillUnmount(() => this.chartInstance?.destroy());
    }

    async loadReportDefinition(reportId) {
        if (!reportId || isNaN(reportId)) return;
        try {
            const reports = await this.orm.read(
                "bi.duckdb.report",
                [Number(reportId)],
                ["name", "pg_extract_sql", "view_ids"]
            );
            if (!reports || !reports.length) return;
            const report = reports[0];
            this.state.reportName = report.name;

            // Extract SQL parameter names (:param, excluding company_ids)
            const matches = [...(report.pg_extract_sql || "").matchAll(/:([a-zA-Z0-9_]+)/g)];
            const extracted = [...new Set(matches.map((m) => m[1]).filter((p) => p !== "company_ids"))];
            this.state.paramNames = extracted;

            const newParamValues = { ...this.state.paramValues };
            for (const p of extracted) {
                if (!(p in newParamValues)) {
                    if (p.includes("date_from")) {
                        const d = new Date();
                        d.setDate(d.getDate() - 30);
                        newParamValues[p] = d.toISOString().slice(0, 10);
                    } else if (p.includes("date")) {
                        newParamValues[p] = new Date().toISOString().slice(0, 10);
                    } else {
                        newParamValues[p] = "";
                    }
                }
            }
            this.state.paramValues = newParamValues;

            if (report.view_ids && report.view_ids.length > 0) {
                const views = await this.orm.read(
                    "bi.duckdb.report.view",
                    report.view_ids,
                    ["id", "name", "duckdb_sql"]
                );
                this.state.views = views;
                if (views.length > 0) {
                    this.state.activeViewId = views[0].id;
                    this.state.activeSql = views[0].duckdb_sql;
                }
            } else {
                this.state.views = [];
                this.state.activeViewId = null;
                this.state.activeSql = "SELECT * FROM raw_dataset LIMIT 100";
            }
        } catch (err) {
            console.error("Error loading report definition:", err);
            this.state.error = `Failed to load report configuration: ${err.message || err}`;
        }
    }

    async onReportChange(ev) {
        const newReportId = Number(ev.target.value);
        if (!newReportId || newReportId === this.state.selectedReportId) return;
        this.state.selectedReportId = newReportId;
        this.state.datasetLoaded = false;
        this.state.columns = [];
        this.state.rows = [];
        this.chartInstance?.destroy();
        this.chartInstance = null;
        await this.loadReportDefinition(newReportId);
        await this.loadServerDataset();
    }

    async loadServerDataset() {
        const reportId = this.state.selectedReportId;
        if (!reportId || isNaN(reportId)) {
            this.state.error = "Please select a valid report before loading data.";
            return;
        }
        this.state.loading = true;
        this.state.error = null;
        const t0 = performance.now();
        try {
            const resp = await fetch(`/bi/duckdb/dataset/${reportId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(this.state.paramValues),
            });
            if (!resp.ok) {
                const errText = await resp.text();
                throw new Error(`Server returned HTTP ${resp.status}: ${errText}`);
            }

            const fmt = resp.headers.get("X-Dataset-Format") || "csv";
            const buf = new Uint8Array(await resp.arrayBuffer());
            const { db, conn } = await getDuckDBConnection();

            const fileName = `raw_dataset_${reportId}.${fmt}`;
            await db.registerFileBuffer(fileName, buf);
            const readerFn = fmt === "parquet" ? `read_parquet('${fileName}')` : `read_csv_auto('${fileName}')`;
            await conn.query(`CREATE OR REPLACE VIEW raw_dataset AS SELECT * FROM ${readerFn}`);

            this.state.datasetLoaded = true;
            this.state.statusText = `Loaded ${(buf.byteLength / 1024).toFixed(1)} KB into WASM in ${(performance.now() - t0).toFixed(0)} ms`;
            await this.runClientQuery();
        } catch (err) {
            this.state.error = err.message;
        } finally {
            this.state.loading = false;
        }
    }

    async selectTab(view) {
        this.state.activeViewId = view.id;
        this.state.activeSql = view.duckdb_sql;
        await this.runClientQuery();
    }

    async runClientQuery() {
        if (!this.state.datasetLoaded) return;
        this.state.error = null;
        const t0 = performance.now();
        try {
            const { conn } = await getDuckDBConnection();
            const arrowResult = await conn.query(this.state.activeSql);
            const cols = arrowResult.schema.fields.map((f) => f.name);
            this.rawObjects = arrowResult.toArray();
            this.state.columns = cols;
            this.state.rows = this.rawObjects.slice(0, 2000).map((r) => cols.map((c) => String(r[c] ?? "")));
            this.state.statusText = `WASM Query: ${this.rawObjects.length} rows in ${(performance.now() - t0).toFixed(1)} ms (0 server requests)`;
            this.renderChart();
        } catch (err) {
            this.state.error = err.message;
        }
    }

    async exportClientFile(fmt) {
        if (!this.state.datasetLoaded) return;
        this.state.error = null;
        try {
            const { db, conn } = await getDuckDBConnection();
            const fileName = `export_${Date.now()}.${fmt}`;
            const cleanSql = this.state.activeSql.trim().replace(/;+\s*$/, "");
            const copyOpts = fmt === "parquet" ? "(FORMAT PARQUET, COMPRESSION ZSTD)" : "(FORMAT CSV, HEADER)";

            await conn.query(`COPY (${cleanSql}) TO '${fileName}' ${copyOpts}`);
            const buffer = await db.copyFileToBuffer(fileName);
            await db.dropFile(fileName);

            const url = URL.createObjectURL(new Blob([buffer], { type: "application/octet-stream" }));
            Object.assign(document.createElement("a"), {
                href: url,
                download: `report_${this.state.selectedReportId || "bi"}.${fmt}`
            }).click();
            URL.revokeObjectURL(url);
        } catch (err) {
            this.state.error = err.message;
        }
    }

    renderChart() {
        this.chartInstance?.destroy();
        this.chartInstance = null;
        const cols = this.state.columns;
        if (this.state.chartType === "none" || cols.length < 2 || !this.rawObjects.length || !this.canvasRef.el) {
            return;
        }

        const sample = this.rawObjects.slice(0, 100);
        const labels = sample.map((r) => String(r[cols[0]] ?? ""));
        const datasets = cols.slice(1).map((col) => ({
            label: col,
            data: sample.map((r) => Number(r[col] ?? 0)),
        }));

        this.chartInstance = new window.Chart(this.canvasRef.el, {
            type: this.state.chartType,
            data: { labels, datasets },
            options: { responsive: true, maintainAspectRatio: false, animation: false },
        });
    }
}

registry.category("actions").add("bi_duckdb_engine.report_action", DuckDBReportAction);
