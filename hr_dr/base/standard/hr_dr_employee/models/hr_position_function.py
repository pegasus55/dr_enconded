# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrPositionFunction(models.Model):
    _name = "hr.position.function"
    _inherit = ['mail.thread']
    _description = 'Position function'

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)