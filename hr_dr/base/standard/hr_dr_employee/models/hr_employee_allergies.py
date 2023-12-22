# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Allergies(models.Model):
    _name = 'hr.employee.allergies'
    _description = 'Employee allergies'
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)