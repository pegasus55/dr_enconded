# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from datetime import datetime
import time

# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"
#
#     retired_employee_id = fields.Many2one('retired.employee.salary', 'Salario jubilado')
#     retired_employee_d13_id = fields.Many2one('retired.employee.thirteenth.salary', 'Decimotercer salario jubilado')
#     retired_employee_d14_id = fields.Many2one('retired.employee.fourteenth.salary', 'Decimocuarto salario jubilado')


class PayLivingWage(models.Model):
    _inherit = 'pay.living.wage'

    def get_income(self, employee, date_from, date_to):
        result = dict()
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        wage = 0
        reserve_fund = 0
        thirteenth_salary = 0
        fourteenth_salary = 0
        commissions = 0
        other_income = 0

        for payslip in payslip_ids:
            for line in payslip.line_ids:

                if line.code == 'BASIC' or line.code == 'VACACIONES_TOMADAS' or line.code == 'RETROACTIVO':
                    wage += line.total

                elif line.code == 'PROV_FOND_RESERV_MENSUAL':
                    reserve_fund += line.total

                elif line.code == 'PROV_DTERCERO_MENSUAL':
                    thirteenth_salary += line.total

                elif line.code == 'PROV_DCUARTO_MENSUAL':
                    fourteenth_salary += line.total

                elif line.code == 'AJUSTE_DCUARTO':
                    fourteenth_salary += line.total

                elif line.code == 'ALIMENTACION' or line.code == 'SUBSIDIO_GUARDERIA' \
                        or line.code == 'TRANSPORTE' or line.code == 'REEMPLAZOS' \
                        or line.code == 'OTROS_INGRESOS_APORTABLES' or line.code == 'BONIFICACIONES_POR_CUMPLIMIENTO' \
                        or line.code == 'BONO_VARIABLE_RENTABILIDAD':
                    other_income += line.total

                elif line.code == 'BONO_DE_VENTAS' or line.code == 'COMISIONES':
                    commissions += line.total

            PROV_DTERCERO = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_DTERCERO_MENSUAL')
            if not any(PROV_DTERCERO):
                thirteenth_salary += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_DTERCERO_ACUMULADO').mapped('total'))

            PROV_DCUARTO = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_DCUARTO_MENSUAL')
            if not any(PROV_DCUARTO):
                fourteenth_salary += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_DCUARTO_ACUMULADO').mapped('total'))

            PROV_FOND_RESERV = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_FOND_RESERV_MENSUAL')
            if not any(PROV_FOND_RESERV):
                reserve_fund += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_FOND_RESERV_ACUMULADO').mapped('total'))

        result['W'] = wage
        result['RF'] = reserve_fund
        result['D13'] = thirteenth_salary
        result['D14'] = fourteenth_salary
        result['C'] = commissions
        result['OI'] = other_income
        return result

    def action_create_update_lines(self, delete_actual_lines=True):
        if delete_actual_lines:
            line_ids = self.env['pay.living.wage.line'].with_context(active_test=False).search([
                ('pay_living_wage_id', '=', self.id),
            ])
            if line_ids:
                line_ids.unlink()

        results = []
        lines = self.env['pay.living.wage.line']

        total_living_wage = self.get_total_living_wage(self.fiscal_year)

        all_employees = self.env['hr.employee'].with_context(active_test=False).search(
            [('state', 'in', ['affiliate', 'temporary', 'unemployed', 'retired']),
             ('employee_admin', '=', False)])
        for e in all_employees:
            worked_days = 0
            contract_ids = self.env['hr.contract'].get_all_contract(e, self.period_start, self.period_end)
            for contract in self.env['hr.contract'].browse(contract_ids):
                start_date = contract.date_start
                if self.period_start > contract.date_start:
                    start_date = self.period_start

                end_date = self.period_end
                if contract.date_end and contract.date_end < end_date:
                    end_date = contract.date_end

                worked_days_this_contract = (end_date - start_date).days + 1
                if worked_days_this_contract > 360:
                    worked_days_this_contract = 360

                if contract.resource_calendar_id.hours_per_day < 8:
                    precision = self.env['decimal.precision'].precision_get('Payroll')
                    worked_days_this_contract = round(
                        (360 * worked_days_this_contract * contract.resource_calendar_id.hours_per_day / 2880),
                        precision)

                worked_days += worked_days_this_contract

            if worked_days > 360:
                worked_days = 360

            if worked_days > 0:
                proportional_living_wage = self.get_proportional_living_wage(self.fiscal_year, worked_days)

                utility = self.get_utility_by_year_and_employee(self.fiscal_year, e)

                wage = 0
                reserve_fund = 0
                thirteenth_salary = 0
                fourteenth_salary = 0
                commissions = 0
                other_income = 0

                incomes = self.get_income(e, self.period_start, self.period_end)
                for k in incomes.keys():
                    if k == 'W':
                        wage = incomes.get(k, 0)
                    if k == 'RF':
                        reserve_fund = incomes.get(k, 0)
                    if k == 'D13':
                        thirteenth_salary = incomes.get(k, 0)
                    if k == 'D14':
                        fourteenth_salary = incomes.get(k, 0)
                    if k == 'C':
                        commissions = incomes.get(k, 0)
                    if k == 'OI':
                        other_income = incomes.get(k, 0)

                all_income = utility + wage + reserve_fund + thirteenth_salary + fourteenth_salary + commissions \
                             + other_income

                if proportional_living_wage > all_income:
                    diff = proportional_living_wage - all_income

                    results.append({
                        'employee_id': e.id,
                        'employee_state': e.state,
                        'utility': utility,
                        'wage': wage,
                        'reserve_fund': reserve_fund,
                        'thirteenth_salary': thirteenth_salary,
                        'fourteenth_salary': fourteenth_salary,
                        'commissions': commissions,
                        'other_income': other_income,
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
        return True