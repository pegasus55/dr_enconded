# -*- coding: utf-8 -*-
from odoo import http

# class HrDrPersonalAction(http.Controller):
#     @http.route('/hr_dr_personal_action/hr_dr_personal_action/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_personal_action/hr_dr_personal_action/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_personal_action.listing', {
#             'root': '/hr_dr_personal_action/hr_dr_personal_action',
#             'objects': http.request.env['hr_dr_personal_action.hr_dr_personal_action'].search([]),
#         })

#     @http.route('/hr_dr_personal_action/hr_dr_personal_action/objects/<model("hr_dr_personal_action.hr_dr_personal_action"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_personal_action.object', {
#             'object': obj
#         })