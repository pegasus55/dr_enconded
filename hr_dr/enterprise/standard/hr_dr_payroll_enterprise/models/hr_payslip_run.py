# -*- coding:utf-8 -*-

from odoo import api, Command, fields, models, _
from dateutil.relativedelta import relativedelta


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            next_month = relativedelta(months=+1, day=1, days=-1)
            self.date_end = self.date_start + next_month