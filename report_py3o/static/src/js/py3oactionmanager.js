/** @odoo-module **/

import {
    download
} from "@web/core/network/download";
import {
    registry
} from "@web/core/registry";

registry
    .category("ir.actions.report handlers")
    .add("py3o_handler", async function (action, options, env) {
        if (action.report_type === "py3o") {
            const type = action.report_type;
            let url = `/report/${type}/${action.report_name}`;
            const actionContext = action.context || {};
            if (action.data && JSON.stringify(action.data) !== "{}") {
                // Build a query string with `action.data` (it's the place where reports
                // using a wizard to customize the output traditionally put their options)
                const action_options = encodeURIComponent(JSON.stringify(action.data));
                const context = encodeURIComponent(JSON.stringify(actionContext));
                url += `?options=${action_options}&context=${context}`;
            } else {
                if (actionContext.active_ids) {
                    url += `/${actionContext.active_ids.join(",")}`;
                }
                if (type === "py3o") {
                    const context = encodeURIComponent(
                        JSON.stringify(env.services.user.context)
                    );
                    url += `?context=${context}`;
                }
            }
            env.services.ui.block();
            try {
                await download({
                    url: "/report/download",
                    data: {
                        data: JSON.stringify([url, action.report_type]),
                        context: JSON.stringify(env.services.user.context),
                    },
                });
            } finally {
                env.services.ui.unblock();
            }
            const onClose = options.onClose;
            if (action.close_on_report_download) {
                return env.services.action.doAction({
                    type: "ir.actions.act_window_close"
                }, {
                    onClose
                });
            } else if (onClose) {
                onClose();
            }
            return Promise.resolve(true);
        }
        return Promise.resolve(false);
    });

/* Copyright 2017-2018 ACSONE SA/NV
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
//odoo.define("report_py3o.report", function (require) {
//    "use strict";
//
//    var ActionManager = require("web.ActionManager");
//
//    ActionManager.include({
//        _executeReportAction: function (action, options) {
//            // Py3o reports
//            if ("report_type" in action && action.report_type === "py3o") {
//                return this._triggerDownload(action, options, "py3o");
//            }
//            return this._super.apply(this, arguments);
//        },
//
//        _makeReportUrls: function (action) {
//            var reportUrls = this._super.apply(this, arguments);
//            reportUrls.py3o = "/report/py3o/" + action.report_name;
//            // We may have to build a query string with `action.data`. It's the place
//            // were report's using a wizard to customize the output traditionally put
//            // their options.
//            if (
//                _.isUndefined(action.data) ||
//                _.isNull(action.data) ||
//                (_.isObject(action.data) && _.isEmpty(action.data))
//            ) {
//                if (action.context.active_ids) {
//                    var activeIDsPath = "/" + action.context.active_ids.join(",");
//                    reportUrls.py3o += activeIDsPath;
//                }
//            } else {
//                var serializedOptionsPath =
//                    "?options=" + encodeURIComponent(JSON.stringify(action.data));
//                serializedOptionsPath +=
//                    "&context=" + encodeURIComponent(JSON.stringify(action.context));
//                reportUrls.py3o += serializedOptionsPath;
//            }
//            return reportUrls;
//        },
//    });
//});