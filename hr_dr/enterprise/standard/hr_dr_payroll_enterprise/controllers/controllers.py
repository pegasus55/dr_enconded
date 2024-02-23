# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPayroll(http.Controller):
#     @http.route('/hr_dr_payroll/hr_dr_payroll/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_payroll/hr_dr_payroll/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_payroll.listing', {
#             'root': '/hr_dr_payroll/hr_dr_payroll',
#             'objects': http.request.env['hr_dr_payroll.hr_dr_payroll'].search([]),
#         })

#     @http.route('/hr_dr_payroll/hr_dr_payroll/objects/<model("hr_dr_payroll.hr_dr_payroll"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_payroll.object', {
#             'object': obj
#         })
