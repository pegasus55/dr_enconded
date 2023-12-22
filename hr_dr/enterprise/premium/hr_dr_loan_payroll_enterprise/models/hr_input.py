# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrInput(models.Model):
    _inherit = 'hr.input'

    hr_loan_id = fields.Many2one('hr.loan', string='Loan', ondelete='cascade')
    hr_loan_line_id = fields.Many2one('hr.loan.line', string='Loan detail', ondelete='cascade')