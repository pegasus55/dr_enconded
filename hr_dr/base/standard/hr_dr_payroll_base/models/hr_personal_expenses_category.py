# -*- coding: utf-8 -*-
from odoo import models, tools, fields, api, _


class PersonalExpensesCategory(models.Model):
    _name = 'hr.personal.expenses.category'
    _inherit = ['mail.thread']
    _description = 'Personal expenses category'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)