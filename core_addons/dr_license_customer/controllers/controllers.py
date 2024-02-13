# -*- coding: utf-8 -*-
# from odoo import http


# class DrLicenseCustomer(http.Controller):
#     @http.route('/dr_license_customer/dr_license_customer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dr_license_customer/dr_license_customer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dr_license_customer.listing', {
#             'root': '/dr_license_customer/dr_license_customer',
#             'objects': http.request.env['dr_license_customer.dr_license_customer'].search([]),
#         })

#     @http.route('/dr_license_customer/dr_license_customer/objects/<model("dr_license_customer.dr_license_customer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dr_license_customer.object', {
#             'object': obj
#         })
