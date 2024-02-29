# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Department(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic account')