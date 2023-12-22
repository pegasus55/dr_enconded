# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    input_ids = fields.Many2many('hr.input', 'payslip_input_input_rel', 'payslip_input_id', 'input_id', string='Inputs')
    type = fields.Selection(string="Type", required=True, related='input_type_id.type')
    code = fields.Char(string='Code', required=True, related='input_type_id.code')
    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding')
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', related='judicial_withholding_id.partner_id',
                                     readonly=True, store=True)
