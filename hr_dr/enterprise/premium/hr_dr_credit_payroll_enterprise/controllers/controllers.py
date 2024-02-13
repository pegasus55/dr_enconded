# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrCreditPayrollEnterprise(http.Controller):
#     @http.route('/hr_dr_credit_payroll_enterprise/hr_dr_credit_payroll_enterprise/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_credit_payroll_enterprise/hr_dr_credit_payroll_enterprise/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_credit_payroll_enterprise.listing', {
#             'root': '/hr_dr_credit_payroll_enterprise/hr_dr_credit_payroll_enterprise',
#             'objects': http.request.env['hr_dr_credit_payroll_enterprise.hr_dr_credit_payroll_enterprise'].search([]),
#         })

#     @http.route('/hr_dr_credit_payroll_enterprise/hr_dr_credit_payroll_enterprise/objects/<model("hr_dr_credit_payroll_enterprise.hr_dr_credit_payroll_enterprise"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_credit_payroll_enterprise.object', {
#             'object': obj
#         })
