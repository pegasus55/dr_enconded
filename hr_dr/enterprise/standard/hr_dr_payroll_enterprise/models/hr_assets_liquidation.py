# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, float_compare, float_is_zero
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from math import ceil, floor
import re
from calendar import isleap, monthrange

CAUSES = [
    ('C01', _('Por terminación del contrato.')),
    ('C02', _('Por acuerdo de las partes (Renuncia voluntaria).')),
    # ('C02', _('Por la conclusión de la obra, período de labor o servicios objeto del contrato.')),
    # ('C03', _('Por muerte o incapacidad del empleador o extinción de la persona jurídica contratante.')),
    # ('C04', _('Por muerte del trabajador o incapacidad permanente y total para el trabajo.')),
    # ('C05', _('Por caso fortuito o fuerza mayor que imposibiliten el trabajo, como incendio, terremoto, tempestad, '
    #           'explosión, plagas del campo, guerra y, en general, cualquier otro acontecimiento extraordinario que los '
    #           'contratantes no pudieron prever o que previsto no lo pudieron evitar.')),
    # ('C06', _('Por voluntad del empleador previo visto bueno.')),
    ('C07', _('Visto bueno.')),
    # ('C07', _('Por voluntad del trabajador previo visto bueno.')),
    ('C08', _('Por desahucio.')),
    ('C09', _('Por despido intempestivo.')),
    # ('C10', _('Por terminación del contrato antes del plazo convenido.')),
    ('C11', _('No pasa periodo de prueba')),
    # ('C11', _('Por Terminación dentro del periodo de prueba')),
    # ('C12', _('Por las causas legalmente previstas en el contrato')),
    # ('C13', _('Por disposición general quinta del Acuerdo MDT-2018-0073')),
    # ('C14', _('Por disposición general quinta del Acuerdo MDT-2018-0074')),
    # ('C15', _('Por disposición general quinta del Acuerdo MDT-2018-0075')),
    # ('C16', _('Por disposición general quinta del Acuerdo MDT-2018-0096')),
    # ('C17', _('Por disposición general quinta del Acuerdo MDT-2018-0097')),
]

_STATES = [
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ]

APROVED_STATES = ['open', 'pending', 'close']

_REGIONS = [
    # ('sierra', _('Región Sierra')),
    # ('coast', _('Región Costa')),
    # ('eastern', _('Región Oriente')),
    # ('island', _('Región Galápagos')),
    ('sierra_oriente_fourteenth_salary', 'Sierra - Oriente'),
    ('costa_fourteenth_salary', 'Costa - Galápagos')
]


class AssetsLiquidationCause(models.Model):
    _name = 'hr.assets.liquidation.cause'
    _description = 'Assets liquidation cause table'

    name = fields.Char(string='Description')
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)

