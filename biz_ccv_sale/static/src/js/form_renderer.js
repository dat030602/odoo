odoo.define('biz_ccv_sale.form_renderer', function(require) {
    "use strict";
    
    var FormRenderer = require('web.FormRenderer');
    var FormView = require('web.FormView');
    var core = require('web.core');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var framework = require('web.framework');
    var view_dialogs = require('web.view_dialogs');
    var _t = core._t;
    
    view_dialogs.FormViewDialog.include({
        init(parent, options) {
            this._super.apply(this, arguments);
            var self = this;
            var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
            if (!multi_select && this.res_model == 'sale.route'){
                self.buttons.push({
                    text: _t("Remove"),
                    classes: "btn-primary",
                    hotkey: 'r',
                    click: function () {

                        self._remove().then(self.close.bind(self));
                    }
                });
            }
            
        },
    });

//    var CCVFormRenderer = FormRenderer.extend({
//        events: _.extend({}, FormRenderer.prototype.events, {
//            'click #show_cammera': '_show_cammera_for_user_authentication',
//        }),
//        /*
//         * Open the m2o item selection from another button
//         */
//        _show_cammera_for_user_authentication: function(ev) {
//            var self = this,
//                WebCamDialog = $(qweb.render("UserAuthDialog")),
//                img_data
//
//            Webcam.set({
//                width: 320,
//                height: 240,
//                dest_width: 320,
//                dest_height: 240,
//                image_format: 'jpeg',
//                jpeg_quality: 90,
//                force_flash: false,
//                fps: 45,
//                swfURL: '/biz_ccv_sale/static/src/js/webcam.swf',
//            });
//
//            rpc.query({
//                model: 'ir.config_parameter',
//                method: 'get_webcam_flash_fallback_mode_config',
//            }).then(function(default_flash_fallback_mode) {
//                if (default_flash_fallback_mode == 1) {
//                    Webcam.set({
//                        force_flash: true,
//                    });
//                }
//            });
//            var parnter_id = self.state.data.id
//
//            // Step1: Get coordinates
//            rpc.query({
//                model: 'res.partner',
//                method: 'action_check_in',
//                args: [parnter_id],
//            }).then(function(check_coordinates_received) {
//                if(check_coordinates_received){
//
//                    var error = check_coordinates_received.error,
//                        error_name = check_coordinates_received.error_name
//                    console.log(error)
//                    if (error){
//                        Dialog.alert(this, error_name, {
//                            title: _t("Error"),
//                        });
//                    }else{
//                        var lat = check_coordinates_received.lat,
//                        long = check_coordinates_received.long
//
//                        if (navigator.geolocation) {
//                            navigator.geolocation.getCurrentPosition(function(position) {
//                                lat = position.coords.latitude
//                                long = position.coords.longitude
//                            })
//                        }
//
//                        var dialog = new Dialog(this, {
//                        title: _t("User Authentication"),
//                        size: 'large',
//                        $content: WebCamDialog,
//                        buttons: [{
//                            text: _t("Take Snapshot"),
//                            classes: 'btn-primary take_snap_btn',
//                            click: function () {
//                                Webcam.snap( function(data) {
//                                    img_data = data;
//                                    // Display Snap besides Live WebCam Preview
//                                    WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
//                                });
//                                if (Webcam.live) {
//                                    // Remove "disabled" attr from "Save & Close" button
//                                    $('.save_close_btn').removeAttr('disabled');
//                                }
//                            }
//                            },
//                            // click: save
//                            {
//                                text: _t("Save & Close"),
//                                classes: 'btn-primary save_close_btn',
//                                close: true,
//                                click: function () {
//                                    if(!img_data){
//                                        Webcam.snap( function(data) {
//                                            img_data = data;
//                                            // Display Snap besides Live WebCam Preview
//                                            WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
//                                        });
//                                    }
//                                    var img_data_base64 = img_data.split(',')[1]
//                                    return rpc.query({
//                                        model: 'res.partner',
//                                        method: 'generate_checkin_history',
//                                        args: [parnter_id, img_data_base64, lat, long],
//                                    }).then(function(check_coordinates_received) {
//                                        location.reload();
//                                    });
//                                }
//                            },
//                            {
//                                text: _t("Close"),
//                                close: true
//                            }]
//                        }).open();
//
//                        dialog.opened().then(function() {
//                            Webcam.attach('#live_webcam');
//                            $('.s').attr('disabled', 'disabled');
//                            WebCamDialog.find("#webcam_result").html('<img src="/biz_ccv_sale/static/src/img/webcam_placeholder.png"/>');
//                        });
//                    }
//                }
//            });
//        },
//
//    });

    Dialog.include({
        destroy: function () {
            // Shut Down the Live Camera Preview | Reset the System
            Webcam.reset();
            this._super.apply(this, arguments);
        },
    });
    
//    var AssetFormView = FormView.extend({
//        config: _.extend({}, FormView.prototype.config, {
//            Renderer: CCVFormRenderer,
//        }),
//    });
//
//    viewRegistry.add("abc_test", AssetFormView);
//
//    return {
//        CCVFormRenderer: CCVFormRenderer,
//        AssetFormView: AssetFormView,
//    };
    
});
    