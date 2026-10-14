/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class KpiFormulaWidget extends Component {
    static template = "dn_kpi_scorecard.KpiFormulaWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            formula: this.props.record.data[this.props.name] || "",
            formulaParts: [],
            measures: [],
            kpis: [],
            operands: ["+", "-", "*", "/", "(", ")", "**"],
            customNumber: "",
            searchMeasure: "",
            searchKpi: "",
            activeTab: "measures",
            isRawMode: false,
            // Drag and drop state
            draggedIndex: null,
            dragOverIndex: null,
            isCanvasDragOver: false,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onWillUpdateProps(async (nextProps) => {
            const nextFormula = nextProps.record.data[nextProps.name] || "";
            if (nextFormula !== this.state.formula) {
                this.state.formula = nextFormula;
                await this.refreshFormulaParts();
            }
        });
    }

    get currentFormula() {
        return this.props.record.data[this.props.name] || "";
    }

    async loadData() {
        try {
            const kpiId = this.props.record.data.id || 0;
            const res = await this.orm.call("kpi.item", "action_return_measures", [[kpiId], this.currentFormula]);
            this.state.measures = res.measures || [];
            this.state.kpis = res.kpis || [];
            this.state.operands = res.operands || ["+", "-", "*", "/", "(", ")", "**"];
            this.state.formulaParts = res.formulaparts || [];
        } catch (error) {
            console.error("Failed to load KPI measures:", error);
        }
    }

    async refreshFormulaParts() {
        if (!this.state.formula) {
            this.state.formulaParts = [];
            return;
        }
        try {
            const parts = await this.orm.call("kpi.item", "action_render_formula", [this.state.formula]);
            this.state.formulaParts = parts || [];
        } catch (error) {
            console.error("Failed to render formula parts:", error);
        }
    }

    async updateFormula(newFormula) {
        this.state.formula = newFormula;
        await this.props.record.update({ [this.props.name]: newFormula });
        await this.refreshFormulaParts();
    }

    async addPart(id, name, type) {
        const current = (this.state.formula || "").trim();
        let updated;
        if (!current) {
            updated = id;
        } else {
            updated = `${current};${id}`;
        }
        await this.updateFormula(updated);
    }

    async addOperator(op) {
        await this.addPart(op, op, "OPERATOR");
    }

    async addNumber() {
        const num = String(this.state.customNumber || "").trim();
        if (num) {
            await this.addPart(num, num, "NUMBER");
            this.state.customNumber = "";
        }
    }

    async addDirectNumber(numStr) {
        await this.addPart(numStr, numStr, "NUMBER");
    }

    onNumberKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addNumber();
        }
    }

    async removePart(index) {
        const parts = (this.state.formula || "").split(";");
        if (index >= 0 && index < parts.length) {
            parts.splice(index, 1);
            const updated = parts.join(";");
            await this.updateFormula(updated);
        }
    }

    async backspace() {
        const parts = (this.state.formula || "").split(";");
        if (parts.length > 0) {
            parts.pop();
            const updated = parts.join(";");
            await this.updateFormula(updated);
        }
    }

    async clearFormula() {
        await this.updateFormula("");
    }

    toggleRawMode() {
        this.state.isRawMode = !this.state.isRawMode;
    }

    async onRawFormulaChange(ev) {
        const val = ev.target.value || "";
        await this.updateFormula(val);
    }

    setActiveTab(tabName) {
        this.state.activeTab = tabName;
    }

    filterList(list, query) {
        if (!query) {
            return list || [];
        }
        const q = query.toLowerCase().trim();
        return (list || []).filter((item) => item.name && item.name.toLowerCase().includes(q));
    }

    getPillClass(part) {
        if (part.type === "MEASURE") return "kpi-pill-measure";
        if (part.type === "KPI") return "kpi-pill-kpi";
        if (part.type === "CONST") return "kpi-pill-const";
        if (part.type === "PERIOD" || part.type === "PERIOD_passed") return "kpi-pill-period";
        if (part.type === "OPERATOR") return "kpi-pill-operator";
        return "kpi-pill-number";
    }

    // --- Drag and Drop Handlers ---

    onPillDragStart(ev, index) {
        if (this.props.readonly) {
            ev.preventDefault();
            return;
        }
        this.state.draggedIndex = index;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", String(index));
    }

    onPillDragOver(ev, index) {
        if (this.props.readonly) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        if (this.state.dragOverIndex !== index) {
            this.state.dragOverIndex = index;
        }
    }

    onPillDragLeave(ev, index) {
        if (this.state.dragOverIndex === index) {
            this.state.dragOverIndex = null;
        }
    }

    onPillDragEnd(ev) {
        this.state.draggedIndex = null;
        this.state.dragOverIndex = null;
        this.state.isCanvasDragOver = false;
    }

    async onPillDrop(ev, targetIndex) {
        if (this.props.readonly) return;
        ev.preventDefault();
        ev.stopPropagation();

        const sourceIndex = this.state.draggedIndex;
        this.state.draggedIndex = null;
        this.state.dragOverIndex = null;
        this.state.isCanvasDragOver = false;

        // Check if dragging an item from toolbox
        const toolboxDataStr = ev.dataTransfer.getData("application/json");
        if (toolboxDataStr) {
            try {
                const data = JSON.parse(toolboxDataStr);
                if (data.id) {
                    const parts = (this.state.formula || "").split(";").filter(Boolean);
                    parts.splice(targetIndex, 0, data.id);
                    await this.updateFormula(parts.join(";"));
                    return;
                }
            } catch (e) {
                console.error("Failed to parse dropped toolbox item:", e);
            }
        }

        // Swapping two pills on the canvas
        if (sourceIndex !== null && sourceIndex !== undefined && sourceIndex !== targetIndex) {
            const parts = (this.state.formula || "").split(";").filter(Boolean);
            if (sourceIndex >= 0 && sourceIndex < parts.length && targetIndex >= 0 && targetIndex < parts.length) {
                // Swap places between sourceIndex and targetIndex
                const temp = parts[sourceIndex];
                parts[sourceIndex] = parts[targetIndex];
                parts[targetIndex] = temp;
                await this.updateFormula(parts.join(";"));
            }
        }
    }

    onToolboxDragStart(ev, id, name, type) {
        if (this.props.readonly) {
            ev.preventDefault();
            return;
        }
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("application/json", JSON.stringify({ id, name, type }));
    }

    onCanvasDragOver(ev) {
        if (this.props.readonly) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        this.state.isCanvasDragOver = true;
    }

    onCanvasDragLeave(ev) {
        if (ev.currentTarget === ev.target) {
            this.state.isCanvasDragOver = false;
        }
    }

    async onCanvasDrop(ev) {
        if (this.props.readonly) return;
        ev.preventDefault();
        this.state.isCanvasDragOver = false;
        const sourceIndex = this.state.draggedIndex;
        this.state.draggedIndex = null;
        this.state.dragOverIndex = null;

        // Check if dragged from toolbox
        const toolboxDataStr = ev.dataTransfer.getData("application/json");
        if (toolboxDataStr) {
            try {
                const data = JSON.parse(toolboxDataStr);
                if (data.id) {
                    await this.addPart(data.id, data.name, data.type);
                    return;
                }
            } catch (e) {
                console.error("Failed to parse dropped toolbox item:", e);
            }
        }

        // If pill dragged and dropped on canvas background: move to end
        if (sourceIndex !== null && sourceIndex !== undefined) {
            const parts = (this.state.formula || "").split(";").filter(Boolean);
            if (sourceIndex >= 0 && sourceIndex < parts.length) {
                const [item] = parts.splice(sourceIndex, 1);
                parts.push(item);
                await this.updateFormula(parts.join(";"));
            }
        }
    }
}

export const kpiFormulaWidget = {
    component: KpiFormulaWidget,
    supportedTypes: ["char"],
};

registry.category("fields").add("kpiFormulaWidget", kpiFormulaWidget);
