# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPayrollEnterpriseIncomeTax(http.Controller):
#     @http.route('/hr_dr_payroll_enterprise_income_tax/hr_dr_payroll_enterprise_income_tax', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_payroll_enterprise_income_tax/hr_dr_payroll_enterprise_income_tax/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_income_tax.listing', {
#             'root': '/hr_dr_payroll_enterprise_income_tax/hr_dr_payroll_enterprise_income_tax',
#             'objects': http.request.env['hr_dr_payroll_enterprise_income_tax.hr_dr_payroll_enterprise_income_tax'].search([]),
#         })

#     @http.route('/hr_dr_payroll_enterprise_income_tax/hr_dr_payroll_enterprise_income_tax/objects/<model("hr_dr_payroll_enterprise_income_tax.hr_dr_payroll_enterprise_income_tax"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_income_tax.object', {
#             'object': obj
#         })
