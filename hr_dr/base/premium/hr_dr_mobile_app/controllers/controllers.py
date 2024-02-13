# -*- coding: utf-8 -*-
from odoo import http

# class HrRxrMobileApp(http.Controller):
#     @http.route('/hr_rxr_mobile_app/hr_rxr_mobile_app/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_rxr_mobile_app/hr_rxr_mobile_app/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_rxr_mobile_app.listing', {
#             'root': '/hr_rxr_mobile_app/hr_rxr_mobile_app',
#             'objects': http.request.env['hr_rxr_mobile_app.hr_rxr_mobile_app'].search([]),
#         })

#     @http.route('/hr_rxr_mobile_app/hr_rxr_mobile_app/objects/<model("hr_rxr_mobile_app.hr_rxr_mobile_app"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_rxr_mobile_app.object', {
#             'object': obj
#         })