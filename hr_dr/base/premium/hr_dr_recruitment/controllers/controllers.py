# -*- coding: utf-8 -*-
from odoo import http

# class HrdrRecruitment(http.Controller):
#     @http.route('/hr_dr_recruitment/hr_dr_recruitment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_recruitment/hr_dr_recruitment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_recruitment.listing', {
#             'root': '/hr_dr_recruitment/hr_dr_recruitment',
#             'objects': http.request.env['hr_dr_recruitment.hr_dr_recruitment'].search([]),
#         })

#     @http.route('/hr_dr_recruitment/hr_dr_recruitment/objects/<model("hr_dr_recruitment.hr_dr_recruitment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_recruitment.object', {
#             'object': obj
#         })