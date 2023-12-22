# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class BfbPerFl(models.Model):
    _name = 'bfb.per.fl'
    _description = 'Basic family basket per family load'
    _inherit = ['mail.thread']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc, family_load asc"
    _sql_constraints = [
        ('_unique_fiscal_year_family_load', 'unique (fiscal_year, family_load)',
         "For the same fiscal year you cannot repeat the amount of family loads."),
    ]

    def _default_fiscal_year(self):
        date = datetime.utcnow()
        return date.year

    @api.depends('fiscal_year', 'basic_family_basket')
    def _compute_maximum_deductible_expense(self):
        for rec in self:
            bfb = self.get_basic_family_basket(rec.fiscal_year)
            rec.maximum_deductible_expense = round(bfb * rec.basic_family_basket, 2)

    def get_basic_family_basket(self, year):
        bfb = self.env['hr.basic.family.basket'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if bfb:
            return bfb.value
        else:
            raise ValidationError(_('You must establish the basic family basket for the year {}.').format(str(year)))

    fiscal_year = fields.Integer(string='Fiscal year', required=True, tracking=True, default=_default_fiscal_year)
    family_load = fields.Integer(string='Family load', default=0, required=True, tracking=True)
    basic_family_basket = fields.Integer(string='Basic family basket', default=7, required=True, tracking=True)
    maximum_deductible_expense = fields.Monetary(string='Maximum deductible expense',
                                                 compute='_compute_maximum_deductible_expense', store=True,
                                                 tracking=True, currency_field='currency_id')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)