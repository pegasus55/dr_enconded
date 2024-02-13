# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class LoanLine(models.Model):
    _inherit = "hr.loan.line"

    payslip_id = fields.Many2one('hr.payslip', string="Payslip", readonly=True)