# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrInput(models.Model):
    _inherit = 'hr.input'

    hr_credit_id = fields.Many2one('hr.credit', string='Credit', ondelete='cascade')
    hr_credit_line_id = fields.Many2one('hr.credit.line', string='Credit detail', ondelete='cascade')