class HrAssetsLiquidation(models.Model):
    _name = 'hr.assets.liquidation'
    _description = 'Liquidation of assets table'
    _rec_name = 'employee_id'

    @api.model
    def get_journal_wage_id(self):
        """
        Este método setea el diario del contrato con el diario configurado en la compañia como "Diario de salarios"
        en caso que no este seteado, buscamos por xml_id el "Diario de Sueldos", que normalmente deben coincidir
        """
        journal_wage = self.env.ref('ecua_invoice_type.journal_wage', False)
        if journal_wage:
            journal_wage = journal_wage.id
        if self.env.user.company_id.journal_wage_id:
            journal_wage = self.env.user.company_id.journal_wage_id.id
        return journal_wage

    employee_id = fields.Many2one('hr.employee', string='Collaborator', required=True, ondelete='cascade',
                                  context={'active_test': False})
    cause_id = fields.Many2one('hr.assets.liquidation.cause', string='Cause', required=True,
                            help='Grounds for Termination of the Individual Contract.')
    cause_code = fields.Char(related='cause_id.code')
    # causes = fields.Selection(selection=CAUSES, string=_('Causes'), required=True,
    #                           help=_('Grounds for Termination of the Individual Contract.'))
    # first_contract_date_start = fields.Date(string='Fecha de (última) entrada', required=True,
    #                                         compute='_compute_first_contract_date_start')
    date_from = fields.Date(string='Contract date start', required=True)
    date_to = fields.Date(string='Contract date end', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato')
    region = fields.Selection(_REGIONS, string='Region', related='contract_id.payment_period_fourteenth', required=True, tracking=True)
    payslip_id = fields.Many2one('hr.payslip', string='Rol de Pago')
    pay_provision = fields.Boolean(string="Include historical provision", default=False)
    #
    # worked_days = fields.Float(string='Worked Days', tracking=True, default=30.0,
    #                            digits='Payroll', help='')
    # # disease = fields.Float(string='Disease', tracking=True, default=0.0,
    # #                        digits='Payroll', help='')
    # line_ids = fields.One2many('hr.assets.liquidation.line', 'slip_id', string='Assets Liquidation Lines',
    #                            readonly=True, states={'draft': [('readonly', False)]})
    # input_line_ids = fields.One2many('hr.assets.liquidation.input', 'assets_liquidation_id',
    #                                  string='Assets Liquidation Inputs', readonly=True,
    #                                  states={'draft': [('readonly', False)]})
    # worked_days_line_ids = fields.One2many('hr.assets.liquidation.worked_days', 'assets_liquidation_id',
    #                                        string='Assets Liquidation Worked Days', copy=True, readonly=True,
    #                                        states={'draft': [('readonly', False)]})
    # unified_basic_salary = fields.Float(compute='_get_unified_basic_salary',
    #                         string='Unified Basic Salary',  store=True,
    #                         help='The unified basic salary used to calculate the provision of the fourteenth salary')
    # employee_information = fields.Many2one('hr.personal.expense', compute='_get_employee_information',
    #                                        string='Employee Information',  store=False,
    #                                        help='')
    # journal_id = fields.Many2one('account.journal', 'Salary Journal', readonly=True, required=True,
    #                              states={'draft': [('readonly', False)]}, default=get_journal_wage_id)
    # move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)
    # provision_move_id = fields.Many2one('account.move', 'Provision Entry', readonly=True, copy=False,
    #     help='Contiene los asientos correspondientes a las reglas salariales marcadas '
    #          'como Invisibles, es decir que no se muestran en la nomina impresa.')
    # credit_note = fields.Boolean(string='Credit Note', readonly=True,
    #                      states={'draft': [('readonly', False)]},
    #                      help="If its checked, indicates that all payslips generated from here are refund payslips.")
    # details_by_salary_rule_category = fields.One2many('hr.assets.liquidation.line',
    #                                                   compute='_compute_details_by_salary_rule_category',
    #                                                   string='Details by Salary Rule Category')
    # employee_age = fields.Integer(string='Age', compute='_compute_age', help='Employee\'s current age')
    # years_in_service = fields.Integer(string="Years of service", compute="_get_time_in_service",
    #     store=False, help='Years of service since employee\'s first contract, up to the payroll cut-off date\n'
    #                       'Used for computing benefits such as the reserve fund and vacations provision')
    # months_in_service = fields.Integer(string="Months of service", compute="_get_time_in_service",
    #     store=False, help='Months of service since employee\'s first contract,up to the payroll cut-off date\n'
    #                       'Used for computing benefits such as the reserve fund and vacations provision'
    # )
    # days_in_service = fields.Integer(string="Days of Service", compute="_get_time_in_service",
    #     store=False, help='Days of service since employee\'s first contract,up to the payroll cut-off date\n'
    #                       'Used for computing benefits such as the reserve fund and vacations provision'
    # )
    # company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
    #                              default=lambda self: self.env['res.company']._company_default_get(),
    #                              states={'draft': [('readonly', False)]})
    # net_salary = fields.Float(compute='_get_net_salary', string='Net salary',  store=True,
    #                           help='The net salary')
    #
    # last_payment = fields.Float(string='Last payment received', required=True)
    # best_payment = fields.Float(string='Best payment received', required=True)
    amount = fields.Float('Mutually agreed compensation')
    last_wage = fields.Float('Last payment received', required=True, default=0.00)
    best_wage = fields.Float('Best payment received', required=True, default=0.00)
    # payment_thirteenth_salary = fields.Selection([('monthly', _('Monthly')), ('accumulated', 'Accumulated')],
    #                                              string='Payment thirteenth salary', default='accumulated')
    # payment_fourteenth_salary = fields.Selection([('monthly', _('Monthly')), ('accumulated', 'Accumulated')],
    #                                              string='Payment fourteenth salary', default='accumulated')
    # # vacations = fields.Integer(string='Non spent vacations')
    pregnant_woman = fields.Boolean(string='Pregnant woman', default=False)
    union_leader = fields.Boolean(string='Union leader', default=False)
    non_occupational_disease = fields.Boolean(string='Non-occupational disease', default=False)
    disability_deduction = fields.Boolean(string='Disability', default=False)
    discrimination = fields.Boolean(string='Discrimination', default=False)
    # unfair_dismissal = fields.Boolean(string='Unfair dismissal', compute='_compute_unfair_dismissal')
    eviction = fields.Boolean(string='Eviction', default=False)
    #
    # show_bonus = fields.Boolean(string='Show bounus', compute='_compute_show_bonus')
    # retirement_bonus = fields.Boolean(string='Retirement bonus', default=False)
    # retirement_bonus_percent = fields.Integer(string='Percent', help='Percent of basic salary to pay.', default=35)
    # retirement_bonus_years = fields.Float(string='Years', digits='Payroll', help='Years in the company.')
    #
    # income_ids = fields.One2many('hr.assets.liquidation.input', 'assets_liquidation_id', string='Additional Income',
    #                              tracking=True, domain=[('type', '=', 'income')], help='')
    # expense_ids = fields.One2many('hr.assets.liquidation.input', 'assets_liquidation_id', string='Additional Expense',
    #                               tracking=True, domain=[('type', '=', 'expense')], help='')
    # other_expense_ids = fields.One2many('hr.assets.liquidation.input', 'assets_liquidation_id',
    #                                     string='Other Additional Expense', tracking=True,
    #                                     domain=[('type', '=', 'other_expense')], help='')
    state = fields.Selection(_STATES, string='Estado', default='draft', readonly=True, help='',
                             tracking=True)
    #
    #
    # def action_compute(self):
    #     for rec in self:
    #         if not rec.employee_id.id:
    #             raise ValidationError(_('There is no employee selected.'))
    #         if not rec.employee_id.contract_id.id:
    #             raise ValidationError(_('{} has no current contract defined.'.format(rec.employee_id.display_name)))
    #         if not rec.employee_id.contract_id.struct_id.id:
    #             raise ValidationError(_('{}\'s current contract has no structure defined.'
    #                                     .format(rec.employee_id.display_name)))
    #
    #         # Busco el diario y la cuenta contable a utilizar en el contrato, si no están definidos, tomo los de la
    #         # compañía
    #         journal_id = False
    #         if rec.employee_id.contract_id.id and hasattr(rec.employee_id.contract_id, 'journal_id'):
    #             journal_id = rec.employee_id.contract_id.journal_id.id
    #         if not journal_id:
    #             journal_id = rec.employee_id.company_id.journal_wage_id.id
    #         account_payable_payslip_id = False
    #         if rec.employee_id.contract_id.id and hasattr(rec.employee_id.contract_id, 'account_payable_payroll'):
    #             account_payable_payslip_id = rec.employee_id.contract_id.account_payable_payroll.id
    #         if not account_payable_payslip_id:
    #             account_payable_payslip_id = rec.employee_id.company_id.account_payable_payslip_id.id
    #
    #         # delete old payslip lines
    #         rec.line_ids.unlink()
    #
    #         contract_ids = rec.get_contract(rec.employee_id, rec.date_from, rec.date_to)
    #         lines = [(0, 0, line) for line in rec._get_assets_liquidation_lines(contract_ids, rec.id)]
    #         rec.write({'line_ids': lines})
    #
    #         # Una vez calculadas las líneas obtengo los valores necesarios para la liquidación y recalculo
    #         liquidation_amounts = rec._get_liquidation_amounts(rec)
    #         rec.line_ids.unlink()
    #         lines = [(0, 0, line) for line in rec._get_assets_liquidation_lines(contract_ids, rec.id,
    #                                             add_liquidation_rules=True, liquidation_amounts=liquidation_amounts)]
    #         rec.write({'line_ids': lines, 'state': 'computed'})
    #
    # def _get_liquidation_amounts(self, assets_liquidation):
    #     """
    #     Obteniendo los valores correspondientes a vacaciones y décimos.
    #     """
    #
    #     # Obtengo los valores de los décimos y vacaciones
    #     fourteenth = assets_liquidation._get_fourteenth()
    #     thirteenth = assets_liquidation._get_thirteenth()
    #     vacations = assets_liquidation._get_vacations()
    #     # new_lines = []
    #     contract = assets_liquidation.employee_id.contract_id
    #     amounts = {}
    #
    #     # Adiciono los valores de la nómina de liquidación a los acumulados
    #     for line in assets_liquidation.line_ids:
    #         if line.code == 'PROV_DCUARTO_ACUMULADO':
    #             fourteenth += line.total
    #         if line.code == 'PROV_DTERCERO_ACUMULADO':
    #             thirteenth += line.total
    #         if line.code == 'PROV_VACA':
    #             vacations += line.total
    #         if line.code == 'VACACIONES_TOMADAS' or line.code == 'VACACIONES_PAGADAS':
    #             vacations -= line.total
    #
    #     # Devuelvo diccionario con los valores obtenidos
    #     if fourteenth > 0:
    #         rule_id = self.env.ref('hr_dr_payroll.salary_rule_36', False)
    #         if rule_id:
    #             amounts[rule_id.id] = fourteenth
    #     if thirteenth > 0:
    #         rule_id = self.env.ref('hr_dr_payroll.salary_rule_35', False)
    #         if rule_id:
    #             amounts[rule_id.id] = thirteenth
    #     if vacations > 0:
    #         rule_id = self.env.ref('hr_dr_payroll.salary_rule_37', False)
    #         if rule_id:
    #             amounts[rule_id.id] = vacations
    #     return amounts
    #
    #
    # def action_mark_as_draft(self):
    #     self.state = 'draft'
    #
    #
    # def action_assets_liquidation_done(self):
    #
    #     # Buscando si el colaborador tiene créditos o préstamos este código inicial es el mismo que en get_inputs para
    #     # marcar como pagados los mismos plazos de créditos y préstamos que se utilizaron para calcular la deuda.
    #     contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
    #     contracts = self.env['hr.contract'].browse(contract_ids)
    #     structure_ids = contracts.get_all_structures()
    #     rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
    #
    #     # Obtengo solo un listado de ids de la lista de tuplas con id y orden
    #     rule_ids_only = [x[0] for x in rule_ids]
    #
    #     inputs = self.env['hr.salary.rule'].browse(rule_ids_only).mapped('input_ids')
    #
    #     for contract in contracts:
    #         for input in inputs:
    #             # Condición para el módulo de préstamos
    #             if input.code == 'PREST_EMP':
    #                 # Marcando todos los préstamos como hechos.
    #                 loan_obj = self.env['hr.loan'].search([
    #                     ('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')])
    #                 for loan in loan_obj:
    #                     for loan_line in loan.loan_lines:
    #                         if not loan_line.paid:
    #                             loan_line.paid = True
    #                             loan_line.loan_id._compute_loan_amount()
    #                             # loan_line._compute_loan_amount()
    #             # Condición para el módulo de créditos a empleados
    #             elif input.code == 'CRED_EMP_PROF':
    #                 # Marcando todos los créditos de empleados como hechos.
    #                 employee_credit = self.env['hr.employee.credit'].search(
    #                     [('employee_id', '=', self.employee_id.id), ('state', '=', 'in_payroll')])
    #                 for ec in employee_credit:
    #                     for ecl in ec.credit_lines:
    #                         if not ecl.paid:
    #                             ecl.paid = True
    #                             ecl.employee_credit_id._compute_credit_amount()
    #                             # ecl._compute_credit_amount()
    #
    #     # primero recalculamos las lineas nuevamente asegurando integridad
    #     ctx = self.env.context.copy()
    #     ctx.update({'bypass_core_accounting_move': True})
    #     # valida que el campo analytic_account_id exista y tenga un valor.
    #     if self.employee_id.contract_id._fields.get('analytic_account_id', False):
    #         if self.employee_id.contract_id.analytic_account_id:
    #             ctx.update({'analytic_account_id': self.employee_id.contract_id.analytic_account_id.id})
    #
    #     self.with_context(ctx).action_compute()
    #
    #     assets_liquidation_ids = self.search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('date_from', '>=', self.date_from),
    #         ('date_to', '<=', self.date_to),
    #         ('state', 'in', ['done', 'paid']),
    #         ('id', '!=', self.id),
    #     ])
    #     if assets_liquidation_ids:
    #         list1 = '\n'.join('* ' + liquidation.employee_id.display_name for liquidation in assets_liquidation_ids)
    #         raise UserError(_('The following employees have confirmed or paid liquidations in the selected period: '
    #                           '\n%s') % list1)
    #     if self.employee_id.contract_id.state != 'open':
    #         #TODO poner alguna validacion para contratos viejos cerrados que requieren reprocesamiento de nomina
    #         raise ValidationError(_('You can only approve payroll when the contract is ongoing.'))
    #     for line in self.line_ids:
    #         if line.salary_rule_id.code == 'SUBT_NET' and float_compare(line.total, 0.0, precision_rounding=2) == -1:
    #             raise ValidationError(_('Payroll whose net salary to be received is less than 0 cannot be validated. '
    #                                     'Employee %s') % self.employee_id.name)
    #     for liquidation in self:
    #         if liquidation.employee_information and liquidation.employee_information.rent_tax_table_id.state != 'confirmed':
    #             raise ValidationError(_('In "%s" the income tax table does not exist or is in draft state.')
    #                                   % liquidation.name)
    #         if not liquidation.employee_information and self.env.user.company_id.required_personal_expenses == 'required':
    #             raise ValidationError(_('You cannot complete the operation, in %s the projection of personal expenses '
    #                                     'does not exist or it is in draft state.') % liquidation.employee_id.display_name)
    #         contract_ids = liquidation.get_contract(liquidation.employee_id, liquidation.date_from, liquidation.date_to)
    #         if liquidation.employee_id.contract_id.id not in contract_ids:
    #             raise ValidationError(_('In the assets liquidation "%s" the effective date of the selected contract is '
    #                                     'not consistent with the date of the assets liquidation. Check contract dates '
    #                                     'or delete and rebuild the payroll.') % (liquidation.employee_id.display_name))
    #         if hasattr(liquidation.employee_id.address_home_id,
    #                    'type_vat') and liquidation.employee_id.address_home_id.type_vat == 'RUC':
    #             raise ValidationError(_('Employee %s is registered with RUC, only employees with ID or PASSPORT')
    #                                   % liquidation.employee_id.address_home_id.name)
    #         # invocamos en el for ambos asientos para que tengan secuencias contiguas
    #         liquidation.with_context(ctx).make_move_payslip()
    #         liquidation.with_context(ctx).make_move_payslip_provision()
    #         liquidation.with_context(ctx)._reconcile_receivables_vs_payslip()
    #         if liquidation.employee_information and liquidation.employee_information.calculation_method == 'assumption_total':
    #             liquidation.employee_information._compute_amount()
    #             liquidation.employee_information.profit_tax_employer = liquidation.employee_information.profit_tax_firt_calculation
    #
    #     return self.write({'state': 'done'})
    #
    # def action_assets_liquidation_cancel(self):
    #     """
    #     Aplicamos la misma logica que para el move_id
    #     """
    #     # desconciliamos los asientos de la nomina que pagan facturas
    #     lines_to_unreconcile = self.details_by_salary_rule_category.filtered(
    #         lambda r: r.amount_select == 'account_move')
    #     lines_to_unreconcile.mapped('move_line_ids').remove_move_reconcile()
    #     # removemos el asiento de la provision
    #     moves = self.mapped('provision_move_id')
    #     moves.filtered(lambda x: x.state == 'posted').button_cancel()
    #     moves.unlink()
    #
    #     # remueve el asiento principal, entre otras cosas
    #     if self.filtered(lambda slip: slip.state == 'done'):
    #         raise UserError(_("Cannot cancel a payslip that is done."))
    #     return self.write({'state': 'cancel'})
    #
    #
    #     for payslip in self:
    #         if payslip.employee_information and payslip.employee_information.calculation_method == 'assumption_total':
    #             # TODO JOSE: Deberia removerse el compute amount, deberia ser disparado de forma automatica
    #             payslip.employee_information._compute_amount()
    #             payslip.employee_information.profit_tax_employer = payslip.employee_information.profit_tax_firt_calculation
    #     return res
    #
    # @api.onchange('date_to')
    # def onchange_date_to(self):
    #     '''
    #     Invocamos el método onchange_date_to para validar los dias trabajados.
    #     campo de solo lectura
    #     '''
    #     vals = {'value': {}}
    #     vals['value'].update(
    #         self._get_worked_days(self.date_from, self.date_to, self.employee_id.contract_id.id))
    #     return vals
    #
    # @api.onchange('employee_id', 'date_from', 'date_to')
    # def _onchange_employee(self):
    #     vals = {'value': {}, 'warning': {}, 'domain': {}}
    #
    #     contract_ids = []
    #     if self.employee_id.id:
    #         if not self.employee_id.contract_id.id:
    #             raise ValidationError(_('{} has no current contract defined.'.format(self.employee_id.display_name)))
    #
    #         self._compute_first_contract_date_start()
    #         self.payment_thirteenth_salary = self.employee_id.contract_id.payment_thirteenth_salary
    #         self.payment_fourteenth_salary = self.employee_id.contract_id.payment_fourteenth_salary
    #         if self.employee_id.contract_id.payment_period_fourteenth:
    #             if self.employee_id.contract_id.payment_period_fourteenth == 'sierra_oriente_fourteenth_salary':
    #                 self.region = 'sierra_oriente_fourteenth_salary'
    #             if self.employee_id.contract_id.payment_period_fourteenth == 'costa_fourteenth_salary':
    #                 self.region = 'costa_fourteenth_salary'
    #         self.disability_deduction = self.employee_id.disability_deduction
    #
    #         # Tiempo en la compañía para calcular bonificación de jubilación (máximo valor 25 años)
    #         self.retirement_bonus_years = min(25, self.years_in_service if (
    #                 self.months_in_service == 0 and self.days_in_service == 0) else self.years_in_service + 1)
    #
    #         self._get_last_payment()
    #         self._get_best_payment()
    #
    #
    #         if self.date_from <= self.date_to:
    #             contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
    #             if not contract_ids or len(contract_ids) == 0:
    #                 raise ValidationError(_('There are no current contracts for the selected employee and period.'))
    #             else:
    #                 vals['value'].update(
    #                     self._get_worked_days(self.date_from, self.date_to, contract_ids))
    #                 income_ids = [(5,)]
    #                 expense_ids = [(5,)]
    #                 other_expense_ids = [(5,)]
    #                 inputs = self.get_inputs(contract_ids, self.date_from, self.date_to)
    #                 for input in inputs:
    #                     # Ingresos adicionales
    #                     if input.get('type') == 'income':
    #                         # income_ids += income_ids.new(input)
    #                         income_ids.append((0, 0, input))
    #                     # Egresos adicionales
    #                     elif input.get('type') == 'expense':
    #                         expense_ids.append((0, 0, input))
    #                     # Egresos adicionales con beneficiario
    #                     elif input.get('type') == 'other_expense':
    #                         other_expense_ids.append((0, 0, input))
    #                 self.income_ids = income_ids
    #                 self.expense_ids = expense_ids
    #                 self.other_expense_ids = other_expense_ids
    #         else:
    #             raise ValidationError(_('The end date must be greater than or equal to the start date.'))
    #     return vals
    #
    # @api.onchange('causes')
    # def _onchange_causes(self):
    #     if self.causes in ['C02', 'C07', 'C08', 'C09']:
    #         self.eviction = True
    #     else:
    #         self.eviction = False
    #
    # @api.depends('date_from')
    # def _get_unified_basic_salary(self):
    #     """
    #     Este método devuelve el salario basico unificado en base a la fecha final de la nómina
    #     """
    #     for rec in self:
    #         rec.unified_basic_salary = self.get_sbu_by_year(rec.date_to.year)
    #     return True
    #
    # @api.model
    # def get_sbu_by_year(self, year):
    #     sbu = self.env['hr.sbu'].sudo().search([
    #         ('fiscal_year', '=', year),
    #     ], limit=1)
    #     if sbu:
    #         return sbu.value
    #     else:
    #         raise ValidationError(_('You must set the unified base salary for the year {}.').format(str(year)))
    #
    # def _get_last_payment(self):
    #     last_payslip = self.env['hr.payslip'].sudo().search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('state', 'in', ['done', 'paid'])
    #     ], order='date_from DESC', limit=1)
    #     self.last_payment = 0
    #
    #     if last_payslip.id:
    #         for line in last_payslip.line_ids:
    #             if line.code == 'SUBT_INGRESOS':
    #                 self.last_payment += line.total
    #
    # def _get_best_payment(self):
    #     payslips = self.env['hr.payslip'].sudo().search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('state', 'in', ['done', 'paid'])
    #     ])
    #
    #     self.best_payment = 0
    #
    #     for payslip in payslips:
    #         for line in payslip.line_ids:
    #             if line.code == 'SUBT_INGRESOS':
    #                 self.best_payment = max(self.best_payment, line.total)
    #
    # def _get_fourteenth(self):
    #     # Mes en que inicia el periodo de acumulación para el decimocuarto según la región.
    #     # period_start_month = {'coast': 3, 'island': 3, 'sierra': 8, 'eastern': 8}
    #     period_start_month = {'costa_fourteenth_salary': 3, 'sierra_oriente_fourteenth_salary': 8}
    #     period_start_date = None
    #
    #     if self.date_to.month >= period_start_month[self.region]:
    #         period_start_date = self.date_to.replace(
    #             day=1, month=period_start_month[self.region])
    #     else:
    #         period_start_date = self.date_to.replace(
    #             day=1, month=period_start_month[self.region], year=self.date_to.year - 1)
    #
    #     if self.first_contract_date_start > period_start_date:
    #         period_start_date = self.first_contract_date_start
    #
    #     period_end_date = self.date_to
    #
    #     fourteenth_salary = 0
    #     if self.payment_fourteenth_salary == 'accumulated':
    #         payslip_ids = self.env['hr.payslip'].sudo().search([
    #             ('employee_id', '=', self.employee_id.id),
    #             ('date_from', '>=', period_start_date),
    #             ('date_to', '<=', period_end_date),
    #             ('state', 'in', ['done', 'paid'])
    #         ], order='date_from')
    #
    #         for payslip in payslip_ids:
    #             for line in payslip.line_ids:
    #                 if line.code == 'PROV_DCUARTO_ACUMULADO':
    #                     fourteenth_salary += line.total
    #     return fourteenth_salary
    #
    # def _get_thirteenth(self):
    #     period_start_date = self.date_to.replace(day=1, month=12, year=self.date_to.year - 1)
    #     period_end_date = self.date_to
    #
    #     if self.first_contract_date_start > period_start_date:
    #         period_start_date = self.first_contract_date_start
    #
    #     thirteenth_salary = 0
    #     if self.payment_thirteenth_salary == 'accumulated':
    #         payslip_ids = self.env['hr.payslip'].sudo().search([
    #             ('employee_id', '=', self.employee_id.id),
    #             ('date_from', '>=', period_start_date),
    #             ('date_to', '<=', period_end_date),
    #             ('state', 'in', ['done', 'paid'])
    #         ], order='date_from')
    #
    #         for payslip in payslip_ids:
    #             for line in payslip.line_ids:
    #                 if line.code == 'PROV_DTERCERO_ACUMULADO':
    #                     thirteenth_salary += line.total
    #     return thirteenth_salary
    #
    # def _get_vacations(self):
    #     #TODO: crear un campo para inicio y fin del periodo anual en la configuración general.
    #     # Se asume inicio del periodo 1-sep y fin 31-ago.
    #
    #     # if self.date_to.month >= 9:
    #     #     period_start_date = self.date_to.replace(day=1, month=9)
    #     #     period_end_date = self.date_to.replace(day=31,month=8,year=self.date_to.year + 1)
    #     # else:
    #     #     period_start_date = self.date_to.replace(day=1, month=9, year=self.date_to.year - 1)
    #     #     period_end_date = self.date_to.replace(day=31, month=8)
    #
    #     period_start_date = self.date_to.replace(day=1, month=1)
    #     period_end_date = self.date_to.replace(day=31,month=12,year=self.date_to.year)
    #
    #     payslip_ids = self.env['hr.payslip'].sudo().search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('state', 'in', ['done', 'paid'])
    #     ], order='date_from')
    #
    #     accumulated = 0.0
    #     spent = 0.0
    #     for payslip in payslip_ids:
    #         for line in payslip.line_ids:
    #             if line.code == 'PROV_VACA':
    #                 accumulated += line.total
    #             if line.code == 'VACACIONES_TOMADAS' or line.code == 'VACACIONES_PAGADAS':
    #                 spent += line.total
    #
    #     # period_0 = {'start': period_start_date,
    #     #             'end': period_end_date,
    #     #             'accumulated':{9: 0.0, 10 : 0.0, 11 : 0.0, 12 : 0.0,
    #     #                            1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0},
    #     #             'spent':0}
    #     # period_1 = {'start': period_start_date.replace(year=period_start_date.year - 1),
    #     #             'end': period_end_date.replace(year=period_end_date.year - 1),
    #     #             'accumulated':{9: 0.0, 10 : 0.0, 11 : 0.0, 12 : 0.0,
    #     #                            1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0},
    #     #             'spent':0}
    #     # period_2 = {'start': period_start_date.replace(year=period_start_date.year - 2),
    #     #             'end': period_end_date.replace(year=period_end_date.year - 2),
    #     #             'accumulated':{9: 0.0, 10 : 0.0, 11 : 0.0, 12 : 0.0,
    #     #                            1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0},
    #     #             'spent':0}
    #     #
    #     # for period in [period_0, period_1, period_2]:
    #     #     if period['end'] > self.first_contract_date_start:
    #     #         payslip_ids = self.env['hr.payslip'].sudo().search([
    #     #             ('employee_id', '=', self.employee_id.id),
    #     #             ('date_from', '>=', period['start']),
    #     #             ('date_to', '<=', period['end']),
    #     #             ('state', 'in', ['done', 'paid'])
    #     #         ], order='date_from')
    #     #
    #     #         for payslip in payslip_ids:
    #     #             for line in payslip.line_ids:
    #     #                 if line.code == 'PROV_VACA':
    #     #                     period['accumulated'][payslip.date_from.month] += line.total
    #     #                 if line.code == 'VACACIONES_TOMADAS' or line.code == 'VACACIONES_PAGADAS':
    #     #                     period['spent'] += line.total
    #     # print(sum(period_0['accumulated'].values())-period_0['spent'])
    #     #
    #     # return [period_0, period_1, period_2]
    #
    #     return accumulated - spent
    #
    # # @api.onchange('employee_id', 'date_from', 'date_to')
    # # def onchange_employee(self):
    # #     res = super(HrAssetsLiquidation, self).onchange_employee()
    # #     if self.employee_id.id:
    # #         self.name = _('Assets liquidation for %s') % (self.employee_id.name)
    # #     return res
    #
    # @api.model
    # def get_contract(self, employee, date_from, date_to):
    #     """
    #     Se sobrescribe el metodo get_contract pues ahora queremos aplicar otros criterios en el filtrado de contratos
    #     """
    #     contract_ids = self.env['hr.contract'].search([
    #         ('employee_id', '=', employee.id), ('date_start', '<=', date_from), ('date_end', '>=', date_from),
    #         ('state', 'in', ['open', 'close'])])
    #     if not contract_ids:
    #         # Para el caso que la ultima version del contrato este en ejecucion y no tenga seteada la fecha de vigencia
    #         contract_ids = self.env['hr.contract'].search([
    #             ('employee_id', '=', employee.id), ('date_start', '<=', date_from), ('date_end', '=', False),
    #             ('state', 'in', ['open', 'close'])])
    #         if not contract_ids:
    #             contract_ids = self.env['hr.contract'].search([
    #                 ('employee_id', '=', employee.id), ('date_start', '<=', date_to), ('date_end', '=', False),
    #                 ('state', 'in', ['open', 'close'])], order='date_start DESC')
    #             if not contract_ids:
    #                 contract_ids = self.env['hr.contract'].search([
    #                     ('employee_id', '=', employee.id), ('date_start', '>=', date_from), ('date_end', '<=', date_to),
    #                     ('state', 'in', ['open', 'close'])])
    #     return contract_ids.mapped('id')
    #
    # @api.model
    # def _get_worked_days(self, date_from, date_to, contract_id, disease=0):
    #     '''
    #     Metodo devuelve los valores del date_from para los contratos que comienzan luego del comienzo del mes que se esta procesando,
    #     devuelve el date_to para los contratos que finalizan en el mes, y los dias trabajados segun estos parametros tomando
    #     siempre como valor mayor 30 dias para los meses.
    #     :return:
    #     '''
    #
    #     contract = self.env['hr.contract']
    #     if contract_id:
    #         contract = contract.browse(contract_id)
    #         if not contract.contract_date_start:
    #             raise UserError(_('Please enter the contract start date to continue.'))
    #         else:
    #             contract_date_start = contract.contract_date_start
    #     else:
    #         contract_date_start = date_from.replace(day=1)
    #
    #     date_start_contract = contract_date_start
    #
    #     date_end_contract = False
    #     if contract.date_end:
    #         date_end_contract = contract.date_end
    #     if date_start_contract > date_from:
    #         date_from = date_start_contract
    #     if date_end_contract:
    #         if date_end_contract < date_to:
    #             date_to = date_end_contract
    #
    #     worked_days = date_to.day - date_from.day + 1 - disease
    #
    #     return {'worked_days': worked_days,
    #             'date_from': date_from,
    #             'date_to': date_to,
    #             }
    #
    # @api.model
    # def get_inputs(self, contracts, date_from, date_to):
    #     """
    #     Invocamos el metodo get_inputs para agregar nuevas entradas a la nómina
    #     """
    #
    #     # Convirtiendo el listado de id de contratos en objetos
    #     contracts = self.env['hr.contract'].browse(contracts)
    #
    #     res = []
    #
    #     structure_ids = contracts.get_all_structures()
    #     rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
    #     sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
    #     inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')
    #
    #     for contract in contracts:
    #         for input in inputs:
    #             # Condición para el módulo de préstamos
    #             if input.code == 'PREST_EMP':
    #                 amount = 0
    #                 # loan_line_id = 0
    #                 lon_obj = self.env['hr.loan'].search([
    #                     ('employee_id', '=', contract.employee_id.id), ('state', '=', 'approved')
    #                 ])
    #                 for loan in lon_obj:
    #                     # if loan_line_id != 0:
    #                     #     break
    #                     for loan_line in loan.loan_lines:
    #                         # if date_from <= loan_line.date <= date_to and not loan_line.paid:
    #                         if not loan_line.paid:
    #                             amount += loan_line.amount
    #                             # loan_line_id = loan_line.id
    #                             # break
    #
    #                 input_data = {
    #                     'name': input.name,
    #                     'code': input.code,
    #                     'contract_id': contract.id,
    #                     'amount': amount,
    #                     # 'loan_line_id':loan_line_id,
    #                     'type': input.type,
    #                 }
    #                 res += [input_data]
    #             # Condición para el módulo de créditos a empleados
    #             elif input.code == 'CRED_EMP_PROF':
    #                 amount = 0
    #                 # ec_line_id = 0
    #                 employee_credit = self.env['hr.employee.credit'].search(
    #                     [('employee_id', '=', contract.employee_id.id), ('state', '=', 'in_payroll')])
    #
    #                 for ec in employee_credit:
    #                     # if ec_line_id != 0:
    #                     #     break
    #                     for ecl in ec.credit_lines:
    #                         # if date_from <= ecl.date <= date_to and not ecl.paid:
    #                         if not ecl.paid:
    #                             amount += ecl.amount
    #                             # ec_line_id = ecl.id
    #                             # break
    #
    #                 input_data = {
    #                     'name': input.name,
    #                     'code': input.code,
    #                     'contract_id': contract.id,
    #                     'amount': amount,
    #                     # 'employee_credit_line_id': ec_line_id,
    #                     'type': input.type,
    #                 }
    #                 res += [input_data]
    #             # Comportamiento por defecto
    #             else:
    #                 input_data = {
    #                     'name': input.name,
    #                     'code': input.code,
    #                     'type': input.type,
    #                     'contract_id': contract.id,
    #                 }
    #                 res += [input_data]
    #
    #     for contract in contracts:
    #         if hasattr(contract, 'income_ids'):
    #             for input in contract.income_ids:
    #                 # Removemos reglas salariales que ya existen en el contrato
    #                 res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
    #                 line = {
    #                     'name': input.rule_id.name,
    #                     'code': input.rule_id.code,
    #                     'amount': input.amount,
    #                     'partner_id': input.partner_id.id,
    #                     'type': input.type,
    #                     'contract_id': contract.id
    #                 }
    #                 res += [line]
    #
    #         if hasattr(contract, 'expense_ids'):
    #             for input in contract.expense_ids:
    #                 # Removemos reglas salariales que ya existen en el contrato
    #                 res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
    #                 line = {
    #                     'name': input.rule_id.name,
    #                     'code': input.rule_id.code,
    #                     'amount': input.amount,
    #                     'partner_id': input.partner_id.id,
    #                     'type': input.type,
    #                     'contract_id': contract.id
    #                 }
    #                 res += [line]
    #
    #         if hasattr(contract, 'other_expense_ids'):
    #             for input in contract.other_expense_ids:
    #                 # Removemos reglas salariales que ya existe en el contrato
    #                 res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
    #                 line = {
    #                     'name': input.rule_id.name,
    #                     'code': input.rule_id.code,
    #                     'amount': input.amount,
    #                     'partner_id': input.partner_id.id,
    #                     'type': input.type,
    #                     'contract_id': contract.id
    #                 }
    #                 res += [line]
    #
    #     return res
    #
    # @api.model
    # def _get_assets_liquidation_lines(self, contract_ids, assets_liquidation_id, add_liquidation_rules=False,
    #                                   liquidation_amounts={}):
    #     def _sum_salary_rule_category(localdict, category, amount):
    #         if category.parent_id:
    #             localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
    #
    #         if category.code in localdict['categories'].dict:
    #             localdict['categories'].dict[category.code] += amount
    #         else:
    #             localdict['categories'].dict[category.code] = amount
    #
    #         return localdict
    #
    #     class BrowsableObject(object):
    #         def __init__(self, employee_id, dict, env):
    #             self.employee_id = employee_id
    #             self.dict = dict
    #             self.env = env
    #
    #         def __getattr__(self, attr):
    #             return attr in self.dict and self.dict.__getitem__(attr) or 0.0
    #
    #     class InputLine(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""
    #                         SELECT sum(amount) as sum
    #                         FROM hr_assets_liquidation as hp, hr_assets_liquidation_input as pi
    #                         WHERE hp.employee_id = %s AND hp.state = 'done'
    #                         AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.assets_liquidation_id AND pi.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             return self.env.cr.fetchone()[0] or 0.0
    #
    #     class WorkedDays(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def _sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""
    #                         SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
    #                         FROM hr_assets_liquidation as hp, hr_assets_liquidation_worked_days as pi
    #                         WHERE hp.employee_id = %s AND hp.state = 'done'
    #                         AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.assets_liquidation_id
    #                         AND pi.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             return self.env.cr.fetchone()
    #
    #         def sum(self, code, from_date, to_date=None):
    #             res = self._sum(code, from_date, to_date)
    #             return res and res[0] or 0.0
    #
    #         def sum_hours(self, code, from_date, to_date=None):
    #             res = self._sum(code, from_date, to_date)
    #             return res and res[1] or 0.0
    #
    #     class AssetLiquidation(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
    #                                 FROM hr_assets_liquidation as hp, hr_assets_liquidation_line as pl
    #                                 WHERE hp.employee_id = %s AND hp.state = 'done'
    #                                 AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             res = self.env.cr.fetchone()
    #             return res and res[0] or 0.0
    #
    #     def _get_rules_by_move(localdict, sorted_rules):
    #         """Buscamos los moves en las reglas de tipo move, y retornamos la permutacion de reglas y moves"""
    #         rules_by_move = []
    #         aml_obj = self.sudo().env['account.move.line']  # usamos sudo para poder acceder a los registros contables
    #         for rule in sorted_rules:
    #             move_ids = []
    #             if rule.amount_select in ['account_move']:
    #                 # si es del nuevo tipo, basado en movimientos contables, buscamos los movimientos
    #                 payslip = self.search([('id', '=', localdict['payslip'].id)])
    #                 partner = payslip.employee_id.address_home_id.commercial_partner_id
    #                 if not partner:
    #                     raise UserError(u'El colaborador %s no tiene una empresa configurada' % payslip.employee_id.name)
    #                 account = rule.account_credit
    #                 if not account:
    #                     raise UserError(
    #                         u'La regla salarial %s es de tipo Neteo Saldo Contable, solo debe tener una cuenta acreedora configurada' % rule.name)
    #                 if rule.account_debit or rule.condition_acc:
    #                     raise UserError(
    #                         u'La regla salarial %s es de tipo Neteo Saldo Contable, solo debe tener una cuenta acreedora configurada' % rule.name)
    #                 move_ids = aml_obj.search(_get_domain_rules_by_move(partner, payslip, account, rule))
    #             if move_ids:
    #                 for move in move_ids:
    #                     rules_by_move.append((rule, move))
    #             else:
    #                 # se retorna el objeto vacío aml_obj para facilitar la programacion
    #                 rules_by_move.append((rule, aml_obj))
    #         return rules_by_move
    #
    #     def _get_domain_rules_by_move(partner, payslip, account, rule):
    #         """
    #         Hook para modificar criterio de busqueda account_move_line.
    #         @return: Domain
    #         """
    #
    #         return [
    #             ('partner_id', '=', partner.id),
    #             ('date_maturity', '>=', payslip.date_from),
    #             ('date_maturity', '<=', payslip.date_to),
    #             ('account_id', '=', account.id),
    #             ('debit', '>', 0.0),  # escuchamos en el debe
    #             ('full_reconcile_id', '=', False),
    #         ]
    #
    #     # we keep a dict with the result because a value can be overwritten by another rule with the same code
    #     result_dict = {}
    #     rules_dict = {}
    #     worked_days_dict = {}
    #     inputs_dict = {}
    #     blacklist = []
    #     assets_liquidation = self.env['hr.assets.liquidation'].browse(assets_liquidation_id)
    #     for worked_days_line in assets_liquidation.worked_days_line_ids:
    #         worked_days_dict[worked_days_line.code] = worked_days_line
    #     for input_line in assets_liquidation.input_line_ids:
    #         inputs_dict[input_line.code] = input_line
    #
    #     categories = BrowsableObject(assets_liquidation.employee_id.id, {}, self.env)
    #     inputs = InputLine(assets_liquidation.employee_id.id, inputs_dict, self.env)
    #     worked_days = WorkedDays(assets_liquidation.employee_id.id, worked_days_dict, self.env)
    #     assets_liquidations = AssetLiquidation(assets_liquidation.employee_id.id, assets_liquidation, self.env)
    #     rules = BrowsableObject(assets_liquidation.employee_id.id, rules_dict, self.env)
    #     baselocaldict = {'float_round': float_round, 'categories': categories, 'rules': rules,
    #                      'payslip': assets_liquidations, 'worked_days': worked_days, 'inputs': inputs}
    #     # get the ids of the structures on the contracts and their parent id as well
    #     contracts = self.env['hr.contract'].browse(contract_ids)
    #     if len(contracts) == 1 and assets_liquidation.employee_id.contract_id.struct_id:
    #         structure_ids = list(set(assets_liquidation.employee_id.contract_id.struct_id._get_parent_structure().ids))
    #     else:
    #         structure_ids = contracts.get_all_structures()
    #     # get the rules of the structure and thier children
    #     rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
    #
    #     # Adicionando las reglas salariales para la liquidación de haberes
    #     if add_liquidation_rules:
    #         # Adicionando reglas para liquidaciones
    #         fourteenth_rule = self.env.ref('hr_dr_payroll.salary_rule_36', False)
    #         thirteenth_rule = self.env.ref('hr_dr_payroll.salary_rule_35', False)
    #         vacations_rule = self.env.ref('hr_dr_payroll.salary_rule_37', False)
    #         if fourteenth_rule:
    #             fourteenth_rule.amount_fix = liquidation_amounts.get(fourteenth_rule.id, 0.0)
    #             rule_ids.append((fourteenth_rule.id, fourteenth_rule.sequence))
    #         if thirteenth_rule:
    #             thirteenth_rule.amount_fix = liquidation_amounts.get(thirteenth_rule.id, 0.0)
    #             rule_ids.append((thirteenth_rule.id, thirteenth_rule.sequence))
    #         if vacations_rule:
    #             vacations_rule.amount_fix = liquidation_amounts.get(vacations_rule.id, 0.0)
    #             rule_ids.append((vacations_rule.id, vacations_rule.sequence))
    #
    #         if self.causes in ['C02', 'C07', 'C08']:
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_39', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #         if self.causes == 'C09':
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_38', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #             # Adicionando reglas para indemnizaciones
    #             # if self.pregnant_woman:
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_40', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #             # if self.union_leader:
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_41', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #             # if self.non_occupational_disease:
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_43', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #             # if self.disability_deduction:
    #             rule = self.env.ref('hr_dr_payroll.salary_rule_42', False)
    #             if rule:
    #                 rule_ids.append((rule.id, rule.sequence))
    #             if self.discrimination:
    #                 rule = self.env.ref('hr_dr_payroll.salary_rule_44', False)
    #                 if rule:
    #                     rule_ids.append((rule.id, rule.sequence))
    #             if self.eviction:
    #                 rule = self.env.ref('hr_dr_payroll.salary_rule_39', False)
    #                 if rule:
    #                     rule_ids.append((rule.id, rule.sequence))
    #         # Adicionando reglas para bonos
    #         # if self.retirement_bonus:
    #         rule = self.env.ref('hr_dr_payroll.salary_rule_45', False)
    #         if rule:
    #             rule_ids.append((rule.id, rule.sequence))
    #     # run the rules by sequence
    #     sorted_rule_ids = self.get_sorted_rules(rule_ids)
    #     sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
    #     for contract in contracts:
    #         employee = contract.employee_id
    #         localdict = dict(baselocaldict, employee=employee, contract=contract)
    #         sequence = 0
    #         sorted_rules_and_moves = _get_rules_by_move(localdict, sorted_rules)
    #         for rule, move in sorted_rules_and_moves:
    #             sequence += 1
    #             key = rule.code + '-' + str(contract.id) + '-' + str(move.id)
    #             localdict['force_amount'] = 0.0
    #             if move.amount_residual:
    #                 localdict['force_amount'] = move.amount_residual  # todo en validar regla en satisfy_condition
    #             elif not move.full_reconcile_id:
    #                 # cuando la cuenta no es de tipo por pagar no tiene amount_Residual
    #                 # en este caso tomamos el valor de debito
    #                 localdict['force_amount'] = abs(move.debit)
    #             # check if the rule can be applied
    #             if rule._satisfy_condition(localdict) and rule.id not in blacklist:
    #                 # compute the amount of the rule
    #                 amount, qty, rate = rule._compute_rule(localdict)
    #                 # check if there is already a rule computed with that code
    #                 previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
    #                 # set/overwrite the amount computed for this rule in the localdict
    #                 tot_rule = amount * qty * rate / 100.0
    #
    #                 if localdict.get(rule.code):
    #                     localdict[rule.code] += tot_rule
    #                 else:
    #                     localdict[rule.code] = tot_rule
    #                 rules_dict[rule.code] = rule
    #                 # sum the amount for its salary category
    #                 localdict = _sum_salary_rule_category(localdict, rule.category_id,
    #                                                       localdict[rule.code] - previous_amount)
    #                 result_dict[key] = {
    #                     'salary_rule_id': rule.id,
    #                     'contract_id': contract.id,
    #                     'name': assets_liquidation.get_name_rule(rule),
    #                     'code': rule.code,
    #                     'category_id': rule.category_id.id,
    #                     'sequence': sequence,
    #                     'appears_on_payslip': rule.appears_on_payslip,
    #                     'condition_select': rule.condition_select,
    #                     'condition_python': rule.condition_python,
    #                     'condition_range': rule.condition_range,
    #                     'condition_range_min': rule.condition_range_min,
    #                     'condition_range_max': rule.condition_range_max,
    #                     'amount_select': rule.amount_select,
    #                     'amount_fix': rule.amount_fix,
    #                     'amount_python_compute': rule.amount_python_compute,
    #                     'amount_percentage': rule.amount_percentage,
    #                     'amount_percentage_base': rule.amount_percentage_base,
    #                     'register_id': rule.register_id.id,
    #                     'amount': amount,
    #                     'employee_id': contract.employee_id.id,
    #                     'quantity': qty,
    #                     'rate': rate,
    #                     'receivable_move_line_id': move.id,
    #                 }
    #             else:
    #                 # blacklist this rule and its children
    #                 blacklist += [id for id, seq in rule._recursive_search_of_rules()]
    #
    #     return list(result_dict.values())
    #
    # @api.model
    # def get_name_rule(self, rule):
    #     """
    #     Este metodo concatena la cantidad de horas extras al 50 y 100 porciento para que salga en el calculo
    #     de la nómina y en el reporte impreso
    #     """
    #     res = rule.name
    #     if rule.code in ('HORA_EXTRA_REGULAR', 'HORA_EXTRA_EXTRAORDINARIA'):
    #         input_ids = self.env['hr.assets.liquidation.input'].search([('assets_liquidation_id', 'in', [self.id]), ('code', '=', rule.code)])
    #         if input_ids:
    #             res = res + ' (' + str(input_ids[0].amount) + ')'
    #     return res
    #
    # @api.model
    # def get_sorted_rules(self, rule_ids):
    #     """
    #     Este metodo ordena las reglas salariales en base a la categoria y luego a la secuencia de la regla
    #     """
    #     sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
    #     # sorted_rule_ids = super(HrPayslip, self).get_sorted_rules(rule_ids)
    #     sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
    #     incomes = []
    #     others = []
    #     expenses = []
    #     contributions = []
    #     subtotals = []
    #     for rule in sorted_rules:
    #         # Ingresos (Genera beneficios sociales)
    #         if rule.category_id.code == 'INGRESOS':
    #             incomes += [rule.id]
    #         # Otros Ingresos (No genera beneficios sociales)
    #         elif rule.category_id.code == 'OINGRESOS':
    #             others += [rule.id]
    #         # Egresos
    #         elif rule.category_id.code == 'EGRESOS':
    #             expenses += [rule.id]
    #         # Contribución de la Compañía
    #         elif rule.category_id.code == 'COMPANIA':
    #             contributions += [rule.id]
    #         # Subtotales
    #         elif rule.category_id.code == 'SUBTOTALES':
    #             subtotals += [rule.id]
    #         else:
    #             raise UserError(u'La regla %s no pertenece a ninguna categoría.' % rule.name)
    #     sorted_rule_ids = incomes + others + expenses + contributions + subtotals
    #     return sorted_rule_ids
    #
    # @api.model
    # def get_name_rule(self, rule):
    #     '''
    #     Este metodo concatena la cantidad de horas extras al 50 y 100 porciento para que salga en el calculo
    #     de la nómina y en el reporte impreso
    #     '''
    #     # res = super(HrPayslip, self).get_name_rule(rule)
    #     res = rule.name
    #     if rule.code in ('HORA_EXTRA_REGULAR', 'HORA_EXTRA_EXTRAORDINARIA'):
    #         input_ids = self.env['hr.assets.liquidation.input'].search([('assets_liquidation_id', 'in', [self.id]), ('code', '=', rule.code)])
    #         if input_ids:
    #             res = res + ' (' + str(input_ids[0].amount) + ')'
    #     return res
    #
    #
    # def _get_employee_information(self):
    #     """
    #     Este metodo relaciona la nómina con la información del colaborador para el calculo del impuesto a la renta
    #     """
    #     for liquidation in self:
    #         employee_information = None
    #         employee_information_ids = self.env['hr.personal.expense'].search([
    #             ('employee_id', '=', liquidation.employee_id.id),
    #             ('rent_tax_table_id.fiscal_year', '=', liquidation.date_from.year),
    #             ('state', '=', 'done')
    #         ])
    #         if employee_information_ids:
    #             employee_information = employee_information_ids[0].id
    #         liquidation.employee_information = employee_information
    #     return True
    #
    # def make_move_payslip(self):
    #     """
    #     Crea el movimiento contable para los registros visibles en la nómina impresa
    #     """
    #     name = _('Assets liquidation of %s') % (self.employee_id.name)
    #     date = self.date_to
    #     number = "LIQ/{}".format(self.id)
    #
    #     move_header = {
    #         'narration': name,
    #         'ref': number,
    #         'journal_id': self.journal_id.id,
    #         'date': date,
    #         'partner_id': self.employee_id.address_home_id.commercial_partner_id.id,
    #     }
    #     move_lines = self._compute_move_lines(self.line_ids)
    #     move = self._create_account_moves(move_header, move_lines)
    #     self.move_id = move.id
    #     # toca volver a poner, a pesar que ya esta en el move_header no coge
    #     move.partner_id = self.employee_id.address_home_id.commercial_partner_id.id
    #
    # def make_move_payslip_provision(self):
    #     """
    #     Realizamos el asiento de las provisiones
    #     """
    #     name = _('Provision of %s') % (self.employee_id.name)
    #     date = self.date_to
    #     number = "LIQ/{}".format(self.id)
    #
    #     move_header = {
    #         'narration': name,
    #         'ref': number,
    #         'journal_id': self.journal_id.id,
    #         'date': date,
    #         'partner_id': self.employee_id.address_home_id.commercial_partner_id.id,
    #     }
    #     move_lines = self._compute_move_lines(self.details_by_salary_rule_category - self.line_ids)
    #     move = self._create_account_moves(move_header, move_lines)
    #     self.provision_move_id = move.id
    #     # toca volver a poner, a pesar que ya esta en el move_header no coge
    #     move.partner_id = self.employee_id.address_home_id.commercial_partner_id.id
    #
    #
    # def _reconcile_receivables_vs_payslip(self):
    #     """
    #     Concilia la nomina contra las facturas a cobrar al colaborador
    #     Lo hace línea por línea de nómina, en base a los campos receivable_move_line_id y move_line_ids
    #     """
    #     # tomamos todas las nóminas a la vez, considerando las líneas visibles y no visibles en la nómina
    #     lines = self.details_by_salary_rule_category.filtered(lambda r: r.amount_select == 'account_move')
    #     # conciliamos las receivables
    #     for line in lines:
    #         # solo conciilamos si la cuenta es CxC y el valor esta en el credito
    #         counterpart_moves = line.move_line_ids.filtered(
    #             lambda r: r.account_id.internal_type == 'receivable').filtered(lambda r: r.credit > 0.0)
    #         satisfy_reconcile_conditions = True
    #         if satisfy_reconcile_conditions and line.receivable_move_line_id and counterpart_moves:
    #             moves_to_reconcile = line.receivable_move_line_id + counterpart_moves
    #             moves_to_reconcile.reconcile()
    #
    #
    # def _compute_move_lines(self, lines):
    #     """
    #     Computa las lineas de asiento contable en base a las líneas de la nomina pasadas como argumento
    #     @lines payslip.lines, en base a las cuales se crea el asiento contable
    #     """
    #     self.ensure_one()  # usamos api.multi a pesar de estar implementado para una sola nomina
    #     precision = self.env['decimal.precision'].precision_get('Payroll')
    #     date = self.date_to
    #     debit_sum = 0.0
    #     credit_sum = 0.0
    #     move_ids = []  # los vals de los asientos a crear
    #     for line in lines:
    #         amount = self.credit_note and -line.total or line.total
    #         if float_is_zero(amount, precision_digits=precision):
    #             continue
    #         debit_account_id = self.get_debit_account_id(line)
    #         credit_account_id = self.get_credit_account_id(line)
    #         if debit_account_id:
    #             debit_line = (0, 0, self.get_split_debit_lines(self, line, date, amount, debit_account_id))
    #             # damos otra vuelta agregando plazos de pago
    #             # TODO v11 unificar los plazos de pago en el core
    #             # TODO v11 replicar lo del debe en el haber
    #             if line.salary_rule_id.payment_term_days:
    #                 date_maturity = datetime.strptime(debit_line[2]['date'], '%Y-%m-%d') + \
    #                                 timedelta(days=line.salary_rule_id.payment_term_days)
    #                 debit_line[2].update({'date_maturity': date_maturity})
    #             move_ids.append(debit_line)
    #             debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
    #         if credit_account_id:
    #             for credit_line in self.get_split_credit_lines(self, line, date, amount, credit_account_id):
    #                 move_ids.append(credit_line)
    #                 credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
    #         if not debit_account_id and not credit_account_id and line.salary_rule_id.category_id.code != 'SUBTOTALES':
    #             raise ValidationError(
    #                 _('To continue you must set up a debit or credit account in the salary rule "%s"')
    #                 % line.salary_rule_id.name)
    #     # El core ya valida que el asiento este cuadrado
    #     # TODO Implementar un metodo que valide que el asiento este cuadrado pero
    #     # que muestre en pantalla (aunque sea en texto formateado como tabla) los valores para que se pueda
    #     # identificar con facilidad la causa del descuadre
    #     return move_ids
    #
    #
    # def _compute_details_by_salary_rule_category(self):
    #     for liquidation in self:
    #         liquidation.details_by_salary_rule_category = liquidation.mapped('line_ids').filtered(lambda line: line.category_id)
    #
    # def _compute_unfair_dismissal(self):
    #     for rec in self:
    #         if rec.causes == 'C09':
    #             rec.unfair_dismissal = True
    #         else:
    #             rec.unfair_dismissal = False
    #
    # @api.depends('days_in_service', 'months_in_service', 'years_in_service')
    # def _compute_first_contract_date_start(self):
    #     for rec in self:
    #         # Resto aquí el día que se adicionó de más en days_in_service
    #         rec.first_contract_date_start = rec.date_to - relativedelta(
    #             days=rec.days_in_service - 1, months=rec.months_in_service, years=rec.years_in_service)
    #
    # @api.depends('days_in_service', 'months_in_service', 'years_in_service', 'employee_age')
    # def _compute_show_bonus(self):
    #     for rec in self:
    #         rec.show_bonus =  rec.employee_age >= 55
    #
    # @api.depends('line_ids.amount')
    # def _get_net_salary(self):
    #     net_salary = 0.0
    #     if self.line_ids:
    #         for line in self.line_ids:
    #             if line.salary_rule_id.code == 'SUBT_NET':
    #                 net_salary = line.amount
    #     self.net_salary = net_salary
    #
    # @api.model
    # def _create_account_moves(self, move_dict, line_ids):
    #     """
    #     Método auxiliar para crear el asiento contable
    #     """
    #     move_dict['line_ids'] = line_ids
    #     move = self.env['account.move'].create(move_dict)
    #     move.post()
    #     return move
    #
    # @api.model
    # def get_debit_account_id(self, line):
    #     '''
    #     Invocamos el get_debit_account_id para setear la cuenta deudora cuando este activo el check de cuentas contables
    #     por tipo de contrato en la regla salarial
    #     '''
    #     account_id = line.salary_rule_id.account_debit.id
    #     if line.salary_rule_id.condition_acc:
    #         # Mano de obra directa
    #         hr_contract_type_mdi = self.env.ref('hr_dr_payroll.hr_contract_type_mdi')
    #         # Mano de obra indirecta
    #         hr_contract_type_min = self.env.ref('hr_dr_payroll.hr_contract_type_min')
    #         # Administrativo
    #         hr_contract_type_wrkr = self.env.ref('hr_dr_payroll.hr_contract_type_wrkr')
    #         # Ventas
    #         hr_contract_type_sub = self.env.ref('hr_dr_payroll.hr_contract_type_sub')
    #         contract_type = line.slip_id.employee_id.contract_id.type_id
    #         if contract_type == hr_contract_type_mdi:
    #             account_id = line.salary_rule_id.debit_acc_manu_di.id
    #         elif contract_type == hr_contract_type_min:
    #             account_id = line.salary_rule_id.debit_acc_manu_in.id
    #         elif contract_type == hr_contract_type_wrkr:
    #             account_id = line.salary_rule_id.debit_acc_administrative.id
    #         elif contract_type == hr_contract_type_sub:
    #             account_id = line.salary_rule_id.debit_acc_sales.id
    #     return account_id
    #
    # @api.model
    # def get_credit_account_id(self, line):
    #     """
    #     Invocamos el get_credit_account_id para setear la cuenta acreedora cuando este activo el check de cuentas
    #     contables por tipo de contrato en la regla salarial. Adicionalmente seteamos la cuenta acreedora del salario
    #     neto a recibir, tiene mas peso la configurada en el contrato
    #     """
    #     account_id = line.salary_rule_id.account_credit.id
    #     if line.salary_rule_id.condition_acc:
    #         # Mano de obra directa
    #         hr_contract_type_mdi = self.env.ref('hr_dr_payroll.hr_contract_type_mdi')
    #         # Mano de obra indirecta
    #         hr_contract_type_min = self.env.ref('hr_dr_payroll.hr_contract_type_min')
    #         # Administrativo
    #         hr_contract_type_wrkr = self.env.ref('hr_dr_payroll.hr_contract_type_wrkr')
    #         # Ventas
    #         hr_contract_type_sub = self.env.ref('hr_dr_payroll.hr_contract_type_sub')
    #         contract_type = line.slip_id.employee_id.contract_id.type_id
    #         if contract_type == hr_contract_type_mdi:
    #             if line.salary_rule_id.credit_acc_manu_di:
    #                 account_id = line.salary_rule_id.credit_acc_manu_di.id
    #         elif contract_type == hr_contract_type_min:
    #             if line.salary_rule_id.credit_acc_manu_in:
    #                 account_id = line.salary_rule_id.credit_acc_manu_in.id
    #         elif contract_type == hr_contract_type_wrkr:
    #             if line.salary_rule_id.credit_acc_administrative:
    #                 account_id = line.salary_rule_id.credit_acc_administrative.id
    #         elif contract_type == hr_contract_type_sub:
    #             if line.salary_rule_id.credit_acc_sales:
    #                 account_id = line.salary_rule_id.credit_acc_sales.id
    #     if line.salary_rule_id.code == 'SUBT_NET':
    #         if line.contract_id.account_payable_payroll:
    #             account_id = line.contract_id.account_payable_payroll.id
    #         if not account_id:
    #             account_id = self.employee_id.company_id.account_payable_payslip_id.id
    #         if not account_id:
    #             raise ValidationError(_('You must configure the "Account payable" in the contract or the '
    #                                     '"Creditor account" in the salary rule "Subtotal: Net salary to receive".'))
    #     return account_id
    #
    # @api.model
    # def get_account_analytic(self, account_id):
    #     """
    #     Obtenemos la cuenta analitica para cada linea del asiento contable.
    #     cuando el codigo de la cuenta este en 4,5,6,7,8,9
    #     """
    #     # TODO: Se deberia implementar el campo analytic_policy in ['always_plan']
    #     account = self.env['account.account'].browse(account_id)
    #     if re.match(r'^[4,5,6,7,8,9].', account.code):
    #         ctx = self._context.copy()
    #         return ctx.get('analytic_account_id', False)
    #     else:
    #         return False
    #
    # @api.model
    # def get_split_debit_lines(self, slip, line, date, amount, debit_account_id):
    #     """
    #     Invocamos el método get_split_debit_lines para agregarle la cuenta analitica a las lineas del asiento contable.
    #     el contexto solo llega si el campo cuenta analitica del contrato del colaborador cuenta con un valor.
    #     """
    #     ctx = self.env.context.copy()
    #
    #     analytic_account_id = line.salary_rule_id.analytic_account_id.id or line.employee_id.department_id.analytic_account_id.id
    #
    #     debit_line = {
    #         'name': line.name + ', ' + line.employee_id.name,
    #         'partner_id': line._get_partner_id(credit_account=False),
    #         'account_id': debit_account_id,
    #         'journal_id': slip.journal_id.id,
    #         'date': date,
    #         'debit': amount > 0.0 and amount or 0.0,
    #         'credit': amount < 0.0 and -amount or 0.0,
    #         'analytic_account_id': analytic_account_id,
    #         'tax_line_id': line.salary_rule_id.account_tax_id.id,
    #     }
    #
    #     debit_line.update({'assets_liquidation_line_id': line.id})
    #     if ctx.get('analytic_account_id', False):
    #         analytic_account_id = self.get_account_analytic(debit_account_id)
    #         if analytic_account_id:
    #             debit_line.update({
    #                 'analytic_account_id': analytic_account_id
    #             })
    #     return debit_line
    #
    # @api.model
    # def get_split_credit_lines(self, slip, line, date, amount, credit_account_id):
    #     """
    #     Invocamos el get_split_credit_lines para modificar las líneas de apuntes contables cuando la regla analizada
    #     sea reflejada una o mas veces en el tree de egresos adicionales con beneficiario, se quiere que el asiento
    #     se haga en base a los beneficiarios
    #     """
    #
    #     credit_line = [(0, 0, {
    #         'name': line.name + ', ' + line.employee_id.name,
    #         'partner_id': line._get_partner_id(credit_account=True),
    #         'account_id': credit_account_id,
    #         'journal_id': slip.journal_id.id,
    #         'date': date,
    #         'debit': amount < 0.0 and -amount or 0.0,
    #         'credit': amount > 0.0 and amount or 0.0,
    #         'analytic_account_id': line.salary_rule_id.analytic_account_id.id
    #                                or line.employee_id.department_id.analytic_account_id.id,
    #         'tax_line_id': line.salary_rule_id.account_tax_id.id,
    #     })]
    #
    #     credit_line[0][2].update({'assets_liquidation_line_id': line.id})
    #     other_expense_ids = self.env['hr.assets.liquidation.input'].search([
    #         ('assets_liquidation_id', '=', slip.id),
    #         ('code', '=', line.code),
    #         ('type', '=', 'other_expense'),
    #     ])
    #     if len(other_expense_ids) >= 1:
    #         credit_line = []
    #         for input in other_expense_ids:
    #             analytic_account_id = self.get_account_analytic(
    #                 credit_account_id) or line.salary_rule_id.analytic_account_id.id or line.employee_id.department_id.analytic_account_id.id
    #             credit_line.append((0, 0, {
    #                 'name': input.name,
    #                 'partner_id': input.partner_id.id,
    #                 'account_id': credit_account_id,
    #                 'journal_id': slip.journal_id.id,
    #                 'date': date,
    #                 'debit': input.amount < 0.0 and -input.amount or 0.0,
    #                 'credit': input.amount > 0.0 and input.amount or 0.0,
    #                 'analytic_account_id': analytic_account_id,
    #                 'tax_line_id': line.salary_rule_id.account_tax_id.id,
    #                 'assets_liquidation_line_id': line.id,
    #             }))
    #     return credit_line
    #
    # def _compute_age(self):
    #     for rec in self:
    #         if rec.employee_id.birthday:
    #             rec.employee_age = relativedelta(date.today(), rec.employee_id.birthday).years
    #         else:
    #             rec.employee_age = 0
    #
    # @api.depends('employee_id', 'date_to')
    # def _get_time_in_service(self):
    #     """
    #     Computa por los años, meses y días que un colaborador ha trabajando para la empresa
    #     a la fecha de corte de la nomina.
    #     """
    #     for liquidation in self:
    #
    #         # Obtengo el tiempo transcurrido entre la última entrada a la compañía y la fecha de salida
    #         entry_date = liquidation.employee_id.last_company_entry_date
    #         exit_date = liquidation.date_to
    #         liquidation.years_in_service = relativedelta(exit_date, entry_date).years
    #         liquidation.months_in_service = relativedelta(exit_date, entry_date).months
    #         liquidation.days_in_service = relativedelta(exit_date, entry_date).days
    #
    #         # years = 0
    #         # months = 0
    #         # days = 0
    #         # # Se añade el tiempo antes del uso de Odoo
    #         # years += liquidation.employee_id.total_time_in_company_years or 0.0
    #         # months += liquidation.employee_id.total_time_in_company_months or 0.0
    #         # days += liquidation.employee_id.total_time_in_company_days or 0.0
    #         # # Se añade el tiempo de los contratos viejos (las versiones de contratos se consideran como contratos viejos)
    #         # # Se obtienen todos los contratos anteriores a la fecha seleccionada
    #         # previous_contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),
    #         #                                                         ('date_end', '<=', liquidation.employee_id.contract_id.date_start),
    #         #                                                         ('state', 'in', APROVED_STATES),
    #         #                                                         ('id', '!=', liquidation.employee_id.contract_id.id),
    #         #                                                         ],
    #         #                                                        order='date_end')
    #         # for previous in previous_contract_ids:
    #         #     years_previous, months_previous, days_previous = self.get_legal_years_months_days(
    #         #         previous.date_start,
    #         #         previous.date_end)
    #         #     years += years_previous
    #         #     months += months_previous
    #         #     days += days_previous
    #         # # se añade el tiempo del contrato vigente (el que esta en la nomina)
    #         # # en este caso no validamos que el contrato este aprobado pues es posible que el usuario haga
    #         # # la nomina y luego anule el contrato para pruebas por ejemplo, en este caso es deseable que
    #         # # si se lo considere para el tiempo
    #         # years_current, months_current, days_current = self.get_legal_years_months_days(
    #         #     liquidation.employee_id.contract_id.date_start, liquidation.date_to)
    #         # years += years_current
    #         # months += months_current
    #         # days += days_current
    #         # # normalizamos el computo, por ejemplo 13 meses se convierten a 1 anio y 1 mes
    #         # years, months, days = self.normalize_years_months_days(years, months, days)
    #         # liquidation.years_in_service = years
    #         # liquidation.months_in_service = months
    #         # liquidation.days_in_service = days
    #
    #
    # def get_legal_years_months_days(self, date_start, date_end):
    #     """
    #     Metodo auxiliar para centralizar el computo de deltas de tiempo
    #     @self objeto payslip, no se usa! (lo dejamos para instanciar la clase e invocar el metodo)
    #     @date_start fecha inicio
    #     @date_end fecha final
    #     """
    #     if not date_start or not date_end:
    #         return 0, 0, 0
    #
    #     # a la fecha final se sumamos 1 dia, de esta forma:
    #     # - Cuando el colaborador trabajó del 1ene2017 al 1ene2017 le dará 1 dia
    #     # - Cuando el colaborador trabajó del 1ene2017 al 31ene2017 le dará 1 mes, 0 días
    #     date_end = date_end + timedelta(days=1)
    #
    #     rd = relativedelta(date_end, date_start)
    #     return rd.years, rd.months, rd.days
    #
    #
    # def normalize_years_months_days(self, years, months, legal_days):
    #     """
    #     Normalizamos el computo, por ejemplo 13 meses se convierten a 1 anio y 1 mes
    #     """
    #     if legal_days > 30:
    #         months += int(legal_days / 30)
    #         legal_days = legal_days % 30  # el saldo de la division
    #     if months > 12:
    #         years += int(months / 12)
    #         months = months % 12  # el saldo de la division
    #     if months == 12:
    #         years += int(months / 12)
    #         months = months % 12  # el saldo de la division
    #     return years, months, legal_days
    #
    # def generate_archive(self):
    #     """
    #     Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
    #     diferente.
    #     """
    #
    #     class Line(object):
    #         """Clase auxiliar para la generación de ficheros"""
    #
    #         def __init__(self, dict):
    #             self.__dict__ = dict
    #
    #     exportFile = self.env['hr.dr.export.file']
    #
    #     lines = []
    #     for rec in self:
    #         lines.append(Line({"employee_id": rec.employee_id, "value": rec.net_salary,
    #                            "reference":"LIQ/{}".format(rec.id)}))
    #
    #     messages = exportFile._create_text_files(lines, _('Assets Liquidation'))
    #     if len(messages) > 0:
    #         raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
    #                               .format("\n-\t".join(messages)))
    #
    #     return exportFile._compress_and_show('Assets Liquidation.zip')

    def goto_payslip(self):
        self.create_liquidation_payslip()
        self.payslip_id.compute_sheet()

        return {
            'name': 'Liquidation payslip',
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            # 'view_id': self.env.ref('hr_payroll.view_hr_payslip_form').id,
            # 'target': 'new', # or 'self'
        }

    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id.id:
            contract_obj = self.env['hr.contract']
            # TODO: Revisar si empleado tiene algún método implementado para obtener primer y último contrato, de no ser
            #  así, crear las funcionalidades pues deberían obtenerse desde el objeto employee_id.
            first_contract_id = contract_obj.search(
                [('employee_id', '=', self.employee_id.id), ('state', '!=', 'draft')], order='id asc', limit=1
            )
            if first_contract_id.id:
                self.date_from = first_contract_id.date_start
            last_contract_id = contract_obj.search(
                [('employee_id', '=', self.employee_id.id), ('state', '!=', 'draft')], order='id desc', limit=1
            )
            if last_contract_id.id:
                self.contract_id = last_contract_id.id
                if last_contract_id.date_end:
                    self.date_to = last_contract_id.date_end
                else:
                    self.date_to = date.today()
                    # self.contract_id.date_end = date.today()

            self.last_wage = self.get_last_wage()
            self.best_wage = self.get_best_wage()
        else:
            self.date_from = False
            self.date_to = False
            self.last_wage = 0.0
            self.best_wage = 0.0

    def create_liquidation_payslip(self):
        if not self.payslip_id.id:
            payslip_obj = self.env['hr.payslip']
            # TODO: Revisar el tema de la cantidad de días en la nómina, si no debe tomar más de 30 días en el caso de
            #  los meses largos.

            self.payslip_id = payslip_obj.create({
                'employee_id': self.employee_id.id,
                'contract_id': self.contract_id.id,
                'date_from': self.date_to.replace(day=1),
                'date_to': self.date_to,
                'is_liquidation_payslip': True,
                'state': 'draft',
                'name': _('Liquidation payslip for {}').format(self.employee_id.name),
                'struct_id': self.get_structure_id(),
                'input_line_ids': self.get_compensation_lines(),
                'active': False
            })

            self.payslip_id.onchange_fields_affect_days_worked()
            self.payslip_id.compute_sheet()
            self.payslip_id.update({
                'xiii_liquidation': self.get_xiii_amount(),
                'xiv_liquidation': self.get_xiv_amount(),
                'vacations_liquidation': self.get_vacations_amount()
            })



    def get_structure_id(self):
        return self.contract_id.struct_id.id

    def get_last_wage(self):
        """Obtiene el último salario percibido entre las nóminas pagadas"""
        last_payslip_id = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id), ('state', '=', 'paid'), ('is_liquidation_payslip', '=', False)
        ], order='date_to desc', limit=1)
        taxable_income = self._get_taxable_incomes(last_payslip_id) if last_payslip_id.id else 0.00
        return max(taxable_income, self.contract_id.wage)

    def get_best_wage(self):
        """Obtiene el mejor salario percibido entre las nóminas pagadas."""
        payslip_ids = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id), ('state', '=', 'paid'), ('is_liquidation_payslip', '=', False)
        ])
        value = 0.00
        for payslip in payslip_ids:
            taxable_income = self._get_taxable_incomes(payslip)
            if value < taxable_income:
                value = taxable_income
        return max(value, self.get_last_wage())

    def _get_taxable_incomes(self, payslip):
        """Obtiene el valor total de ingresos aportables de una nómina."""
        taxable_income = 0.00
        for line in payslip.line_ids:
            if line.category_id.code == 'INGRESOS':
                taxable_income += line.total
        return taxable_income

    def get_compensation_lines(self):
        lines = []

        if self.amount > 0:  # Mutuo acuerdo
            type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_compensation')
            lines.append(self._prepare_input_line(type_id, self.amount))

        if self.cause_id.code == 'C09':  # Despido intempestivo
            years_started = self.years_started()
            years = years_started if years_started > 3 else 3
            amount = (min(years, 25) * self.last_wage)
            if amount > 0:
                type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_untimely_termination_compensation')
                lines.append(self._prepare_input_line(type_id, amount))

            if self.disability_deduction:  # Discapacidad
                amount = (self.best_wage * 18)
                if amount > 0:
                    type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_disability_compensation')
                    lines.append(self._prepare_input_line(type_id, amount))

            if self.pregnant_woman:  # Embarazo
                amount = (self.best_wage * 18)
                if amount:
                    if amount > 0:
                        type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_pregnancy_compensation')
                        lines.append(self._prepare_input_line(type_id, amount))

            if self.union_leader:  # Líder sindical
                amount = (self.last_wage * 12)
                if amount:
                    if amount > 0:
                        type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_union_leader_compensation')
                        lines.append(self._prepare_input_line(type_id, amount))

        amount = (self.years_completed() * self.last_wage * 0.25)
        if amount:
            type_id = self.env.ref('hr_dr_payroll_enterprise.hr_payslip_input_type_eviction_compensation')
            lines.append(self._prepare_input_line(type_id, amount))
        return lines

    def _prepare_input_line(self, type_id, amount):
        """Prepara una input line para la nómina de liquidación."""

        return (0, 0, {
            'name': type_id.name,
            'amount': amount,
            'input_type_id': type_id.id,
            'contract_id': self.contract_id.id,
            'input_ids': [(0, 0, {
                'name': type_id.name,
                'date': self.date_to,
                'payslip_input_type_id': type_id.id,
                'employee_id': self.employee_id.id,
                'amount': amount
            })]
        })

    def years_started(self):
        return ceil((self.date_to - self.date_from).days/365.2425)

    def years_completed(self):
        return floor((self.date_to - self.date_from).days/365.2425)

    def get_xiv_period(self):
        year = self.date_to.year
        if self.region == 'sierra_oriente_fourteenth_salary':
            if self.date_to.month > 6:
                date_start = date(year, 7, 1)
                date_end = date(year + 1, 6, 30)
            else:
                date_start = date(year - 1, 7, 1)
                date_end = date(year, 6, 30)
        if self.region == 'costa_fourteenth_salary':
            if self.date_to.month > 2:
                date_start = date(year, 3, 1)
                date_end = self.date_to.replace(day=monthrange(year, self.date_to.month)[1])
            else:
                date_start = date(year - 1, 3, 1)
                date_end = date(year, 2, 29) if isleap(year) else date(year, 2, 28)
        return date_start, date_end

    def get_xiii_period(self):
        if self.date_to.month == 12:
            year = self.date_to.year
            date_start = date(year, 12, 1)
            date_end = date(year, 12, 31)
        else:
            year = self.date_to.year
            date_start = date(year - 1, 12, 1)
            date_end = self.date_to.replace(day=monthrange(year, self.date_to.month)[1])
        return date_start, date_end

    def get_total_expenses(self):
        return sum([abs(l.total) for l in self.payslip_id.line_ids if l.category_id.code == 'EGRESOS'
                    or l.category_id.code == 'EGRESOS_PASIVOS'])

    def get_total_incomes(self):
        amount = sum([l.total for l in self.payslip_id.line_ids if l.category_id.code in ('INGRESOS', 'INGRESOS_NGBS')])
        # amount -= self.calcule_sayings('ProvDec13')
        # amount -= self.calcule_sayings('ProvDec14')
        # amount -= self.calcule_sayings('VACACIONES')
        return amount

    def get_xiii_amount(self):
        obj_payslip = self.env['hr.payslip']
        date_start, date_end = self.get_xiii_period()
        payslip_ids = obj_payslip.search([('employee_id', '=', self.employee_id.id), ('date_from', '>=', date_start),
                                          ('date_to', '<=', date_end), ('state', '=', 'paid')])
        total_amount = 0.00

        # Calculando los valores acumulados hasta la fecha
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'PROV_DTERCERO_ACUMULADO':
                    total_amount += line.total
        # Calculando el valor proporcional de la nómina generada
        if self.payslip_id.id:

            for l in self.payslip_id.line_ids:
                print(l.category_id.code)

            amount = sum(l.total for l in self.payslip_id.line_ids if l.category_id.code == 'INGRESOS') / 12
            days = (self.date_to - self.date_to.replace(day=1)).days

            # TODO: Tengo dudas si el proporcional aplica de esta forma o no es necesario ya que el total de ingresos ya
            #  es proporcional
            total_amount += amount * days / 30
        print(total_amount)
        return total_amount

    def get_xiv_amount(self):
        obj_payslip = self.env['hr.payslip']
        date_start, date_end = self.get_xiv_period()
        payslip_ids = obj_payslip.search([('employee_id', '=', self.employee_id.id), ('date_from', '>=', date_start),
                                          ('date_to', '<=', date_end), ('state', '=', 'paid')])
        total_amount = 0.00
        # Calculando los valores acumulados hasta la fecha
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'PROV_DCUARTO_ACUMULADO':
                    total_amount += line.total

        # Calculando el valor proporcional de la nómina generada
        if self.payslip_id.id:
            amount = (self.payslip_id.unified_basic_salary / 12.0) * (self.contract_id.daily_hours / self.contract_id.standard_daily_hours) * (self.payslip_id.worked_days / 30)
            days = (self.date_to - self.date_to.replace(day=1)).days
            total_amount += amount * days / 30
        return total_amount

    def get_vacations_amount(self):
        obj_payslip = self.env['hr.payslip']
        payslip_ids = obj_payslip.search([('employee_id', '=', self.employee_id.id), ('date_from', '>=', self.date_from),
                                          ('date_to', '<=', self.date_to), ('state', '=', 'paid')])
        total_amount = 0.00
        for payslip in payslip_ids:
            total_amount += self._get_vacation_amount_by_payslip(payslip)

        # TODO: No estoy seguro si en la nómina actual hay que multiplicar el total por la proporción de días o no para
        #    la provisión de vacaciones
        if self.payslip_id.id:
            total_amount += self._get_vacation_amount_by_payslip(self.payslip_id)
        return total_amount

    def _get_vacation_amount_by_payslip(self, payslip):
        total_amount = 0.0
        for line in payslip.line_ids:
            if line.code == 'PROV_VACA':
                total_amount += line.total
            elif line.code in ['PAY_VACATIONS', 'VACATIONS_TAKEN']:
                total_amount -= line.total
        return total_amount

    def get_rule(self, code):
        obj_payslip = self.env['hr.payslip']
        value = 0.00
        if code == 'PROV_DTERCERO_ACUMULADO':
            date_start, date_end = self.get_xiii_period()
        elif code == 'PROV_DCUARTO_ACUMULADO':
            date_start, date_end = self.get_xiv_period()
        else:
            if self.date_from.month <= self.date_to.month:
                year = self.date_to.year
            else:
                year = self.date_to.year - 1

            date_start = date(year, self.date_from.month, 1)
            date_end = self.date_to.replace(day=monthrange(year, self.date_to.month)[1])

        payslip_ids = obj_payslip.search([('employee_id', '=', self.employee_id.id), ('date_from', '>=', date_start),
                                          ('date_to', '<=', date_end), ('state', '=', 'paid')])
        for payslip in payslip_ids:
            if code == 'PROV_VACA':
                total = [line.total for line in payslip.line_ids if line.code == code][0]
                date_start = date(date_start.year, date_start.month, self.date_from.day)
                if payslip.date_from < date_start and int(31 - self.date_from.day) < payslip.worked_days_line_ids[0].number_of_days:
                    value += (total / payslip.worked_days_line_ids[0].number_of_days) * int(31 - self.date_from.day)
                else:
                    value += total
            else:
                value += sum([line.total for line in payslip.line_ids if line.code in code])
        return value

