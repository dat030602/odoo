/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { View } from '@web/views/view';
import { patch } from '@web/core/utils/patch';
import { onWillStart, useState, useSubEnv } from '@odoo/owl';

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        this.mjbFormActions = useState({
            mode: 'default',
            selectedRecordId: null,
            selectedResModel: this.props.resModel,
            splitWidth: 50,
            setMode: (mode) => this.setFormActionMode(mode),
            setSelectedRecord: (id, resModel) => {
                this.mjbFormActions.selectedRecordId = id;
                this.mjbFormActions.selectedResModel = resModel || this.props.resModel;
            },
            setSelectedRecordId: (id) => {
                this.mjbFormActions.selectedRecordId = id;
                this.mjbFormActions.selectedResModel = this.props.resModel;
            },
            onResizeStart: (ev) => this.onResizeStart(ev),
            getMjbViewComponent: () => View,
        });

        useSubEnv({ mjbFormActions: this.mjbFormActions });

        onWillStart(async () => {
            const localKey = this.getLocalKeyFormView();
            const storedValue = localKey ? localStorage.getItem(localKey) : null;

            const savedWidth = localStorage.getItem(localKey + '_width');
            if (savedWidth) {
                this.mjbFormActions.splitWidth = parseFloat(savedWidth);
            }

            let storedMode = 'default';
            if (storedValue) {
                try {
                    const parsed = JSON.parse(storedValue);
                    if (parsed === true) storedMode = 'split';
                    else if (parsed === false) storedMode = 'default';
                    else storedMode = parsed;
                } catch {
                    storedMode = storedValue;
                }
            }

            const defaultMode = this.props.context?.split_view ? 'split' : 'default';
            const mode = storedMode && ['default', 'current', 'split', 'popup'].includes(storedMode)
                ? storedMode
                : defaultMode;
            this.setFormActionMode(mode);
        });
    },

    getLocalKeyFormView() {
        return `mjb_ff_${this.props.resModel}`;
    },

    setFormActionMode(mode) {
        const localKey = this.getLocalKeyFormView();
        if (localKey) {
            localStorage.setItem(localKey, JSON.stringify(mode));
        }
        this.mjbFormActions.mode = mode;

        if (mode !== 'split') {
            this.mjbFormActions.selectedRecordId = null;
            this.mjbFormActions.selectedResModel = this.props.resModel;
        }
    },

    onResizeStart(ev) {
        ev.preventDefault();
        const startX = ev.clientX;
        const initialWidth = this.mjbFormActions.splitWidth;
        const containerEl = ev.target.closest('.dn-form-view-container');
        if (!containerEl) {
            return;
        }

        document.body.classList.add('dn-resizing');

        const containerWidth = containerEl.clientWidth;
        const wrapperEl = containerEl.querySelector('.dn-form-wrapper');
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
                this.mjbFormActions.splitWidth = this.tempSplitWidth;
            }
            
            const localKey = this.getLocalKeyFormView() + '_width';
            localStorage.setItem(localKey, this.mjbFormActions.splitWidth);
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    },
});
