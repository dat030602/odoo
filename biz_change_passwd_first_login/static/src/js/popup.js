odoo.define('biz_change_passwd_first_login.popup', function (require) {
'use strict';

const { jsonRpc } = require("web.ajax");
const {_t} = require('web.core');

$(document).on('click','#SubmitPopup',function(){
    var login = $("#myPopup #login_popup").val();
    var passwd = $("#myPopup #password_popup").val();
    var re_passwd = $("#myPopup #re_password_popup").val();
    if (!passwd || !re_passwd) {
        $("#myPopup .notification .raise-error").show()
        $("#myPopup .notification .raise-error")[0].innerHTML = _t('Please Enter Password');
        if (passwd) {$("#myPopup #password_popup").removeClass('border-red');}
        if (re_passwd) {$("#myPopup #re_password_popup").removeClass('border-red');}
        if (!passwd) {$("#myPopup #password_popup").addClass('border-red');}
        if (!re_passwd) {$("#myPopup #re_password_popup").addClass('border-red');}
        return
    }
    if (passwd != re_passwd) {
        $("#myPopup .notification .raise-error").show()
        $("#myPopup .notification .raise-error")[0].innerHTML = _t('Password not Match!');
        return
    }
    jsonRpc('/change_password_popup', 'call',{'login': login,'passwd': passwd})
    .then(function(result) {
        console.log('resadas',result)
        if (result.success) {
            $("#myPopup .notification .raise-error").hide()
            $("#myPopup .notification .success").show();
            setTimeout(function reload_page() {location.reload()}, 2000);
        }else {
            $("#myPopup .notification .raise-error").show()
            $("#myPopup .notification .raise-error")[0].innerHTML = result.error;
        }
    });
})
$(document).on('click','#closePopup',function(){
    $('#myPopup').hide()
})
});
