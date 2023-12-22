# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrPayrollStructureType(models.Model):
    _name = 'hr.payroll.structure.type'
    _inherit = ['hr.payroll.structure.type', 'mail.thread']

    description = fields.Text(string='Description', tracking=True)
    normative_id = fields.Many2one('hr.normative', string="Regulation", required=True, help='', tracking=True)
    active = fields.Boolean(string='Active', default='True', help='', tracking=True)