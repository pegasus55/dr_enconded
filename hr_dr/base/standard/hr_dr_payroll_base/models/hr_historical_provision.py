# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class HrHistoricalProvision(models.Model):
    _name = 'hr.historical.provision'
    _description = 'Historical provision'
    _inherit = ['mail.thread']

    fiscal_year = fields.Integer(string='Fiscal year', required=True, help='', tracking=True)
    period_start = fields.Date(string='Start of period', tracking=True)
    period_end = fields.Date(string='End of period', tracking=True)
    employee_id = fields.Many2one('hr.employee', string=_('Collaborator'), required=True, help='', tracking=True)

    value_actual_fiscal_year = fields.Monetary(string=_('Value (Actual fiscal year)'), tracking=True,
                                               currency_field='currency_id')
    working_days_actual_fiscal_year = fields.Float(string=_('Working days (Actual fiscal year)'), tracking=True)

    value_previous_fiscal_year = fields.Monetary(string=_('Value (Previous fiscal year)'), tracking=True,
                                                 currency_field='currency_id')
    working_days_previous_fiscal_year = fields.Float(string=_('Working days (Previous fiscal year)'), tracking=True)

    total_value = fields.Monetary(string=_('Total value'), compute="_compute_total_value", currency_field='currency_id')
    total_working_days = fields.Float(string=_('Total working days'), compute="_compute_total_working_days")
    partner_id = fields.Many2one('res.partner', string='Beneficiary', tracking=True)
    active = fields.Boolean(string=_('Active'), default=True, tracking=True)
    type = fields.Selection([
        ('taxable_income', _('Taxable income')),
        ('D13', _('Thirteenth salary')),
        ('R_D13_JW', _('Retention of D13 for judicial withholding')),
        ('D14', _('Fourteenth salary')),
        ('R_D14_JW', _('Retention of D14 for judicial withholding')),
        ('living_wage', _('Living wage')),
        ('payment_utility', _('Payment utility')),
    ], string=_('Type'), required=True, tracking=True)
    payment_type = fields.Selection([
        ('na', _('N/A')),
        ('monthly', _('Monthly')),
        ('accumulated', _('Accumulated'))
    ], string=_('Payment type'), required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')

    @api.depends('value_actual_fiscal_year', 'value_previous_fiscal_year')
    def _compute_total_value(self):
        for record in self:
            record.total_value = record.value_actual_fiscal_year + record.value_previous_fiscal_year

    @api.depends('working_days_actual_fiscal_year', 'working_days_previous_fiscal_year')
    def _compute_total_working_days(self):
        for record in self:
            record.total_working_days = record.working_days_actual_fiscal_year + \
                                        record.working_days_previous_fiscal_year