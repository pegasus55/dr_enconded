# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class PayFortnight(models.Model):
    _name = "hr.fortnight"
    _description = "Fortnight"
    _inherit = ['mail.thread']
    _order = "date desc, employee_id"

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id', tracking=True)
    date = fields.Date(string='Payment date', default=date.today())
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True,
                                  related='company_id.currency_id')
    active = fields.Boolean(string='Active', default=True)