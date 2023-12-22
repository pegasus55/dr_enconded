# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.constrains('wage', 'mode', 'last_minimum_salary')
    def _constrain_wage(self):
        if self.mode == 'minimum_salary':
            if self.wage < self.last_minimum_salary:
                raise ValidationError('The salary defined in the contract must be greater than or equal '
                                      'to the established sectoral minimum.')

    IESS_sector_code = fields.Many2one('hr.sector.table', string='IESS sector code', tracking=True, required=True,
                                       help='Defines the number assigned by the IESS according to the position '
                                            'it occupies in the company.')

    mode = fields.Selection(string='Mode', related='IESS_sector_code.mode')
    last_year = fields.Integer(string='Last year', related='IESS_sector_code.last_year')
    last_minimum_salary = fields.Float(string='Last minimum salary', related='IESS_sector_code.last_minimum_salary')
    last_minimum_fee = fields.Float(string='Last minimum fee', related='IESS_sector_code.last_minimum_fee')