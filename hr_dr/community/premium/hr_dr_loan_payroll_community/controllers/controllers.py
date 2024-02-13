# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrLoanPayrollCommunity(http.Controller):
#     @http.route('/hr_dr_loan_payroll_community/hr_dr_loan_payroll_community/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_loan_payroll_community/hr_dr_loan_payroll_community/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_loan_payroll_community.listing', {
#             'root': '/hr_dr_loan_payroll_community/hr_dr_loan_payroll_community',
#             'objects': http.request.env['hr_dr_loan_payroll_community.hr_dr_loan_payroll_community'].search([]),
#         })

#     @http.route('/hr_dr_loan_payroll_community/hr_dr_loan_payroll_community/objects/<model("hr_dr_loan_payroll_community.hr_dr_loan_payroll_community"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_loan_payroll_community.object', {
#             'object': obj
#         })
