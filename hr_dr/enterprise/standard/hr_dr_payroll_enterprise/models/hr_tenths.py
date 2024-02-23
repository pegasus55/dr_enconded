# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class Line(object):
    """Clase auxiliar para la generación de ficheros"""
    def __init__(self, dict):
        self.__dict__ = dict


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    tenth_id = fields.Many2one('hr.tenth', string="Tenth")


class HrTenth(models.Model):
    _inherit = 'hr.tenth'

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

    def get_all_historical(self, year, provision_type, payment_type, employee):
        historical_ids = self.env['hr.historical.provision'].sudo().search([
            ('type', '=', provision_type),
            ('payment_type', '=', payment_type),
            ('fiscal_year', '=', year),
            ('employee_id', '=', employee.id),
        ])
        return historical_ids

    def get_worked_days(self, employee, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from asc')

        worked_days = 0
        for payslip in payslip_ids:
            if not payslip.contract_id.settlement:
                days = payslip.worked_days * payslip.daily_hours / payslip.standard_daily_hours
                if payslip.reduction_of_working_hours:
                    days = days * (100 - payslip.percentage_reduction_of_working_hours) / 100
                worked_days += days
        return worked_days

    def get_income(self, employee, code, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from asc')
        value = 0
        mode = self.get_mode_by_code(code)
        for payslip in payslip_ids:
            if not payslip.contract_id.settlement:
                for line in payslip.line_ids:
                    if mode == 'by_rules':
                        if line.code in self.get_rule_by_process(code):
                            value += line.total
                    elif mode == 'by_categories':
                        if line.category_id.code in self.get_category_by_process(code) and \
                                line.code not in self.get_rule_excluded_by_process(code):
                            value += line.total
        return value

    def get_judicial_withholding(self, employee_id):
        last_contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee_id.id),
            ('state', 'in', ['open', 'close'])],
            order='date_start DESC', limit=1
        )
        judicial_withholding = 0
        if last_contract:
            for input in last_contract.input_ids:
                if input.input_type_id.code in ['PALIMENTOS_1', 'PALIMENTOS_2', 'PALIMENTOS_3', 'PALIMENTOS_4',
                                                'PALIMENTOS_5']:
                    judicial_withholding = judicial_withholding + input.amount
        return judicial_withholding

    def get_advance_amount(self, type_tenth, partner_id, date_from, date_to):
        # TODO Buscar los anticipos por tipo de décimo en el período de cálculo.
        return 0

    def get_judicial_withholding_list(self, employee, type_tenth):
        judicial_withholding_list = []
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from asc')
        code_provisioned = mode_provisioned = code_monthly = mode_monthly = ''
        provision_type = ''
        if type_tenth == 'D14':
            code_provisioned = 'D-DP_D14_A_PALIMENTOS'
            mode_provisioned = self.get_mode_by_code(code_provisioned)
            code_monthly = 'D-D_D14_M_PALIMENTOS'
            mode_monthly = self.get_mode_by_code(code_monthly)
            provision_type = 'R_D14_JW'
        elif type_tenth == 'D13':
            code_provisioned = 'D-DP_D13_A_PALIMENTOS'
            mode_provisioned = self.get_mode_by_code(code_provisioned)
            code_monthly = 'D-D_D13_M_PALIMENTOS'
            mode_monthly = self.get_mode_by_code(code_monthly)
            provision_type = 'R_D13_JW'

        for payslip in payslip_ids:
            if not payslip.contract_id.settlement:
                for line in payslip.line_ids:
                    # D-DP_D14_A_PALIMENTOS y D-DP_D13_A_PALIMENTOS
                    if mode_provisioned == 'by_rules':
                        if line.code in self.get_rule_by_process(code_provisioned):
                            judicial_withholding = {
                                'retained_judicial_withholding': line.total,
                                'discounted_judicial_withholding': 0,
                                'judicial_withholding_id': line.judicial_withholding_id.id,
                                'family_load_id': line.judicial_withholding_id.family_load_id.id,
                                'partner_id': line.judicial_withholding_id.partner_id.id,
                            }
                            judicial_withholding_list.append((0, 0, judicial_withholding))
                    elif mode_provisioned == 'by_categories':
                        if line.category_id.code in self.get_category_by_process(code_provisioned) and \
                                line.code not in self.get_rule_excluded_by_process(code_provisioned):
                            judicial_withholding = {
                                'retained_judicial_withholding': line.total,
                                'discounted_judicial_withholding': 0,
                                'judicial_withholding_id': line.judicial_withholding_id.id,
                                'family_load_id': line.judicial_withholding_id.family_load_id.id,
                                'partner_id': line.judicial_withholding_id.partner_id.id,
                            }
                            judicial_withholding_list.append((0, 0, judicial_withholding))

                    # D-D_D14_M_PALIMENTOS y D-D_D13_M_PALIMENTOS
                    if mode_monthly == 'by_rules':
                        if line.code in self.get_rule_by_process(code_monthly):
                            judicial_withholding = {
                                'retained_judicial_withholding': 0,
                                'discounted_judicial_withholding': line.total,
                                'judicial_withholding_id': line.judicial_withholding_id.id,
                                'family_load_id': line.judicial_withholding_id.family_load_id.id,
                                'partner_id': line.judicial_withholding_id.partner_id.id,
                            }
                            judicial_withholding_list.append((0, 0, judicial_withholding))
                    elif mode_monthly == 'by_categories':
                        if line.category_id.code in self.get_category_by_process(code_monthly) and \
                                line.code not in self.get_rule_excluded_by_process(code_monthly):
                            judicial_withholding = {
                                'retained_judicial_withholding': 0,
                                'discounted_judicial_withholding': line.total,
                                'judicial_withholding_id': line.judicial_withholding_id.id,
                                'family_load_id': line.judicial_withholding_id.family_load_id.id,
                                'partner_id': line.judicial_withholding_id.partner_id.id,
                            }
                            judicial_withholding_list.append((0, 0, judicial_withholding))

        historical_R_D13_A_JW = self.get_all_historical(self.fiscal_year, provision_type, 'accumulated',
                                                        employee)
        for historical in historical_R_D13_A_JW:
            retained_judicial_withholding = (
                    historical.value_previous_fiscal_year +
                    historical.value_actual_fiscal_year)
            judicial_withholding = {
                'origin': 'of_the_historical',
                'retained_judicial_withholding': retained_judicial_withholding,
                'discounted_judicial_withholding': 0,
                # 'judicial_withholding_id': line.judicial_withholding_id.id,
                # 'family_load_id': line.judicial_withholding_id.family_load_id.id,
                'partner_id': historical.partner_id.id,
            }
            judicial_withholding_list.append((0, 0, judicial_withholding))

        historical_R_D13_M_JW = self.get_all_historical(self.fiscal_year, provision_type, 'monthly',
                                                        employee)
        for historical in historical_R_D13_M_JW:
            discounted_judicial_withholding = (
                    historical.value_previous_fiscal_year +
                    historical.value_actual_fiscal_year)
            judicial_withholding = {
                'origin': 'of_the_historical',
                'retained_judicial_withholding': 0,
                'discounted_judicial_withholding': discounted_judicial_withholding,
                # 'judicial_withholding_id': line.judicial_withholding_id.id,
                # 'family_load_id': line.judicial_withholding_id.family_load_id.id,
                'partner_id': historical.partner_id.id,
            }
            judicial_withholding_list.append((0, 0, judicial_withholding))

        return judicial_withholding_list

    def get_judicial_withholding_summary_list(self, employee, type_tenth):
        result = dict()
        judicial_withholding_summary_list = []
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from asc')

        code_provisioned = mode_provisioned = code_monthly = mode_monthly = ''
        provision_type = ''
        if type_tenth == 'D14':
            code_provisioned = 'D-DP_D14_A_PALIMENTOS'
            mode_provisioned = self.get_mode_by_code(code_provisioned)
            code_monthly = 'D-D_D14_M_PALIMENTOS'
            mode_monthly = self.get_mode_by_code(code_monthly)
            provision_type = 'R_D14_JW'
        elif type_tenth == 'D13':
            code_provisioned = 'D-DP_D13_A_PALIMENTOS'
            mode_provisioned = self.get_mode_by_code(code_provisioned)
            code_monthly = 'D-D_D13_M_PALIMENTOS'
            mode_monthly = self.get_mode_by_code(code_monthly)
            provision_type = 'R_D13_JW'

        for payslip in payslip_ids:
            if not payslip.contract_id.settlement:
                for line in payslip.line_ids:
                    # D-DP_D14_A_PALIMENTOS y D-DP_D13_A_PALIMENTOS
                    if mode_provisioned == 'by_rules':
                        if line.code in self.get_rule_by_process(code_provisioned):
                            if line.judicial_withholding_id.partner_id.id in result:
                                if 'retained_judicial_withholding' in result[line.judicial_withholding_id.partner_id.id]:
                                    result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] = result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] + line.total
                                else:
                                    result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] = line.total
                            else:
                                details = {
                                    'retained_judicial_withholding': line.total,
                                    'discounted_judicial_withholding': 0
                                }
                                result[line.judicial_withholding_id.partner_id.id] = details
                    elif mode_provisioned == 'by_categories':
                        if line.category_id.code in self.get_category_by_process(code_provisioned) and \
                                line.code not in self.get_rule_excluded_by_process(code_provisioned):
                            if line.judicial_withholding_id.partner_id.id in result:
                                if 'retained_judicial_withholding' in result[line.judicial_withholding_id.partner_id.id]:
                                    result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] = result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] + line.total
                                else:
                                    result[line.judicial_withholding_id.partner_id.id]['retained_judicial_withholding'] = line.total
                            else:
                                details = {
                                    'retained_judicial_withholding': line.total,
                                    'discounted_judicial_withholding': 0
                                }
                                result[line.judicial_withholding_id.partner_id.id] = details

                    # D-D_D14_M_PALIMENTOS y D-D_D13_M_PALIMENTOS
                    if mode_monthly == 'by_rules':
                        if line.code in self.get_rule_by_process(code_monthly):
                            if line.judicial_withholding_id.partner_id.id in result:
                                if 'discounted_judicial_withholding' in result[line.judicial_withholding_id.partner_id.id]:
                                    result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] = result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] + line.total
                                else:
                                    result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] = line.total
                            else:
                                details = {
                                    'retained_judicial_withholding': 0,
                                    'discounted_judicial_withholding': line.total
                                }
                                result[line.judicial_withholding_id.partner_id.id] = details
                    elif mode_monthly == 'by_categories':
                        if line.category_id.code in self.get_category_by_process(code_monthly) and \
                                line.code not in self.get_rule_excluded_by_process(code_monthly):

                            if line.judicial_withholding_id.partner_id.id in result:
                                if 'discounted_judicial_withholding' in result[line.judicial_withholding_id.partner_id.id]:
                                    result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] = result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] + line.total
                                else:
                                    result[line.judicial_withholding_id.partner_id.id]['discounted_judicial_withholding'] = line.total
                            else:
                                details = {
                                    'retained_judicial_withholding': 0,
                                    'discounted_judicial_withholding': line.total
                                }
                                result[line.judicial_withholding_id.partner_id.id] = details

        historical_R_D13_A_JW = self.get_all_historical(self.fiscal_year, provision_type, 'accumulated',
                                                        employee)
        for historical in historical_R_D13_A_JW:
            retained_judicial_withholding = (
                historical.value_previous_fiscal_year +
                historical.value_actual_fiscal_year
            )
            if historical.partner_id.id in result:
                if 'retained_judicial_withholding' in result[historical.partner_id.id]:
                    result[historical.partner_id.id]['retained_judicial_withholding'] = (
                        result[historical.partner_id.id]['retained_judicial_withholding'] +
                        retained_judicial_withholding
                    )
                else:
                    result[historical.partner_id.id]['retained_judicial_withholding'] = retained_judicial_withholding
            else:
                details = {
                    'retained_judicial_withholding': retained_judicial_withholding,
                    'discounted_judicial_withholding': 0
                }
                result[historical.partner_id.id] = details

        historical_R_D13_M_JW = self.get_all_historical(self.fiscal_year, provision_type, 'monthly',
                                                        employee)
        for historical in historical_R_D13_M_JW:
            discounted_judicial_withholding = (
                historical.value_previous_fiscal_year +
                historical.value_actual_fiscal_year
            )

            if historical.partner_id.id in result:
                if 'discounted_judicial_withholding' in result[historical.partner_id.id]:
                    result[historical.partner_id.id]['discounted_judicial_withholding'] = (
                        result[historical.partner_id.id]['discounted_judicial_withholding'] +
                        discounted_judicial_withholding
                    )
                else:
                    result[historical.partner_id.id]['discounted_judicial_withholding'] = \
                        discounted_judicial_withholding
            else:
                details = {
                    'retained_judicial_withholding': 0,
                    'discounted_judicial_withholding': discounted_judicial_withholding
                }
                result[historical.partner_id.id] = details

        for k in result.keys():
            judicial_withholding_summary = {
                'retained_judicial_withholding': result[k]['retained_judicial_withholding'],
                'discounted_judicial_withholding': result[k]['discounted_judicial_withholding'],
                'partner_id': k,
            }
            judicial_withholding_summary_list.append((0, 0, judicial_withholding_summary))
        return judicial_withholding_summary_list

    def prepare_line_d14(self, e, type_tenth):
        date_to_previous_year = self.date_from + relativedelta(day=31, month=12)
        date_from_actual_year = self.date_to + relativedelta(day=1, month=1)

        # Valores de décimo cuarto sueldo acumulado, mensual, días trabajados
        # e ingresos que generan beneficios sociales obtenidos de las nóminas en función de los
        # códigos de reglas salariales definidos en el modelo reglas salariales por proceso.
        # Esto para el periodo desde el inicio del décimo hasta el fin de año.
        provisioned_value_previous_year = self.get_income(e, 'D-D14A', self.date_from, date_to_previous_year)
        monthly_value_previous_year = self.get_income(e, 'D-D14M', self.date_from, date_to_previous_year)
        previous_year_IGBS = self.get_income(e, 'D-IGBS', self.date_from, date_to_previous_year)
        worked_days_previous_year = self.get_worked_days(e, self.date_from, date_to_previous_year)
        judicial_withholding_provisioned_value_previous_year = self.get_income(
            e, 'D-DP_D14_A_PALIMENTOS', self.date_from, date_to_previous_year)
        judicial_withholding_monthly_value_previous_year = self.get_income(
            e, 'D-D_D14_M_PALIMENTOS', self.date_from, date_to_previous_year)

        # Valores históricos de décimo cuarto sueldo mensual.
        # Se cargan los valores tanto de montos como de días trabajados para el periodo anterior
        # y el periodo actual.
        historical_value_previous_year_monthly = 0
        historical_worked_days_previous_year_monthly = 0
        historical_value_actual_year_monthly = 0
        historical_worked_days_actual_year_monthly = 0
        historical_monthly = self.get_historical(self.fiscal_year, 'D14', 'monthly', e)
        if historical_monthly:
            historical_value_previous_year_monthly = \
                historical_monthly.value_previous_fiscal_year
            historical_worked_days_previous_year_monthly = \
                historical_monthly.working_days_previous_fiscal_year
            historical_value_actual_year_monthly = \
                historical_monthly.value_actual_fiscal_year
            historical_worked_days_actual_year_monthly = \
                historical_monthly.working_days_actual_fiscal_year

        # Valores históricos de décimo cuarto sueldo acumulados.
        # Se cargan los valores tanto de montos como de días trabajados para el periodo anterior
        # y el periodo actual.
        historical_value_previous_year_provisioned = 0
        historical_worked_days_previous_year_provisioned = 0
        historical_value_actual_year_provisioned = 0
        historical_worked_days_actual_year_provisioned = 0
        historical_provisioned = self.get_historical(self.fiscal_year, 'D14', 'accumulated', e)
        if historical_provisioned:
            historical_value_previous_year_provisioned = \
                historical_provisioned.value_previous_fiscal_year
            historical_worked_days_previous_year_provisioned = \
                historical_provisioned.working_days_previous_fiscal_year
            historical_value_actual_year_provisioned = \
                historical_provisioned.value_actual_fiscal_year
            historical_worked_days_actual_year_provisioned = \
                historical_provisioned.working_days_actual_fiscal_year

        # Valores históricos de ingresos que generan beneficios sociales.
        historical_value_previous_year_IGBS = 0
        historical_value_actual_year_IGBS = 0
        historical_IGBS = self.get_historical(self.fiscal_year, 'taxable_income', 'na', e)
        if historical_IGBS:
            historical_value_previous_year_IGBS = historical_IGBS.value_previous_fiscal_year
            historical_value_actual_year_IGBS = historical_IGBS.value_actual_fiscal_year

        # Valores históricos de retenciones de décimo cuarto salario acumulado por retenciones judiciales.
        historical_value_previous_year_R_D14_A_JW = 0
        historical_value_actual_year_R_D14_A_JW = 0
        historical_R_D14_A_JW = self.get_historical(self.fiscal_year, 'R_D14_JW',
                                                    'accumulated', e)
        if historical_R_D14_A_JW:
            historical_value_previous_year_R_D14_A_JW = historical_R_D14_A_JW.value_previous_fiscal_year
            historical_value_actual_year_R_D14_A_JW = historical_R_D14_A_JW.value_actual_fiscal_year

        # Valores históricos de retenciones de décimo cuarto salario mensual por retenciones judiciales.
        historical_value_previous_year_R_D14_M_JW = 0
        historical_value_actual_year_R_D14_M_JW = 0
        historical_R_D14_M_JW = self.get_historical(self.fiscal_year, 'R_D14_JW', 'monthly', e)
        if historical_R_D14_M_JW:
            historical_value_previous_year_R_D14_M_JW = historical_R_D14_M_JW.value_previous_fiscal_year
            historical_value_actual_year_R_D14_M_JW = historical_R_D14_M_JW.value_actual_fiscal_year

        sbu = self.get_unified_basic_salary()
        # Valores no provisionados de décimo cuarto salario en los meses correspondientes al ejercicio
        # fiscal anterior al año de pago del décimo por el incremento del SBU.
        by_increment_sbu = round(
            (provisioned_value_previous_year + monthly_value_previous_year +
             historical_value_previous_year_monthly + historical_value_previous_year_provisioned) *
            sbu.percent_increase / 100, 2
        )

        # Valores de décimo cuarto sueldo acumulado, mensual, días trabajados
        # e ingresos que generan beneficios sociales obtenidos de las nóminas en función de los
        # códigos de reglas salariales definidos en el modelo reglas salariales por proceso.
        # Esto para el periodo desde el inicio del año hasta el fin del décimo.
        provisioned_value_actual_year = self.get_income(e, 'D-D14A', date_from_actual_year, self.date_to)
        monthly_value_actual_year = self.get_income(e, 'D-D14M', date_from_actual_year, self.date_to)
        actual_year_IGBS = self.get_income(e, 'D-IGBS', date_from_actual_year, self.date_to)
        worked_days_actual_year = self.get_worked_days(e, date_from_actual_year, self.date_to)
        judicial_withholding_provisioned_value_actual_year = self.get_income(
            e, 'D-DP_D14_A_PALIMENTOS', date_from_actual_year, self.date_to)
        judicial_withholding_monthly_value_actual_year = self.get_income(
            e, 'D-D_D14_M_PALIMENTOS', date_from_actual_year, self.date_to)

        # Anticipos de décimos realizados al colaborador
        advance_amount = self.get_advance_amount('Fourteenth', e.address_home_id, self.date_from,
                                                 self.date_to)

        taxable_income = (
                previous_year_IGBS + actual_year_IGBS + historical_value_previous_year_IGBS +
                historical_value_actual_year_IGBS
        )
        worked_days = (
                worked_days_previous_year + worked_days_actual_year +
                historical_worked_days_previous_year_monthly + historical_worked_days_actual_year_monthly +
                historical_worked_days_previous_year_provisioned + historical_worked_days_actual_year_provisioned
        )

        provisioned_amount = (
                provisioned_value_previous_year + provisioned_value_actual_year +
                historical_value_previous_year_provisioned + historical_value_actual_year_provisioned
        )
        monthly_amount = (
                monthly_value_previous_year + monthly_value_actual_year +
                historical_value_previous_year_monthly + historical_value_actual_year_monthly
        )

        amount = (
                provisioned_amount +
                monthly_amount +
                by_increment_sbu
        )

        retained_judicial_withholding = (
                judicial_withholding_provisioned_value_previous_year +
                judicial_withholding_provisioned_value_actual_year +
                historical_value_previous_year_R_D14_A_JW +
                historical_value_actual_year_R_D14_A_JW
        )

        discounted_judicial_withholding = (
                judicial_withholding_monthly_value_previous_year + judicial_withholding_monthly_value_actual_year +
                historical_value_previous_year_R_D14_M_JW + historical_value_actual_year_R_D14_M_JW
        )

        judicial_withholding = (
                retained_judicial_withholding +
                discounted_judicial_withholding
        )

        vals = {
            'employee_id': e.id,
            'employee_state': e.state,
            'taxable_income': taxable_income,
            'worked_days': worked_days,
            'amount': amount,
            'provisioned_amount': provisioned_amount,
            'monthly_amount': monthly_amount,
            'by_increment_sbu': by_increment_sbu,
            'judicial_withholding': judicial_withholding,
            'retained_judicial_withholding': retained_judicial_withholding,
            'discounted_judicial_withholding': discounted_judicial_withholding,
            'advance_amount': advance_amount,
            'judicial_withholding_ids': self.get_judicial_withholding_list(e, type_tenth),
            'judicial_withholding_summary_ids': self.get_judicial_withholding_summary_list(e, type_tenth),
        }
        return vals

    def prepare_line_d13(self, e, type_tenth):
        taxable_income = self.get_income(e, 'D-IGBS', self.date_from, self.date_to)
        provisioned_value = self.get_income(e, 'D-D13A', self.date_from, self.date_to)
        monthly_value = self.get_income(e, 'D-D13M', self.date_from, self.date_to)
        advance_amount = self.get_advance_amount('Thirteenth', e.address_home_id, self.date_from,
                                                 self.date_to)
        monthly_judicial_withholding = self.get_income(e, 'D-D_D13_M_PALIMENTOS', self.date_from, self.date_to)
        provisioned_judicial_withholding = self.get_income(e, 'D-DP_D13_A_PALIMENTOS', self.date_from,
                                                           self.date_to)
        worked_days = self.get_worked_days(e, self.date_from, self.date_to)

        historical_value_previous_year_monthly = 0
        historical_worked_days_previous_year_monthly = 0
        historical_value_actual_year_monthly = 0
        historical_worked_days_actual_year_monthly = 0
        historical_monthly = self.get_historical(self.fiscal_year, 'D13', 'monthly', e)
        if historical_monthly:
            historical_value_previous_year_monthly = historical_monthly.value_previous_fiscal_year
            historical_worked_days_previous_year_monthly = historical_monthly.working_days_previous_fiscal_year
            historical_value_actual_year_monthly = historical_monthly.value_actual_fiscal_year
            historical_worked_days_actual_year_monthly = historical_monthly.working_days_actual_fiscal_year

        historical_value_previous_year_provisioned = 0
        historical_worked_days_previous_year_provisioned = 0
        historical_value_actual_year_provisioned = 0
        historical_worked_days_actual_year_provisioned = 0
        historical_provisioned = self.get_historical(self.fiscal_year, 'D13', 'accumulated', e)
        if historical_provisioned:
            historical_value_previous_year_provisioned = historical_provisioned.value_previous_fiscal_year
            historical_worked_days_previous_year_provisioned = historical_provisioned.working_days_previous_fiscal_year
            historical_value_actual_year_provisioned = historical_provisioned.value_actual_fiscal_year
            historical_worked_days_actual_year_provisioned = historical_provisioned.working_days_actual_fiscal_year

        historical_value_previous_year_IGBS = 0
        historical_value_actual_year_IGBS = 0
        historical_IGBS = self.get_historical(self.fiscal_year, 'taxable_income', 'na', e)
        if historical_IGBS:
            historical_value_previous_year_IGBS = historical_IGBS.value_previous_fiscal_year
            historical_value_actual_year_IGBS = historical_IGBS.value_actual_fiscal_year

        # Valores históricos de retenciones de décimo tercer salario acumulado
        # por concepto retenciones judiciales.
        historical_value_previous_year_R_D13_A_JW = 0
        historical_value_actual_year_R_D13_A_JW = 0
        historical_R_D13_A_JW = self.get_historical(self.fiscal_year, 'R_D13_JW',
                                                    'accumulated', e)
        if historical_R_D13_A_JW:
            historical_value_previous_year_R_D13_A_JW = historical_R_D13_A_JW.value_previous_fiscal_year
            historical_value_actual_year_R_D13_A_JW = historical_R_D13_A_JW.value_actual_fiscal_year

        # Valores históricos de retenciones de décimo tercer salario mensualizado
        # por concepto retenciones judiciales.
        historical_value_previous_year_R_D13_M_JW = 0
        historical_value_actual_year_R_D13_M_JW = 0
        historical_R_D13_M_JW = self.get_historical(self.fiscal_year, 'R_D13_JW',
                                                    'monthly', e)
        if historical_R_D13_M_JW:
            historical_value_previous_year_R_D13_M_JW = historical_R_D13_M_JW.value_previous_fiscal_year
            historical_value_actual_year_R_D13_M_JW = historical_R_D13_M_JW.value_actual_fiscal_year

        taxable_income = (
                taxable_income +
                historical_value_previous_year_IGBS +
                historical_value_actual_year_IGBS
        )
        worked_days = (
                worked_days +
                historical_worked_days_previous_year_monthly + historical_worked_days_actual_year_monthly +
                historical_worked_days_previous_year_provisioned + historical_worked_days_actual_year_provisioned
        )

        monthly_value = (
                monthly_value +
                historical_value_previous_year_monthly +
                historical_value_actual_year_monthly
        )

        provisioned_value = (
                provisioned_value +
                historical_value_previous_year_provisioned +
                historical_value_actual_year_provisioned
        )

        amount = (
                monthly_value +
                provisioned_value
        )

        retained_judicial_withholding = (
                provisioned_judicial_withholding +
                historical_value_previous_year_R_D13_A_JW +
                historical_value_actual_year_R_D13_A_JW
        )

        discounted_judicial_withholding = (
                monthly_judicial_withholding +
                historical_value_previous_year_R_D13_M_JW +
                historical_value_actual_year_R_D13_M_JW
        )

        judicial_withholding = (retained_judicial_withholding + discounted_judicial_withholding)

        vals = {
            'employee_id': e.id,
            'employee_state': e.state,
            'taxable_income': taxable_income,
            'worked_days': worked_days,
            'amount': amount,
            'provisioned_amount': provisioned_value,
            'monthly_amount': monthly_value,
            'judicial_withholding': judicial_withholding,
            'retained_judicial_withholding': retained_judicial_withholding,
            'discounted_judicial_withholding': discounted_judicial_withholding,
            'advance_amount': advance_amount,
            'judicial_withholding_ids': self.get_judicial_withholding_list(e, type_tenth),
            'judicial_withholding_summary_ids': self.get_judicial_withholding_summary_list(e, type_tenth),
        }
        return vals

    def prepare_line(self, e, type_tenth):
        if type_tenth == 'D14':
            return self.prepare_line_d14(e, type_tenth)
        elif type_tenth == 'D13':
            return self.prepare_line_d13(e, type_tenth)

    def action_calculate(self):
        newlines = self.env['hr.tenth.line']
        if self.tenth_line_ids:
            self.tenth_line_ids.unlink()
        if self.judicial_withholding_summary_ids:
            self.judicial_withholding_summary_ids.unlink()

        employee_ids = self.env['hr.employee'].search([
            ('employee_admin', '=', False),
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['affiliate', 'temporary'])
        ])
        if self.type_tenth == 'thirteenth_salary':
            for e in employee_ids:
                if not e.contract_id.settlement:
                    vals = self.prepare_line(e, 'D13')
                    new_line = newlines.new(vals)
                    newlines += new_line
                    self.write({
                        'judicial_withholding_summary_ids':
                            self.get_judicial_withholding_summary_list(e, 'D13'),
                    })
        elif self.type_tenth == 'sierra_oriente_fourteenth_salary':
            for e in employee_ids:
                if (not e.contract_id.settlement
                        and e.contract_id.payment_period_fourteenth == 'sierra_oriente_fourteenth_salary'):
                    vals = self.prepare_line(e, 'D14')
                    new_line = newlines.new(vals)
                    newlines += new_line
                    self.write({
                        'judicial_withholding_summary_ids':
                            self.get_judicial_withholding_summary_list(e, 'D14'),
                    })
        elif self.type_tenth == 'costa_fourteenth_salary':
            for e in employee_ids:
                if (not e.contract_id.settlement
                        and e.contract_id.payment_period_fourteenth == 'costa_fourteenth_salary'):
                    vals = self.prepare_line(e, 'D14')
                    new_line = newlines.new(vals)
                    newlines += new_line
                    self.write({
                        'judicial_withholding_summary_ids':
                            self.get_judicial_withholding_summary_list(e, 'D14'),
                    })
        self.tenth_line_ids = newlines
        self.write({
            'state': 'calculated',
        })

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('tenth_id', '=', self.id)])
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

    def getaccountreport(self, type):
        """
        Metodo utilizado en el reporte como filtro por cuenta contable,
        """
        account = []
        if self.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
            if type == 'provisioned':
                if not self.env.user.company_id.xiv_provision_account:
                    raise ValidationError(u'Por favor, configure la cuenta de provisiones de décimos en la compañía.')
                if not self.env.user.company_id.xiv_adjust_admin_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste administrativa en la compañía.')
                if not self.env.user.company_id.xiv_adjust_sales_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de ventas en la compañía.')
                if not self.env.user.company_id.xiv_adjust_direct_account:
                    raise ValidationError(
                        u'Por favor, configure la cuenta de ajuste de mano de obra directa en la compañía.')
                if not self.env.user.company_id.xiv_adjust_indirect_account:
                    raise ValidationError(
                        u'Por favor, configure la cuenta de ajuste de mano de obra indirecta en la compañía.')
                account.append(self.env.user.company_id.xiv_provision_account.id)
                account.append(self.env.user.company_id.xiv_adjust_admin_account.id)
                account.append(self.env.user.company_id.xiv_adjust_sales_account.id)
                account.append(self.env.user.company_id.xiv_adjust_direct_account.id)
                account.append(self.env.user.company_id.xiv_adjust_indirect_account.id)
                return account
            if type == 'advance':
                if not self.env.user.company_id.xiv_advance_account:
                    raise ValidationError(u'Por favor, configure la cuenta de anticipos de décimos en la compañía.')
                account.append(self.env.user.company_id.xiv_advance_account.id)
                return account
        elif self.type_tenth in 'thirteenth_salary':
            if type == 'provisioned':
                if not self.env.user.company_id.xiii_provision_account:
                    raise ValidationError(u'Por favor, configure la cuenta de provisiones de décimos en la compañía.')
                if not self.env.user.company_id.xiii_adjust_admin_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste administrativa en la compañía.')
                if not self.env.user.company_id.xiii_adjust_sales_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de ventas en la compañía.')
                if not self.env.user.company_id.xiii_adjust_direct_account:
                    raise ValidationError(
                        u'Por favor, configure la cuenta de ajuste de mano de obra directa en la compañía.')
                if not self.env.user.company_id.xiii_adjust_indirect_account:
                    raise ValidationError(
                        u'Por favor, configure la cuenta de ajuste de mano de obra indirecta en la compañía.')
                account.append(self.env.user.company_id.xiii_provision_account.id)
                account.append(self.env.user.company_id.xiii_adjust_admin_account.id)
                account.append(self.env.user.company_id.xiii_adjust_sales_account.id)
                account.append(self.env.user.company_id.xiii_adjust_direct_account.id)
                account.append(self.env.user.company_id.xiii_adjust_indirect_account.id)
                return account
            if type == 'advance':
                if not self.env.user.company_id.xiii_advance_account:
                    raise ValidationError(u'Por favor, configure la cuenta de anticipos de décimos en la compañía.')
                account.append(self.env.user.company_id.xiii_advance_account.id)
                return account

    def getjournalreport(self, type):
        """
        Metodo utilizado en el reporte como filtro X diario,
        """
        journal = []
        if self.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary', 'thirteenth_salary'):
            if type == 'provisioned':
                # agregamos los diarios que se utilizaran
                # en la busqueda de los apuntes contables
                if not self.env.user.company_id.journal_wage_id:
                    raise ValidationError(u'Por favor, configure el diario de salarios en la compañía.')
                # Diario de sueldos.
                journal.append(self.env.user.company_id.journal_wage_id.id)
            if type == 'advance':
                self.env.cr.execute("""select distinct journal_id from hr_advance""")
                journals = self.env.cr.dictfetchall()
                for index in range(0, len(journals)):
                    journal.append(journals[index].get('journal_id'))
        return journal

    def action_paid(self):
        """
        Este método levanta un wizard para registrar los pago de provisiones
        """
        res = self.env.ref('hr_dr_payroll.wizard_payment_tenth_form')
        return {
            'name': u'Registrar pago de décimos',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res.id or False,
            'res_model': 'wizard.payment.tenth',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new'
        }

    def action_done(self):
        super(HrTenth, self).action_done()

        if self.type_tenth == 'costa_fourteenth_salary' or self.type_tenth == 'sierra_oriente_fourteenth_salary':
            if not self.company_id.journal_fourteenth_id:
                raise ValidationError(_("Please add the fourteenth settlement journal in the company's payroll setup."))
        elif self.type_tenth == 'thirteenth_salary':
            if not self.company_id.journal_thirteenth_id:
                raise ValidationError(_("Please add the thirteenth settlement journal in the company's payroll setup."))
        employees = []
        for line in self.tenth_line_ids:
            if line.amount_to_receive < 0.0:
                employees.append(line.employee_id.name)
        if employees:
            mistakes = '\n'.join('* ' + employee for employee in employees)
            raise UserError(_('The total to be received from the following collaborators is less than zero, '
                              'review the provisioned values, '
                              'payroll roles or alternatively remove affected collaborators:\n%s') % mistakes)
        self.tenth_line_ids.make_move()
        return True

    def action_cancel(self):
        super(HrTenth, self).action_cancel()

        moves = self.tenth_line_ids.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        return True


