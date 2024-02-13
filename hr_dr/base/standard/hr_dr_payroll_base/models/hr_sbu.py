# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class SBU(models.Model):
    _name = 'hr.sbu'
    _description = 'SBU'
    _inherit = ['mail.thread']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc"
    _sql_constraints = [('fiscal_year_uniq', 'unique(fiscal_year)', 'The fiscal year must be unique.')]

    def _default_fiscal_year(self):
        date = datetime.utcnow()
        return date.year

    @api.onchange('value', 'value_previous_fiscal_year')
    @api.depends('value', 'value_previous_fiscal_year')
    def compute_percent_increase(self):
        for rec in self:
            if rec.value_previous_fiscal_year and rec.value:
                rec.percent_increase = round(((rec.value / rec.value_previous_fiscal_year) - 1) * 100, 2)
            else:
                rec.percent_increase = 0.0

    fiscal_year = fields.Integer(string='Fiscal year', required=True, help='', tracking=True,
                                 default=_default_fiscal_year)
    value = fields.Monetary(string='Value', required=True, help='', tracking=True,
                            currency_field='currency_id')
    value_previous_fiscal_year = fields.Monetary(string='Value for the previous fiscal year',
                                                 required=True, help='', tracking=True, currency_field='currency_id')
    percent_increase = fields.Float(string='Percent increase', compute='compute_percent_increase')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)