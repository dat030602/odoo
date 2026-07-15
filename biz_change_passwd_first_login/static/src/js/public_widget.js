/** @odoo-module **/

import registry from 'web.public.widget';
import ajax from "web.ajax";
import dom from 'web.dom';
var return_login = false;
registry.registry.login.include({
    _onSubmit(ev) {
        if (return_login) {
            if (!ev.isDefaultPrevented()) {
                const btnEl = ev.currentTarget.querySelector('button[type="submit"]');
                const removeLoadingEffect = dom.addButtonLoadingEffect(btnEl);
                const oldPreventDefault = ev.preventDefault.bind(ev);
                ev.preventDefault = () => {
                    removeLoadingEffect();
                    oldPreventDefault();
                };
            }
        } else {
            ev.preventDefault();
            var login = $(ev.target).find('#login').val();
            ajax.jsonRpc('/check_popup_change_password', 'call',{'login': login})
            .then(function(result) {
                if (result) {
                    $("#myPopup #login_popup")[0].value = login;
                    $("#myPopup #login_popup").prop('disabled', true);
                    $("#myPopup").show();
                    return_login = false;
                }else {
                    return_login = true;
                    $(ev.target).submit();
                }
            });
        }
    },
})