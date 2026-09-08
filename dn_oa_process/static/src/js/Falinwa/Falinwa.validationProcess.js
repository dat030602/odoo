/** @odoo-module */
import { registry } from "@web/core/registry";
import { session } from "@web/session";

class ValidationProcess {
    constructor(env, services) {
        this.orm = services.orm;
        this.action = services.action;
        this.container = null;
        this.model = null;
        this.resId = null;
        this.refreshKey = null;
        this.refreshPromise = null;
        this.boundClick = this.onClick.bind(this);
    }

    isVprocessModel(model) {
        const models = session.vprocess_models || [];
        return !!model && models.includes(model);
    }

    async refresh(model, resId) {
        if (!this.isVprocessModel(model)) {
            return false;
        }
        const refreshKey = `${model || ""}:${resId || "new"}`;
        if (this.refreshKey === refreshKey && this.container?.isConnected) {
            return false;
        }
        this.model = model;
        this.resId = resId;
        this.refreshKey = refreshKey;
        if (!model || !resId) {
            this.removeContainer();
            this.clearLocks();
            return false;
        }
        this.removeContainer();
        this.clearLocks();
        if (this.refreshPromise) {
            await this.refreshPromise;
        }
        this.refreshPromise = this.orm
            .call("fal.vprocess", "render_approval_bar", [model, resId])
            .then((payload) => {
                if (this.refreshKey === refreshKey) {
                    this.applyPayload(payload);
                }
                return payload;
            })
            .finally(() => {
                this.refreshPromise = null;
            });
        return this.refreshPromise;
    }

    applyPayload(payload) {
        this.removeContainer();
        if (!payload?.html) {
            this.clearLocks();
            return;
        }
        let buttonBox = document.querySelector(".oe_button_box");
        if (!buttonBox) {
            const sheet = document.querySelector(".o_form_sheet");
            if (!sheet) {
                return;
            }
            buttonBox = document.createElement("div");
            buttonBox.className = "oe_button_box";
            buttonBox.setAttribute("name", "button_box");
            sheet.prepend(buttonBox);
        }
        buttonBox.insertAdjacentHTML("afterbegin", payload.html);
        this.container = buttonBox.querySelector("#" + payload.container_id);
        this.container?.parentElement?.addEventListener("click", this.boundClick);
        this.applyLocks(payload);
    }

    applyLocks(payload) {
        document.body.classList.toggle("validationProcess_lock_edit", !!payload.lock_edit);
        document.body.classList.toggle(
            "validationProcess_lock_actions",
            !!payload.lock_actions
        );
    }

    async onClick(event) {
        const button = event.target.closest("[data-vp-action]");
        if (!button || button.disabled || !this.container?.contains(button)) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (button.dataset.vpAction === "history") {
            const action = await this.orm.call(
                "fal.vprocess",
                "action_open_approval_history",
                [this.model, this.resId]
            );
            await this.action.doAction(action);
            return;
        }
        button.disabled = true;
        try {
            const payload = await this.orm.call("fal.vprocess", "execute_approval_action", [
                this.model,
                this.resId,
                button.dataset.vpAction,
            ]);
            this.applyPayload(payload);
        } catch (error) {
            button.disabled = false;
            throw error;
        }
    }

    removeContainer() {
        this.container?.parentElement?.removeEventListener("click", this.boundClick);
        this.container?.remove();
        this.container = null;
    }

    clearLocks() {
        document.body.classList.remove("validationProcess_lock_edit");
        document.body.classList.remove("validationProcess_lock_actions");
    }
}

export const validationProcess = {
    dependencies: ["orm", "action"],
    start(env, services) {
        const instance = new ValidationProcess(env, services);
        window.odoo = window.odoo || {};
        window.odoo._mb = window.odoo._mb || {};
        window.odoo._mb.ValidationProcess = instance;
        return instance;
    },
};

registry.category("services").add("validationProcess", validationProcess);
