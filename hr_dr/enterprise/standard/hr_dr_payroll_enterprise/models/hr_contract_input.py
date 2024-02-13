# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ContractInput(models.Model):
    _inherit = 'hr.contract.input'

    input_type_id = fields.Many2one('hr.payslip.input.type', string='Type', required=True)
    type = fields.Selection(string="Type", required=True, related='input_type_id.type')
    code = fields.Char(string='Code', required=True, related='input_type_id.code')