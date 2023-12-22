# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrEmployeeCertificates(http.Controller):
#     @http.route('/hr_dr_employee_certificates/hr_dr_employee_certificates/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_employee_certificates/hr_dr_employee_certificates/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_employee_certificates.listing', {
#             'root': '/hr_dr_employee_certificates/hr_dr_employee_certificates',
#             'objects': http.request.env['hr_dr_employee_certificates.hr_dr_employee_certificates'].search([]),
#         })

#     @http.route('/hr_dr_employee_certificates/hr_dr_employee_certificates/objects/<model("hr_dr_employee_certificates.hr_dr_employee_certificates"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_employee_certificates.object', {
#             'object': obj
#         })
