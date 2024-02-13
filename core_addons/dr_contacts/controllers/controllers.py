# -*- coding: utf-8 -*-
from odoo import http

# class RxrContacts(http.Controller):
#     @http.route('/rxr_contacts/rxr_contacts/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/rxr_contacts/rxr_contacts/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('rxr_contacts.listing', {
#             'root': '/rxr_contacts/rxr_contacts',
#             'objects': http.request.env['rxr_contacts.rxr_contacts'].search([]),
#         })

#     @http.route('/rxr_contacts/rxr_contacts/objects/<model("rxr_contacts.rxr_contacts"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('rxr_contacts.object', {
#             'object': obj
#         })