# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrSkills(http.Controller):
#     @http.route('/hr_dr_skills/hr_dr_skills/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_skills/hr_dr_skills/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_skills.listing', {
#             'root': '/hr_dr_skills/hr_dr_skills',
#             'objects': http.request.env['hr_dr_skills.hr_dr_skills'].search([]),
#         })

#     @http.route('/hr_dr_skills/hr_dr_skills/objects/<model("hr_dr_skills.hr_dr_skills"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_skills.object', {
#             'object': obj
#         })
