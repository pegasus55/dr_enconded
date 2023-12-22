# -*- coding: utf-8 -*-
# from odoo import http


# class HrDrLoanAccountingCommunity(http.Controller):
#     @http.route('/hr_dr_loan_accounting_community/hr_dr_loan_accounting_community/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_dr_loan_accounting_community/hr_dr_loan_accounting_community/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_dr_loan_accounting_community.listing', {
#             'root': '/hr_dr_loan_accounting_community/hr_dr_loan_accounting_community',
#             'objects': http.request.env['hr_dr_loan_accounting_community.hr_dr_loan_accounting_community'].search([]),
#         })

#     @http.route('/hr_dr_loan_accounting_community/hr_dr_loan_accounting_community/objects/<model("hr_dr_loan_accounting_community.hr_dr_loan_accounting_community"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_dr_loan_accounting_community.object', {
#             'object': obj
#         })
