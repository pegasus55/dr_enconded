# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError


class HrInput(models.Model):
    _name = 'hr.input'
    _description = "Input"
    _inherit = ['mail.thread']

    date = fields.Date(string='Date', default=datetime.today(), required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True)
    identification = fields.Char(string='Identification', tracking=True)
    amount = fields.Monetary(string="Amount", required=True, currency_field='currency_id', tracking=True)
    state = fields.Selection([
        ('available', _('Available')),
        ('processed', _('Processed')),
    ], string="Status", default="available")
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)
    generate_hr_fortnight_id = fields.Many2one("generate.hr.fortnight", string="Generate fortnight", store=False)
    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding')
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', related='judicial_withholding_id.partner_id',
                                     readonly=True, store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('identification'):
                employee = self.env['hr.employee'].search(
                    [
                        '|',
                        ('identification_id', '=', vals['identification']),
                        ('passport_id', '=', vals['identification'])
                    ], limit=1)
                if not employee:
                    raise ValidationError(_("There is no collaborator with the following identification: %s." %
                                            (vals['identification'])))
                vals['employee_id'] = employee.id
        return super(HrInput, self).create(vals)

    @api.constrains('amount')
    def check_amount(self):
        for record in self:
            if record.amount == 0.0:
                raise ValidationError('The value must be different from zero.')