class HrTenthLine(models.Model):
    _inherit = 'hr.tenth.line'

    def action_view_account_form_lines(self):
        """
        Accion para mostrar los asientos relacionados a los décimos.
        """
        pass
        # self.ensure_one()
        # #Obtiene las cuentas y diarios para la consulta de décimos.
        # journals = self.tenth_id.getjournalreport('provisioned')
        # accounts = self.tenth_id.getaccountreport('provisioned')
        # action = {
        #     'name': u'Cuentas de décimos',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'account.move.line',
        #     'type': 'ir.actions.act_window',
        #     'domain': [('date', '>=', self.tenth_id.date_from),
        #                ('date', '<=', self.tenth_id.date_to),
        #                ('partner_id','=', self.employee_id.address_home_id.commercial_partner_id.id),
        #                ('account_id','in', tuple(accounts)),
        #                ('journal_id','in', tuple(journals))
        #                ],
        #     'context':{'default_journal_id': tuple(journals),
        #                'default_account_id': tuple(accounts)},
        #     'target': 'current'
        # }
        # return action

    def make_move(self):
        """
        Crea el movimiento contable correspondiente al registro
        """
        for line in self:
            if line.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
                name = _("%s's fourteenth salary") % line.employee_id.name
                journal_id = line.tenth_id.company_id.journal_fourteenth_id.id
            else:
                name = _("%s's thirteenth salary") % line.employee_id.name
                journal_id = line.tenth_id.company_id.journal_thirteenth_id.id
            move_header = {
                'narration': name,
                'ref': name,
                'journal_id': journal_id,
                'date': line.tenth_id.date,
            }
            move_lines = line._compute_move_lines(move_header)
            move = line._create_account_moves(move_header, move_lines)
            line.move_id = move.id

    def _compute_move_lines(self, move_header):
        """
        Computa las líneas de asiento contable
        """
        pass
        # precision = self.env['decimal.precision'].precision_get('Account')
        # partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        # name = move_header['narration']
        # line_ids = []
        # if self.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
        #     if not self.env.user.company_id.xiv_provision_account:
        #         raise ValidationError(u'Configure la cuenta de provisión para el décimo cuarto en la compañía.')
        #     if not self.env.user.company_id.xiv_earnings_attachment_account:
        #         raise ValidationError(u'Configure la cuenta de retenciones judiciales para el décimo cuarto en la compañía.')
        #     if not self.env.user.company_id.xiv_advance_account:
        #         raise ValidationError(u'Configure la cuenta de anticipos para el décimo cuarto en la compañía.')
        #     if not self.env.user.company_id.xiv_payable_account:
        #         raise ValidationError(u'Configure la cuenta de pagos para el décimo cuarto en la compañía.')
        #     provision_account_id = self.env.user.company_id.xiv_provision_account.id
        #     earnings_attachment_account_id = self.env.user.company_id.xiv_earnings_attachment_account.id
        #     advance_account_id = self.env.user.company_id.xiv_advance_account.id
        #     payable_account_id = self.env.user.company_id.xiv_payable_account.id
        # else:
        #     if not self.env.user.company_id.xiii_provision_account:
        #         raise ValidationError(u'Configure la cuenta de provisión para el décimo tercero en la compañía.')
        #     if not self.env.user.company_id.xiii_earnings_attachment_account:
        #         raise ValidationError(u'Configure la cuenta de retenciones judiciales para el décimo tercero en la compañía.')
        #     if not self.env.user.company_id.xiii_advance_account:
        #         raise ValidationError(u'Configure la cuenta de anticipos para el décimo tercero en la compañía.')
        #     if not self.env.user.company_id.xiii_payable_account:
        #         raise ValidationError(u'Configure la cuenta de pagos para el décimo tercero en la compañía.')
        #     provision_account_id = self.env.user.company_id.xiii_provision_account.id
        #     earnings_attachment_account_id = self.env.user.company_id.xiii_earnings_attachment_account.id
        #     advance_account_id = self.env.user.company_id.xiii_advance_account.id
        #     payable_account_id = self.env.user.company_id.xiii_payable_account.id
        # #ASIENTO DE PROVISION
        # if self.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
        #     amount = self.provisioned_amount
        #
        # else:
        #     if self.provisioned_amount == 0:
        #         amount = self.amount - self.monthly_amount
        #     else:
        #         amount = self.provisioned_amount
        # if not float_is_zero(amount, precision_digits=precision):
        #     line_ids.append((0, 0, {
        #         'name': name,
        #         'partner_id': partner_id,
        #         'account_id': provision_account_id,
        #         'debit': amount
        #     }))
        # #ASIENTO DE RETENCION JUDICIAL
        # self.judicial_withholding
        # if not float_is_zero(self.judicial_withholding, precision_digits=precision):
        #     line_ids.append((0, 0, {
        #         'name': name,
        #         'partner_id': partner_id,
        #         'account_id': earnings_attachment_account_id,
        #         'credit': self.judicial_withholding
        #     }))
        # #ASIENTO DE ANTICIPOS
        # #netea la cuenta de anticipos que fueron entregados contra el décimo
        # # self.advance_amount
        # # if not float_is_zero(self.advance_amount, precision_digits=precision):
        # #     line_ids.append((0, 0, {
        # #         'name': name,
        # #         'partner_id': partner_id,
        # #         'account_id': advance_account_id,
        # #         'credit': self.advance_amount
        # #     }))
        # #ASIENTO DEL VALOR A PAGAR
        # self.amount_to_receive
        # if not float_is_zero(self.amount_to_receive, precision_digits=precision):
        #     line_ids.append((0, 0, {
        #         'name': name,
        #         'partner_id': partner_id,
        #         'account_id': payable_account_id,
        #         'credit': self.amount_to_receive
        #     }))
        # #ASIENTO DE DESAJUSTE ENTRE LO PROVISIONADO Y LO COMPUTADO
        # self.difference
        # if not float_is_zero(self.difference, precision_digits=precision):
        #     #Determinamos la cuenta contable, depende del centro de costo de la sup cias
        #     #en base al contrato vigente
        #     if not self.contract_id:
        #         raise ValidationError(u'El colaborador %s no tiene un contrato vigente a la fecha de corte.' % self.employee_id.name)
        #     #Mano de obra directa
        #     hr_contract_type_mdi = self.env.ref('hr_dr_payroll.hr_contract_type_mdi')
        #     #Mano de obra indirecta
        #     hr_contract_type_min = self.env.ref('hr_dr_payroll.hr_contract_type_min')
        #     #Administrativo
        #     hr_contract_type_wrkr = self.env.ref('hr_dr_payroll.hr_contract_type_wrkr')
        #     #Ventas
        #     hr_contract_type_sub = self.env.ref('hr_dr_payroll.hr_contract_type_sub')
        #     contract_type = self.contract_id.type_id
        #     if not contract_type:
        #         raise ValidationError(u'El contrato %s no tiene un tipo de contrato.' % self.contract_id.name)
        #     account_id = None
        #     if self.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
        #
        #         # De forma temporal, cualquier tipo de contrato que no esté contemplado aquí, utilizará la cuenta de ajuste administrativa
        #         account_id = self.env.user.company_id.xiv_adjust_admin_account.id
        #
        #         if contract_type == hr_contract_type_mdi:
        #             account_id = self.env.user.company_id.xiv_adjust_direct_account.id
        #         elif contract_type == hr_contract_type_min:
        #             account_id = self.env.user.company_id.xiv_adjust_indirect_account.id
        #         elif contract_type == hr_contract_type_wrkr:
        #             account_id = self.env.user.company_id.xiv_adjust_admin_account.id
        #         elif contract_type == hr_contract_type_sub:
        #             account_id = self.env.user.company_id.xiv_adjust_sales_account.id
        #     else:
        #
        #         # De forma temporal, cualquier tipo de contrato que no esté contemplado aquí, utilizará la cuenta de ajuste administrativa
        #         account_id = self.env.user.company_id.xiii_adjust_admin_account.id
        #
        #         if contract_type == hr_contract_type_mdi:
        #             account_id = self.env.user.company_id.xiii_adjust_direct_account.id
        #         elif contract_type == hr_contract_type_min:
        #             account_id = self.env.user.company_id.xiii_adjust_indirect_account.id
        #         elif contract_type == hr_contract_type_wrkr:
        #             account_id = self.env.user.company_id.xiii_adjust_admin_account.id
        #         elif contract_type == hr_contract_type_sub:
        #             account_id = self.env.user.company_id.xiii_adjust_sales_account.id
        #     line_ids.append((0, 0, {
        #         'name': name,
        #         'partner_id': partner_id,
        #         'account_id': account_id,
        #         'debit': self.difference > 0.0 and self.difference or 0.0,
        #         'credit': self.difference < 0.0 and -self.difference or 0.0,
        #         'analytic_account_id': self.contract_id.analytic_account_id.id
        #     }))
        # return line_ids

    def _create_account_moves(self, move_dict, line_ids):
        """
        Método auxiliar para crear el asiento contable.
        """
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        # move.post()
        return move