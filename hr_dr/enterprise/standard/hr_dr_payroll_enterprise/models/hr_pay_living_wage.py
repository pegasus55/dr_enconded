# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pay_living_wage_id = fields.Many2one('pay.living.wage', string="Pay living wage")


class PayLivingWage(models.Model):
    _inherit = 'pay.living.wage'

    def get_historical(self, year, provision_type, payment_type, employee):
        historical = self.env['hr.historical.provision'].sudo().search([
            ('type', '=', provision_type),
            ('payment_type', '=', payment_type),
            ('fiscal_year', '=', year),
            ('employee_id', '=', employee.id),
        ], limit=1)
        if historical:
            return historical
        else:
            return False

    def get_worked_days(self, employee, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        worked_days = 0
        for payslip in payslip_ids:
            days = payslip.worked_days * payslip.daily_hours / payslip.standard_daily_hours
            if payslip.reduction_of_working_hours:
                days = days * (100 - payslip.percentage_reduction_of_working_hours) / 100
            worked_days += days
        worked_days = round(worked_days, 2)
        return worked_days

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

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('pay_living_wage_id', '=', self.id)])
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

    def action_create_update_lines(self, delete_actual_lines=True):
        if delete_actual_lines:
            line_ids = self.env['pay.living.wage.line'].with_context(
                active_test=False).search([('pay_living_wage_id', '=', self.id)])
            if line_ids:
                line_ids.unlink()

        results = []
        lines = self.env['pay.living.wage.line']
        total_living_wage = self.get_total_living_wage(self.fiscal_year)
        employee_ids = self.env['hr.employee'].with_context(active_test=False).search([
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['affiliate', 'temporary', 'unemployed', 'retired'])
        ])
        for e in employee_ids:
            worked_days = self.get_worked_days(e, self.period_start, self.period_end)
            historical = self.get_historical(self.fiscal_year, "living_wage", "na", e)
            historical_income = 0
            if historical:
                worked_days = worked_days + historical.working_days_previous_fiscal_year
                worked_days = worked_days + historical.working_days_actual_fiscal_year

                historical_income = historical.value_previous_fiscal_year
                historical_income = historical_income + historical.value_actual_fiscal_year

            if worked_days > 0:
                proportional_living_wage = self.get_proportional_living_wage(self.fiscal_year, worked_days)

                wage = self.get_income(e, 'SD-S', self.period_start, self.period_end)
                thirteenth_salary = self.get_income(e, 'SD-D13', self.period_start, self.period_end)
                fourteenth_salary = self.get_income(e, 'SD-D14', self.period_start, self.period_end)
                commissions = self.get_income(e, 'SD-C', self.period_start, self.period_end)
                utility = self.get_utility_by_year_and_employee(self.fiscal_year, e)
                other_income = self.get_income(e, 'SD-BA', self.period_start, self.period_end)
                reserve_fund = self.get_income(e, 'SD-FR', self.period_start, self.period_end)

                all_income = (
                        wage + thirteenth_salary + fourteenth_salary + commissions + utility + other_income +
                        reserve_fund + historical_income)

                if proportional_living_wage > all_income:
                    diff = proportional_living_wage - all_income
                    results.append({
                        'employee_id': e.id,
                        'employee_state': e.state,
                        'wage': wage,
                        'thirteenth_salary': thirteenth_salary,
                        'fourteenth_salary': fourteenth_salary,
                        'commissions': commissions,
                        'utility': utility,
                        'other_income': other_income,
                        'reserve_fund': reserve_fund,
                        'worked_days': worked_days,
                        'total_living_wage': total_living_wage,
                        'proportional_living_wage': proportional_living_wage,
                        'all_income': all_income,
                        'value': diff,
                    })

        for result in results:
            line = lines.new(result)
            lines += line
        self.pay_living_wage_line_ids = lines
        self.state = 'calculated'

    def action_recalculate_based_on_utility(self):
        total = 0
        for line in self.pay_living_wage_line_ids:
            total += line.value

        for line in self.pay_living_wage_line_ids:
            if self.utility < total:
                line.value_to_receive = line.value / total * self.utility
            else:
                line.value_to_receive = line.value
        self.state = 'recalculate'

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Pay living wage request")
        local_context['request'] = _("you have made a pay living wage request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id
        local_context['details'] = _("Pay living wage request for the year {}.").format(self.fiscal_year)
        local_context['commentary'] = self.commentary
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref(
            'hr_dr_payroll_base.pay_living_wage_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_work_entry_contract_enterprise.menu_hr_payroll_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        return local_context

    def mark_as_done(self):
        super(PayLivingWage, self).mark_as_done()
        lines = []
        for detail in self.pay_living_wage_line_ids:
            if detail.value_to_receive > 0:
                lines = self.generate_account_move_line(detail, lines)
        self.create_account_move(lines)

    def generate_payments(self, account_journal):
        for line in self.pay_living_wage_line_ids:
            if line.value_to_receive > 0:
                self.create_payment(line, account_journal)

    def create_account_move(self, lines):
        obj_account_move = self.env['account.move']
        journal_id = self.get_journal()
        if not journal_id:
            raise ValidationError(_("You must set up the accounting journal for the living wage payment "
                                    "in the company settings."))
        ref = _('Living wage for fiscal year %s') % (
            str(self.fiscal_year),
        )
        account_move_data = {
            'ref': ref,
            'journal_id': journal_id.id,
            'date': self.date,
            'move_type': 'entry',
            'company_id': self.env.company.id,
            'line_ids': lines
        }
        if lines:
            obj_account_move.create(account_move_data)

    @api.model
    def get_credit_account(self, mode, detail):
        credit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.living_wage_salary_rule_code
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
            credit_account_id = self.company_id.pay_living_wage_credit_account
            if not credit_account_id:
                raise ValidationError(_("You must configure the account for payroll payment "
                                        "in the company's configuration."))
        return credit_account_id

    @api.model
    def get_debit_account(self, mode, detail):
        debit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.living_wage_salary_rule_code
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
            debit_account_id = self.company_id.pay_living_wage_debit_account
            if not debit_account_id:
                raise ValidationError(_("You must configure the account for living wage payment "
                                        "in the company's configuration."))
        return debit_account_id

    @api.model
    def get_journal(self):
        return self.company_id.pay_living_wage_journal

    @api.model
    def get_account_analytic_account(self, mode, detail):
        analytic_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.living_wage_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.analytic_account_id:
                        analytic_account_id = salary_rule.analytic_account_id
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            analytic_account_id = self.company_id.pay_living_wage_account_analytic_account
        return analytic_account_id

    def generate_account_move_line(self, detail, lines):
        mode = self.company_id.living_wage_accounting_entries_based

        analytic_account_id = self.get_account_analytic_account(mode, detail)
        debit_account_id = self.get_debit_account(mode, detail)
        credit_account_id = self.get_credit_account(mode, detail)

        name = _('Living wage for fiscal year %s for the collaborator %s') % (
            str(self.fiscal_year), detail.employee_id.name,
        )
        base_line = {
            'credit': 0.00,
            'debit': 0.00,
            'date': self.date,
            'name': name,
        }
        lines.append((0, 0, {
            **base_line,
            'account_id': debit_account_id.id,
            'debit': detail.value_to_receive,
            'analytic_distribution': {analytic_account_id.id: 100}
        }))
        lines.append((0, 0, {
            **base_line,
            'account_id': credit_account_id.id,
            'credit': detail.value_to_receive,
            'partner_id': detail.employee_id.address_home_id.id,
            'analytic_distribution': {analytic_account_id.id: 100}
        }))
        return lines

    def create_payment(self, line, account_journal):
        mode = self.company_id.living_wage_accounting_entries_based
        debit_account_id = self.get_debit_account(mode, line)
        if not debit_account_id:
            raise ValidationError(_("You must set up the living wage payment account in the company."))

        obj_payment = self.env['account.payment']
        obj_payment_method_line = self.env['account.payment.method.line']

        journal_id = False
        if account_journal:
            journal_id = account_journal
        else:
            if self.company_id.payroll_mode == "01":
                journal_id = self.company_id.main_account_journal
            else:
                for account_journal in self.company_id.account_journal_ids:
                    if account_journal.bank_account_id.bank_id == line.employee_id.bank_account_id.bank_id:
                        journal_id = account_journal
        if not journal_id:
            raise ValidationError(_("You must configure the accounting journal for payroll payments "
                                    "in the company configuration. Review the collaborator's bank account: %s.") %
                                  line.employee_id.name)

        method_line = obj_payment_method_line.search([
            ('code', '=', 'check'),
            ('payment_type', '=', 'outbound'),
            ('journal_id', '=', journal_id.id),
        ], limit=1)
        bank = line.employee_id.bank_account_id.id if line.employee_id.bank_account_id else None
        if bank:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'transfer'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)
        if not method_line:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'manual'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)

        ref = _('Living wage for fiscal year %s for the collaborator %s') % (
            str(self.fiscal_year), line.employee_id.name,
        )
        account_payment = obj_payment.create({
            'partner_type': 'supplier',
            'is_internal_transfer': False,
            'partner_id': False,
            'employee_id': line.employee_id.address_home_id.id,
            'amount': line.value_to_receive,
            'date': self.date,
            'ref': ref,
            'payment_type': 'outbound',
            'payroll_payment': True,
            'journal_id': journal_id.id,
            'destination_account_id': debit_account_id.id,
            'payment_method_line_id': method_line.id,
            'partner_bank_id': bank,
            'company_id': self.env.company.id,
        })
        account_payment.partner_type = 'supplier'