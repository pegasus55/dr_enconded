# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CatastrophicDisease(models.Model):
    _name = 'hr.catastrophic.disease'
    _description = 'Catastrophic disease'
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)