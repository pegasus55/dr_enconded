# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from odoo.tools import float_is_zero, float_compare, float_round
import calendar


class PersonalExpense(models.Model):
    _inherit = 'hr.personal.expense'

    def compute_tax(self):
        for rec in self:
            if rec.employee_id.id:
                tax_table = rec.rent_tax_table_id
                last_contract = self._get_last_contract(rec.employee_id)
                payslip_ids = self._get_payslips(rec.employee_id, tax_table)
                last_payslip = payslip_ids[-1] if payslip_ids else False
                remaining_months = self._get_remaining_months(tax_table, last_contract, last_payslip)
                vals = self._get_values_from_payslips(payslip_ids)
                vals = self._project_remaining_months(last_contract, remaining_months, vals, tax_table)

                rec.wage = vals['wage']
                rec.other_taxable_income = vals['other_taxable_income']
                rec.IESS_this_employer = vals['personal_contribution']

                total_income = rec.wage + rec.other_taxable_income + rec.utility + rec.income_other_employers
                rec.total_income = total_income
                rec.tax_base = total_income - (rec.IESS_this_employer + rec.IESS_other_employer) - rec.total_deduction
                rec.tax_caused = self.get_tax_caused(rec.tax_base, tax_table)








                ### PRIMER CÁLCULO ###
                rec.profit_tax_first_calculation = 0.0
                rec.first_expenses_discount = 0.0
                rec.first_rent_tax = 0.0

                # rec.discount_percent = rec._get_discount_percent()
                rec.taxable_income = self._get_taxed_income(include_assumed_tax=False, include_other_employers=False)
                # Primera base imponible gravada
                rec.tax_base_first_calculation = rec._get_tax_base(first=True)

                if rec.calculation_method != 'withhold_employee':
                    # Primer impuesto a la renta causado
                    rec.profit_tax_first_calculation = self.get_profit_tax_caused(rec.tax_base_first_calculation, tax_table)
                    # Primera rebaja por gastos personales
                    #rec.first_expenses_discount = rec._get_expenses() * rec.discount_percent
                    # Primer impuesto a la renta
                    rec.first_rent_tax = max(0, rec.profit_tax_first_calculation - rec.first_expenses_discount)

                if rec.calculation_method == 'withhold_employee':
                    rec.profit_tax_employer = 0.0
                elif rec.calculation_method == 'assumption_total':
                    rec.profit_tax_employer = rec.first_rent_tax
                elif rec.calculation_method == 'assumption_partial':
                    rec.profit_tax_employer = rec.first_rent_tax / 2

                ### SEGUNDO CÁLCULO ###
                #rec.discount_percent = rec._get_discount_percent(include_assumed_tax=True)

                # Ingresos gravados con este empleador: Sueldos y salarios + Sobresueldos, comisiones, bonos
                # y otros ingresos gravados + Utilidades + Impuesto a la renta asumido por este empleador
                rec.taxable_income = self._get_taxed_income(include_assumed_tax=True, include_other_employers=False)
                # Segunda base imponible gravada
                rec.tax_base = rec._get_tax_base()
                # Segundo impuesto a la renta causado
                rec.profit_tax = self.get_profit_tax_caused(rec.tax_base, tax_table)

                # Segunda rebaja por gastos personales
                #rec.expenses_discount = rec._get_expenses() * rec.discount_percent
                # Segundo impuesto a la renta
                rec.rent_tax = max(0, rec.profit_tax - rec.expenses_discount)

                if rec.calculation_method == 'withhold_employee':
                    rec.profit_tax_employer = 0.0
                elif rec.calculation_method == 'assumption_total':
                    rec.profit_tax_employer = rec.first_rent_tax
                elif rec.calculation_method == 'assumption_partial':
                    rec.profit_tax_employer = rec.first_rent_tax / 2

                # Valor del impuesto asumido por este empleador
                rec.amount_this_employer = rec.profit_tax_employer

                # Segundo valor del impuesto asumido por este empleador
                second_amount_this_employer = 0.0
                if rec.calculation_method == 'assumption_total':
                    second_amount_this_employer = rec.rent_tax - rec.amount_this_employer
                rec.second_amount_this_employer = second_amount_this_employer
                rec.second_amount_this_employer_posted = vals['assumed_tax_2']

                # Valor del impuesto retenido al trabajador por este empleador
                rec.amount_detained_employee = max(0, rec.rent_tax - rec.amount_other_employer - rec.amount_this_employer
                                               - rec.second_amount_this_employer)
                rec.amount_this_employer_posted = vals['assumed_tax']
                rec.amount_detained_employee_posted = vals['employee_tax'] - rec.amount_this_employer_posted \
                                                      - rec.second_amount_this_employer_posted
                # Valores mensuales a descontar
                rec.amount_this_employer_discount = 0
                rec.second_amount_this_employer_discount = 0
                rec.amount_detained_employee_discount = 0
                if remaining_months > 0:
                    rec.amount_this_employer_discount = max(
                        0, (rec.amount_this_employer - rec.amount_this_employer_posted) / remaining_months)
                    rec.second_amount_this_employer_discount = max(
                        0, (rec.second_amount_this_employer - rec.second_amount_this_employer_posted) / remaining_months)
                    rec.amount_detained_employee_discount = max(
                        0, (rec.amount_detained_employee - rec.amount_detained_employee_posted) / remaining_months)

                # computamos valores adicionales POSTEADOS a ser utilizados en el computo del RDEP
                # INGRESOS GRAVADOS CON ESTE EMPLEADOR (incluye la primera asumcion del I.R. pero no la segunda)
                rec.taxable_income_posted = rec._get_taxed_income(
                    include_assumed_tax=True, include_other_employers=False)

                # No se puede usar la variable tax_base pues esta representa el valor calculado que puede
                # variar del aplicado debido por ejemplo a impuestos a la renta asumidos en principio
                # a pesar que despues cambie el valor final debido a renuncia del colaborador y ajuste
                # de la ficha de gastos personales
                rec.tax_base_posted = (
                        rec.taxable_income_posted
                        + rec.income_other_employers
                        - rec.IESS_this_employer - rec.IESS_other_employer
                        - rec.total_deduction
                )
            else:
                rec.wage = 0
                rec.other_taxable_income = 0
                rec.IESS_this_employer = 0
                rec.profit_tax_first_calculation = 0
                rec.first_expenses_discount = 0
                rec.first_rent_tax = 0
                #rec.discount_percent = 0
                rec.taxable_income = 0
                rec.tax_base_first_calculation = 0
                rec.tax_base = 0
                rec.profit_tax = 0
                rec.expenses_discount = 0
                rec.rent_tax = 0
                rec.amount_this_employer = 0
                rec.amount_this_employer_posted = 0
                rec.second_amount_this_employer = 0
                rec.second_amount_this_employer_posted = 0
                rec.amount_this_employer_discount = 0
                rec.second_amount_this_employer_discount = 0
                rec.amount_detained_employee = 0
                rec.amount_detained_employee_posted = 0
                rec.amount_detained_employee_discount = 0

    def _get_last_contract(self, employee_id):
        """Dado un colaborador obtiene el último contrato asociado a él."""
        last_contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee_id.id),
            ('state', 'in', ['open', 'close'])],
            order='date_start DESC', limit=1
        )
        if not last_contract:
            raise UserError(_('There is no active contract for this period.'))
        elif not last_contract.date_start:
            raise UserError(_('Please enter the contract start date to continue.'))
        return last_contract

    def _get_remaining_months(self, tax_table, last_contract, last_payslip=False):
        """Calcula los meses restantes para proyectar el impuesto a la renta."""
        remaining_months = 0
        if last_payslip:
            # Caso 1: Tenemos nóminas, proyectamos con los meses siguientes a la última nómina validada hasta
            # llegar a diciembre.
            date_from = last_payslip.date_from
            # next_month = date_from.month + 1
            # if next_month > 12:
            #     next_month = 12
            # date_start = date_from.replace(month=next_month, day=1)
            # end_date = date_from.replace(month=next_month, day=calendar.mdays[next_month])
            remaining_months = 12 - date_from.month
        else:
            # Caso 2: No tenemos nóminas, tenemos que proyectar con el contrato, el primer paso es ubicar
            # el contrato que esté vigente en el año analizado, ver su mes de inicio y partiendo de ese mes
            # proyectar hasta diciembre.
            if tax_table:
                remaining_months = 12
                # En caso de que el contrato comenzó en el año que se quiere proyectar
                # debemos partir del mes en que inició.
                if int(last_contract.date_start.year) == self.rent_tax_table_id.fiscal_year:
                    remaining_months = 13 - int(last_contract.date_start.month)
        return remaining_months

    def _get_payslips(self, employee_id, tax_table):
        return self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', tax_table.date_from),
            ('date_to', '<=', tax_table.date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

    def _get_values_from_payslips(self, payslip_ids):
        vals = {
            'wage': 0.0,
            'other_taxable_income': 0.0,
            'personal_contribution': 0.0,
        }
        for payslip in payslip_ids:
            for line in payslip.line_ids:

                code = 'IT-S'
                mode = self.get_mode_by_code(code)
                if mode == 'by_rules':
                    if line.code in self.get_rule_by_process(code):
                        vals['wage'] += line.total
                elif mode == 'by_categories':
                    if line.category_id.code in self.get_category_by_process(code) and \
                            line.code not in self.get_rule_excluded_by_process(code):
                        vals['wage'] += line.total

                code = 'IT-IESS-P'
                mode = self.get_mode_by_code(code)
                if mode == 'by_rules':
                    if line.code in self.get_rule_by_process(code):
                        vals['personal_contribution'] += line.total
                elif mode == 'by_categories':
                    if line.category_id.code in self.get_category_by_process(code) and \
                            line.code not in self.get_rule_excluded_by_process(code):
                        vals['personal_contribution'] += line.total

                code = 'IT-IGBS'
                mode = self.get_mode_by_code(code)
                if mode == 'by_rules':
                    if line.code in self.get_rule_by_process(code):
                        vals['other_taxable_income'] += line.total
                elif mode == 'by_categories':
                    if line.category_id.code in self.get_category_by_process(code) and \
                            line.code not in self.get_rule_excluded_by_process(code):
                        vals['other_taxable_income'] += line.total

        return vals

    def _project_remaining_months(self, last_contract, remaining_months, vals, tax_table):
        """Proyecta el cálculo de ingresos para los meses restantes del año."""
        if last_contract:
            monthly_wage = last_contract.wage
            monthly_taxable_income = 0.0

            for income in last_contract.input_ids:
                if income.rule_id.category_id.code in ('INGRESOS'):
                    monthly_taxable_income += income.amount

            predicted_wage = monthly_wage * remaining_months
            predicted_taxable_income = monthly_taxable_income * remaining_months

            vals['wage'] += predicted_wage
            vals['other_taxable_income'] += predicted_taxable_income
            vals['personal_contribution'] += (predicted_wage + predicted_taxable_income) * 0.0945
        return vals

    def _get_taxed_income(self, include_assumed_tax=False, include_other_employers=True):
        self.ensure_one()
        taxed_income = sum([self.wage, self.other_taxable_income, self.utility])
        taxed_income = (taxed_income + self.profit_tax_employer) if include_assumed_tax else taxed_income
        taxed_income = (taxed_income + self.income_other_employers) if include_other_employers else taxed_income
        return taxed_income

    def _get_discount_percent(self, include_assumed_tax=False):
        """Calcula el porciento de descuento al impuesto en base al ingreso bruto."""
        self.ensure_one()
        tax_table = self.rent_tax_table_id
        taxed_income = self._get_taxed_income(include_assumed_tax)
        # exempt_income = self._get_exempt_income()
        # net_income = taxed_income + exempt_income
        # if net_income <= tax_table.bf_total_value:
        #     return 0.1  # 10%
        # else:
        #     return 0.2  # 20%

        return 0.2

    def _get_tax_base(self, first=False):
        """
        Calcula la base imponible.
        [base imponible] = [ingresos gravados] - [costos y gastos deducibles(iess)] - [rebaja 3ra edad o discapacidad]
        """
        self.ensure_one()

        if self.calculation_method == 'withhold_employee':
            method = 1
        elif self.calculation_method == 'assumption_total':
            method = 2
        elif self.calculation_method == 'assumption_partial':
            method = 3

        tax_base = 0.0
        # Primera base imponible gravada
        if first and self.calculation_method != 'withhold_employee':
            taxed_income = self._get_taxed_income()
            iess = self.IESS_this_employer + self.IESS_other_employer
            tax_base = taxed_income - iess - self.total_deduction

        # Segunda base imponible gravada
        if not first:
            taxed_income = self._get_taxed_income(include_assumed_tax=True)
            iess = self.IESS_this_employer + self.IESS_other_employer
            tax_base = taxed_income - iess - self.total_deduction

        return max(0, tax_base)

    def _get_expenses(self):
        self.ensure_one()
        # expenses = sum([self.living_place, self.education, self.feeding, self.clothing, self.sightseeing, self.health])
        expenses = 0
        tax_table = self.rent_tax_table_id
        # Máximo deducible: (Ingresos gravados con este empleador + Ingresos gravados con otros empleadores) * 50%
        # Si el resultado de este valor supera el 1.3 veces de la fracción básica de la tabla del impuesto a la
        # renta para el período seleccionado en lugar de ese valor va el 1.3 veces de la fracción básica de la tabla
        # del impuesto a la renta para el período seleccionado

        # Verificando contra el primer límite

        # max_deductible = (self.taxable_income + self.income_other_employers) * tax_table.maximum_deductible_percentage
        # max_deductible = (self.taxable_income + self.income_other_employers) * 1
        # max_deductible = min(max_deductible, tax_table.maximum_deductible_amount)
        # expenses = min(expenses, max_deductible)

        # Verificando contra el segundo límite
        # expenses = min(expenses, tax_table.bfb_total_value)
        # self.max_deductible = max_deductible
        return expenses

    def get_sbu_by_year(self, year):
        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if sbu:
            return sbu.value
        else:
            return 0

    # @api.depends('employee_id', 'rent_tax_table_id', 'utility', 'calculation_method', 'income_other_employers',
    #              'IESS_other_employer', 'living_place', 'education', 'feeding', 'clothing', 'health',
    #              'amount_other_employer')
    def _compute_amount(self):
        self.compute_tax()
        return True

    def get_tax_caused(self, tax_base, rent_tax_table):
        """
        Obtiene el valor del impuesto a la renta causado buscando el valor de la base imponible en la tabla de
        impuesto a la renta.

        :param tax_base: Valor de la base imponible
        :param rent_tax_table: Tabla de impuesto a la renta a utililzar
        :return: Valor del impuesto a la renta causado
        """
        tax_caused = 0.0
        for line in rent_tax_table.rate_ids:
            if line.basic_fraction <= tax_base and (line.excess_until >= tax_base or line.excess_until == 0.0):
                tax_caused = (((tax_base - line.basic_fraction) * line.excess_fraction_tax / 100)
                              + line.basic_fraction_tax)
                break
        return tax_caused

    def get_profit_tax_caused(self, tax_base, rent_tax_table):
        """
        Obtiene el valor del impuesto a la renta causado buscando el valor de la base imponible en la tabla de
        impuesto a la renta.

        :param tax_base: Valor de la base imponible
        :param rent_tax_table: Tabla de impuesto a la renta a utililzar
        :return: Valor del impuesto a la renta causado
        """
        profit_tax_caused = 0.0
        for line in rent_tax_table.rate_ids:
            if line.basic_fraction <= tax_base and (line.excess_until >= tax_base or line.excess_until == 0.0):
                profit_tax_caused = ((tax_base - line.basic_fraction) * line.excess_fraction_tax / 100) \
                                   + line.basic_fraction_tax
                break
        return profit_tax_caused