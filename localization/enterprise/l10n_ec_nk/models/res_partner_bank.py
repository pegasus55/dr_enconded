# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_type = fields.Selection([('savings', 'Savings account'),
                                     ('checking', 'Checking account')], string='Account type')