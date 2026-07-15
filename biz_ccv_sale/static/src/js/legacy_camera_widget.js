odoo.define('biz_ccv_sale.legacy_camera_widget', function (require) {
"use strict";

const widgetRegistry = require('web.widget_registry');
const Widget = require('web.Widget');
const Dialog = require('web.Dialog');
var rpc = require('web.rpc');
var core = require('web.core');
const qweb = core.qweb;
var _t = core._t;

const CameraWidgetLegacyIn = Widget.extend({
    template: 'biz_ccv_sale.CameraWidgetLegacyIn',
    events: {
        'click button': '_onCheckin'
    },

    init: function (parent, options) {
        this._super(...arguments);
        this.data = options.data
    },
    _onCheckin: function(ev){
        if (!this.data.partner_id){
            Dialog.alert(this, _t('Please select partner'), {
                title: _t("Error"),
            });
            return
        }
        if (!this.data.is_valid_check){
            var error_name = _t('Customer ') + this.data.valid_partner + _t(' have not completed check-in/check-out') 
            Dialog.alert(this, error_name , {
                title: _t("Error"),
            });
            return
        }

        var self = this,
            WebCamDialog = $(qweb.render("UserAuthDialog")), 
            img_data
        
        Webcam.set({
            width: 320,
            height: 240,
            dest_width: 320,
            dest_height: 240,
            image_format: 'jpeg',
            jpeg_quality: 90,
            force_flash: false,
            fps: 45,
            swfURL: '/biz_ccv_sale/static/src/js/webcam.swf',
        });

        rpc.query({
            model: 'ir.config_parameter',
            method: 'get_webcam_flash_fallback_mode_config',
        }).then(function(default_flash_fallback_mode) {
            if (default_flash_fallback_mode == 1) {
                Webcam.set({
                    force_flash: true,
                });
            }
        });
        console.log("self", self)
        var partner_id = self.data.partner_id.res_id
        rpc.query({
            model: 'res.partner',
            method: 'action_check_in',
            args: [partner_id],
        }).then(function(check_coordinates_received) {
            if(check_coordinates_received){
                var error = check_coordinates_received.error,
                    error_name = check_coordinates_received.error_name

                if (error){
                    Dialog.alert(this, error_name, {
                        title: _t("Error"),
                    });
                }else{
                    var lat = check_coordinates_received.lat,
                    long = check_coordinates_received.long

                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(function(position) {
                            lat = position.coords.latitude
                            long = position.coords.longitude
                        })
                    }

                    var dialog = new Dialog(this, {
                    title: _t("User Authentication"),
                    size: 'large',
                    $content: WebCamDialog,
                    buttons: [{
                        text: _t("Take Snapshot"), 
                        classes: 'btn-primary take_snap_btn',
                        click: function () {
                            Webcam.snap( function(data) {
                                img_data = data;
                                // Display Snap besides Live WebCam Preview
                                WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
                            });
                            if (Webcam.live) {
                                // Remove "disabled" attr from "Save & Close" button
                                $('.save_close_btn').removeAttr('disabled');
                            }
                        }
                        },
                        {
                            text: _t("Save & Close"), 
                            classes: 'btn-primary save_close_btn', 
                            close: true,
                            click:  function () {
                                if(!img_data){
                                    Webcam.snap( function(data) {
                                        img_data = data;
                                        // Display Snap besides Live WebCam Preview
                                        WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
                                    });
                                }
                                var img_data_base64 = img_data.split(',')[1]
                                return rpc.query({
                                    model: 'sale.route.line',
                                    method: 'generate_checkin_history',
                                    args: [parseInt(self.data.id), img_data_base64, lat, long],
                                }).then(async function(result) {
                                    console.log("result", result)
                                    if (result){
                                        Dialog.alert(this, _t("Successfully checkin"), {
                                            title: _t("Notifications"),
                                        });
                                        setTimeout(() => {
                                            location.reload()
                                        }, 2000);
                                        
                                    }else{
                                        Dialog.alert(this,_t("Check in failed, Please try again") , {
                                            title: _t("Error"),
                                        });
                                        
                                    }

                                });
                            }
                        },
                        {
                            text: _t("Close"),
                            close: true
                        }]
                    }).open();
    
                    dialog.opened().then(function() {
                        Webcam.attach('#live_webcam');
                        $('.s').attr('disabled', 'disabled');
                        WebCamDialog.find("#webcam_result").html('<img src="/biz_ccv_sale/static/src/img/webcam_placeholder.png"/>');
                    });
                }
            }
        });
    }
});

const CameraWidgetLegacyOut = Widget.extend({
    template: 'biz_ccv_sale.CameraWidgetLegacyOut',
    events: {
        'click button': '_onCheckout'
    },
    init: function (parent, options) {
        this._super(...arguments);
        this.data = options.data
    },
    _onCheckout: function(ev){
        if (!this.data.partner_id){
            Dialog.alert(this, _t('Please select partner'), {
                title: _t("Error"),
            });
            return
        }
        if (!this.data.is_valid_check){
            var error_name = _t('Customer ') + this.data.valid_partner + _t(' have not completed check-in/check-out') 
            Dialog.alert(this, error_name , {
                title: _t("Error"),
            });
            return
        }

        if (!this.data.sale_route_report_id){
            var error_name = _t('Customer ') + this.data.partner_id[1] + _t(" haven't done the check-in yet") 
            Dialog.alert(this, error_name , {
                title: _t("Error"),
            });
            return
        }
        
        var self = this,
            WebCamDialog = $(qweb.render("UserAuthDialog")), 
            img_data
        
        Webcam.set({
            width: 320,
            height: 240,
            dest_width: 320,
            dest_height: 240,
            image_format: 'jpeg',
            jpeg_quality: 90,
            force_flash: false,
            fps: 45,
            swfURL: '/biz_ccv_sale/static/src/js/webcam.swf',
        });

        rpc.query({
            model: 'ir.config_parameter',
            method: 'get_webcam_flash_fallback_mode_config',
        }).then(function(default_flash_fallback_mode) {
            if (default_flash_fallback_mode == 1) {
                Webcam.set({
                    force_flash: true,
                });
            }
        });
        var partner_id = self.data.partner_id.res_id

        rpc.query({
            model: 'res.partner',
            method: 'action_check_in',
            args: [partner_id],
        }).then(function(check_coordinates_received) {
            if(check_coordinates_received){
                var error = check_coordinates_received.error,
                    error_name = check_coordinates_received.error_name

                if (error){
                    Dialog.alert(this, error_name, {
                        title: _t("Error"),
                    });
                }else{
                    var lat = check_coordinates_received.lat,
                    long = check_coordinates_received.long

                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(function(position) {
                            lat = position.coords.latitude
                            long = position.coords.longitude
                        })
                    }

                    var dialog = new Dialog(this, {
                    title: _t("User Authentication"),
                    size: 'large',
                    $content: WebCamDialog,
                    buttons: [{
                        text: _t("Take Snapshot"), 
                        classes: 'btn-primary take_snap_btn',
                        click: function () {
                            Webcam.snap( function(data) {
                                img_data = data;
                                // Display Snap besides Live WebCam Preview
                                WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
                            });
                            if (Webcam.live) {
                                // Remove "disabled" attr from "Save & Close" button
                                $('.save_close_btn').removeAttr('disabled');
                            }
                        }
                        },
                        {
                            text: _t("Save & Close"), 
                            classes: 'btn-primary save_close_btn', 
                            close: true,
                            click:  function () {
                                if(!img_data){
                                    Webcam.snap( function(data) {
                                        img_data = data;
                                        // Display Snap besides Live WebCam Preview
                                        WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
                                    });
                                }
                                var img_data_base64 = img_data.split(',')[1]
                                return rpc.query({
                                    model: 'sale.route.line',
                                    method: 'generate_checkout_history',
                                    args: [parseInt(self.data.id),parseInt(self.data.id), img_data_base64, lat, long],
                                }).then(async function(result) {
                                    if (result){
                                        Dialog.alert(this, _t("Successfully checkout"), {
                                            title: _t("Notifications"),
                                        });
                                        setTimeout(() => {
                                            location.reload()
                                        }, 2000);
                                        
                                    }else{
                                        Dialog.alert(this,_t("Check out failed, Please try again") , {
                                            title: _t("Error"),
                                        });
                                        
                                    }

                                });
                            }
                        },
                        {
                            text: _t("Close"),
                            close: true
                        }]
                    }).open();
    
                    dialog.opened().then(function() {
                        Webcam.attach('#live_webcam');
                        $('.s').attr('disabled', 'disabled');
                        WebCamDialog.find("#webcam_result").html('<img src="/biz_ccv_sale/static/src/img/webcam_placeholder.png"/>');
                    });
                }
            }
        });

    }
});

widgetRegistry.add('legacy_camera_widget_checkin', CameraWidgetLegacyIn);
widgetRegistry.add('legacy_camera_widget_checkout', CameraWidgetLegacyOut);
});