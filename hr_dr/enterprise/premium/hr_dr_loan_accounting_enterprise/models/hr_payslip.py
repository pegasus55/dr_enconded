# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def action_payslip_done(self):
        for payslip in self:
            for line in payslip.input_line_ids:
                if line.code == "PREST_EMP":
                    for input in line.input_ids:
                        input.loan_line_id.action_paid_amount()
        return super(HrPayslip, self).action_payslip_done()