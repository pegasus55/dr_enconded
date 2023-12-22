# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import start_of, end_of


class RentTaxTable(models.Model):
    _name = 'hr.rent.tax.table'
    _description = 'Rent tax table'
    _inherit = ['mail.thread']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc"
    _sql_constraints = [('fiscal_year_uniq', 'unique(fiscal_year)', 'The fiscal year must be unique.')]

    def unlink(self):
        for rentTax in self:
            if rentTax.state != 'draft':
                raise ValidationError(_('You can only delete rent tax table that are in draft status.'))
            information_ids = self.env['hr.personal.expense'].search(
                [('rent_tax_table_id', '=', rentTax.id)])
            if information_ids:
                raise ValidationError(_('You cannot delete tables that are being used in income tax calculations.'))
        return super(RentTaxTable, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_('The rent tax table should not be duplicated.'))

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            self.date_from = start_of(self.date_from, 'year')
            self.date_to = end_of(self.date_from, 'year')
            self.fiscal_year = self.date_to.year

    def action_confirm(self):
        return self.write({'state': 'confirmed'})

    def action_draft(self):
        return self.write({'state': 'draft'})

    date_from = fields.Date(string='From', required=True, help='', default=fields.Date.context_today, tracking=True)
    date_to = fields.Date(string='To', required=True, help='', tracking=True)
    fiscal_year = fields.Integer(string='Fiscal year', required=True, help='', tracking=True)
    basic_fraction = fields.Monetary(string='Basic fraction', required=True, help='', tracking=True,
                                     currency_field='currency_id')
    expense_ids = fields.One2many('hr.rent.tax.table.expense', 'rent_tax_table_id', string='Expense', tracking=True)
    rate_ids = fields.One2many('hr.rent.tax.table.rate', 'rent_tax_table_id', string='Rate', help='', tracking=True)
    disability_benefit_ids = fields.One2many('hr.disability.benefit.table', 'rent_tax_table_id',
                                             string='Disability benefit', help='')
    _STATE = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ]
    state = fields.Selection(_STATE, string='Status', default='draft', help='', tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)

    @api.constrains('date_from')
    def _check_date_from(self):
        for rentTax in self:
            if rentTax.date_from:
                if rentTax.date_from.day != 1 or rentTax.date_from.month != 1:
                    raise ValidationError(_('The initial date must be january 1 of the selected year.'))
            ids = self.search([('date_from', '=', rentTax.date_from), ('id', '!=', rentTax.id)])
            if ids:
                raise ValidationError(_('There is already a rent tax table created for this period.'))
        return True


class RentTaxTableExpense(models.Model):
    _name = 'hr.rent.tax.table.expense'
    _description = 'Rent tax table expense'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('_unique_expense_category_by_region_rtt', 'unique (rent_tax_table_id, region, personal_expenses_category_id)',
         "Expense categories cannot be repeated for the same region and income tax table."),
    ]

    @api.depends('rent_tax_table_id.basic_fraction', 'fraction', 'consumer_price_index')
    def _compute_amount(self):
        precision_payroll_3 = self.env['decimal.precision'].precision_get('Payroll Fraction 3')
        for record in self:
            record.amount = round(record.rent_tax_table_id.basic_fraction * record.fraction *
                                  record.consumer_price_index, precision_payroll_3)

    @api.onchange('region')
    def on_change_region(self):
        if self.region == 'island':
            self.consumer_price_index = 1.803
        else:
            self.consumer_price_index = 1

    rent_tax_table_id = fields.Many2one('hr.rent.tax.table', string='Rent tax table', ondelete='cascade', required=True,
                                        help='', tracking=True)
    personal_expenses_category_id = fields.Many2one('hr.personal.expenses.category', string='Category',
                                                    ondelete='cascade', required=True, tracking=True)
    region = fields.Selection([
        ('sierra', 'Sierra'),
        ('coast', 'Coast'),
        ('eastern', 'Eastern'),
        ('island', 'Island')
    ], string='Region', required=True)
    consumer_price_index = fields.Float(string='Consumer price index', digits='Payroll Fraction 3', required=True,
                                        default=1.0, tracking=True)
    fraction = fields.Float(string='Fraction', digits='Payroll Fraction 3', required=True, default=0.0, tracking=True)
    amount = fields.Monetary(compute='_compute_amount', string='Amount', store=True, currency_field='currency_id',
                             readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", related='rent_tax_table_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='rent_tax_table_id.currency_id',
                                  readonly=True)


class RentTaxTableLine(models.Model):
    _name = 'hr.rent.tax.table.rate'
    _description = 'Rent tax table rate'
    _inherit = ['mail.thread']
    _order = "fiscal_year,basic_fraction"

    rent_tax_table_id = fields.Many2one('hr.rent.tax.table', string='Rent tax table', ondelete='cascade', required=True,
                                        help='', tracking=True)
    fiscal_year = fields.Integer(string="Fiscal year", related='rent_tax_table_id.fiscal_year', readonly=True,
                                 store=True)
    company_id = fields.Many2one('res.company', string="Company", related='rent_tax_table_id.company_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='rent_tax_table_id.currency_id',
                                  readonly=True)
    basic_fraction = fields.Monetary(string='Basic fraction', required=True, help='', tracking=True,
                                     currency_field='currency_id')
    excess_until = fields.Monetary(string='Excess until', required=True, help='', tracking=True,
                                   currency_field='currency_id')
    basic_fraction_tax = fields.Monetary(string='Basic fraction tax', required=True, help='',
                                         tracking=True, currency_field='currency_id')
    excess_fraction_tax = fields.Float(string='Tax fraction excess (%)', required=True, digits='Payroll', help='',
                                       tracking=True)

    def name_get(self):
        return [
            (
                record.id, "{}: {} - {}".format(
                    record.fiscal_year,
                    record.basic_fraction,
                    record.excess_until)) for record in self]


class DisabilityBenefitTable(models.Model):
    _name = 'hr.disability.benefit.table'
    _description = 'Disability benefit table'
    _inherit = ['mail.thread']
    _order = "fiscal_year,minimum_percentage"

    rent_tax_table_id = fields.Many2one('hr.rent.tax.table', string='Rent tax table', ondelete='cascade',
                                        required=True, help='', tracking=True)
    fiscal_year = fields.Integer(string="Fiscal year", related='rent_tax_table_id.fiscal_year', readonly=True,
                                 store=True)
    minimum_percentage = fields.Float(string='Minimum percentage', required=True, digits='Payroll', help='',
                                      tracking=True)
    maximum_percentage = fields.Float(string='Maximum percentage', required=True, digits='Payroll', help='',
                                      tracking=True)
    benefit_percentage = fields.Float(string='Benefit percentage', required=True, digits='Payroll', help='',
                                      tracking=True)

    def name_get(self):
        return [
            (
                record.id, "{}: {} - {}".format(
                    record.fiscal_year,
                    record.minimum_percentage,
                    record.maximum_percentage)) for record in self]