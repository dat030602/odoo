odoo.define("pos_vnpay.models", function (require) {
	var models = require("point_of_sale.models");
	var PaymentVNPay = require("pos_vnpay.payment");

	models.register_payment_method("vnpay", PaymentVNPay);
});
