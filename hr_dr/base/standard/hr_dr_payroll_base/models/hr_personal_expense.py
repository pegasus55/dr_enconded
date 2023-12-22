# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time, timedelta


class PersonalExpense(models.Model):
    _name = 'hr.personal.expense'
    _description = 'Personal expense'
    _rec_name = 'employee_id'
    _inherit = ['hr.generic.request']
    _order = 'rent_tax_table_id desc, employee_id'
    _sql_constraints = [('employee_id_fiscal_year_uniq', 'unique(employee_id, fiscal_year)',
                         'There can only be one projection of personal expenses per employee and fiscal year.')]

    def unlink(self):
        for rec in self:
            if rec.state not in 'draft':
                raise UserError(_('You can only delete personal expense projections in draft status.'))

            if not float_is_zero(rec.amount_this_employer_posted, precision_rounding=2) \
                    or not float_is_zero(rec.second_amount_this_employer_posted, precision_rounding=2) \
                    or not float_is_zero(rec.amount_detained_employee_posted, precision_rounding=2):
                raise UserError(_('You cannot delete a personal expense if posted values already exist.'))
        return super(PersonalExpense, self).unlink()

    def action_validate(self):
        """
        Este método envía los gastos personales del colaborador a estado validado, verificando que la tabla del impuesto
        a la renta usada este en estado confirmado.
        """
        rec = self.env['hr.personal.expense'].search(
            [('employee_id', '=', self.employee_id.id),
             ('rent_tax_table_id', '=', self.rent_tax_table_id.id),
             ('id', '!=', self.id), ('state', '=', 'done')])
        if rec:
            raise ValidationError(_('Cannot validate. '
                                    'There is already a confirmed personal expense projection for this collaborator '
                                    'and fiscal year.'))
        if self.rent_tax_table_id.state != 'confirmed':
            raise ValidationError(_('The rent tax table used must be in confirmed status.'))

        self._check_amount_employer()

        self.write({'state': 'done'})
        return True

    def action_draft(self):
        """
        Este método envía los gastos personales del colaborador a estado borrador.
        """
        return self.write({'state': 'draft'})

    @api.model
    def get_employee_id(self):
        """
        Este método establece el colaborador asociado al usuario autenticado como valor por defecto
        """
        employee_id = False
        employee_ids = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('employee_admin', '=', False)
        ])
        if employee_ids:
            employee_id = employee_ids[0].id
        return employee_id

    @api.model
    def get_rent_tax_table_id(self):
        """
        Este método establece la tabla del impuesto a la renta con base a la fecha actual como valor por defecto
        """
        rent_tax_table_id = False
        current = date.today()
        rent_tax_table_ids = self.env['hr.rent.tax.table'].search([('fiscal_year', '=', current.year)])
        if rent_tax_table_ids:
            rent_tax_table_id = rent_tax_table_ids[0].id
        return rent_tax_table_id

    @api.onchange('profit_tax_employer')
    def _onchange_amount_employer(self):
        self._compute_amount()

    @api.depends('employee_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.env.user.id
            if rec.employee_id:
                rec.user_id = rec.employee_id.user_id.id

    @api.depends('expenses_ids', 'expenses_ids.amount')
    def _compute_total_expenses(self):
        for rec in self:
            total_expenses = 0
            for expense in rec.expenses_ids:
                total_expenses += expense.amount
            rec.total_expenses = total_expenses

    @api.depends('employee_id',
                 'employee_id.family_load_ids',
                 'employee_id.family_load_ids.relationship',
                 'employee_id.family_load_ids.disability',
                 'employee_id.family_load_ids.date_of_birth',
                 'employee_id.family_load_ids.receive_taxed_income',
                 'employee_id.family_load_ids.employee_dependent',
                 'employee_id.family_load_ids.presents_catastrophic_diseases')
    def _compute_family_load(self):
        def calculate_children_age(children, td):
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=td.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years
            else:
                return 100

        for rec in self:
            family_load = 0
            any_family_load_with_catastrophic_diseases = 0
            today = datetime.today().date()
            for fl in rec.employee_id.family_load_ids:
                if ((fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter') and
                        calculate_children_age(fl, today) < 21):
                    family_load += 1
                elif ((fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter') and
                        fl.disability):
                    family_load += 1
                elif ((fl.relationship == 'parent' or fl.relationship == 'mother' or fl.relationship == 'father') and
                        not fl.receive_taxed_income and fl.employee_dependent):
                    family_load += 1
                elif ((fl.relationship == 'spouses' or fl.relationship == 'wife' or fl.relationship == 'husband' or
                       fl.relationship == 'cohabitant') and not fl.receive_taxed_income and fl.employee_dependent):
                    family_load += 1

                if ((fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter' or
                     fl.relationship == 'parent' or fl.relationship == 'mother' or fl.relationship == 'father' or
                     fl.relationship == 'spouses' or fl.relationship == 'wife' or fl.relationship == 'husband' or
                     fl.relationship == 'cohabitant') and
                        fl.presents_catastrophic_diseases):
                    any_family_load_with_catastrophic_diseases += 1

            rec.family_load = family_load
            if any_family_load_with_catastrophic_diseases > 0:
                rec.any_family_load_with_catastrophic_diseases = True
            else:
                rec.any_family_load_with_catastrophic_diseases = False

    def _get_max_deductible(self, year, family_load):
        if family_load >= 0:
            bfb_per_fl_id = self.env['bfb.per.fl'].sudo().search([
                ('fiscal_year', '=', year),
                ('family_load', '=', family_load)], limit=1)
            if bfb_per_fl_id:
                return bfb_per_fl_id.maximum_deductible_expense
            else:
                return 0
        else:
            bfb_per_fl_id = self.env['bfb.per.fl'].sudo().search([
                ('fiscal_year', '=', year)], limit=1, order='family_load desc')
            if bfb_per_fl_id:
                return bfb_per_fl_id.maximum_deductible_expense
            else:
                return 0

    @api.depends('family_load',
                 'fiscal_year',
                 'presents_catastrophic_disease',
                 'any_family_load_with_catastrophic_diseases')
    def _compute_max_deductible(self):
        for rec in self:
            if rec.presents_catastrophic_disease or rec.any_family_load_with_catastrophic_diseases:
                rec.max_deductible = self._get_max_deductible(rec.fiscal_year, -1)
            else:
                rec.max_deductible = self._get_max_deductible(rec.fiscal_year, rec.family_load)

    def _get_disability(self, employee_id, tax_table):
        """Dado un empleado busca si posee algún porcentaje de discapacidad y devuelve el valor a exonerar según la
        tabla de impuesto a la renta."""

        disability = 0.0
        disability_percentage = employee_id.disability_percentage
        if disability_percentage > 0.0:
            for benefit in tax_table.disability_benefit_ids:
                if benefit.minimum_percentage <= disability_percentage <= benefit.maximum_percentage:
                    disability = round(tax_table.basic_fraction * benefit.benefit_percentage / 100 * 2, 2)
                    break
        return disability

    def _get_third_age(self, employee_id, tax_table):
        """Dado un empleado busca si pertenece a la tercera edad y en caso positivo retorna el valor de una fracción
        básica según la tabla de impuesto a la renta."""
        third_age = 0.0
        if employee_id.third_age:
            third_age = round(tax_table.basic_fraction, 2)
        return third_age

    @api.depends('employee_id',
                 'employee_id.disability',
                 'employee_id.disability_percentage',
                 'rent_tax_table_id',
                 'rent_tax_table_id.basic_fraction',
                 'rent_tax_table_id.disability_benefit_ids',
                 'rent_tax_table_id.disability_benefit_ids.minimum_percentage',
                 'rent_tax_table_id.disability_benefit_ids.maximum_percentage',
                 'rent_tax_table_id.disability_benefit_ids.benefit_percentage')
    def _compute_disability_deduction(self):
        for rec in self:
            rec.disability_deduction = rec._get_disability(rec.employee_id, rec.rent_tax_table_id)

    @api.depends('employee_id',
                 'employee_id.third_age',
                 'rent_tax_table_id',
                 'rent_tax_table_id.basic_fraction')
    def _compute_third_age_deduction(self):
        for rec in self:
            rec.third_age_deduction = rec._get_third_age(rec.employee_id, rec.rent_tax_table_id)

    @api.depends('disability_deduction', 'third_age_deduction')
    def _compute_total_deduction(self):
        for rec in self:
            rec.total_deduction = max(rec.disability_deduction, rec.third_age_deduction)

    @api.depends('income_other_employers')
    def _compute_iess_other_employer(self):
        for rec in self:
            rec.IESS_other_employer = round(rec.income_other_employers * 9.45 / 100, 2)

    @api.depends('employee_id',
                 'rent_tax_table_id',
                 'utility',
                 'calculation_method',
                 'income_other_employers',
                 'IESS_other_employer',
                 'total_expenses',
                 'amount_other_employer')
    def _compute_amount(self):
        pass

    def _check_amount_employer(self):
        """
        Este método verifica que para el método de cálculo Asunción del impuesto a la renta de forma parcial,
        el impuesto a la renta asumido por este empleador debe ser menor o igual al impuesto a la renta causado del
        primer cálculo IR, y verifica que el segundo valor de impuesto asumido por este empleador sea menor o igual a
        la resta del impuesto a la renta causado, el valor de impuesto retenido y asumido por otros empleadores durante
        el período declarado, y el valor de impuesto asumido por este empleador para la columna del valor calculado
        """
        for rec in self:
            if rec.calculation_method == 'assumption_partial' \
                    and float_compare(rec.profit_tax_employer, rec.profit_tax_first_calculation,
                                      precision_digits=3) > 0:
                raise UserError(_('Income tax assumed greater than %s') % rec.profit_tax_first_calculation)
            if rec.calculation_method == 'assumption_partial' \
                    and float_compare(rec.second_amount_this_employer, (
                    rec.profit_tax - rec.amount_other_employer - rec.amount_this_employer),
                                      precision_digits=3) > 0:
                raise UserError(
                    _('Second income tax assumed greater than %s') % rec.second_amount_this_employer)
        return True

    _CALCULATION_METHOD = [
        ('withhold_employee', 'Total withholding of income tax to the collaborator'),
        ('assumption_total', 'Total assumption of income tax by the employer'),
        ('assumption_partial', 'Partial assumption (50%) of the income tax by the employer')
    ]
    _STATE = [
        ('draft', 'Draft'),
        ('done', 'Done')
    ]

    employee_id = fields.Many2one('hr.employee', string='Collaborator', default=get_employee_id,
                                  required=True, tracking=True, ondelete='cascade')
    work_region = fields.Selection(string='Work region', related='employee_id.address_id.state_id.region',
                                   readonly=True)
    presents_catastrophic_disease = fields.Boolean(string='Presents catastrophic disease', store=True, readonly=True,
                                                   related='employee_id.presents_catastrophic_disease', tracking=True)
    family_load = fields.Integer(string="Family load", compute='_compute_family_load', store=True, readonly=True,
                                 tracking=True)
    any_family_load_with_catastrophic_diseases = fields.Boolean(string="Any family load with catastrophic diseases",
                                                                compute='_compute_family_load', store=True,
                                                                readonly=True, tracking=True)
    max_deductible = fields.Monetary(string='Maximum deductible', compute='_compute_max_deductible',
                                     currency_field='currency_id', store=True, readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='User', compute='_compute_user_id', store=True, help='',
                              tracking=True)

    rent_tax_table_id = fields.Many2one('hr.rent.tax.table', string='Rent tax table', default=get_rent_tax_table_id,
                                        required=True, tracking=True)
    fiscal_year = fields.Integer(string='Fiscal year', related='rent_tax_table_id.fiscal_year', store=True,
                                 readonly=True, tracking=True)

    calculation_method = fields.Selection(_CALCULATION_METHOD, string='Calculation method', default='withhold_employee',
                                          required=True, tracking=True)
    income_tax_withholding_percentage = fields.Float(string='Income tax withholding percentage', required=True,
                                                     digits='Payroll', default=100.0, tracking=True)
    state = fields.Selection(_STATE, string='Status', default='draft', tracking=True)

    # This employer
    wage = fields.Monetary(compute='_compute_amount', string='Wage', currency_field='currency_id', default=0.0,
                           required=True, tracking=True)
    other_taxable_income = fields.Monetary(compute='_compute_amount', string='Other taxable income',
                                           currency_field='currency_id', default=0.0, required=True, tracking=True)
    utility = fields.Monetary(string='Utilities', currency_field='currency_id', default=0.0, required=True,
                              tracking=True)
    profit_tax_employer = fields.Monetary(string='Income tax assumed by this employer', currency_field='currency_id',
                                          default=0.0, required=True, tracking=True)
    IESS_this_employer = fields.Monetary(compute='_compute_amount',
                                         string='Personal contribution to IESS with this employer',
                                         currency_field='currency_id', default=0.0, required=True, tracking=True)

    # Other employers
    income_other_employers = fields.Monetary(string='Taxed income generated with other employers',
                                             currency_field='currency_id', tracking=True, default=0.0)
    IESS_other_employer = fields.Monetary(string='Personal contribution to IESS with other employers',
                                          currency_field='currency_id', tracking=True, store=True, readonly=False,
                                          compute='_compute_iess_other_employer', default=0.0)
    # Expenses
    expenses_ids = fields.One2many('hr.personal.expense.detail', 'hr_personal_expense_id', string='Expenses',
                                   tracking=True)
    total_expenses = fields.Monetary(compute='_compute_total_expenses', string='Total expense',
                                     currency_field='currency_id', tracking=True)
    # Deductions
    disability_deduction = fields.Monetary(compute='_compute_disability_deduction', string='Disability deduction',
                                           currency_field='currency_id', store=True, tracking=True)
    third_age_deduction = fields.Monetary(compute='_compute_third_age_deduction', string='Third age deduction',
                                          currency_field='currency_id', store=True, tracking=True)
    total_deduction = fields.Monetary(compute='_compute_total_deduction', string='Total deduction',
                                      currency_field='currency_id', store=True, tracking=True)

    # Tax summary

    total_income = fields.Monetary(compute='_compute_amount', string='Total income',
                                   currency_field='currency_id', store=True, tracking=True)
    tax_base = fields.Monetary(
        compute='_compute_amount',
        string='Taxable tax base',
        currency_field='currency_id',
        help='La base fiscal gravable se obtiene de la diferencia entre ingresos (sueldos, comisiones, utilidades e '
             'ingresos generados con otros empleadores) y gastos (Contribuciones al IESS, deducciones de gastos '
             'personales y exoneraciones).\nSi el empleador asume parte o la totalidad del impuesto, el valor asumido '
             'por el empleador se incluye en los ingresos.', tracking=True)

    tax_caused = fields.Monetary(
        compute='_compute_amount',
        string='Tax caused',
        currency_field='currency_id',
        tracking=True)




    taxable_income = fields.Float(compute='_compute_amount', string='Income taxed with this employer',
                                  digits='Payroll', help='Taxable income with this employer (Calculated).',
                                  tracking=True)
    taxable_income_posted = fields.Float(compute='_compute_amount', string='Income taxed with this employer',
                                         digits='Payroll', help='Income taxed with this employer (Recorded). '
                                                                'Useful for reporting on the RDEP.', tracking=True)


    tax_base_posted = fields.Float(
        compute='_compute_amount',
        string='Taxable tax base',
        digits='Payroll',
        help='La "Base Imponible Gravada" a ser reportada en el RDEP', tracking=True)
    tax_base_first_calculation = fields.Float(
        compute='_compute_amount',
        string='Taxable tax base first calculation',
        digits='Payroll',
        help='Solo aplica cuando el empleador asume parte o la totalidad del impuesto.\n'
             'Este primer cálculo no incluye el valor del impuesto asumido por el empleador.', tracking=True)
    profit_tax = fields.Float(
        compute='_compute_amount',
        string='Profit tax caused',
        digits='Payroll',
        help='El impuesto sobre beneficios causados se obtiene al sumar el impuesto a la fracción básica según '
             'el rango correspondiente a la base fiscal gravable en la tabla de impuesto a la renta y '
             'el porcentaje aplicado al exceso de esta base.\nSi el empleador asume parte o la totalidad del impuesto, '
             'el valor asumido por el empleador se incluye en la base fiscal gravable.\n'
             'ISBC = (BFG - fracción básica) * exceso de fracción de impuesto + impuesto fracción básica',
        tracking=True)
    profit_tax_first_calculation = fields.Float(
        compute='_compute_amount',
        string='Profit tax caused first calculation',
        digits='Payroll',
        help='Solo aplica cuando el empleador asume parte o la totalidad del impuesto.\n'
             'Este primer cálculo realizado no incluye el valor del impuesto asumido por el empleador.',
        tracking=True)
    expenses_discount = fields.Float(
        compute='_compute_amount', string='Personal expenses discount', digits='Payroll')
    first_expenses_discount = fields.Float(
        compute='_compute_amount', string='First personal expenses discount', digits='Payroll')
    rent_tax = fields.Float(compute='_compute_amount', string='Rent tax', digits='Payroll')
    first_rent_tax = fields.Float(compute='_compute_amount', string='First rent tax', digits='Payroll')
    amount_other_employer = fields.Float(
        string='Value of the tax withhold and assumed by other employers during the declared period',
        digits='Payroll',
        help='', tracking=True)
    amount_this_employer = fields.Float(
        compute='_compute_amount',
        string='Value of the tax assumed by this employer',
        digits='Payroll',
        help='Valor asumido por el empleador sobre el primer cálculo de la base fiscal gravable.', tracking=True)
    second_amount_this_employer = fields.Float(
        compute='_compute_amount',
        string='Second value of the tax assumed by this employer',
        digits='Payroll', default=0.0,
        help='Valor asumido por el empleador sobre el impuesto generado por el valor asumido por el empleador '
             'sobre la base fiscal gravable.',
        tracking=True)
    amount_this_employer_posted = fields.Float(
        compute='_compute_amount',
        string='Value of the tax assumed by this employer posted',
        digits='Payroll',
        help='Valor publicado hasta la fecha.', tracking=True)
    second_amount_this_employer_posted = fields.Float(
        compute='_compute_amount',
        string='Second value of the tax assumed by this employer posted',
        digits='Payroll',
        help='Valor publicado hasta la fecha.',
        tracking=True)
    amount_this_employer_discount = fields.Float(
        compute='_compute_amount',
        string='Value of the tax assumed by this employer discount',
        digits='Payroll',
        help='Valor mensual a descontar.', tracking=True)
    second_amount_this_employer_discount = fields.Float(
        compute='_compute_amount',
        string='Second value of the tax assumed by this employer discount',
        digits='Payroll',
        help='Valor mensual a descontar.', tracking=True)
    amount_detained_employee = fields.Float(
        compute='_compute_amount',
        string='Value of the tax withhold from the worker by this employer',
        digits='Payroll',
        help='Valor retenido al colaborador por el empleador.\n Si el empleador asume el impuesto de forma parcial, '
             'se incluye el impuesto generado por el valor asumido.', tracking=True)
    amount_detained_employee_posted = fields.Float(
        compute='_compute_amount',
        string='Value of the tax withhold from the worker by this employer posted',
        digits='Payroll',
        help='Valor publicado hasta la fecha.', tracking=True)
    amount_detained_employee_discount = fields.Float(
        compute='_compute_amount',
        string='Value of the tax withhold from the worker by this employer discount',
        digits='Payroll',
        help='Valor mensual a descontar.', tracking=True)


class PersonalExpenseDetail(models.Model):
    _name = 'hr.personal.expense.detail'
    _description = 'Personal expense detail'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('_unique_personal_expense_by_category', 'unique (hr_personal_expense_id, personal_expenses_category_id)',
         "Expense categories cannot be repeated."),
    ]

    @api.model
    def create(self, vals):
        record = super(PersonalExpenseDetail, self).create(vals)
        if record.max_amount != 0:
            if record.amount > record.max_amount:
                raise UserError(_('The value has to be less than or equal to the maximum value.'))
        return record

    def write(self, vals):
        record = super(PersonalExpenseDetail, self).write(vals)
        if self.max_amount != 0:
            if self.amount > self.max_amount:
                raise UserError(_('The value has to be less than or equal to the maximum value.'))
        return record

    @api.depends('hr_personal_expense_id',
                 'hr_personal_expense_id.work_region',
                 'hr_personal_expense_id.rent_tax_table_id',
                 'hr_personal_expense_id.rent_tax_table_id.expense_ids',
                 'hr_personal_expense_id.rent_tax_table_id.expense_ids.amount',
                 'personal_expenses_category_id')
    def _compute_max_amount(self):
        for rec in self:
            if not rec.hr_personal_expense_id.work_region:
                raise UserError(_("You must set the collaborator's work region."))
            if not rec.hr_personal_expense_id.rent_tax_table_id:
                raise UserError(_('You must set the rent tax table.'))

            rent_tax_table_expense_id = self.env['hr.rent.tax.table.expense'].sudo().search([
                ('region', '=', rec.hr_personal_expense_id.work_region),
                ('rent_tax_table_id', '=', rec.hr_personal_expense_id.rent_tax_table_id.id),
                ('personal_expenses_category_id', '=', rec.personal_expenses_category_id.id)
            ], limit=1)

            if rent_tax_table_expense_id:
                rec.max_amount = rent_tax_table_expense_id.amount
            else:
                rec.max_amount = 0

    hr_personal_expense_id = fields.Many2one('hr.personal.expense', string='Personal expense', ondelete='cascade',
                                             required=True, tracking=True)
    personal_expenses_category_id = fields.Many2one('hr.personal.expenses.category', string='Category',
                                                    ondelete='restrict', required=True, tracking=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, tracking=True)
    max_amount = fields.Monetary(compute='_compute_max_amount', string='Max amount', store=True,
                                 currency_field='currency_id', tracking=True)
    company_id = fields.Many2one('res.company', string="Company", related='hr_personal_expense_id.company_id',
                                 readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='hr_personal_expense_id.currency_id',
                                  readonly=True)