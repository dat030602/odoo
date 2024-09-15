/* global VNPayTerminal */
odoo.define("pos_vnpay.payment", function (require) {
	"use strict";

	const core = require("web.core");
	const rpc = require("web.rpc");
	// const ajax = require("web.ajax");
	const PaymentInterface = require("point_of_sale.PaymentInterface");
	const { Gui } = require("point_of_sale.Gui");

	const _t = core._t;

	let PaymentVNPay = PaymentInterface.extend({
		init: function (pos, payment_method) {
			this._super(...arguments);
		},

		getDateTime: function (time = 0) {
			var now = new Date();
			if (time != 0) now.setMinutes(now.getMinutes() + time);
			var year = now.getFullYear();
			var month = now.getMonth() + 1;
			var day = now.getDate();
			var hour = now.getHours();
			var minute = now.getMinutes();
			var second = now.getSeconds();
			if (month.toString().length == 1) {
				month = "0" + month;
			}
			if (day.toString().length == 1) {
				day = "0" + day;
			}
			if (hour.toString().length == 1) {
				hour = "0" + hour;
			}
			if (minute.toString().length == 1) {
				minute = "0" + minute;
			}
			if (second.toString().length == 1) {
				second = "0" + second;
			}
			var dateTime = day + "/" + month + "/" + year + " " + hour + ":" + minute + ":" + second;
			return dateTime;
		},

		get_payload_paymentline: async function (data) {
			let amount = 0;
			for (let index = 0; index < data.orderlines.length; index++) {
				const element = data.orderlines[index];
				amount += element.price * element.quantity;
			}
			return {
				uid: data.uid,
				amount: amount,
			};
		},

		send_payment_request: async function (cid) {
			/**
			 * Override
			 */
			await this._super.apply(this, arguments);
			try {
				let line = this.pos.get_order().selected_paymentline;
				//retry,waiting,reversing,done,reversed
				const payload = await this.get_payload_paymentline(this.pos.get_order());
				let result = await rpc.query({
					model: "pos_vnpay.stack_payment",
					method: "validate_payment",
					args: [payload.uid, payload.amount],
				});
				if (typeof result != "boolean") {
					line.set_payment_status("waiting");
					window.open(result, "_blank");
					return false;
				} else {
					if (result) {
						line.set_payment_status("done");
						return true;
					}

					this._showError("Thanh toán chưa được thực hiện !!!", "VNPay - Lỗi thanh toán");
					return false;
				}
			} catch (error) {
				this._showError(error);
				return false;
			}
		},

		get_qr_code: async function (cid) {
			try {
				const payload = this.get_payload_paymentline(this.pos.get_order());
				const rpc1 = require("web.rpc");
				let result = await rpc1.query({
					model: "pos_vnpay.stack_payment",
					method: "get_qr_code",
					args: [payload.uid, ""],
				});
				if (typeof result != "boolean") {
					const inputElement = document.createElement("input");
					inputElement.type = "file";
					inputElement.style.display = "none";
					inputElement.addEventListener("change", (e) => {
						// var files = e.target.files;
						console.log(files);
						if (files.length > 0) {
							var file = files[0];
							var reader = new FileReader();
							reader.onload = async function (e) {
								console.log(e.target.result);
								const rpc1 = require("web.rpc");
								let result1 = await rpc1.query({
									model: "pos_vnpay.stack_payment",
									method: "get_qr_code",
									args: [payload.uid, e.target.result],
								});
								console.log(result1);
							};
							reader.readAsText(file);
						} else {
							console.log("No file selected");
						}
						document.body.removeChild(inputElement);
					});
					document.body.appendChild(inputElement);
					inputElement.click();
					return false;
				} else {
					return result;
				}
			} catch (error) {
				this._showError(error);
				return false;
			}
		},

		send_payment_cancel: async function (order, cid) {
			/**
			 * Override
			 */
			this._super.apply(this, arguments);
			let line = this.pos.get_order().selected_paymentline;
			// let vnpayCancel = await this.vnpayCancel();
			if (vnpayCancel) {
				console.log("run2");
				line.set_payment_status("retry");
				return true;
			}
		},

		// private methods

		_showError: function (msg, title) {
			if (!title) {
				title = _t("VNPay Error");
			}
			Gui.showPopup("ErrorPopup", {
				title: title,
				body: msg,
			});
		},
	});

	return PaymentVNPay;
});
