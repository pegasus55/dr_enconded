# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrEmployeeNotifications(http.Controller):
#     @http.route('/hr_dr_employee_notifications/hr_dr_employee_notifications/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_employee_notifications/hr_dr_employee_notifications/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_employee_notifications.listing', {
#             'root': '/hr_dr_employee_notifications/hr_dr_employee_notifications',
#             'objects': http.request.env['hr_dr_employee_notifications.hr_dr_employee_notifications'].search([]),
#         })

#     @http.route('/hr_dr_employee_notifications/hr_dr_employee_notifications/objects/<model("hr_dr_employee_notifications.hr_dr_employee_notifications"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_employee_notifications.object', {
#             'object': obj
#         })
