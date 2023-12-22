# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.constrains('input_ids')
    def _check_input(self):
        for contract in self:
            contract_input_ids = self.env['hr.contract.input'].search(
                [('contract_id', '=', contract.id), ('type', 'in', ['income', 'expense', 'expense_with_beneficiary'])])
            if len(contract_input_ids) != len(contract_input_ids.mapped('input_type_id')):
                raise ValidationError(_('There are duplicate inputs.'))
        return True

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        super(Contract, self).onchange_employee_id()

        if self.employee_id:
            index = 1
            # for input in self.input_ids:
            #     input.unlink()
            # self.update({
            #     'input_ids': []
            # })
            for jw in self.employee_id.judicial_withholding_ids:
                code = 'PALIMENTOS_{}'.format(index)
                payslip_input_type = self.env['hr.payslip.input.type'].search([
                    ('code', '=', code)], limit=1)

                input = [(0, 0, {
                    'input_type_id': payslip_input_type.id,
                    'amount': jw.value,
                    'judicial_withholding_id': jw.id,
                })]
                self.update({
                    'input_ids': input
                })
                index += 1

    struct_id = fields.Many2one('hr.payroll.structure', string="Payroll structure")
    input_ids = fields.One2many('hr.contract.input', 'contract_id', copy=True, string='Input', help='')