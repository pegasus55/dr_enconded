# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrStandardEcPrivate(http.Controller):
#     @http.route('/hr_dr_standard_ec_private/hr_dr_standard_ec_private/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_standard_ec_private/hr_dr_standard_ec_private/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_standard_ec_private.listing', {
#             'root': '/hr_dr_standard_ec_private/hr_dr_standard_ec_private',
#             'objects': http.request.env['hr_dr_standard_ec_private.hr_dr_standard_ec_private'].search([]),
#         })

#     @http.route('/hr_dr_standard_ec_private/hr_dr_standard_ec_private/objects/<model("hr_dr_standard_ec_private.hr_dr_standard_ec_private"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_standard_ec_private.object', {
#             'object': obj
#         })
