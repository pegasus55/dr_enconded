# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrContractPublic(http.Controller):
#     @http.route('/hr_dr_contract_public/hr_dr_contract_public/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_contract_public/hr_dr_contract_public/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_contract_public.listing', {
#             'root': '/hr_dr_contract_public/hr_dr_contract_public',
#             'objects': http.request.env['hr_dr_contract_public.hr_dr_contract_public'].search([]),
#         })

#     @http.route('/hr_dr_contract_public/hr_dr_contract_public/objects/<model("hr_dr_contract_public.hr_dr_contract_public"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_contract_public.object', {
#             'object': obj
#         })
