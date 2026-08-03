/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';
import { patch } from '@web/core/utils/patch';
import { onWillStart, useState, useSubEnv } from '@odoo/owl';
import { View } from '@web/views/view'; 

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        const views = this.props.info.views || [];
        const hasForm = views.some(v => v[1] === 'form');
        // Check if the template name suggests it already has our split logic (except the base ones)
        const isSplitInherited = this.constructor.template.startsWith('dn.') 
            && this.constructor.template !== 'dn.ListView' 
            && this.constructor.template !== 'dn.Breadcrumbs';

        this.mjbListActions = useState({ 
            mode: "default",
            selectedRecordId: null,
            selectedResModel: this.props.resModel,
            splitWidth: 50, 
            resModel: this.props.resModel,
            hasForm: hasForm,
            isSplitInherited: isSplitInherited,
            setMode: (mode) => this.setActionMode(mode),
            setSelectedRecord: (id, resModel) => {
                this.mjbListActions.selectedRecordId = id;
                this.mjbListActions.selectedResModel = resModel || this.props.resModel;
            },
            setSelectedRecordId: (id) => {
                this.mjbListActions.selectedRecordId = id;
                this.mjbListActions.selectedResModel = this.props.resModel;
            },
            onResizeStart: (ev) => this.onResizeStart(ev),
            getMjbViewComponent: () => View,
        });

        useSubEnv({ mjbListActions: this.mjbListActions });

        onWillStart(async () => {
            const localKey = this.getLocalKeySplitView();
            const storedValue = localKey ? localStorage.getItem(localKey) : null;
            
            const savedWidth = localStorage.getItem(localKey + "_width");
            if (savedWidth) {
                this.mjbListActions.splitWidth = parseFloat(savedWidth);
            }
            
            let storedMode = "default";
            if (storedValue) {
                try {
                    const parsed = JSON.parse(storedValue);
                    if (parsed === true) storedMode = "split";
                    else if (parsed === false) storedMode = "default";
                    else storedMode = parsed;
                } catch {
                    storedMode = storedValue;
                }
            }

            const defaultMode = this.props.context?.split_view ? "split" : "default";
            this.setActionMode(storedMode && ["default", "split", "popup"].includes(storedMode) ? storedMode : defaultMode);
        });
    },

    getLocalKeySplitView() {
        return `mjb_sf_${this.props.resModel}`;
    },

    setActionMode(mode) {
        const localKey = this.getLocalKeySplitView();
        if (localKey) {
            localStorage.setItem(localKey, JSON.stringify(mode));
        }
        this.mjbListActions.mode = mode;
        
        if (mode !== 'split') {
            this.mjbListActions.selectedRecordId = null;
            this.mjbListActions.selectedResModel = this.props.resModel;
        }
    },

    getMjbViewComponent() {
        return View;
    },

    onResizeStart(ev) {
        ev.preventDefault();
        const startX = ev.clientX;
        const initialWidth = this.mjbListActions.splitWidth; 
        const containerEl = ev.target.closest('.dn-list-view-container');
        if (!containerEl) return;
        
        document.body.classList.add('dn-resizing');

        const containerWidth = containerEl.clientWidth;
        const wrapperEl = containerEl.querySelector('.dn-list-wrapper');
        const splitEl = containerEl.querySelector('.dn-split-form-view');
        this.tempSplitWidth = initialWidth;

        const onMouseMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            const dxPercent = (dx / containerWidth) * 100;
            let newWidth = initialWidth - dxPercent;
            
            if (newWidth < 20) newWidth = 20;
            if (newWidth > 80) newWidth = 80;
            
            this.tempSplitWidth = newWidth;
            if (wrapperEl) wrapperEl.style.width = (100 - newWidth) + '%';
            if (splitEl) splitEl.style.width = newWidth + '%';
        };

        const onMouseUp = () => {
            document.body.classList.remove('dn-resizing');
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            
            if (this.tempSplitWidth !== undefined) {
                this.mjbListActions.splitWidth = this.tempSplitWidth;
            }
            
            const localKey = this.getLocalKeySplitView() + "_width";
            localStorage.setItem(localKey, this.mjbListActions.splitWidth);
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    },

    async openRecord(record) {
        if (this.mjbListActions.hasForm && (this.mjbListActions.mode === 'split' || this.mjbListActions.mode === 'popup')) {
            if (this.mjbListActions.mode === 'split') {
                this.mjbListActions.setSelectedRecord(record.resId, record.resModel || this.props.resModel);
                return;
            } else if (this.mjbListActions.mode === 'popup') {
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: this.props.resModel,
                    res_id: record.resId,
                    views: [[false, 'form']],
                    target: 'new',
                });
                return;
            }
        }
        return super.openRecord(...arguments);
    },
});
