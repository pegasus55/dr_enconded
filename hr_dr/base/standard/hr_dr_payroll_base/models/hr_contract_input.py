# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ContractInput(models.Model):
    _name = 'hr.contract.input'
    _description = 'Contract input'

    amount = fields.Float(string='Value', help='')
    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding')
    partner_id = fields.Many2one('res.partner', string='Beneficiary', help='', store=True,
                                 related='judicial_withholding_id.partner_id', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', help='')
    employee_id = fields.Many2one('hr.employee', string='Collaborator', related='contract_id.employee_id')





