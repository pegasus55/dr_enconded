# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    active = fields.Boolean(string='Active', default=True,
                            help='Only active payroll structure is presented in payroll.')
