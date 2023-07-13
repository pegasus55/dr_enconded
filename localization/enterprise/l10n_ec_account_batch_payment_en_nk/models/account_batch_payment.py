# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    cash_management = fields.Binary(string='Cash management', readonly=True)
    cash_management_name = fields.Char(string='Cash management name', store=True)

    def get_cash_management(self):
        pass