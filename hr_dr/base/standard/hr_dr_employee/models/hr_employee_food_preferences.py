# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FoodPreferences(models.Model):
    _name = 'hr.employee.food.preferences'
    _description = 'Employee food preferences'
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)