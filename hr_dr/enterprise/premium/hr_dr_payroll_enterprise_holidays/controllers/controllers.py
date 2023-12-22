# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPayrollEnterpriseHolidays(http.Controller):
#     @http.route('/hr_dr_payroll_enterprise_holidays/hr_dr_payroll_enterprise_holidays', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_payroll_enterprise_holidays/hr_dr_payroll_enterprise_holidays/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_holidays.listing', {
#             'root': '/hr_dr_payroll_enterprise_holidays/hr_dr_payroll_enterprise_holidays',
#             'objects': http.request.env['hr_dr_payroll_enterprise_holidays.hr_dr_payroll_enterprise_holidays'].search([]),
#         })

#     @http.route('/hr_dr_payroll_enterprise_holidays/hr_dr_payroll_enterprise_holidays/objects/<model("hr_dr_payroll_enterprise_holidays.hr_dr_payroll_enterprise_holidays"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_holidays.object', {
#             'object': obj
#         })
