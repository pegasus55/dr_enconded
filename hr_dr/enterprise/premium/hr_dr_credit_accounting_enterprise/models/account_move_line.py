# -*- coding: utf-8 -*-
from odoo import models, api, fields, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    credit_id = fields.Many2one('hr.credit', string='Credit Id')