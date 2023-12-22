# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeJudicialWithholding(models.Model):
    _name = 'hr.judicial.withholding'
    _description = 'Judicial withholding'
    _inherit = ['mail.thread']
    _order = "employee_id"
    _sql_constraints = [
        ('family_load_id_unique',
         'UNIQUE(family_load_id)',
         "A family load cannot appear in more than one judicial withholding."),
    ]

    def name_get(self):
        return [(record.id,
                 "{}: {} - {} - {}".format(record.employee_id.name, record.card_code, record.judicial_process_number,
                                           record.approval_identifier)) for record in self]

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        if self.partner_id:
            self.representative_name = self.partner_id.name
            self.representative_identification = self.partner_id.vat

    @api.constrains('value')
    def _constrain_value(self):
        if self.value <= 0:
            raise ValidationError('The value of judicial withholding must be greater than zero.')

    employee_id = fields.Many2one('hr.employee', string='Collaborator', required=True, ondelete='cascade', help='',
                                  tracking=True)
    family_load_id = fields.Many2one('hr.employee.family.load', string='Family load', required=True,
                                     domain="[('employee_id', '=', employee_id)]",
                                     ondelete='cascade', tracking=True)
    card_code = fields.Char(string='Card code', help='', required=True, tracking=True)
    judicial_process_number = fields.Char(string='Judicial process number', help='', required=True, tracking=True)
    approval_identifier = fields.Char(string='Approval identifier (NUT)', help='', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Beneficiary', required=True, help='', tracking=True)
    representative_name = fields.Char(string='Representative name', required=True, help='', tracking=True)
    representative_identification = fields.Char(string='Representative identification', required=True, help='',
                                                tracking=True)
    value = fields.Monetary(string='Value', required=True, help='', tracking=True, currency_field='currency_id')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    backup_document = fields.Binary(string="Backup document", help='You can attach your judicial withholding document.')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)