# class HrAssetsLiquidationInput(models.Model):
#     _name = 'hr.assets.liquidation.input'
#     _description = 'Assets Liquidation Input'
#     _order = 'assets_liquidation_id, sequence'
#
#     _TYPE = [
#         ('income', _('Income')),
#         ('expense', _('Expense')),
#         ('other_expense', _('Expense with beneficiary')),
#     ]
#
#     name = fields.Char(string='Description', required=True)
#     assets_liquidation_id = fields.Many2one('hr.assets.liquidation', string='Assets Liquidation', required=True,
#                                             ondelete='cascade', index=True)
#     sequence = fields.Integer(required=True, index=True, default=10)
#     code = fields.Char(required=True, help="The code that can be used in the salary rules")
#     amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
#                                "1% commission of basic salary for per product can defined in expression "
#                                "like result = inputs.SALEURO.amount * contract.wage*0.01.")
#     contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
#         help="The contract for which applied this input")
#     partner_id = fields.Many2one('res.partner', string='Beneficiary',
#                                  help='')
#     type = fields.Selection(_TYPE, string='Type',
#                             help='')
#
#
# class HrAssetsLiquidationWorkedDays(models.Model):
#     _name = 'hr.assets.liquidation.worked_days'
#     _description = 'Payslip Worked Days'
#     _order = 'assets_liquidation_id, sequence'
#
#     name = fields.Char(string='Description', required=True)
#     assets_liquidation_id = fields.Many2one('hr.assets.liquidation', string='Assets Liquidation', required=True,
#                                             ondelete='cascade', index=True)
#     sequence = fields.Integer(required=True, index=True, default=10)
#     code = fields.Char(required=True, help="The code that can be used in the salary rules")
#     number_of_days = fields.Float(string='Number of Days')
#     number_of_hours = fields.Float(string='Number of Hours')
#     contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
#         help="The contract for which applied this input")
#
#
# class HrAssetsLiquidationLine(models.Model):
#     _name = 'hr.assets.liquidation.line'
#     _inherit = 'hr.salary.rule'
#     _description = 'Assets Liquidation Line'
#     _order = 'contract_id, sequence'
#
#     slip_id = fields.Many2one('hr.assets.liquidation', string='Assets Liquidation', required=True, ondelete='cascade')
#     salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
#     employee_id = fields.Many2one('hr.employee', string='Collaborator', required=True, ondelete='cascade')
#     contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
#     rate = fields.Float(string='Rate (%)', digits='Payroll Rate', default=100.0)
#     amount = fields.Float(digits='Payroll')
#     quantity = fields.Float(digits='Payroll', default=1.0)
#     total = fields.Float(compute='_compute_total', string='Total', digits='Payroll', store=True)
#     partner_id = fields.Many2one('res.partner', string='Beneficiary',
#         help='Indica a favor de quien se realizará el asiento contable, util para retenciones legales')
#     receivable_move_line_id = fields.Many2one( 'account.move.line', string='Asiento a pagar',
#         help='''Cuando la regla salarial es de tipo "Movimientos Contables a Netear", indica el
#             asiento contable que se pagaria con esta nomina, permitiendo su conciliación ''')
#     move_line_ids = fields.One2many('account.move.line', 'assets_liquidation_line_id', string='Asientos vinculados',
#         help='''Los asientos contables asociados a la línea del rol de pagos, útil para
#             conciliar este asiento con el "Asiento a Pagar" cuando aplique''',
#     )
#
#     @api.depends('quantity', 'amount', 'rate')
#     def _compute_total(self):
#         for line in self:
#             line.total = float(line.quantity) * line.amount * line.rate / 100
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         for values in vals_list:
#             if 'employee_id' not in values or 'contract_id' not in values:
#                 assets_liquidation = self.env['hr.assets.liquidation'].browse(values.get('slip_id'))
#                 values['employee_id'] = values.get('employee_id') or assets_liquidation.employee_id.id
#                 values['contract_id'] = values.get('contract_id') \
#                                         or assets_liquidation.contract_id and assets_liquidation.contract_id.id
#                 if not values['contract_id']:
#                     raise UserError(_('You must set a contract to create an assets liquidation line.'))
#         return super(HrAssetsLiquidationLine, self).create(vals_list)
#
#     def _get_partner_id(self, credit_account):
#         """
#         Get partner_id of slip line to use in account_move_line
#         """
#         # use partner of salary rule or fallback on employee's address
#         register_partner_id = self.salary_rule_id.register_id.partner_id
#         partner_id = register_partner_id.id or self.slip_id.employee_id.address_home_id.id
#         if credit_account:
#             if register_partner_id or self.salary_rule_id.account_credit.internal_type in ('receivable', 'payable'):
#                 return partner_id
#         else:
#             if register_partner_id or self.salary_rule_id.account_debit.internal_type in ('receivable', 'payable'):
#                 return partner_id
#
#         return self.slip_id.employee_id.address_home_id.id
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     # Columns
#     assets_liquidation_line_id = fields.Many2one(
#         'hr.assets.liquidation.line',
#         string='Detalle Rol Pagos',
#         index=True,  # performance
#         help='Vincula los lineas de asiento contable con las lineas de rol de pagos,\n'
#              'Util para cruzar los asientos de rol de pagos con sus facturas a empleados',
#     )
#     assets_liquidation_id = fields.Many2one(
#         string='Rol Pagos',
#         related='assets_liquidation_line_id.slip_id',
#         help='Vincula los lineas de asiento contable con su rol de pagos',
#     )
