# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrContractPrivate(http.Controller):
#     @http.route('/hr_dr_contract_private/hr_dr_contract_private/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_contract_private/hr_dr_contract_private/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_contract_private.listing', {
#             'root': '/hr_dr_contract_private/hr_dr_contract_private',
#             'objects': http.request.env['hr_dr_contract_private.hr_dr_contract_private'].search([]),
#         })

#     @http.route('/hr_dr_contract_private/hr_dr_contract_private/objects/<model("hr_dr_contract_private.hr_dr_contract_private"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_contract_private.object', {
#             'object': obj
#         })
