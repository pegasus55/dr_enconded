# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError

from dateutil.relativedelta import relativedelta


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_utility_id = fields.Many2one('hr.payment.utility', string="Payment utility")


class HrPaymentUtility(models.Model):
    _inherit = 'hr.payment.utility'

    @api.onchange('utility_value', 'percent_employee', 'percent_family')
    def onchange_utility_value(self):
        if self.utility_value:
            precision = self.env['decimal.precision'].precision_get('Payroll')
            self.utility_value_to_distribute = round(
                (self.utility_value * (self.percent_employee + self.percent_family) / 100), precision)

    def calculate_by_contract(self):
        pass
        # TODO Por implementar.
        # results = []
        # lines = self.env['hr.payment.utility.line']
        # total_worked_days = 0.0
        # total_worked_days_x_family_loads = 0.0
        # employees = self.env['hr.employee'].with_context(active_test=False).search([
        #     ('employee_admin', '=', False),
        #     ('company_id', '=', self.company_id.id),
        #     ('state', 'in', ['affiliate', 'temporary', 'unemployed', 'retired'])
        # ])
        #
        # for e in employees:
        #     worked_days = 0
        #     contract_ids = self.env['hr.contract'].get_all_contract(e, self.start_date, self.end_date)
        #     for contract in self.env['hr.contract'].browse(contract_ids):
        #         if contract.receives_profits:
        #             worked_days_this_contract = 0
        #             start_date = self.start_date
        #             for i in range(11):
        #                 start_date = start_date + relativedelta(months=i)
        #                 end_date = self.last_day_of_month(start_date)
        #
        #                 worked_days_this_contract = (
        #                         worked_days_this_contract +
        #                         self._get_worked_days_by_contract(start_date, end_date, contract)
        #                 )
        #             worked_days += worked_days_this_contract
        #
        #     if worked_days > 0:
        #         total_worked_days += worked_days
        #         family_loads = self.get_family_loads_by_employee(e)
        #         total_worked_days_x_family_loads += worked_days * family_loads
        #         results.append(
        #             {
        #                 'employee_id': e.id,
        #                 'employee_state': e.state,
        #                 'worked_days': worked_days,
        #                 'family_loads': family_loads
        #             }
        #         )
        #
        # for external_service in self.external_service_ids:
        #     if external_service.worked_days > 0:
        #         total_worked_days += external_service.worked_days
        #         total_worked_days_x_family_loads = (
        #                 total_worked_days_x_family_loads + external_service.worked_days * external_service.family_loads
        #         )
        #
        # self.total_worked_days = total_worked_days
        # self.total_worked_days_x_family_loads = total_worked_days_x_family_loads
        #
        # for result in results:
        #     employee = self.env['hr.employee'].browse(result.get('employee_id'))
        #     employee_state = result.get('employee_state')
        #     worked_days = result.get('worked_days')
        #     family_loads = result.get('family_loads')
        #     vals = self.get_line_utility(employee, employee_state, worked_days, family_loads)
        #     line = lines.new(vals)
        #     lines += line
        # self.line_ids = lines
        #
        # precision = self.env['decimal.precision'].precision_get('Payroll')
        # for external_service in self.external_service_ids:
        #     utility_value_percent_employee = self.utility_value * self.percent_employee / 100.00
        #     amount_10_percent = round(
        #         utility_value_percent_employee * external_service.worked_days / self.total_worked_days
        #         if self.total_worked_days > 0 else 0, precision)
        #     external_service.amount_10_percent = amount_10_percent
        #
        #     utility_value_percent_family = self.utility_value * self.percent_family / 100.00
        #     amount_5_percent = 0
        #     amount_judicial_withholding = 0
        #     if self.total_worked_days_x_family_loads > 0:
        #         if external_service.family_loads > 0:
        #             amount_5_percent = round(
        #                 utility_value_percent_family * (external_service.family_loads * external_service.worked_days /
        #                                                 self.total_worked_days_x_family_loads), precision)
        #
        #             if external_service.family_loads == external_service.judicial_withholding:
        #                 amount_judicial_withholding = amount_5_percent
        #                 external_service.amount_5_percent = 0
        #                 external_service.amount_judicial_withholding = amount_judicial_withholding
        #             else:
        #                 amount_5_percent_per_family_load = round(amount_5_percent / external_service.family_loads,
        #                                                          precision)
        #                 amount_judicial_withholding = (
        #                         amount_5_percent_per_family_load * external_service.judicial_withholding)
        #
        #                 external_service.amount_5_percent = amount_5_percent
        #                 external_service.amount_judicial_withholding = amount_judicial_withholding
        #         else:
        #             external_service.amount_5_percent = 0
        #             external_service.amount_judicial_withholding = 0
        #     else:
        #         amount_5_percent = round(
        #             (utility_value_percent_family * external_service.worked_days / self.total_worked_days)
        #             if self.total_worked_days > 0 else 0, precision)
        #         external_service.amount_5_percent = amount_5_percent
        #     external_service.total_utility = round(amount_10_percent + amount_5_percent, precision)
        #     external_service.total_receive = round(amount_10_percent + amount_5_percent - amount_judicial_withholding,
        #                                            precision)
        # self.state = 'calculated'
        # return True

    def calculate_by_payroll(self):
        employees = []
        lines = self.env['hr.payment.utility.line']
        total_worked_days = 0.0
        total_worked_days_x_family_loads = 0.0

        employee_ids = self.env['hr.employee'].with_context(active_test=False).search([
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['affiliate', 'temporary', 'unemployed', 'retired'])
        ])
        for employee in employee_ids:
            worked_days = self.get_worked_days(employee, self.start_date, self.end_date)
            historical = self.get_historical(self.fiscal_year, "taxable_income", "na", employee)
            if historical:
                worked_days = worked_days + historical.working_days_previous_fiscal_year
                worked_days = worked_days + historical.working_days_actual_fiscal_year
            worked_days = round(worked_days, 2)

            if worked_days > 0:
                total_worked_days += worked_days
                family_loads = self.get_family_loads_by_employee(employee)
                total_worked_days_x_family_loads = total_worked_days_x_family_loads + worked_days * family_loads
                employees.append(
                    {
                        'employee_id': employee.id,
                        'employee_state': employee.state,
                        'worked_days': worked_days,
                        'family_loads': family_loads
                    }
                )

        for external_service in self.external_service_ids:
            if external_service.worked_days > 0:
                total_worked_days += external_service.worked_days
                total_worked_days_x_family_loads = (
                    total_worked_days_x_family_loads +
                    external_service.worked_days *
                    external_service.family_loads
                )

        self.total_worked_days = total_worked_days
        self.total_worked_days_x_family_loads = total_worked_days_x_family_loads

        for e in employees:
            employee = self.env['hr.employee'].browse(e.get('employee_id'))
            employee_state = e.get('employee_state')
            worked_days = e.get('worked_days')
            family_loads = e.get('family_loads')
            vals = self.get_line_utility(employee, employee_state, worked_days, family_loads)
            line = lines.new(vals)
            lines += line
        self.line_ids = lines

        precision = self.env['decimal.precision'].precision_get('Payroll')
        for external_service in self.external_service_ids:
            utility_value_percent_employee = self.utility_value * self.percent_employee / 100.00
            amount_10_percent = round(
                utility_value_percent_employee * external_service.worked_days / self.total_worked_days
                if self.total_worked_days > 0 else 0, precision)
            external_service.amount_10_percent = amount_10_percent

            utility_value_percent_family = self.utility_value * self.percent_family / 100.00
            amount_5_percent = 0
            amount_judicial_withholding = 0
            if self.total_worked_days_x_family_loads > 0:
                if external_service.family_loads > 0:
                    amount_5_percent = round(
                        utility_value_percent_family * (external_service.family_loads * external_service.worked_days /
                                                        self.total_worked_days_x_family_loads), precision)

                    if external_service.family_loads == external_service.judicial_withholding:
                        amount_judicial_withholding = amount_5_percent
                        external_service.amount_5_percent = 0
                        external_service.amount_judicial_withholding = amount_judicial_withholding
                    else:
                        amount_5_percent_per_family_load = round(amount_5_percent / external_service.family_loads,
                                                                 precision)
                        amount_judicial_withholding = (
                                amount_5_percent_per_family_load * external_service.judicial_withholding)

                        external_service.amount_5_percent = amount_5_percent
                        external_service.amount_judicial_withholding = amount_judicial_withholding
                else:
                    external_service.amount_5_percent = 0
                    external_service.amount_judicial_withholding = 0
            else:
                amount_5_percent = round(
                    (utility_value_percent_family * external_service.worked_days / self.total_worked_days)
                    if self.total_worked_days > 0 else 0, precision)

                external_service.amount_5_percent = amount_5_percent
            external_service.total_utility = round(amount_10_percent + amount_5_percent, precision)
            external_service.total_receive = round(amount_10_percent + amount_5_percent -
                                                   external_service.utility_advance - amount_judicial_withholding,
                                                   precision)
        self.state = 'calculated'
        return True

    def calculate_by_history(self):
        pass

    def get_worked_days(self, employee, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        worked_days = 0

        for payslip in payslip_ids:
            if payslip.contract_id.receives_profits:
                days = payslip.worked_days * payslip.daily_hours / payslip.standard_daily_hours
                if payslip.reduction_of_working_hours:
                    days = days * (100 - payslip.percentage_reduction_of_working_hours) / 100
                worked_days += days
        return worked_days

    def get_line_utility(self, employee, employee_state, worked_days, family_loads):
        utility_value_percent_employee = self.utility_value * self.percent_employee / 100.00
        precision = self.env['decimal.precision'].precision_get('Payroll')
        amount_10_percent = round(
            utility_value_percent_employee * worked_days / self.total_worked_days if self.total_worked_days > 0 else 0,
            precision)

        utility_value_percent_family = self.utility_value * self.percent_family / 100.00
        amount_5_percent = 0
        judicial_withholding_count = 0
        judicial_withholding_amount = 0
        judicial_withholding_ids = []
        if self.total_worked_days_x_family_loads > 0:
            factor_a = family_loads * worked_days

            amount_5_percent = round(
                utility_value_percent_family * (factor_a / self.total_worked_days_x_family_loads), precision)

            if family_loads > 0:
                amount_5_percent_per_family_load = round(amount_5_percent / family_loads, precision)
                amount_5_percent_calculated = amount_5_percent_per_family_load * family_loads
                difference = 0
                if amount_5_percent_calculated > amount_5_percent:
                    difference = amount_5_percent - amount_5_percent_calculated
                elif amount_5_percent > amount_5_percent_calculated:
                    difference = amount_5_percent - amount_5_percent_calculated

                # judicial_withholding_amount = 0
                # for fl in employee.family_load_ids:
                #     if self._family_load_apply_utility(fl) and fl.judicial_withholding_id:
                #         judicial_withholding_count += 1
                #         if judicial_withholding_count == family_loads:
                #             judicial_withholding_obj = {
                #                 'amount': amount_5_percent_per_family_load + difference,
                #                 'family_load_id': fl.id,
                #                 'judicial_withholding_id': fl.judicial_withholding_id.id,
                #             }
                #             judicial_withholding_ids.append((0, 0, judicial_withholding_obj))
                #             judicial_withholding_amount += (amount_5_percent_per_family_load + difference)
                #         else:
                #             judicial_withholding_obj = {
                #                 'amount': amount_5_percent_per_family_load,
                #                 'family_load_id': fl.id,
                #                 'judicial_withholding_id': fl.judicial_withholding_id.id,
                #             }
                #             judicial_withholding_ids.append((0, 0, judicial_withholding_obj))
                #             judicial_withholding_amount += amount_5_percent_per_family_load
                judicial_withholding_amount = 0
                for jw in employee.judicial_withholding_ids:
                    judicial_withholding_count += 1
                    if judicial_withholding_count == family_loads:
                        judicial_withholding_obj = {
                            'amount': amount_5_percent_per_family_load + difference,
                            'judicial_withholding_id': jw.id,
                            'family_load_id': jw.family_load_id.id,
                            'partner_id': jw.partner_id.id,
                        }
                        judicial_withholding_ids.append((0, 0, judicial_withholding_obj))
                        judicial_withholding_amount += (amount_5_percent_per_family_load + difference)
                    else:
                        judicial_withholding_obj = {
                            'amount': amount_5_percent_per_family_load,
                            'judicial_withholding_id': jw.id,
                            'family_load_id': jw.family_load_id.id,
                            'partner_id': jw.partner_id.id,
                        }
                        judicial_withholding_ids.append((0, 0, judicial_withholding_obj))
                        judicial_withholding_amount += amount_5_percent_per_family_load
        else:
            amount_5_percent = round(
                utility_value_percent_family * worked_days / self.total_worked_days
                if self.total_worked_days > 0 else 0, precision)

        total_utility = round(amount_10_percent + amount_5_percent, precision)
        advance_utility = self.get_advance_utility(employee)
        total_receive = round(total_utility - judicial_withholding_amount - advance_utility, precision)
        payment_mode = self.get_payment_mode(employee)

        return {
            'employee_id': employee.id,
            'employee_state': employee_state,
            'worked_days': worked_days,
            'family_loads': family_loads,
            'judicial_withholding': judicial_withholding_count,
            'amount_judicial_withholding': judicial_withholding_amount,
            'amount_10_percent': amount_10_percent,
            'amount_5_percent': amount_5_percent,
            'total_utility': total_utility,
            'payment_mode': payment_mode,
            'total_receive': total_receive,
            'advance_utility': advance_utility,
            'judicial_withholding_ids': judicial_withholding_ids,
        }

    def get_advance_utility(self, employee):
        advance_value = 0
        # args = self.get_args_search(employee)
        # advances = self.env['account.move.line'].search(args)
        # if advances:
        #     advance_value = sum(advances.mapped('debit'))
        return advance_value

    def get_args_search(self, employee):
        args = []
        accounts = self.company_id.mapped('utility_advance_account').mapped('id')
        if not accounts:
            raise UserError(_('You must set up the utility advance account in the company.'))
        args = [
            ('account_id', 'in', tuple(accounts)),
            ('date_maturity', '>=', self.start_date),
            ('date_maturity', '<=', self.date),
            ('partner_id', '=', employee.address_home_id.id)
        ]
        return args

    def get_income(self, employee, code, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')
        value = 0
        mode = self.get_mode_by_code(code)
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if mode == 'by_rules':
                    if line.code in self.get_rule_by_process(code):
                        value += line.total
                elif mode == 'by_categories':
                    if line.category_id.code in self.get_category_by_process(code) and \
                            line.code not in self.get_rule_excluded_by_process(code):
                        value += line.total
        return value

    def _get_d13_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor de décimo tercer salario anual del período actual de utilidad.
        """
        return self.get_income(employee_id, "U-D13", date_from, date_to)

    def _get_d14_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor de décimo cuarto salario anual del período actual de utilidad.
        """
        return self.get_income(employee_id, "U-D14", date_from, date_to)

    def _get_reserve_funds_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor fondo de reserva del período actual de utilidad.
        """
        return self.get_income(employee_id, "U-FR", date_from, date_to)

    def _get_commissions_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor de las comisiones del período actual de utilidad.
        """
        return self.get_income(employee_id, "U-C", date_from, date_to)

    def _get_additional_cash_benefits_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor de los ingresos adicionales en efectivo del período actual de utilidad.
        """
        return self.get_income(employee_id, "U-BAE", date_from, date_to)

    def _get_salary_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor salario por colaborador.
        """
        return self.get_income(employee_id, "U-S", date_from, date_to)

    def _get_bonus_perks_yearly(self, date_from, date_to, employee_id):
        """
        Obtenemos el valor de Sobresueldo / Gratificaciones por colaborador.
        """
        return self.get_income(employee_id, "U-SG", date_from, date_to)

    def generate_payments(self):
        """
        Este método levanta un wizard para registrar los pago de utilidades
        """
        res = self.env.ref('hr_dr_payroll.wizard_payment_utility_form')
        return {
            'name': 'Registrar pago de utilidades',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res.id or False,
            'res_model': 'wizard.payment.utility',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new'
        }

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('payment_utility_id', '=', self.id)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def action_validate(self):
        super(HrPaymentUtility, self).action_validate()
        for line in self.line_ids:
            self.launch_make_move(line)
        self.action_utility_to_personal_expense()
        return True


class HrPaymentUtilityLine(models.Model):
    _inherit = 'hr.payment.utility.line'

    @api.model
    def get_credit_account(self):
        mode = self.payment_utility_id.company_id.utility_accounting_entries_based
        credit_account_id = False
        if mode == '01':
            employee_id = self.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.payment_utility_id.company_id.utility_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_credit:
                        credit_account_id = salary_rule.account_credit
                    else:
                        raise ValidationError(
                            _("You must specify the credit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            credit_account_id = self.payment_utility_id.company_id.payment_utility_credit_account
            if not credit_account_id:
                raise ValidationError(_("You must configure the credit account in the company's configuration."))
        return credit_account_id

    @api.model
    def get_debit_account(self):
        mode = self.payment_utility_id.company_id.utility_accounting_entries_based
        debit_account_id = False
        if mode == '01':
            employee_id = self.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.payment_utility_id.company_id.utility_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_debit:
                        debit_account_id = salary_rule.account_debit
                    else:
                        raise ValidationError(
                            _("You must specify the debit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            debit_account_id = self.payment_utility_id.company_id.payment_utility_debit_account
            if not debit_account_id:
                raise ValidationError(_("You must configure the debit account in the company's configuration."))
        return debit_account_id

    @api.model
    def get_account_analytic_account(self):
        mode = self.payment_utility_id.company_id.utility_accounting_entries_based
        analytic_account_id = False
        if mode == '01':
            employee_id = self.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.payment_utility_id.company_id.utility_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.analytic_account_id:
                        analytic_account_id = salary_rule.analytic_account_id
                    else:
                        raise ValidationError(
                            _("You must specify the analytic account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            analytic_account_id = self.payment_utility_id.company_id.payment_utility_account_analytic_account
            if not analytic_account_id:
                raise ValidationError(_("You must configure the analytic account in the company's configuration."))
        return analytic_account_id

    @api.model
    def get_advance_account(self):
        utility_advance_account = self.payment_utility_id.company_id.utility_advance_account
        if not utility_advance_account:
            raise ValidationError(_("You must configure the advance account in the company's configuration."))
        return utility_advance_account

    @api.model
    def get_judicial_withholding_account(self):
        utility_judicial_withholding_account = self.payment_utility_id.company_id.utility_judicial_withholding_account
        if not utility_judicial_withholding_account:
            raise ValidationError(_("You must configure the judicial withholding account "
                                    "in the company's configuration."))
        return utility_judicial_withholding_account

    def make_move(self):
        if not self.payment_utility_id.company_id.payment_utility_journal:
            raise ValidationError(_('Please set up the utility payment journal in the company.'))
        name = _('Profits for the year {}').format(str(self.payment_utility_id.fiscal_year))
        move_header = {
            'journal_id': self.payment_utility_id.company_id.payment_utility_journal.id,
            'date': self.payment_utility_id.date,
            'ref': name,
            'narration': name + _('. Collaborator: {}').format(self.employee_id.name)
        }
        move_lines = self._compute_move_lines(move_header)
        move = self._create_account_moves(move_header, move_lines)
        self.move_id = move.id

    def _compute_move_lines(self, move_header, division=False):
        line = self
        if division:
            line = division
        line_ids = []
        name = move_header['ref']
        partner = line.employee_id.address_home_id

        # Asiento de retenciones judiciales
        judicial_withholding_account = self.get_judicial_withholding_account()
        if line.amount_judicial_withholding:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': judicial_withholding_account.id,
                'credit': line.amount_judicial_withholding
            }))
        # Asiento de anticipo utilidades
        advance_account_id = self.get_advance_account()
        if line.advance_utility:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': advance_account_id.id,
                'credit': line.advance_utility
            }))
        # Asiento de participación de trabajadores
        credit_account = self.get_credit_account()
        if line.total_receive:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': credit_account.id,
                'credit': line.total_receive,
            }))
        # Asiento de utilidad
        debit_account = self.get_debit_account()
        if line.total_utility > 0.0:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': debit_account.id,
                'debit': line.total_utility
            }))
        return line_ids

    def _create_account_moves(self, move_dict, line_ids):
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return move