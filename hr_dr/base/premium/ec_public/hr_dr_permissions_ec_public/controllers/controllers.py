# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrPermissionsEcPublic(http.Controller):
#     @http.route('/hr_dr_permissions_ec_public/hr_dr_permissions_ec_public/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_permissions_ec_public/hr_dr_permissions_ec_public/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_permissions_ec_public.listing', {
#             'root': '/hr_dr_permissions_ec_public/hr_dr_permissions_ec_public',
#             'objects': http.request.env['hr_dr_permissions_ec_public.hr_dr_permissions_ec_public'].search([]),
#         })

#     @http.route('/hr_dr_permissions_ec_public/hr_dr_permissions_ec_public/objects/<model("hr_dr_permissions_ec_public.hr_dr_permissions_ec_public"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_permissions_ec_public.object', {
#             'object': obj
#         })
