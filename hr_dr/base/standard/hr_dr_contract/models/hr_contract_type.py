# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ContractType(models.Model):
    _inherit = ['hr.contract.type']

    description = fields.Text(string='Description')
    normative_id = fields.Many2one('hr.normative', string="Regulation", required=True, help='')
    active = fields.Boolean(string='Active', default='True', help='')