# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPayrollVacations(http.Controller):
#     @http.route('/hr_dr_payroll_vacations/hr_dr_payroll_vacations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_payroll_vacations/hr_dr_payroll_vacations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_payroll_vacations.listing', {
#             'root': '/hr_dr_payroll_vacations/hr_dr_payroll_vacations',
#             'objects': http.request.env['hr_dr_payroll_vacations.hr_dr_payroll_vacations'].search([]),
#         })

#     @http.route('/hr_dr_payroll_vacations/hr_dr_payroll_vacations/objects/<model("hr_dr_payroll_vacations.hr_dr_payroll_vacations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_payroll_vacations.object', {
#             'object': obj
#         })
