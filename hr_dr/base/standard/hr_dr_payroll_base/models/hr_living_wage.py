# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class LivingWage(models.Model):
    _name = 'hr.living.wage'
    _description = 'Living wage'
    _inherit = ['mail.thread']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc"
    _sql_constraints = [('fiscal_year_uniq', 'unique(fiscal_year)', 'The fiscal year must be unique.')]

    def _default_fiscal_year(self):
        date = datetime.utcnow()
        return date.year

    fiscal_year = fields.Integer(string='Fiscal year', required=True, help='', tracking=True,
                                 default=_default_fiscal_year)
    value = fields.Monetary(string='Value', required=True, help='', tracking=True,
                            currency_field='currency_id')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)