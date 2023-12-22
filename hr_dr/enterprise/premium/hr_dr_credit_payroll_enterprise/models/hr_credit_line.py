# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CreditLine(models.Model):
    _inherit = "hr.credit.line"

    payslip_id = fields.Many2one('hr.payslip', string="Payslip", readonly=True)