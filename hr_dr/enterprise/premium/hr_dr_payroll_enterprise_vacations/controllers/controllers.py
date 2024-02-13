# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPayrollEnterpriseVacations(http.Controller):
#     @http.route('/hr_dr_payroll_enterprise_vacations/hr_dr_payroll_enterprise_vacations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_payroll_enterprise_vacations/hr_dr_payroll_enterprise_vacations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_vacations.listing', {
#             'root': '/hr_dr_payroll_enterprise_vacations/hr_dr_payroll_enterprise_vacations',
#             'objects': http.request.env['hr_dr_payroll_enterprise_vacations.hr_dr_payroll_enterprise_vacations'].search([]),
#         })

#     @http.route('/hr_dr_payroll_enterprise_vacations/hr_dr_payroll_enterprise_vacations/objects/<model("hr_dr_payroll_enterprise_vacations.hr_dr_payroll_enterprise_vacations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_payroll_enterprise_vacations.object', {
#             'object': obj
#         })
