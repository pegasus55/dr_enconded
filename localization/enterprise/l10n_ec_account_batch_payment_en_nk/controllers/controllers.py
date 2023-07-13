# -*- coding: utf-8 -*-
# from odoo import http


# class L10nEcAccountBatchPaymentEn(http.Controller):
#     @http.route('/l10n_ec_account_batch_payment_en/l10n_ec_account_batch_payment_en', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_ec_account_batch_payment_en/l10n_ec_account_batch_payment_en/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_ec_account_batch_payment_en.listing', {
#             'root': '/l10n_ec_account_batch_payment_en/l10n_ec_account_batch_payment_en',
#             'objects': http.request.env['l10n_ec_account_batch_payment_en.l10n_ec_account_batch_payment_en'].search([]),
#         })

#     @http.route('/l10n_ec_account_batch_payment_en/l10n_ec_account_batch_payment_en/objects/<model("l10n_ec_account_batch_payment_en.l10n_ec_account_batch_payment_en"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_ec_account_batch_payment_en.object', {
#             'object': obj
#         })
