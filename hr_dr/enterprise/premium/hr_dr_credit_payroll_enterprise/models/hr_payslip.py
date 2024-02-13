# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        for payslip in self:
            for line in payslip.input_line_ids:
                if line.code == "CRED_DIR":
                    for input in line.input_ids:
                        input.hr_credit_line_id.write({
                            'payslip_id': payslip.id,
                            'paid': True
                        })
                        input.hr_credit_id._compute_credit_amount()
        return super(HrPayslip, self).action_payslip_done()