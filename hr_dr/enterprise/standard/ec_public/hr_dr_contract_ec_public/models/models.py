# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PayScaleLosep(models.Model):
    _name = 'hr.pay.scale.losep'
    _description = 'Pay scale losep'
    _inherit = ['mail.thread']

    name = fields.Char(string="Occupational group", tracking=True, required=True)
    level = fields.Integer(string="Level", tracking=True, required=True)
    remuneration = fields.Float(string="Remuneration", tracking=True, required=True)
    year = fields.Integer(string='Year', tracking=True, required=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class Contract(models.Model):
    _inherit = 'hr.contract'