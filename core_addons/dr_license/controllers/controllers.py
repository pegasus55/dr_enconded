# -*- coding: utf-8 -*-
# from odoo import http


# class DrLicense(http.Controller):
#     @http.route('/dr_license/dr_license/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dr_license/dr_license/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dr_license.listing', {
#             'root': '/dr_license/dr_license',
#             'objects': http.request.env['dr_license.dr_license'].search([]),
#         })

#     @http.route('/dr_license/dr_license/objects/<model("dr_license.dr_license"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dr_license.object', {
#             'object': obj
#         })
