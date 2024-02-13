# -*- coding: utf-8 -*-
import time
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        for line in self.input_line_ids:
            if line.employee_credit_line_id:
                line.employee_credit_line_id.action_paid_amount()
        return super(HrPayslip, self).action_payslip_done()
