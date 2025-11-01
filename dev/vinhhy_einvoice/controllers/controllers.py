# -*- coding: utf-8 -*-
# from odoo import http


# class VinhhyEinvoiceService(http.Controller):
#     @http.route('/vinhhy_einvoice_service/vinhhy_einvoice_service/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vinhhy_einvoice_service/vinhhy_einvoice_service/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('vinhhy_einvoice_service.listing', {
#             'root': '/vinhhy_einvoice_service/vinhhy_einvoice_service',
#             'objects': http.request.env['vinhhy_einvoice_service.vinhhy_einvoice_service'].search([]),
#         })

#     @http.route('/vinhhy_einvoice_service/vinhhy_einvoice_service/objects/<model("vinhhy_einvoice_service.vinhhy_einvoice_service"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vinhhy_einvoice_service.object', {
#             'object': obj
#         })
