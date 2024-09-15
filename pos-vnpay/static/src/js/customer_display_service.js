odoo.define("pos_vnpay.PosGlobalState", function (require) {
	"use strict";

	var core = require("web.core");

	const rpc = require("web.rpc");

	var QWeb = core.qweb;

	const Registries = require("point_of_sale.Registries");

	const { PosGlobalState } = require("point_of_sale.models");

	// Container of the product images fetched during rendering
	// of customer display. There is no need to observe it, thus,
	// we are putting it outside of PosGlobalState.
	const PRODUCT_ID_TO_IMAGE_CACHE = {};

	const POSVNpayPosGlobalState = (PosGlobalState) =>
		class POSVNpayPosGlobalState extends PosGlobalState {
			pos_qr_code = "";

			setup() {
				super.setup();
				this.pos_qr_code = "";
			}

			async get_qr_code(order) {
				try {
					const rpc1 = require("web.rpc");
					let result = await rpc1.query({
						model: "pos_vnpay.stack_payment",
						method: "get_qr_code",
						args: [order.uid, "", true],
					});
					return { qr_code: result };
				} catch (error) {
					return false;
				}
			}

			//@override
			async render_html_for_customer_facing_display() {
				var self = this;
				var order = this.get_order();
				var qr_code = this.pos_qr_code;

				var get_image_promises = [];

				if (order) {
					order.get_orderlines().forEach(function (orderline) {
						var product = orderline.product;
						var image_url = `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.__last_update}`;

						// only download and convert image if we haven't done it before
						if (!(product.id in PRODUCT_ID_TO_IMAGE_CACHE)) {
							get_image_promises.push(self._convert_product_img_to_base64(product, image_url));
						}
					});
				}

				return Promise.all(get_image_promises).then(function (productIdImagePairs) {
					for (let [product, image] of productIdImagePairs) {
						PRODUCT_ID_TO_IMAGE_CACHE[product.id] = image;
					}
					// Collect the product images that will be used in rendering the customer display template.
					const productImages = {};
					if (order) {
						for (const line of order.get_orderlines()) {
							productImages[line.product.id] = PRODUCT_ID_TO_IMAGE_CACHE[line.product.id];
						}
					}

					return QWeb.render("CustomerFacingDisplayOrder", {
						pos: self,
						origin: window.location.origin,
						order: order,
						productImages,
						srcQrCode: typeof qr_code == "boolean" ? "" : qr_code,
					});
				});
			}

			//@override
			async send_current_order_to_customer_facing_display() {
				var self = this;
				var order = this.get_order();

				let qrCodeResult = await this.get_qr_code(order);
				this.pos_qr_code = typeof qrCodeResult.qr_code == "boolean" ? "" : qrCodeResult.qr_code;

				if (!this.config.iface_customer_facing_display) return;
				this.render_html_for_customer_facing_display().then((rendered_html) => {
					if (self.env.pos.customer_display) {
						var $renderedHtml = $("<div>").html(rendered_html);
						$(self.env.pos.customer_display.document.body).html(
							$renderedHtml.find(".pos-customer_facing_display")
						);
						var orderlines = $(self.env.pos.customer_display.document.body).find(".pos_orderlines_list");
						orderlines.scrollTop(orderlines.prop("scrollHeight"));
					} else if (
						this.config.iface_customer_facing_display_via_proxy &&
						this.env.proxy.posbox_supports_display
					) {
						this.env.proxy.update_customer_facing_display(rendered_html);
					}
				});
			}
		};
	Registries.Model.extend(PosGlobalState, POSVNpayPosGlobalState);
	return POSVNpayPosGlobalState;
});
