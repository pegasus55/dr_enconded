# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrInput(models.Model):
    _inherit = 'hr.input'
    _order = "date desc, payslip_input_type_id, employee_id"

    payslip_input_type_id = fields.Many2one('hr.payslip.input.type', string='Income/Expense', required=True,
                                            tracking=True)
    type = fields.Selection(string="Type", related='payslip_input_type_id.type', store=True, readonly=True)
    name = fields.Char(string="Name", related='payslip_input_type_id.name', store=True, readonly=True)
    code = fields.Char(string="Code", related='payslip_input_type_id.code', store=True, readonly=True)