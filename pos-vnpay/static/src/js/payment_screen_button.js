odoo.define("custom_button.PaymentScreenButton", function (require) {
	"use strict";
	const { useListener } = require("@web/core/utils/hooks");
	const Registries = require("point_of_sale.Registries");
	const PaymentScreen = require("point_of_sale.PaymentScreen");

	const CustomButtonPaymentScreen = (PaymentScreen) =>
		class extends PaymentScreen {
			setup() {
				super.setup();
				useListener("click", this.IsCustomButton.bind(this));
			}
			async IsCustomButton(event) {
				// Update QRCode
				var buttonId = event.target.id;
				if (buttonId == "btn_update_qr_code") {
					let list_product = this.env.pos.db.product_by_id;
					let new_list_product = Object.keys(list_product);

					// Add product
					new_list_product = new_list_product.filter((index) => list_product[index].lst_price == 0);
					var order = this.env.pos.get_order();
					if (new_list_product.length > 0)
						await order.add_product(list_product[new_list_product[0]], { quantity: 1, price: 0 });

					// Delete product
					let current_order = this.env.pos.get_order();
					let orderLines = current_order.orderlines.filter((line) => line.get_product());
					orderLines.forEach(async (element) => {
						if (parseInt(element.price) == 0) {
							await current_order.remove_orderline(element);
						}
					});
					console.log("Updated QRCode");
				}
			}
		};
	Registries.Component.extend(PaymentScreen, CustomButtonPaymentScreen);
	return CustomButtonPaymentScreen;
});
