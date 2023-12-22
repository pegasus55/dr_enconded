# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding')
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', related='judicial_withholding_id.partner_id',
                                     readonly=True, store=True)