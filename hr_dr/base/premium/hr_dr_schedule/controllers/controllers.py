# -*- coding: utf-8 -*-
from odoo import http

# class HrdrSchedule(http.Controller):
#     @http.route('/hr_dr_schedule/hr_dr_schedule/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_schedule/hr_dr_schedule/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_schedule.listing', {
#             'root': '/hr_dr_schedule/hr_dr_schedule',
#             'objects': http.request.env['hr_dr_schedule.hr_dr_schedule'].search([]),
#         })

#     @http.route('/hr_dr_schedule/hr_dr_schedule/objects/<model("hr_dr_schedule.hr_dr_schedule"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_schedule.object', {
#             'object': obj
#         })