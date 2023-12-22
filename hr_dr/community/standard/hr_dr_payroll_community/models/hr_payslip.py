# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round
from datetime import date, datetime, time, timedelta
from xlwt import Workbook, easyxf, Formula
import xlwt
# from odoo.addons.general_reports.tools.xls_tools import get_style, GET_LETTER, cm2width
# from odoo.addons.l10n_ec.models.auxiliar_functions import convert_datetime_to_ECT

#from general_reports.tools.xls_tools import get_style, cm2width
# from l10n_ec_niif.models.auxiliar_functions import convert_datetime_to_ECT

from dateutil import relativedelta
import odoo.addons.decimal_precision as dp
import base64, calendar, io, logging, math, pytz, re, time

import odoo
import odoo.release
import odoo.sql_db
import odoo.tools
import threading
from datetime import datetime

_logger = logging.getLogger(__name__)

def cm2width(cm):
    ref = 65535/50.12
    return int(round(cm*ref))

def get_style(bold=False, font_name='Calibri', height=12, font_color='black',
              rotation=0, align='center', vertical='center', wrap=True,
              border=True, color=None, format=None):
    str_style = ''
    if bold or font_name or height or font_color:
        str_style += 'font: '
        str_style += bold and ('bold %s, '%bold) or ''
        str_style += font_name and ('name %s, '%font_name) or ''
        str_style += height and ('height %s, '%(height*20)) or ''
        str_style += font_color and ('color %s, '%font_color) or ''
        str_style = str_style[:-2] + ';'
    if rotation or align or vertical or wrap:
        str_style += 'alignment: '
        str_style += rotation and ('rotation %s, '%rotation) or ''
        str_style += align and ('horizontal %s, '%align) or ''
        str_style += vertical and ('vertical %s, '%vertical) or ''
        str_style += wrap and ('wrap %s, '%wrap) or ''
        str_style = str_style[:-2] + ';'
    str_style += border and 'border: left thin, right thin, top thin, bottom thin;' or ''
    str_style += color and 'pattern: pattern solid, fore_colour %s;'%color or ''
    return easyxf(str_style, num_format_str = format)

def convert_datetime_to_ECT(date_as_string):
    # Convierte un string de datetime de Odoo a la hora del SRI (GMT -5)
    if not date_as_string:
        return ''  # si no se pasa la fecha retornamos una cadena vacia
    # Odoo guarda las fechas en UTC, pero se requiere imprimir en GTM -5
    # Creamos nuestro propio metodo para la conversion a GMT -5
    local = pytz.timezone('America/Guayaquil')  # la zona horaria del SRI es GMT -5
    utc = pytz.utc
    try:
        naive = datetime.strptime(date_as_string, '%Y-%m-%d %H:%M:%S.%f')
    except:
        try:
            naive = datetime.strptime(date_as_string, '%Y-%m-%d %H:%M:%S')
        except:
            naive = datetime.strptime(date_as_string, '%Y-%m-%d')
            naive += timedelta(hours=12)
    utc_dt = utc.localize(naive, is_dst=None)
    auth_date_in_local = utc_dt.astimezone(local)
    return str(auth_date_in_local)

STYLES = {
    'title': get_style(
        bold=True, font_name='Calibri', height=12, font_color=None,
        rotation=0, align=None, vertical='center', wrap=False,
        border=False, color=None, format=None
    ),
    'header': get_style(
        bold=True, font_name='Calibri', height=8, font_color=None,
        rotation=0, align='center', vertical='center', wrap=False,
        border=True, color=None, format=None
    ),
    'header_white': get_style(
        bold=False, font_name='Calibri', height=8, font_color='white',
        rotation=0, align='center', vertical='center', wrap=False,
        border=False, color=None, format=None
    ),
    'text_table': get_style(
        bold=False, font_name='Calibri', height=8, font_color=None,
        rotation=0, align=None, vertical='center', wrap=False,
        border=True, color=None, format=None
    ),
    'date_table': get_style(
        bold=False, font_name='Calibri', height=8, font_color=None,
        rotation=0, align=None, vertical='center', wrap=False,
        border=True, color=None, format='dd/mm/yyyy'
    )
}

APROVED_STATES = ['open','pending','close']


class Line(object):
    """Clase auxiliar para la generación de ficheros"""
    def __init__(self, dict):
        self.__dict__ = dict


class BaseFileReport(models.TransientModel):
    """Modelo en memoria para almacenar temporalmente los archivos generados al cargar un reporte.
    Todos los asistentes que generen un archivo (xls, xml, etc.) deben devolver la función show()"""
    _name = 'base.file.report'

    file = fields.Binary('Archivo generado', readonly=True, required=True)

    filename = fields.Char('Archivo generado', required=True)

    def show_excel(self, book, filename):
        buf = io.BytesIO()
        book.save(buf)
        out = base64.encodebytes(buf.getvalue())
        buf.close()
        return self.show(out, filename)

    def show_str(self, str, filename):
        out = base64.encodebytes(str)
        return self.show(out, filename)

    def show(self, file, filename):
        file_report = self.env['base.file.report'].create({'file': file, 'filename': filename})

        return {
            'name': filename + time.strftime(' (%Y-%m-%d %H:%M:%S)'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': self._name,
            'res_id': file_report.id,
            'target': 'new',
        }


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _create_last_vacation_period(self, date_from, date_to, periods):
        # Base para el calculo proporcional de vacaciones, 360
        vacation_base_calculation = self._get_vacation_base_calculation()

        # Numero de dias estandar de vacaciones que se acumulan en un periodo completo
        vacation_standard_accumulated = self._get_vacation_standard_accumulated()

        # Proporcional ultimo periodo
        difference = date_to - date_from
        number_of_days_last_period = difference.days + 1
        periods += 1
        accumulated_new_period = number_of_days_last_period * vacation_standard_accumulated / vacation_base_calculation
        if accumulated_new_period > vacation_standard_accumulated:
            accumulated_new_period = vacation_standard_accumulated

        # Incremento por antiguedad
        accumulated_by_seniority = self._get_accumulated_by_seniority('proportional',periods,number_of_days_last_period)

        # Incremento por edad
        increase_by_age = self._get_increase_by_age('proportional', date_from, date_to)

        evd = self.env['hr.employee.vacation.detail'].sudo().create({
            'employee_id': self.id,
            'sequence': periods,
            'type': 'proportional',
            'date_from': date_from,
            'date_to': date_to,
            'standard_accumulated': accumulated_new_period,
            'accumulated_by_seniority': accumulated_by_seniority,
            'increase_by_age': increase_by_age
        })
        evd.vacation_execution = evd._get_vacation_execution() + evd._get_vacation_execution_occupy_from_another_period()
        evd.permissions = evd._get_permissions()
        evd.permissions += evd._get_permissions_in_the_future()
        evd.vacation_execution += evd._get_vacation_execution_in_the_future()
        return evd

    def _get_last_period_available(self, date_from, date_to, periods):
        # Base para el calculo proporcional de vacaciones, 360
        vacation_base_calculation = self._get_vacation_base_calculation()

        # Numero de dias estandar de vacaciones que se acumulan en un periodo completo
        vacation_standard_accumulated = self._get_vacation_standard_accumulated()

        # Proporcional ultimo periodo
        difference = date_to - date_from
        number_of_days_last_period = difference.days + 1
        periods += 1
        accumulated_new_period = number_of_days_last_period * vacation_standard_accumulated / vacation_base_calculation
        if accumulated_new_period > vacation_standard_accumulated:
            accumulated_new_period = vacation_standard_accumulated

        # Incremento por antiguedad
        accumulated_by_seniority = self._get_accumulated_by_seniority('proportional', periods,
                                                                      number_of_days_last_period)

        # Incremento por edad
        increase_by_age = self._get_increase_by_age('proportional', date_from, date_to)

        evd = self.env['hr.employee.vacation.detail'].sudo().new({
            'employee_id': self.id,
            'sequence': periods,
            'type': 'proportional',
            'date_from': date_from,
            'date_to': date_to,
            'standard_accumulated': accumulated_new_period,
            'accumulated_by_seniority': accumulated_by_seniority,
            'increase_by_age': increase_by_age
        })
        evd.vacation_execution = evd._get_vacation_execution() + evd._get_vacation_execution_occupy_from_another_period()
        evd.permissions = evd._get_permissions()
        evd.permissions += evd._get_permissions_in_the_future()
        evd.vacation_execution += evd._get_vacation_execution_in_the_future()
        return evd.available

    def get_vacations_available_to(self, date_to):
        total_vacations = 0.0
        last_date = False
        # Sumo las vacaciones acumuladas de periodos completos
        vacations_detail_ids = self.env['hr.employee.vacation.detail'].sudo().search([
            ('employee_id', '=', self.id), ('date_to', '<=', date_to)], order='date_to')
        for detail in vacations_detail_ids:
            total_vacations += detail.available
            last_date = detail.date_to

        if last_date:
            first_date = last_date + relativedelta.relativedelta(days=1)
            # period = self._create_last_vacation_period(first_date, date_to, len(vacations_detail_ids))
            period = self._get_last_period_available(first_date, date_to, len(vacations_detail_ids))
            # total_vacations += period.available
            total_vacations += period
            # period.sudo().unlink()
        return total_vacations


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _order = 'date_from desc, employee_id'
    
    @api.model
    def default_get(self, fields):
        """
        Cuando el día en curso sea anterior a 25 se deben setear las fechas con el primer y último día del mes anterior.
        """        
        vals = super(HrPayslip, self).default_get(fields)
        current = datetime.strptime(convert_datetime_to_ECT(time.strftime('%Y-%m-%d %H:%M:%S'))[:19],
                                    '%Y-%m-%d %H:%M:%S').date()
        if current.day < 20:
            if vals.get('date_from'):
                date_from = datetime.strftime(
                    datetime.strptime(
                        vals.get('date_from').isoformat(), '%Y-%m-%d').date() -
                    relativedelta.relativedelta(months=1), '%Y-%m-%d')
                date_to = datetime.strftime(current.replace(day=1)+timedelta(days=-1), '%Y-%m-%d')   
                vals.update({
                    'date_from': date_from,
                    'date_to': date_to
                })
        return vals
    
    # @api.model
    # def create(self, vals):
    #     """
    #     Invocamos el metodo create para setear algunos valores cuando la creacion es invocada desde los batch
    #     """
    #     if not vals.get('journal_id'):
    #         vals.update({'journal_id': self.env.context.get('journal_id', False)})
    #     if not vals.get('account_payable_payslip_id'):
    #         account_payable_payslip_id = False
    #         contract = self.env['hr.contract'].browse(vals.get('contract_id'))
    #         if vals.get('contract_id') and hasattr(contract, 'account_payable_payroll'):
    #             account_payable_payslip_id = contract.account_payable_payroll.id
    #         if not account_payable_payslip_id:
    #             account_payable_payslip_id = contract.employee_id.company_id.account_payable_payslip_id.id
    #
    #         net_salary_rule = self.env['hr.salary.rule'].search([('code', '=', 'SUBT_NET')])
    #         if not account_payable_payslip_id and not net_salary_rule.account_credit.id:
    #             raise ValidationError(_('You must configure the "Account payable" in the contract or the "Creditor '
    #                                     'account" in the salary rule "Subtotal: Net salary to receive".'))
    #         vals.update({'account_payable_payslip_id': account_payable_payslip_id})
    #     if vals.get('date_from') and vals.get('date_to') and vals.get('contract_id'):
    #         # vals.update(self._get_worked_days(vals.get('date_from'), vals.get('date_to'), vals.get('contract_id'),
    #         #                                   vals.get('disease')))
    #         vals.update(self._get_worked_days(vals.get('date_from'), vals.get('date_to'), vals.get('contract_id')))
    #     return super(HrPayslip, self).create(vals)
    #
    # def _write(self, vals):
    #     """
    #     Invocamos al metodo write para que se invoquen los metodos que pagan o regresan a estado confirmado
    #     la nómina, este metodo se levanta cuando se ejecuta el metodo _compute_residual, en base a sus
    #     dependencias, en este caso solo nos interesan los que hacen alusion a los apuntes contables
    #     """
    #     pre_not_reconciled = self.filtered(lambda payslip: not payslip.reconciled)
    #     pre_reconciled = self - pre_not_reconciled
    #     res = super(HrPayslip, self)._write(vals)
    #     reconciled = self.filtered(lambda payslip: payslip.reconciled)
    #     not_reconciled = self - reconciled
    #     (reconciled & pre_reconciled).filtered(lambda payslip: payslip.state == 'done').action_payslip_paid()
    #     (not_reconciled & pre_not_reconciled).filtered(lambda payslip: payslip.state == 'paid').action_payslip_re_open()
    #     return res

    @api.model
    def _get_worked_days(self, date_from, date_to, contract_id):
        """
        Este método devuelve los valores del date_from para los contratos que comienzan luego del comienzo del mes
        que se está procesando,
        devuelve el date_to para los contratos que finalizan en el mes, y los dias trabajados según estos parámetros
        tomando siempre como valor mayor 30 días para los meses.
        :return:
        """
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
        else:
            date_from = datetime.strptime(date_from.isoformat(), '%Y-%m-%d')

        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
        else:
            date_to = datetime.strptime(date_to.isoformat(), '%Y-%m-%d')

        contract = self.env['hr.contract']
        if contract_id:
            contract = contract.browse(contract_id)
            if not contract.contract_date_start:
                raise UserError(_('Please enter the contract start date to continue.'))
            else:
                contract_date_start = contract.contract_date_start
        else:
            contract_date_start = '%s-%s-01' % (date_from.year, date_from.month)

        date_start_contract = None
        if isinstance(contract_date_start, str):
            date_start_contract = datetime.strptime(contract_date_start, '%Y-%m-%d')
        else:
            date_start_contract = datetime.strptime(contract_date_start.isoformat(), '%Y-%m-%d')

        date_end_contract = False
        if contract.date_end:
            date_end_contract = datetime.strptime(contract.date_end.isoformat(), '%Y-%m-%d')
        if date_start_contract > date_from:
            date_from = date_start_contract
        if date_end_contract:
            if date_end_contract < date_to:
                date_to = date_end_contract
        worked_days = date_to.day
        if date_to.month == 2 and not date_end_contract:
            # Febrero
            if date_to.year % 4:
                # Tiene 28 días
                worked_days += 2
            else:
                # Año bisiesto, tiene 29 días
                worked_days += 1
        elif date_to.day == 31:
            worked_days = 30
        worked_days -= date_from.day - 1
        return \
            {
                'worked_days': worked_days,
                'date_from': date_from.date(),
                'date_to': date_to.date(),
            }

    @api.onchange('date_to')
    def onchange_date_to(self):
        """
        Invocamos el método onchange_date_to para validar los días trabajados.
        Campo de solo lectura.
        """
        vals = {'value': {}}
        vals['value'].update(self._get_worked_days(self.date_from, self.date_to, self.contract_id.id))
        return vals

    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):
        """
        Invocamos el método onchange_employee para validar las fechas y setear el contrato pues ahora es un
        campo de solo lectura.
        """
        def last_day_of_month(self):
            """
            Este método devuelve el último día del mes para una fecha dada.
            """
            date_from = datetime.strptime(self.date_from.isoformat(), '%Y-%m-%d').date()
            if date_from.month == 12:
                return date_from.replace(day=31)
            return date_from.replace(month=date_from.month+1, day=1) - timedelta(days=1)
        contract_ids = []
        res = super(HrPayslip, self).onchange_employee() or {}
        vals = {'value': {}, 'warning': {}, 'domain': {}}
        vals['value'].update(res.get('value', {}))
        vals['warning'].update(res.get('warning', {}))
        vals['domain'].update(res.get('domain', {}))
        if self.employee_id:
            self.date_to = last_day_of_month(self)
            date1 = datetime.strptime(self.date_from.isoformat(), '%Y-%m-%d')
            date2 = datetime.strptime(self.date_to.isoformat(), '%Y-%m-%d')
            if date1 <= date2:
                # Estableciendo el valor de las vacaciones
                # self.vacation_days = self._get_vacation_days()

                contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
                if contract_ids:
                    vals['value']['contract_id'] = contract_ids[0]
                else:
                    if self.employee_id.id:
                        vals['value'].update({'contract_id': False})
                        msg = {
                            'title': _('Warning'),
                            'message': _('There are no current contracts for the selected employee and period.')
                        }
                        vals['warning'] = msg
            else:
                vals['value'].update({'contract_id': False})
                msg = {
                    'title': _('Warning'),
                    'message': _('The end date must be greater than or equal to the start date.')
                }
                vals['warning'] = msg

        if contract_ids:
            vals['value'].update(self._get_worked_days(self.date_from, self.date_to, contract_ids))
            income_ids = self.income_ids.browse([])
            expense_ids = self.expense_ids.browse([])
            other_expense_ids = self.other_expense_ids.browse([])
            inputs = self.get_inputs(contract_ids, self.date_from, self.date_to)
            for input in inputs:
                # Ingresos adicionales
                if input.get('type') == 'income':
                    income_ids += income_ids.new(input)
                # Egresos adicionales
                elif input.get('type') == 'expense':
                    e = expense_ids.new(input)
                    e.employee_credit_line_id = input.get('employee_credit_line_id', 0)
                    e.loan_line_id = input.get('loan_line_id', 0)
                    expense_ids += e
                # Egresos adicionales con beneficiario
                elif input.get('type') == 'other_expense':
                    other_expense_ids += other_expense_ids.new(input)
            self.income_ids = income_ids
            self.expense_ids = expense_ids
            self.other_expense_ids = other_expense_ids
        return vals

    @api.onchange('contract_id')
    def onchange_contract(self):
        """
        Invocamos el onchange_contract para setear la cuenta por pagar
        """
        res = super(HrPayslip, self).onchange_contract()
        vals = {'value': {}, 'warning': {},'domain': {}}
        vals['value'].update(res.get('value', {}) if res else {})
        vals['warning'].update(res.get('warning', {}) if res else {})
        vals['domain'].update(res.get('domain', {}) if res else {})
        journal_wage_id = self.env.user.company_id.journal_wage_id.id
        if self.contract_id.journal_id:
            journal_wage_id = self.contract_id.journal_id.id
        account_payable_payslip_id = self.env.user.company_id.account_payable_payslip_id.id

        # if self.contract_id.account_payable_payslip_id:
        #     account_payable_payslip_id = self.contract_id.account_payable_payslip_id.id
        if self.contract_id.account_payable_payroll:
            account_payable_payslip_id = self.contract_id.account_payable_payroll

        vals['value'].update({
            'journal_id': journal_wage_id,
            'account_payable_payslip_id': account_payable_payslip_id,
        })
        return vals
    
    @api.onchange('worked_days')
    def onchange_worked_days(self):
        """
        Este metodo garantiza que los dias trabajados sean mayores que 0 y menores o iguales a 30
        """
        vals = {'value': {}, 'warning': {} ,'domain': {}}
        if int(self.worked_days) <= 0 or int(self.worked_days) > 30:
            vals['value'] = {'worked_days': 30}
            vals['warning'] = {
                'title': _(Warning),
                'message': _('Worked days must be greater than 0 and less than or equal to 30.')
            }
        return vals
    
    @api.model
    def get_input_type(self, input):
        """
        Este metodo devuelve el tipo de entrada de la nómina
        """
        # res = super(HrPayslip, self).get_input_type(input)
        res = input.type
        return res

    @api.model
    def get_name_rule(self, rule):
        """
        Este metodo concatena la cantidad de horas extras al 50 y 100 porciento para que salga en el calculo
        de la nómina y en el reporte impreso
        """
        # res = super(HrPayslip, self).get_name_rule(rule)
        res = rule.name
        if rule.code in ('HORA_EXTRA_REGULAR', 'HORA_EXTRA_EXTRAORDINARIA'):
            input_ids = self.env['hr.payslip.input'].search([('payslip_id','in',[self.id]), ('code','=',rule.code)])
            if input_ids:
                res = res + ' (' + str(input_ids[0].amount) + ')'
        return res
    
    @api.model
    def get_sorted_rules(self, rule_ids):
        """
        Este metodo ordena las reglas salariales en base a la categoria y luego a la secuencia de la regla
        """
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        # sorted_rule_ids = super(HrPayslip, self).get_sorted_rules(rule_ids)
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        incomes = []
        others = []
        expenses = []
        contributions = []
        subtotals = []
        overdraft = []
        for rule in sorted_rules:
            # Los sobregiros se calculan después de los ingresos y egresos así que lo extraigo antes de agrupar las
            # categorías
            if rule.code == 'SOBREGIROS':
                overdraft += [rule.id]
            else:
                #Ingresos (Genera beneficios sociales)
                if rule.category_id.code == 'INGRESOS':
                    incomes += [rule.id]
                #Otros Ingresos (No genera beneficios sociales)
                elif rule.category_id.code == 'OINGRESOS':
                    others += [rule.id]
                #Egresos
                elif rule.category_id.code == 'EGRESOS':
                    expenses += [rule.id]
                #Contribución de la Compañía
                elif rule.category_id.code == 'COMPANIA':
                    contributions += [rule.id]
                #Subtotales
                elif rule.category_id.code == 'SUBTOTALES':
                    subtotals += [rule.id]
                else:
                    raise UserError(u'La regla %s no pertenece a ninguna categoría.' % rule.name)
        sorted_rule_ids = incomes + others + expenses + overdraft + contributions + subtotals
        return sorted_rule_ids
    
    
    def action_payslip_print(self):
        """
        Este metodo se encarga de mandar a imprimir la nómina
        """
        return self.env.ref('hr_payroll.action_report_payslip').report_action(self)

    
    def action_payslip_reviewed(self):
        self.state = 'reviewed'
        return self
    
    
    def action_payslip_done(self):
        """
        - Invocamos el método action_payslip_done para evitar validar dos nominas en un mismo período
        - Modificado para separar en dos asientos para X y poder reprocesarlos por separado en v11
        - Pasamos por contexto la cuenta analitica.
        """
        # primero llamamos a super, el super llama a 'calcular' las lineas nuevamente asegurando integridad



        #Método original de hr_payroll
        if not self.env.context.get('without_compute_sheet'):
            self.compute_sheet()
        res = self.write({'state': 'done'})

        #Método de hr_payslip_account
        # for slip in self:
        #     line_ids = []
        #     debit_sum = 0.0
        #     credit_sum = 0.0
        #     date = slip.date or slip.date_to
        #     currency = slip.company_id.currency_id or slip.journal_id.company_id.currency_id
        #
        #     name = _('Payslip of %s') % (slip.employee_id.name)
        #     move_dict = {
        #         'narration': name,
        #         'ref': slip.number,
        #         'journal_id': slip.journal_id.id,
        #         'date': date,
        #     }
        #     for line in slip.details_by_salary_rule_category:
        #         amount = currency.round(slip.credit_note and -line.total or line.total)
        #         if currency.is_zero(amount):
        #             continue
        #         debit_account_id = line.salary_rule_id.account_debit.id
        #         credit_account_id = line.salary_rule_id.account_credit.id
        #
        #         if debit_account_id:
        #             debit_line = (0, 0, {
        #                 'name': line.name,
        #                 'partner_id': line._get_partner_id(credit_account=False),
        #                 'account_id': debit_account_id,
        #                 'journal_id': slip.journal_id.id,
        #                 'date': date,
        #                 'debit': amount > 0.0 and amount or 0.0,
        #                 'credit': amount < 0.0 and -amount or 0.0,
        #                 'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
        #                 'tax_line_id': line.salary_rule_id.account_tax_id.id,
        #             })
        #             line_ids.append(debit_line)
        #             debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
        #
        #         if credit_account_id:
        #             credit_line = (0, 0, {
        #                 'name': line.name,
        #                 'partner_id': line._get_partner_id(credit_account=True),
        #                 'account_id': credit_account_id,
        #                 'journal_id': slip.journal_id.id,
        #                 'date': date,
        #                 'debit': amount < 0.0 and -amount or 0.0,
        #                 'credit': amount > 0.0 and amount or 0.0,
        #                 'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
        #                 'tax_line_id': line.salary_rule_id.account_tax_id.id,
        #             })
        #             line_ids.append(credit_line)
        #             credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
        #
        #     if currency.compare_amounts(credit_sum, debit_sum) == -1:
        #         acc_id = slip.journal_id.default_credit_account_id.id
        #         if not acc_id:
        #             raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
        #                 slip.journal_id.name))
        #         adjust_credit = (0, 0, {
        #             'name': _('Adjustment Entry'),
        #             'partner_id': False,
        #             'account_id': acc_id,
        #             'journal_id': slip.journal_id.id,
        #             'date': date,
        #             'debit': 0.0,
        #             'credit': currency.round(debit_sum - credit_sum),
        #         })
        #         line_ids.append(adjust_credit)
        #
        #     elif currency.compare_amounts(debit_sum, credit_sum) == -1:
        #         acc_id = slip.journal_id.default_debit_account_id.id
        #         if not acc_id:
        #             raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
        #                 slip.journal_id.name))
        #         adjust_debit = (0, 0, {
        #             'name': _('Adjustment Entry'),
        #             'partner_id': False,
        #             'account_id': acc_id,
        #             'journal_id': slip.journal_id.id,
        #             'date': date,
        #             'debit': currency.round(credit_sum - debit_sum),
        #             'credit': 0.0,
        #         })
        #         line_ids.append(adjust_debit)
        #     move_dict['line_ids'] = line_ids
        #     move = self.env['account.move'].create(move_dict)
        #     slip.write({'move_id': move.id, 'date': date})
        #     move.post()


        # Método propio
        ctx = self.env.context.copy()
        ctx.update({'bypass_core_accounting_move': True})
        # valida que el campo analytic_account_id exista y tenga un valor.
        if self.contract_id._fields.get('analytic_account_id', False):
            if self.contract_id.analytic_account_id:
                ctx.update({'analytic_account_id': self.contract_id.analytic_account_id.id})

        # res = super(HrPayslip, self.with_context(ctx)).action_payslip_done()
        payroll_ids = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['done', 'paid']),
            ('id', '!=', self.id),
        ])
        if payroll_ids:
            list1 = '\n'.join('* ' + payroll.number for payroll in payroll_ids)
            raise UserError(_('The following payrolls are confirmed or paid for this employee in the selected period: '
                              '\n%s' ) % list1)
        if self.contract_id.state != 'open':
            # TODO poner alguna validacion para contratos viejos cerrados que requieren reprocesamiento de nomina
            raise ValidationError(_('You can only approve payroll when the contract is ongoing.'))
        for line in self.line_ids:
            if line.salary_rule_id.code == 'SUBT_NET' and float_compare(line.total, 0.0, precision_rounding=2) == -1:
                raise ValidationError(_('Payroll whose net salary to be received is less than 0 cannot be validated. '
                                        'Employee %s') % self.employee_id.name)
        for payslip in self:
            if payslip.employee_information and payslip.employee_information.rent_tax_table_id.state != 'confirmed':
                raise ValidationError(_('In "%s" the income tax table does not exist or is in draft state.')
                                      % payslip.name)
            if not payslip.employee_information and self.env.user.company_id.required_personal_expenses == 'required':
                raise ValidationError(_('You cannot complete the operation, in %s the projection of personal expenses '
                                        'does not exist or it is in draft state.') % payslip.name)
            contract_ids = payslip.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            if payslip.contract_id.id not in contract_ids:
                raise ValidationError(_('In the payment role "%s" the effective date of the selected contract is not '
                                        'consistent with the date of the payment role. Check contract dates or delete '
                                        'and rebuild the payroll.' ) % (payslip.number or payslip.name))
            if hasattr(payslip.employee_id.address_home_id, 'type_vat') and payslip.employee_id.address_home_id.type_vat == 'RUC':
                raise ValidationError(_('Employee %s is registered with RUC, only employees with ID or PASSPORT')
                                      % payslip.employee_id.address_home_id.name)

            #invocamos en el for ambos asientos para que tengan secuencias contiguas
            payslip.with_context(ctx).make_move_payslip()
            # No generar el movimiento de provisiones si no hay nada por provisionar
            if len(self.details_by_salary_rule_category - self.line_ids) > 0:
                payslip.with_context(ctx).make_move_payslip_provision()

            payslip.with_context(ctx)._reconcile_receivables_vs_payslip()
            if payslip.employee_information:
                payslip.employee_information._compute_amount()
                if payslip.employee_information.calculation_method == 'assumption_total':
                    payslip.employee_information.profit_tax_employer = payslip.employee_information.profit_tax_firt_calculation
        return res
    
    
    def action_payslip_paid(self):
        """
        Este metodo envia la nómina a estado pagado
        """
        pre_not_reconciled = self.filtered(lambda payslip: not payslip.reconciled)
        to_pay_payslips = self.filtered(lambda payslip: payslip.state != 'paid')
        if to_pay_payslips.filtered(lambda payslip: payslip.state != 'done'):
            raise ValidationError(_('Payroll must be in confirmed state to register the payment.'))
        if to_pay_payslips.filtered(lambda payslip: not payslip.reconciled):
            raise ValidationError(_('You cannot pay a payroll that is partially paid. You need to destroy the related '
                                    'payment reconciliation first.'))
        return to_pay_payslips.write({'state': 'paid'})

    
    def action_payslip_cancel(self):
        """
        Aplicamos la misma logica que para el move_id
        """
        #desconciliamos los asientos de la nomina que pagan facturas
        lines_to_unreconcile = self.details_by_salary_rule_category.filtered(lambda r: r.amount_select == 'account_move')
        lines_to_unreconcile.mapped('move_line_ids').remove_move_reconcile()
        #removemos el asiento de la provision
        moves = self.mapped('provision_move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        #super remueve el asiento principal, entre otras cosas
        res = super(HrPayslip, self).action_payslip_cancel()
        for payslip in self:
            if payslip.employee_information and payslip.employee_information.calculation_method == 'assumption_total':
                #TODO JOSE: Deberia removerse el compute amount, deberia ser disparado de forma automatica
                payslip.employee_information._compute_amount()
                payslip.employee_information.profit_tax_employer = payslip.employee_information.profit_tax_firt_calculation
        return res

    
    def action_payslip_re_open(self):
        """
        Este metodo envia la nómina a estado confirmado
        """
        if self.filtered(lambda payslip: payslip.state != 'paid'):
            raise ValidationError(_('Payroll must be paid before it can be returned to confirmed state.'))
        return self.write({'state': 'done'})

    
    def check_payslip_state(self):
        """
        Las nóminas pagadas no pueden ser anuladas
        """
        if self.filtered(lambda slip: slip.state == 'paid'):
            raise ValidationError(_('You cannot cancel a payroll that is already paid.'))

    
    def refund_sheet(self):
        """
        Deprecamos este metodo, no queremos que su logica sea llamada en ningun caso
        """
        raise ValidationError(_('Corrective invoices cannot be created from payroll.'))
        return super(HrPayslip, self).refund_sheet()
    
    @api.model
    def is_manager_payslip(self):
        """
        Este método determina si el usuario activo tiene el rol de responsable en nóminas
        """
        manager = True
        self.env.cr.execute("""
            select g.id, g.name, mc.name
            from res_groups g join 
                res_groups_users_rel gu 
                    on g.id=gu.gid join
                res_users u 
                    on u.id=gu.uid join
                ir_module_category mc
                    on mc.id=g.category_id
            where gu.uid=%s and g.name='Manager' and mc.name='Payroll'
            """, (self.env.user.id,)
        )
        result = self.env.cr.fetchall()
        if not result:
            manager = False
        return manager

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        Se sobrescribe el metodo get_contract pues ahora queremos aplicar otros criterios en el filtrado de contratos
        """
        contract_ids = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id), ('date_start', '<=', date_from), ('date_end', '>=', date_from),
            ('state', 'in', ['open', 'close'])])
        if not contract_ids:
            #Para el caso que la ultima version del contrato este en ejecucion y no tenga seteada la fecha de vigencia
            contract_ids = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id), ('date_start', '<=', date_from), ('date_end', '=', False),
                ('state', 'in', ['open', 'close'])])
            if not contract_ids:
                contract_ids = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id), ('date_start', '<=', date_to), ('date_end', '=', False),
                    ('state', 'in', ['open', 'close'])], order='date_start DESC')
                if not contract_ids:
                    contract_ids = self.env['hr.contract'].search([
                        ('employee_id', '=', employee.id), ('date_start', '>=', date_from), ('date_end', '<=', date_to),
                        ('state', 'in', ['open','close'])])
        return contract_ids.mapped('id')

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """
        Invocamos el metodo get_inputs para agregar nuevas entradas a la nómina
        """

        # En ocasiones contracts es un objeto de tipo list en lugar de hr.contract, convirtiéndolo
        if isinstance(contracts, list):
            contracts = self.env['hr.contract'].browse(contracts)

        # Convirtiendo las fechas recibidas como string a objetos datetime.date
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        res = []
        # # Dainovy
        # contracts = self.env['hr.contract'].browse(contracts)
        # # Dainovy
        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            for input in inputs:
                if input.code == 'PREST_EMP':

                    amount = 0
                    loan_line_id = 0
                    lon_obj = self.env['hr.loan'].search([('employee_id', '=', contract.employee_id.id), ('state', '=', 'approved')])
                    for loan in lon_obj:
                        if loan_line_id != 0:
                            break
                        for loan_line in loan.loan_lines:
                            if date_from <= loan_line.date <= date_to and not loan_line.paid:
                                amount = loan_line.amount
                                loan_line_id = loan_line.id
                                break

                    input_data = {
                        'name': input.name,
                        'code': input.code,
                        'contract_id': contract.id,
                        'amount': amount,
                        'loan_line_id': loan_line_id,
                        'type': self.get_input_type(input),
                    }
                    res += [input_data]
                elif input.code == 'CRED_EMP_PROF':
                    amount = 0
                    ec_line_id = 0
                    employee_credit = self.env['hr.employee.credit'].search(
                        [('employee_id', '=', contract.employee_id.id), ('state', '=', 'in_payroll')])
                    for ec in employee_credit:
                        if ec_line_id != 0:
                            break
                        for ecl in ec.credit_lines:
                            if date_from <= ecl.date <= date_to and not ecl.paid:
                                amount = ecl.amount
                                ec_line_id = ecl.id
                                break

                    input_data = {
                        'name': input.name,
                        'code': input.code,
                        'contract_id': contract.id,
                        'amount': amount,
                        'employee_credit_line_id': ec_line_id,
                        'type': self.get_input_type(input),
                    }
                    res += [input_data]
                else:
                    input_data = {
                        'name': input.name,
                        'code': input.code,
                        'contract_id': contract.id,
                        # Dainovy
                        'type': self.get_input_type(input),
                        # Dainovy
                    }
                    res += [input_data]

        # for contract in self.env['hr.contract'].browse(contract_ids):
        #     #Ingresos adicionales, egresos adicionales y egresos adicionales con beneficiario
        #     for input in contract.income_ids + contract.expense_ids + contract.other_expense_ids:
        #         #Removemos reglas salariales que ya existe en el contrato
        #         res =  filter(lambda x: x.get('code') != input.rule_id.code, res)
        #         line = {
        #             'name': input.rule_id.name,
        #             'code': input.rule_id.code,
        #             'amount': input.amount,
        #             'partner_id': input.partner_id.id,
        #             'type': input.type,
        #             'contract_id': contract.id
        #         }
        #         res += [line]

        for contract in contracts:
            if hasattr(contract, 'income_ids'):
                for input in contract.income_ids:
                    # Removemos reglas salariales que ya existe en el contrato
                    res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
                    line = {
                        'name': input.rule_id.name,
                        'code': input.rule_id.code,
                        'amount': input.amount,
                        'partner_id': input.partner_id.id,
                        'type': input.type,
                        'contract_id': contract.id
                    }
                    res += [line]

            if hasattr(contract, 'expense_ids'):
                for input in contract.expense_ids:
                    # Removemos reglas salariales que ya existen en el contrato
                    res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
                    line = {
                        'name': input.rule_id.name,
                        'code': input.rule_id.code,
                        'amount': input.amount,
                        'partner_id': input.partner_id.id,
                        'type': input.type,
                        'contract_id': contract.id
                    }
                    res += [line]

            if hasattr(contract, 'other_expense_ids'):
                for input in contract.other_expense_ids:
                    # Removemos reglas salariales que ya existen en el contrato
                    res = list(filter(lambda x: x.get('code') != input.rule_id.code, res))
                    line = {
                        'name': input.rule_id.name,
                        'code': input.rule_id.code,
                        'amount': input.amount,
                        'partner_id': input.partner_id.id,
                        'type': input.type,
                        'contract_id': contract.id
                    }
                    res += [line]

            # Adicionando input para vacaciones
            # res += [{
            #     'name': 'Días de Vacaciones Pagados',
            #     'code': 'VACACIONES_PAGADAS',
            #     'contract_id': contract.id,
            #     'amount': 0,
            #     'type': 'income',
            # }]

        return res
    
    @api.model
    def get_debit_account_id(self, line):
        """
        Invocamos el get_debit_account_id para setear la cuenta deudora cuando este activo el check de cuentas contables
        por tipo de contrato en la regla salarial
        """
        account_id = line.salary_rule_id.account_debit.id
        if line.salary_rule_id.condition_acc:
            #Mano de obra directa
            hr_contract_type_mdi = self.env.ref('hr_rxr_payroll.hr_contract_type_mdi')
            #Mano de obra indirecta
            hr_contract_type_min = self.env.ref('hr_rxr_payroll.hr_contract_type_min')
            #Administrativo
            hr_contract_type_wrkr = self.env.ref('hr_rxr_payroll.hr_contract_type_wrkr')
            #Ventas
            hr_contract_type_sub = self.env.ref('hr_rxr_payroll.hr_contract_type_sub')
            contract_type = line.slip_id.contract_id.type_id
            if contract_type == hr_contract_type_mdi:
                account_id = line.salary_rule_id.debit_acc_manu_di.id
            elif contract_type == hr_contract_type_min:
                account_id = line.salary_rule_id.debit_acc_manu_in.id
            elif contract_type == hr_contract_type_wrkr:
                account_id = line.salary_rule_id.debit_acc_administrative.id
            elif contract_type == hr_contract_type_sub:    
                account_id = line.salary_rule_id.debit_acc_sales.id
        return account_id
    
    @api.model
    def get_credit_account_id(self, line):
        """
        Invocamos el get_credit_account_id para setear la cuenta acreedora cuando este activo el check de cuentas
        contables por tipo de contrato en la regla salarial. Adicionalmente seteamos la cuenta acreedora del salario
        neto a recibir, tiene mas peso la configurada en el contrato
        """
        account_id = line.salary_rule_id.account_credit.id
        if line.salary_rule_id.condition_acc:
            #Mano de obra directa
            hr_contract_type_mdi = self.env.ref('hr_rxr_payroll.hr_contract_type_mdi')
            #Mano de obra indirecta
            hr_contract_type_min = self.env.ref('hr_rxr_payroll.hr_contract_type_min')
            #Administrativo
            hr_contract_type_wrkr = self.env.ref('hr_rxr_payroll.hr_contract_type_wrkr')
            #Ventas
            hr_contract_type_sub = self.env.ref('hr_rxr_payroll.hr_contract_type_sub')
            contract_type = line.slip_id.contract_id.type_id
            if contract_type == hr_contract_type_mdi:
                if line.salary_rule_id.credit_acc_manu_di:
                    account_id = line.salary_rule_id.credit_acc_manu_di.id
            elif contract_type == hr_contract_type_min:
                if line.salary_rule_id.credit_acc_manu_in:
                    account_id = line.salary_rule_id.credit_acc_manu_in.id
            elif contract_type == hr_contract_type_wrkr:
                if line.salary_rule_id.credit_acc_administrative:
                    account_id = line.salary_rule_id.credit_acc_administrative.id
            elif contract_type == hr_contract_type_sub:
                if line.salary_rule_id.credit_acc_sales:
                    account_id = line.salary_rule_id.credit_acc_sales.id
        if line.salary_rule_id.code == 'SUBT_NET':
            if line.contract_id.account_payable_payroll:
                account_id = line.contract_id.account_payable_payroll.id
            if not account_id:
                account_id = self.company_id.account_payable_payslip_id.id
            if not account_id:
                raise ValidationError(_('You must configure the "Account payable" in the contract or the '
                                        '"Creditor account" in the salary rule "Subtotal: Net salary to receive".'))
        return account_id
    
    @api.model
    def get_account_analytic(self, account_id):
        """
        Obtenemos la cuenta analitica para cada linea del asiento contable.
        cuando el codigo de la cuenta este en 4,5,6,7,8,9
        """
        #TODO: Se deberia implementar el campo analytic_policy in ['always_plan']
        account = self.env['account.account'].browse(account_id)
        if re.match(r'^[4,5,6,7,8,9].', account.code):
                ctx = self._context.copy()
                return ctx.get('analytic_account_id', False)
        else:
            return False
    
    @api.model
    def get_split_credit_lines(self, slip, line, date, amount, credit_account_id):
        """
        Invocamos el get_split_credit_lines para modificar las líneas de apuntes contables cuando la regla analizada
        sea reflejada una o mas veces en el tree de egresos adicionales con beneficiario, se quiere que el asiento
        se haga en base a los beneficiarios
        """

        credit_line = [(0, 0, {
            'name': line.name + ', ' + line.employee_id.name,
            'partner_id': line._get_partner_id(credit_account=True),
            'account_id': credit_account_id,
            'journal_id': slip.journal_id.id,
            'date': date,
            'debit': amount < 0.0 and -amount or 0.0,
            'credit': amount > 0.0 and amount or 0.0,
            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.employee_id.department_id.analytic_account_id.id,
            'tax_line_id': line.salary_rule_id.account_tax_id.id,
        })]

        credit_line[0][2].update({'payslip_line_id': line.id})
        other_expense_ids = self.env['hr.payslip.input'].search([
            ('payslip_id','=',slip.id), 
            ('code','=',line.code),
            ('type','=','other_expense'),
        ])
        if len(other_expense_ids) >= 1:
            credit_line = []
            for input in other_expense_ids:
                analytic_account_id = self.get_account_analytic(credit_account_id) or line.salary_rule_id.analytic_account_id.id or line.employee_id.department_id.analytic_account_id.id
                credit_line.append((0, 0, {
                    'name': input.name,
                    'partner_id': input.partner_id.id,
                    'account_id': credit_account_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': input.amount < 0.0 and -input.amount or 0.0,
                    'credit': input.amount > 0.0 and input.amount or 0.0,
                    'analytic_account_id': analytic_account_id ,
                    'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    'payslip_line_id': line.id,
                }))
        return credit_line
    
    def make_move_payslip(self):
        """Crea el movimiento contable para los registros visibles en la nomina impresa
        """
        name = _('Payslip of %s') % (self.employee_id.name)
        date = self.date or self.date_to
        move_header = {
            'narration': name,
            'ref': self.number,
            'journal_id': self.journal_id.id,
            'date': date,
            'partner_id': self.employee_id.address_home_id.commercial_partner_id.id,
        }
        move_lines = self._compute_move_lines(self.line_ids)
        move = self._create_account_moves(move_header, move_lines)
        self.move_id = move.id
        #toca volver a poner, a pesar que ya esta en el move_header no coge
        move.partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        
    def make_move_payslip_provision(self):
        """Realizamos el asiento de las provisiones
        """
        name = _('Provision of %s') % (self.employee_id.name)
        date = self.date or self.date_to
        move_header = {
            'narration': name,
            'ref': self.number,
            'journal_id': self.journal_id.id,
            'date': date,
            'partner_id': self.employee_id.address_home_id.commercial_partner_id.id,
        }
        move_lines = self._compute_move_lines(self.details_by_salary_rule_category - self.line_ids)
        move = self._create_account_moves(move_header, move_lines)
        self.provision_move_id = move.id
        #toca volver a poner, a pesar que ya esta en el move_header no coge
        move.partner_id = self.employee_id.address_home_id.commercial_partner_id.id
    
    def _compute_move_lines(self, lines):
        """Computa las lineas de asiento contable en base a las líneas de la nomina pasadas como argumento 
        @lines payslip.lines, en base a las cuales se crea el asiento contable
        """ 
        self.ensure_one() #usamos api.multi a pesar de estar implementado para una sola nomina
        precision = self.env['decimal.precision'].precision_get('Payroll')
        date = self.date or self.date_to
        debit_sum = 0.0
        credit_sum = 0.0
        move_ids = [] #los vals de los asientos a crear
        for line in lines:
            amount = self.credit_note and -line.total or line.total
            if float_is_zero(amount, precision_digits=precision):
                continue
            debit_account_id = self.get_debit_account_id(line)
            credit_account_id = self.get_credit_account_id(line)
            if debit_account_id:
                debit_line = (0, 0, self.get_split_debit_lines(self, line, date, amount, debit_account_id))
                #damos otra vuelta agregando plazos de pago
                #TODO v11 unificar los plazos de pago en el core
                #TODO v11 replicar lo del debe en el haber
                if line.salary_rule_id.payment_term_days:
                    date_maturity = datetime.strptime(debit_line[2]['date'], '%Y-%m-%d') + \
                                    timedelta(days=line.salary_rule_id.payment_term_days)
                    debit_line[2].update({'date_maturity': date_maturity})
                move_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            if credit_account_id:
                for credit_line in self.get_split_credit_lines(self, line, date, amount, credit_account_id):
                    move_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            if not debit_account_id and not credit_account_id and line.salary_rule_id.category_id.code != 'SUBTOTALES':
                raise ValidationError(_('To continue you must set up a debit or credit account in the salary rule "%s"')
                                      % line.salary_rule_id.name)
        #El core ya valida que el asiento este cuadrado
        #TODO Implementar un metodo que valide que el asiento este cuadrado pero 
        #que muestre en pantalla (aunque sea en texto formateado como tabla) los valores para que se pueda identificar
        # con facilidad la causa del descuadre
        return move_ids
    
    @api.model
    def get_split_debit_lines(self, slip, line, date, amount, debit_account_id):
        """
        Invocamos el método get_split_debit_lines para agregarle la cuenta analitica a las lineas del asiento contable.
        el contexto solo llega si el campo cuenta analitica del contrato del empleado cuenta con un valor.
        """
        ctx = self.env.context.copy()

        analytic_account_id = line.salary_rule_id.analytic_account_id.id or line.employee_id.department_id.analytic_account_id.id

        debit_line = {
            'name': line.name + ', ' + line.employee_id.name,
            'partner_id': line._get_partner_id(credit_account=False),
            'account_id': debit_account_id,
            'journal_id': slip.journal_id.id,
            'date': date,
            'debit': amount > 0.0 and amount or 0.0,
            'credit': amount < 0.0 and -amount or 0.0,
            'analytic_account_id': analytic_account_id,
            'tax_line_id': line.salary_rule_id.account_tax_id.id,
        }

        debit_line.update({'payslip_line_id': line.id})
        if ctx.get('analytic_account_id',False):
            analytic_account_id = self.get_account_analytic(debit_account_id)
            if analytic_account_id:
                debit_line.update({
                    'analytic_account_id': analytic_account_id
                })
        return debit_line
    
    @api.model
    def _create_account_moves(self, move_dict, line_ids):
        """Metodo auxiliar para crear el asiento contable
        """
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return move
    
    def _reconcile_receivables_vs_payslip(self):
        """Concilia la nomina contra las facturas a cobrar al empleado
        Lo hace linea por linea de nomina, en base a los campos
        receivable_move_line_id y move_line_ids
        """
        #tomamos todas las nominas a la vez, considerando las lineas visibles y no visibles en la nomina
        lines = self.details_by_salary_rule_category.filtered(lambda r: r.amount_select == 'account_move')
        #conciliamos las receivables
        for line in lines:
            #solo conciilamos si la cuenta es CxC y el valor esta en el credito
            counterpart_moves = line.move_line_ids.filtered(lambda r: r.account_id.internal_type == 'receivable').filtered(lambda r: r.credit > 0.0)
            satisfy_reconcile_conditions = self._satisfy_reconcile_conditions(line.receivable_move_line_id, counterpart_moves)
            if satisfy_reconcile_conditions and line.receivable_move_line_id and counterpart_moves:
                moves_to_reconcile = line.receivable_move_line_id + counterpart_moves
                moves_to_reconcile.reconcile()

    @api.model
    def _satisfy_reconcile_conditions(self, receivable_move_line_id, counterpart_moves_lines):
        """Hook para decidir si se concilia o no
        Util en proyecto X para conciliar solo si estan en la misma division
        """
        return True
    
    def get_legal_years_months_days(self, date_start, date_end):
        """Metodo auxiliar para centralizar el computo de deltas de tiempo
        @self objeto payslip, no se usa! (lo dejamos para instanciar la clase e invocar el metodo)
        @date_start fecha inicio
        @date_end fecha final
        """
        if not date_start or not date_end:
            return 0, 0, 0

        if not isinstance(date_start, str):
            date_start = datetime.strptime(date_start.isoformat(), '%Y-%m-%d')
        else:
            date_start = datetime.strptime(date_start, '%Y-%m-%d')
        #a la fecha final se sumamos 1 dia, de esta forma:
        # - Cuando el empleado trabajó del 1ene2017 al 1ene2017 le dará 1 dia
        # - Cuando el empleado trabajó del 1ene2017 al 31ene2017 le dará 1 mes, 0 días

        if not isinstance(date_end, str):
            date_end = datetime.strptime(date_end.isoformat(), '%Y-%m-%d') + timedelta(days=1)
        else:
            date_end = datetime.strptime(date_end, '%Y-%m-%d') + timedelta(days=1)

        rd = relativedelta.relativedelta(date_end,date_start)
        return rd.years, rd.months, rd.days
#         Esta seccion comentada es la alternativa a usar relativedelta.relativedelta
#         Estaba a medio hacer y relativedelta ya estaba listo y disponible
#         Se deja comentado por si acaso se necesite en el futuro
#         years = 0
#         months = 0
#         days = 0        
#         #años cumplidos, basado en script conocido para cumpleanios
#         years = date_end.year - date_start.year - ((date_end.month, date_end.day) < (date_start.month, date_start.day))
#         date_start = date_start.replace(year=date_start.year+years) #actualizamos al saldo
#         #ahora buscamos los meses, basado en algoritmo probado
#         #https://stackoverflow.com/questions/7015587/python-difference-of-2-datetimes-in-months
#         d1 = date_start
#         months = 0
#         while True:
#             mdays = calendar.monthrange(d1.year, d1.month)[1]
#             d1 += timedelta(days=mdays)
#             if d1 <= date_end:
#                 months += 1
#             else:
#                 break
#         #actualizamos la fecha inicial recorriendola los meses computados
#         delta_months = date_start.month + months
#         delta_years = 0
#         if delta_months > 12: #nunca puede ser mas de un anio
#             delta_years = 1
#             delta_months -= 12
#         date_start = date_start.replace(month=delta_months, 
#                                         year=date_start.year+delta_years)
#         #y ahora calculamos los dias, con el saldo
#         delta = date_end - date_start
#         days = delta.days
#         return years, months, days
    
    def normalize_years_months_days(self, years, months, legal_days):
        """#normalizamos el computo, por ejemplo 13 meses se convierten a 1 anio y 1 mes
        """
        if legal_days > 30:
            months += int(legal_days/30)
            legal_days = legal_days % 30 #el saldo de la division
        if months > 12:
            years += int(months/12)
            months = months % 12  #el saldo de la division
        if months == 12:
            years += int(months/12)
            months = months % 12  #el saldo de la division
        return years, months, legal_days
    
    @api.depends('employee_id', 'date_to')
    def _get_time_in_service_current_contract(self):
        """
        Computa por los años, meses y días que un empleado ha trabajando EN EL CONTRATO ACTUAL
        a la fecha de corte de la nomina.
        Esta basado en el metodo _get_time_in_service
        #TODO V11 hacerlo DRY
        """
        for payslip in self:
            years = 0
            months = 0
            days = 0
            #se añade el tiempo del contrato vigente (el que esta en la nomina)
            #en este caso no validamos que el contrato este aprobado pues es posible que el usuario haga
            #la nomina y luego anule el contrato para pruebas por ejemplo, en este caso es deseable que 
            #si se lo considere para el tiempo
            years_curent, months_curent, days_curent = self.get_legal_years_months_days(payslip.contract_id.date_start,
                                                                                   payslip.date_to)
            years += years_curent
            months += months_curent
            days += days_curent
            #normalizamos el computo, por ejemplo 13 meses se convierten a 1 anio y 1 mes
            years, months, days = self.normalize_years_months_days(years, months, days)
            payslip.years_in_service_current_contract = years
            payslip.months_in_service_current_contract = months
            payslip.days_in_service_current_contract = days

    # @api.depends('employee_id', 'date_from', 'date_to')
    # def _compute_days_in_service_payslip_period(self):
    #     for payslip in self:
    #         if payslip.contract_id:
    #             if payslip.contract_id.contract_date_start < payslip.date_from:
    #                 # La fecha de inicio del contrato es menor que la fecha de inicio del periodo de calculo de nomina
    #                 if payslip.contract_id.contract_date_end and payslip.contract_id.contract_date_end <= payslip.date_to and payslip.contract_id.contract_date_end > payslip.date_from:
    #                     # Hay fecha de fin del contrato y es menor que la fecha de fin del periodo de calculo de la nomina
    #
    #                     days = payslip.contract_id.contract_date_end.day
    #                     if payslip.date_from.month == 2:  # febrero
    #                         if payslip.date_from.year % 4:
    #                             # tiene 28 dias
    #                             days += 2
    #                         else:  # año bisiesto, tiene 29 dias
    #                             days += 1
    #                     # elif days == 31:
    #                     #     days = 30
    #
    #                     if days == 31:
    #                         days = 30
    #
    #                     payslip.days_in_service_payslip_period = days
    #
    #                 elif not payslip.contract_id.contract_date_end or payslip.contract_id.contract_date_end > payslip.date_to:
    #                     payslip.days_in_service_payslip_period = 30
    #             else:
    #                 # La fecha de inicio del contrato es mayor o igual que la fecha de inicio del período de cálculo de la nómina
    #                 if payslip.contract_id.contract_date_end and payslip.contract_id.contract_date_end <= payslip.date_to:
    #                     # Hay fecha de fin del contrato y es menor que la fecha de fin del periodo de calculo de la nomina
    #                     days = (payslip.contract_id.contract_date_end - payslip.contract_id.contract_date_start).days + 1
    #                     payslip.days_in_service_payslip_period = days
    #                 else:
    #                     payslip.days_in_service_payslip_period = 30 - payslip.contract_id.contract_date_start.day + 1
    #
    #             if payslip.days_in_service_payslip_period == 30:
    #                 payslip.complete_period = True
    #             else:
    #                 payslip.complete_period = False
    
    @api.depends('date_to')
    def _get_calendar_days_in_month(self):
        """
        Computa los dias calendario que tiene el mes en cuestion, util para crear reglas salariales
        """
        for payslip in self:
            date_end = datetime.strptime(payslip.date_to.isoformat(), '%Y-%m-%d')
            weekday, days_in_month = calendar.monthrange(date_end.year,date_end.month)
            payslip.calendar_days_in_month = days_in_month
    
    @api.depends('employee_id', 'date_to')
    def _get_time_in_service(self):
        """
        Computa por los años, meses y días que un empleado ha trabajando para la empresa
        a la fecha de corte de la nomina.
        """
        for payslip in self:
            years = 0
            months = 0
            days = 0
            #Se añade el tiempo antes del uso de Odoo
            years += payslip.employee_id.total_time_in_company_years or 0.0
            months += payslip.employee_id.total_time_in_company_months or 0.0
            days += payslip.employee_id.total_time_in_company_days or 0.0
            #Se añade el tiempo de los contratos viejos (las versiones de contratos se consideran como contratos viejos)
            #Se obtienen todos los contratos anteriores a la fecha seleccionada
            previous_contract_ids = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id), 
                                                                    ('date_end','<=',payslip.contract_id.date_start), 
                                                                    ('state','in',APROVED_STATES),
                                                                    ('id','!=',payslip.contract_id.id),
                                                                    ], 
                                                                   order='date_end')
            for previous in previous_contract_ids:
                years_previous, months_previous, days_previous = self.get_legal_years_months_days(
                    previous.date_start,
                    previous.date_end)
                years += years_previous
                months += months_previous
                days += days_previous
            #se añade el tiempo del contrato vigente (el que esta en la nomina)
            #en este caso no validamos que el contrato este aprobado pues es posible que el usuario haga
            #la nomina y luego anule el contrato para pruebas por ejemplo, en este caso es deseable que 
            #si se lo considere para el tiempo
            years_current, months_current, days_current = self.get_legal_years_months_days(
                payslip.contract_id.date_start, payslip.date_to)
            years += years_current
            months += months_current
            days += days_current
            #normalizamos el computo, por ejemplo 13 meses se convierten a 1 anio y 1 mes
            years, months, days = self.normalize_years_months_days(years, months, days)
            payslip.years_in_service = years
            payslip.months_in_service = months
            payslip.days_in_service = days
    
    @api.depends('employee_id', 'date_to')
    def _get_number_service_months(self):
        """
        Util para el calculo del fondo de reserva. Devuelve un entero con el numero de meses que 
        ha trabajado el empleado hasta el corte de la nomina, notas:
        - Una fracción de mes cuenta como mes
        - Si encuentra dos contratos distintos que se sobrelapan en el mismo mes va a asumir
          que cuentan como dos meses.
        """
        for payslip in self:
            payslip.number_service_months = self.years_in_service*12 + \
                                            self.months_in_service + \
                                            int(math.ceil(self.days_in_service/30.0)) 
                                            #se usa 30.0 para convertir a flotante
    
    @api.depends('employee_id', 'date_to')
    def _get_days_to_pay_reserve_fund(self):
        """
        Campo auxiliar para el computo de fondos de reserva en el 13avo mes
        Para el 13avo mes retorna el numero de dias que se debe pagar por 
        fondo de reserva, por ejemplo:
         
        Para la nomina del 28 de febrero 2018:
        - Para un empleado que ingreso un 01 de febr. 2017 retornará 30 días (pago completo) 
        - Para un empleado que ingreso un 02 de febr. 2017 retornará 29 días
        - Para un empleado que ingreso un 03 de febr. 2017 retornará 28 días
        - Para un empleado que ingreso un 15 de febr. 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de febr. 2017 retornará 14 días
        - Para un empleado que ingreso un 27 de febr. 2017 retornará 04 días
        - Para un empleado que ingreso un 28 de febr. 2017 retornará 03 días
 
        Para la nomina del 30 de marzo 2018:
        - Para un empleado que ingreso un 01 de marzo 2017 retornará 30 días (pago completo)
        - Para un empleado que ingreso un 02 de marzo 2017 retornará 29 días
        - Para un empleado que ingreso un 15 de marzo 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de marzo 2017 retornará 14 días
        - Para un empleado que ingreso un 29 de marzo 2017 retornará 02 días
        - Para un empleado que ingreso un 30 de marzo 2017 retornará 01 días
        - Para un empleado que ingreso un 31 de marzo 2017 retornará 01 días
            
        Para la nomina del 30 de abril 2018:
        - Para un empleado que ingreso un 01 de abril 2017 retornará 30 días (pago completo)
        - Para un empleado que ingreso un 02 de abril 2017 retornará 29 días
        - Para un empleado que ingreso un 15 de abril 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de abril 2017 retornará 14 días
        - Para un empleado que ingreso un 29 de abril 2017 retornará 02 días
        - Para un empleado que ingreso un 30 de abril 2017 retornará 01 días
        """
        if self.number_service_months < 13:
            days_to_pay_reserve_fund = 0
        elif self.number_service_months == 13:
            #los dias que me sobran del ultimo mes
            #pero maximo 30 dias pues la formula en la regla salarial
            #de fondo de reserva la divide para  30 dias
            date_end = datetime.strptime(self.date_to.isoformat(), '%Y-%m-%d')
            days_in_service = self.days_in_service
            if self.days_in_service == 0:
                #en este caso si son 13 meses entonces es 1 año y 1 mes, osea 30 dias
                days_in_service = 30
            elif date_end.month == 2: #febrero
                if date_end.year % 4:
                    #tiene 28 dias
                    days_in_service += 2
                else: #año bisiesto, tiene 29 dias
                    days_in_service += 1
            elif date_end.day == 31:
                days_in_service = max(1, days_in_service-1)
            days_to_pay_reserve_fund = min(30, days_in_service)
        else: #mayor que 13 meses
            days_to_pay_reserve_fund = 30

        self.days_to_pay_reserve_fund = days_to_pay_reserve_fund
    
    @api.depends('date_from')
    def _get_unified_basic_salary(self):
        """
        Este método devuelve el salario basico unificado en base a la fecha final de la nómina
        """
        for payslip in self:
            payslip.unified_basic_salary = self.get_sbu_by_year(payslip.date_to.year)
        return True

    @api.model
    def get_sbu_by_year(self, year):
        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if sbu:
            return sbu.value
        else:
            raise ValidationError(_('You must set the unified base salary for the year {}.').format(str(year)))
    
    @api.depends('line_ids.amount')
    def _get_net_salary(self):
        net_salary = 0.0
        if self.line_ids:
            for line in self.line_ids:
                if line.salary_rule_id.code == 'SUBT_NET':
                    net_salary =line.amount
        self.net_salary = net_salary
    
    @api.depends('state', 'move_id.line_ids.amount_residual', 'move_id.line_ids.full_reconcile_id')
    def _compute_residual(self):
        """
        Este metodo determina el monto pendiente de pago en la nómina(residual) y si esta
        conciliada o no (reconciled)
        """
        for payslip in self:
            residual = 0.0
            domain = [('credit','>',0.0)]
            if payslip.move_id:
                domain.append(('move_id','=',payslip.move_id.id))
            if payslip.account_payable_payslip_id:
                domain.append(('account_id','=',payslip.account_payable_payslip_id.id))
            #Buscamos los asiento contables a pagar
            line_ids = self.env['account.move.line'].search(domain)
            for line in line_ids:
                residual += line.amount_residual
            self.residual = abs(residual)
            digits_rounding_precision = self.env.user.company_id.currency_id.rounding
            if float_is_zero(self.residual, precision_rounding=digits_rounding_precision) and payslip.state != 'draft':
                self.reconciled = True
            else:
                self.reconciled = False
    
    
    def _get_employee_information(self):
        """
        Este metodo relaciona la nómina con la información del empleado para el calculo del impuesto a la renta
        """
        for payslip in self:
            employee_information = None
            employee_information_ids = self.env['hr.personal.expense'].search([
                ('employee_id','=',payslip.employee_id.id),
                ('rent_tax_table_id.fiscal_year', '=', payslip.date_from.year),
                ('state','=','done')
            ])
            if employee_information_ids:
                employee_information = employee_information_ids[0].id
            payslip.employee_information = employee_information
        return True
    
    @api.depends('date_from', 'date_to')
    def _get_profits_worked_days(self):
        for payslip in self:
            worked_days = payslip.date_to
            worked_days -= payslip.date_from
            payslip.profits_worked_days = worked_days.days + 1
    
    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)

            # Obteniendo el valor de un día de vacaciones.
            self._compute_vacation_day_amount()
            # Obteniendo el valor del sobregiro del mes anterior si existe
            self._compute_last_month_overdraft()
            # Obteniendo los valores para el cálculo del ajuste de decimocuarto
            self._compute_fourteenth_adjustment()

            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})
        return True

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """

        exportFile = self.env['hr.rxr.export.file']
        for rec in self:
            lines = []
            lines.append(Line({"employee_id": rec.employee_id, "value": rec.net_salary, "reference": rec.number}))

            messages = exportFile._create_text_files(lines, rec.name)
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return exportFile._compress_and_show("{} ({})".format(rec.name, rec.employee_id.display_name) + '.zip')

    def _get_domain_rules_by_move(self, partner, payslip, account, rule):
        """
        Hook para modificar criterio de busqueda account_move_line.
        @return: Domain
        """

        return [
            ('partner_id', '=', partner.id),
            ('date_maturity', '>=', payslip.date_from),
            ('date_maturity', '<=', payslip.date_to),
            ('account_id', '=', account.id),
            ('debit', '>', 0.0),  # escuchamos en el debe
            ('full_reconcile_id', '=', False),
        ]

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)

            if category.code in localdict['categories'].dict:
                localdict['categories'].dict[category.code] += amount
            else:
                localdict['categories'].dict[category.code] = amount

            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                        SELECT sum(amount) as sum
                        FROM hr_payslip as hp, hr_payslip_input as pi
                        WHERE hp.employee_id = %s AND hp.state = 'done'
                        AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                        SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                        FROM hr_payslip as hp, hr_payslip_worked_days as pi
                        WHERE hp.employee_id = %s AND hp.state = 'done'
                        AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                                FROM hr_payslip as hp, hr_payslip_line as pl
                                WHERE hp.employee_id = %s AND hp.state = 'done'
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        def _get_rules_by_move(localdict, sorted_rules):
            """Buscamos los moves en las reglas de tipo move, y retornamos la
            permutacion de reglas y moves"""
            rules_by_move = []
            aml_obj = self.sudo().env['account.move.line']  # usamos sudo para poder acceder a los registros contables
            for rule in sorted_rules:
                move_ids = []
                if rule.amount_select in ['account_move']:
                    # si es del nuevo tipo, basado en movimientos contables, buscamos
                    # los movimiento
                    payslip = self.search([('id', '=', localdict['payslip'].id)])
                    partner = payslip.employee_id.address_home_id.commercial_partner_id
                    if not partner:
                        raise UserError(u'El empleado %s no tiene una empresa configurada' % payslip.employee_id.name)
                    account = rule.account_credit
                    if not account:
                        raise UserError(
                            u'La regla salarial %s es de tipo Neteo Saldo Contable, solo debe tener una cuenta acreedora configurada' % rule.name)
                    if rule.account_debit or rule.condition_acc:
                        raise UserError(
                            u'La regla salarial %s es de tipo Neteo Saldo Contable, solo debe tener una cuenta acreedora configurada' % rule.name)
                    # siguiente linea fue modificada por RXRSolutions
                    move_ids = aml_obj.search(self._get_domain_rules_by_move(partner, payslip, account, rule))
                if move_ids:
                    for move in move_ids:
                        rules_by_move.append((rule, move))
                else:
                    # se retonra el objeto vacio aml_obj para facilitar la programacion
                    rules_by_move.append((rule, aml_obj))
            return rules_by_move

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        # La siguiente línea fue modificada por RXRSolutions
        baselocaldict = {'float_round': tools.float_round, 'categories': categories, 'rules': rules,
                         'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        # La siguiente línea fue modificada por RXRSolutions
        sorted_rule_ids = self.get_sorted_rules(rule_ids)
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            # Seccion modificada por RXRSolutions
            sequence = 0
            sorted_rules_and_moves = _get_rules_by_move(localdict, sorted_rules)
            for rule, move in sorted_rules_and_moves:
                sequence += 1
                key = rule.code + '-' + str(contract.id) + '-' + str(move.id)
                localdict['force_amount'] = 0.0
                if move.amount_residual:
                    localdict['force_amount'] = move.amount_residual  # todo en validar regla en satisfy_condition
                elif not move.full_reconcile_id:
                    # cuando la cuenta no es de tipo por pagar no tiene amount_Residual
                    # en este caso tomamos el valor de debito
                    localdict['force_amount'] = abs(move.debit)
                # fin seccion modificada por RXRSolutions
                # check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    # MODIFICADO POR RXRSolutions PARA PERMITIR SUMAR VARIOS REGISTROS
                    # DE LA MISMA REGLA SALARIAL
                    if localdict.get(rule.code):
                        localdict[rule.code] += tot_rule
                    else:
                        localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id,
                                                          localdict[rule.code] - previous_amount)
                    # FIN MODIFICACION RXRSolutions
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        # La siguiente línea fue modificada por RXRSolutions
                        'name': payslip.get_name_rule(rule),
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        # La siguiente línea fue modificada por RXRSolutions
                        'sequence': sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                        'receivable_move_line_id': move.id,  # RXRSolutions agregado
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    def _get_vacations_amount(self):
        """Obtiene el importe total acumulado por vacaciones del empleado"""
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')
        accumulated = 0.0
        spent = 0.0
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'PROV_VACA':
                    accumulated += line.total
                if line.code == 'VACACIONES_TOMADAS' or line.code == 'VACACIONES_PAGADAS':
                    spent += line.total
        return accumulated - spent

    def _compute_vacation_day_amount(self):
        for rec in self:
            if 'hr_rxr_vacations' in self.env.registry._init_modules:
                if rec.date_from.month > 1:
                    from_date = rec.date_from.replace(month=rec.date_from.month-1)
                else:
                    from_date = rec.date_from.replace(month=12, year=rec.date_from.year-1)
                to_date = rec.date_from - relativedelta.relativedelta(days=1)

                # Busco la fecha de cierre del periodo anterior
                period = self.env['hr.attendance.period'].sudo().search([
                    ('end', '>=', from_date), ('end','<=', to_date)], limit=1)
                date_limit = False
                if period.id:
                    date_limit = period.end
                if not date_limit:
                    date_limit = rec.date_from - relativedelta.relativedelta(days=1)
                total_vacation_days = rec.employee_id.get_vacations_available_to(date_limit)
                total_vacation_money = rec._get_vacations_amount()
                if total_vacation_days > 0:
                    rec.vacation_day_amount = total_vacation_money / total_vacation_days
                else:
                    rec.vacation_day_amount = 0
            else:
                rec.vacation_day_amount = 0

    def _get_vacation_days(self):
        """Obtiene la cantidad de días de vacaciones solicitadas en el periodo de la nómina por el empleado"""

        # Busco el primer periodo activo
        period = self.env['hr.attendance.period'].sudo().search([('state','=','open')], limit=1, order='end')

        vacation_days = 0
        if 'hr_rxr_vacations' in self.env.registry._init_modules:
            approved_vacations = self.env['hr.vacation.planning.request'].sudo().search([
                ('employee_requests_id', '=', self.employee_id.id), ('state', '=', 'approved'),
                ('date_from', '<=', period.end), ('date_to', '>=', period.start)])

            for vacation_request in approved_vacations:
                vacation_days = (min(vacation_request.date_to, self.date_to) - max(vacation_request.date_from, self.date_from)).days + 1
        return vacation_days

    def _compute_last_month_overdraft(self):
        """Obtiene el valor del sobregiro declarado en la nómina anterior."""
        for rec in self:
            rec.last_month_overdraft = 0
            payslip_ids = self.env['hr.payslip'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['done', 'paid'])
            ], order='date_from desc', limit=1)
            for payslip in payslip_ids:
                for line in payslip.line_ids:
                    if line.code == 'SOBREGIROS':
                        rec.last_month_overdraft = line.total

    @api.depends('contract_id','date_to')
    def _compute_fourteenth_adjustment(self):
        # Mes en que culmina el periodo de acumulación para el decimocuarto según la región.
        period_end_month = {'costa_fourteenth_salary': 2, 'sierra_oriente_fourteenth_salary': 7}

        for rec in self:
            rec.total_fourteenth_provision = 0.0
            rec.total_fourteenth_to_pay = 0.0
            if rec.date_to and rec.contract_id.id:
                if rec.date_to.month == period_end_month[rec.contract_id.payment_period_fourteenth]:
                    fourteenth_data = rec._get_fourteenth_period_data(rec)
                    for month, data in fourteenth_data.items():
                        rec.total_fourteenth_provision += data['provision']
                        rec.total_fourteenth_to_pay += rec.unified_basic_salary / 12 * data['worked_days'] / 30 * data['hours_per_week'] / 40

    def _get_fourteenth_period_data(self, pl):
        """
        Obtiene el tiempo trabajado en el último periodo de decimocuarto y el importe provisionado.

        :return: dict con cada uno de los meses trabajados en el último periodo de decimocuarto con la provisión
                realizada en cada uno de ellos y los días trabajados.
        """

        # Mes en que inicia el periodo de acumulación para el decimocuarto según la región.
        period_start_month = {'costa_fourteenth_salary': 3, 'sierra_oriente_fourteenth_salary': 8}
        period_start_date = None

        if pl.date_to.month >= period_start_month[pl.contract_id.payment_period_fourteenth]:
            period_start_date = pl.date_to.replace(
                day=1, month=period_start_month[pl.contract_id.payment_period_fourteenth])
        else:
            period_start_date = pl.date_to.replace(
                day=1, month=period_start_month[pl.contract_id.payment_period_fourteenth], year=pl.date_to.year - 1)

        first_contract_date_start = pl.date_to - relativedelta.relativedelta(
            days=pl.days_in_service - 1, months=pl.months_in_service, years=pl.years_in_service)
        if first_contract_date_start > period_start_date:
            period_start_date = first_contract_date_start

        period_end_date = pl.date_to

        fourteenth_salary = {}
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', pl.employee_id.id),
            ('date_from', '>=', period_start_date),
            ('date_to', '<=', period_end_date),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            if not payslip.date_to.month in fourteenth_salary:
                fourteenth_salary.update({payslip.date_to.month: {'provision': 0.0, 'worked_days': 0.0,
                                                                  'hours_per_week':0.0}})
            month_line = fourteenth_salary[payslip.date_to.month]
            month_line['worked_days'] += payslip.worked_days
            month_line['hours_per_week'] += payslip.contract_id.hours_week
            for line in payslip.line_ids:
                if line.code == 'PROV_DCUARTO_ACUMULADO' or line.code == 'PROV_DCUARTO_MENSUAL':
                    month_line['provision'] += line.total
        return fourteenth_salary

    calendar_days_in_month = fields.Integer(string="Month days", compute="_get_calendar_days_in_month", method=True,
                                            store=True, help='Calendar days in month. '
                                                             'Useful for advanced salary rules.')
    years_in_service_current_contract = fields.Integer(
        string="Years of service in the current contract", compute="_get_time_in_service_current_contract", method=True,
        store=False, help='Years of service in the current contract (Ignoring historical versions), '
                          'up to the payroll cut-off date. Useful for advanced salary rules.')
    months_in_service_current_contract = fields.Integer(
        string="Months of service in the current contract",
        compute="_get_time_in_service_current_contract",
        method=True,
        store=False,
        help='Months of service in the current contract (Ignoring historical versions), '
             'up to the payroll cut-off date. Useful as a build block for advanced salary rules.')
    days_in_service_current_contract = fields.Integer(
        string="Days of service in the current contract",
        compute="_get_time_in_service_current_contract",
        method=True,
        store=False,
        help='Days of service in the current contract (Ignoring historical versions), '
             'up to the payroll cut-off date. Useful as a build block for advanced salary rules')
    years_in_service = fields.Integer(
        string="Years of service",
        compute="_get_time_in_service",
        method=True,
        store=False,
        help='Years of service since employee\'s first contract, up to the payroll cut-off date\n'
             'Used for computing benefits such as the reserve fund and vacations provision',
    ) 
    months_in_service = fields.Integer(
        string="Months of service",
        compute="_get_time_in_service",
        method=True,
        store=False,
        help="Months of service since employee's first contract, up to the payroll cut-off date. "
             "Used for computing benefits such as the reserve fund and vacations provision.")
    days_in_service = fields.Integer(
        string="Days of service",
        compute="_get_time_in_service",
        method=True,
        store=False,
        help="Days of service since employee's first contract, up to the payroll cut-off date. "
             "Used for computing benefits such as the reserve fund and vacations provision.")
    number_service_months = fields.Integer(
        string="Number of service months",
        compute="_get_number_service_months",
        method=True,
        store=False,
        help="Number of different months that the employee has rendered services. "
             "Useful to pay reserve funds from the 13th month")
    days_to_pay_reserve_fund = fields.Integer(
        string="Days to pay reserve fund",
        compute="_get_days_to_pay_reserve_fund",
        method=True,
        store=False,
        help="Number of days for which reserve funds must be paid at employee's 13th month")
    unified_basic_salary = fields.Float(compute='_get_unified_basic_salary', 
                                        string='Unified basic salary', method=True, store=True,
                                        help='The unified basic salary used to calculate the provision '
                                             'of the fourteenth salary')
    net_salary = fields.Float(compute='_get_net_salary', string='Net salary', method=True, store=True,
                              help='The net salary.')
    worked_days = fields.Float(string='Worked days', tracking=True, default=30.0, digits='Payroll', help='')

    currency_id = fields.Many2one('res.currency', string='Currency', help='')
    residual = fields.Monetary(compute='_compute_residual', 
                               string='Residual', method=True, store=True,
                               help='Remaining amount due')
    reconciled = fields.Boolean(compute='_compute_residual',
                                string='Paid/Reconciled', method=True, store=True, readonly=True, 
                                help='It indicates that the payslip has been paid and the journal entry of the payslip has '
                                     'been reconciled with one or several journal entries of payment')
    account_payable_payslip_id = fields.Many2one('account.account', string='Account Payable Payslip',
                                                 help='')
    income_ids = fields.One2many('hr.payslip.input', 'payslip_id', 
                                 string='Additional income',
                                 tracking=True, 
                                 domain=[('type', '=', 'income')],
                                 help='')
    expense_ids = fields.One2many('hr.payslip.input', 'payslip_id', 
                                  string='Additional expense',
                                  tracking=True, 
                                  domain=[('type', '=', 'expense')],
                                  help='')
    other_expense_ids = fields.One2many('hr.payslip.input', 'payslip_id', 
                                        string='Expense with beneficiary',
                                        tracking=True, 
                                        domain=[('type', '=', 'other_expense')],
                                        help='')
    payment_mode = fields.Selection(string='Payment method', related='employee_id.payment_method',
                                    method=True, store=True, help='')
    employee_information = fields.Many2one('hr.personal.expense', compute='_get_employee_information', 
                                           string='Employee Information', method=True, store=False, 
                                           help='')
    state = fields.Selection(selection_add=[('reviewed', 'Revisado'),('paid', 'Paid')])
    provision_move_id = fields.Many2one(
        'account.move', 
        'Asiento Provisiones', 
        readonly=True,
        help='Contiene los asientos correspondientes a las reglas salariales marcadas '
             'como Invisibles, es decir que no se muestran en la nomina impresa.', 
        copy=False
        )
    comment = fields.Text(string='Comments', help='Enter comments to be printed on the payroll.')
    date_from = fields.Date(tracking=True)
    date_to = fields.Date(tracking=True)
    profits_worked_days = fields.Float(
        string='Days worked according to the calendar year',
        compute="_get_profits_worked_days",
        method=True,
        store=True,
        readonly=True,
        digits='Payroll',
        help='Days worked according to the calendar year (Maximum 365 days).')
    vacation_days = fields.Float('Vacations', digits='Payroll',
                                 help='Days of vacations the employee used in the period.')
    vacation_day_amount = fields.Float('Vacations amount per day', compute='_compute_vacation_day_amount',
                                       digits='Payroll',
                                       help='Amount to pay for one day of vacations to the employee.')
    total_fourteenth_provision = fields.Float(compute='_compute_fourteenth_adjustment')
    total_fourteenth_to_pay = fields.Float(compute='_compute_fourteenth_adjustment')
    last_month_overdraft = fields.Monetary(compute='_compute_last_month_overdraft',
                                           string='Overdraft', method=True, store=True,
                                           help='Overdraft from last payroll.')
    import_done_state = fields.Boolean('Import confirmed', default=False)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    _TYPE = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('other_expense', 'Expense with beneficiary'),
    ]
    
    # Columns
    partner_id = fields.Many2one('res.partner', string='Beneficiary', help='')
    type = fields.Selection(_TYPE, string='Type', help='')


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'
    
    # def _get_partner_id(self, credit_account):
    #     """
    #     Invocamos el metodo _get_partner_id para que el partner de los apuntes contables quede seteado en todas las líneas
    #     """
    #     partner_id = super(HrPayslipLine, self)._get_partner_id(credit_account)
    #     if not partner_id:
    #         partner_id = self.slip_id.employee_id.address_home_id.id
    #     return partner_id
    
    # Columns
    # Indica a favor de quien se realizará el asiento contable, útil para retenciones legales.
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 help='Indicates in favor of whom the accounting entry will be made, '
                                      'useful for legal withholding.')
    # Cuando la regla salarial es de tipo "Movimientos contables a netear",
    # indica el asiento contable que se pagará con esta nómina, permitiendo su conciliación.
    receivable_move_line_id = fields.Many2one('account.move.line', string='Accounting seat',
                                              help="""When the salary rule is of the "Accounting movements to net" 
                                              type, it indicates the accounting entry that will be paid with this 
                                              payroll, allowing its reconciliation.""")
    # move_line_ids = fields.One2many(
    #     'account.move.line',
    #     'payslip_line_id',
    #     string='Asientos vinculado',
    #     help="""Los asientos contables asociados a la línea del rol de pagos, útil para
    #     conciliar este asiento con el "Asiento a Pagar" cuando aplique""",
    #     )


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.model
    def default_get(self, fields):
        """
        Cuando el día en curso sea anterior a 25 se deben setar las fechas con el primer y ultimo dia del mes anterior
        """        
        vals = super(HrPayslipRun, self).default_get(fields)
        current = datetime.strptime(convert_datetime_to_ECT(time.strftime('%Y-%m-%d %H:%M:%S'))[:19], '%Y-%m-%d %H:%M:%S').date()
        if current.day < 25:
            if vals.get('date_start'):
                date_start = datetime.strftime(datetime.strptime(vals.get('date_start').isoformat(), '%Y-%m-%d').date() - relativedelta.relativedelta(months=1), '%Y-%m-%d')
                date_end = datetime.strftime(current.replace(day=1)+timedelta(days=-1), '%Y-%m-%d')   
                vals.update({
                    'date_start': date_start,
                    'date_end': date_end
                })
        return vals
    
    
    def unlink(self):
        """
        Invocamos el metodo unlink para eliminar los procesamientos de nóminas solo en estado borrador
        """
        for run in self:
            if run.state == 'done':
                raise ValidationError(u'Solamente puede eliminar procesamientos de nóminas en estado borrador.')
            else:
                #el proceso masivo no elimina las nominas asociadas.
                if run.slip_ids:
                    run.slip_ids.unlink()
        return super(HrPayslipRun, self).unlink()
    
    
    def action_export_additional_data(self):
        """
        Este metodo se encarga de generar y descargar la plantilla con los datos adicionales de la nómina
        """
        book = Workbook(encoding='UTF-8')
        sheet = book.add_sheet('Hoja1')
        sheet.write(0, 0, self.env.user.company_id.name, STYLES['title'])
        sheet.write(1, 0, u'Procesamiento de nómina: ' + self.name, STYLES['title'])

        row_ini, col_ini = 1, 0
        columns = [(u'CI', 3.0), (u'NOMBRE', 6.0), (u'FECHA INGRESO', 3.0)]
        if self.include_worked_days():
            columns.append((u'DIAS TRABAJADOS', 3.0))
        columns.append((u'DEPARTAMENTO', 6.0))
        columns.append((u'CARGO', 6.0))

        columns_code = []
        #Iteramos por las nómina para obtener de los datos adicionales los codigos de reglas
        #salariales que usaremos como nombre de columna
        sorted_slip_ids = sorted(self.slip_ids, key=lambda x: x.mapped('employee_id').mapped('name'))
        for payroll in sorted_slip_ids:
            for line in payroll.income_ids + payroll.expense_ids:
                rule = self.env['hr.salary.rule'].search([('code','=',line.code)])
                column = (line.name + '/' + rule.code, 3.0) if rule.category_id.code else (line.name + '/', 3.0)
                column_code = (line.code + '/' + rule.code, 3.0) if rule.category_id.code else (line.code + '/', 3.0)
                if column_code not in columns_code: #para que tengan siempre la misma longitud sin importar palabras repetidas
                    columns.append(column)
                    columns_code.append(column_code)
        # sheet.write(row_ini + 1, col_ini, u'Nóminas', STYLES['title'])

        initial_col = 5
        if self.include_worked_days():
            initial_col = 6
        for col, (name, size) in enumerate(columns_code, initial_col):
            sheet.write(row_ini + 2, col, name, STYLES['header_white'])
            if size: sheet.col(col).width = cm2width(size)
        for col, (name, size) in enumerate(columns, col_ini):
            sheet.write(row_ini + 3, col, name, STYLES['header'])
            if size: sheet.col(col).width = cm2width(size)
        row_ini += 4
        for payroll in sorted_slip_ids:
            # sheet.write(row_ini, col_ini + 0, payroll.employee_id.address_home_id.vat, style=STYLES['text_table'])
            # sheet.write(row_ini, col_ini + 1, payroll.employee_id.address_home_id.name, style=STYLES['text_table'])
            sheet.write(row_ini, col_ini + 0, payroll.employee_id.identification_id, style=STYLES['text_table'])
            sheet.write(row_ini, col_ini + 1, payroll.employee_id.display_name, style=STYLES['text_table'])

            if payroll.employee_id.last_company_entry_date:
                sheet.write(row_ini, col_ini + 2, payroll.employee_id.last_company_entry_date, STYLES['date_table'])
            else:
                sheet.write(row_ini, col_ini + 2, "", style=STYLES['text_table'])

            if self.include_worked_days():
                sheet.write(row_ini, col_ini + 3, payroll.worked_days, style=STYLES['text_table'])

            if payroll.employee_id.department_id:
                sheet.write(row_ini, col_ini + 4, payroll.employee_id.department_id.name, style=STYLES['text_table'])
            else:
                sheet.write(row_ini, col_ini + 4, "", style=STYLES['text_table'])

            if payroll.employee_id.job_id.position_id:
                sheet.write(row_ini, col_ini + 5, payroll.employee_id.job_id.position_id.name, style=STYLES['text_table'])
            else:
                sheet.write(row_ini, col_ini + 5, "", style=STYLES['text_table'])

            for n in range(initial_col, len(columns)):
                i = n - initial_col
                sheet.write(row_ini, col_ini + n, self.get_value_additional_data(payroll, columns_code[col_ini + i][0].split('/')[0]), style=STYLES['text_table'])
            row_ini += 1
        return self.env['base.file.report'].show_excel(book, self.name + u'.xls')
    
    @api.model
    def include_worked_days(self):
        """
        Este metodo determina si se incluyen o no los dias trabajados en el excel de los datos adicionales de la nomina
        """
        return True
    
    @api.model
    def get_value_additional_data(self, payslip, code):
        """
        Este método devuelve el valor de la regla salaria configurada en la informacion adicional de la nómina
        """
        amount = 0.0
        line_ids = self.env['hr.payslip.input'].search([('payslip_id', '=', payslip.id), 
                                                        ('code', '=', code), 
                                                        ('type','in',['income','expense']),
                                                        ])
        if line_ids:
            amount = line_ids[0].amount
        return amount

    
    def action_export_payroll_excel(self):
        """
        Este metodo se encarga de generar y descargar las nóminas en formato excel
        """
        book = Workbook(encoding='UTF-8')
        sheet = book.add_sheet('Hoja1')
        sheet.write(0, 0, self.env.user.company_id.name, STYLES['title'])
        sheet.write(1, 0, u'Procesamiento de nómina: ' + self.name, STYLES['title'])
        row_ini, col_ini = 2, 0
        columns = [(u'CI', 3.0), (u'NOMBRE', 6.0), (u'FECHA INGRESO', 3.0), (u'DIAS TRABAJADOS', 3.0), (u'DEPARTAMENTO', 6.0), (u'CARGO', 6.0)]
        #Se quiere que salgan todos los roles del período del procesamiento de nomina, incluyendo los que se hicieron
        #a mano fuera del proceso automatico
        all_slip_ids = self.env['hr.payslip'].search([('date_from','>=',self.date_start), ('date_to','<=',self.date_end)])
        sorted_slip_ids = sorted(all_slip_ids, key=lambda x: x.mapped('employee_id').mapped('name'))
        payslip_ids = []

        # date_format = xlwt.XFStyle()
        # date_format.num_format_str = 'dd/mm/yyyy'

        for payslip in sorted_slip_ids:
            payslip_ids.append(payslip.id)
        self.env.cr.execute("""
            select
                sequence,
                name,
                code
            from hr_payslip_line 
            where slip_id in %s
            group by sequence, name, code
            order by sequence
        """,(tuple(payslip_ids if payslip_ids else [0]),))
        rules = self.env.cr.fetchall()
        for rule in rules:
            name = rule[1]
            code = rule[2]
            column = (name, 3.0)
            #En el caso de las horas extras se concatena la cantidad de horas al nombre de la regla, por tal motivo
            #solo dejamos el nombre de la regla como encabezado de columna para que no se dupliquen
            if code in ('HORA_EXTRA_REGULAR', 'HORA_EXTRA_EXTRAORDINARIA'):
                column = (name.split('(')[0], 3.0)
            if column not in columns:
                columns.append(column)
        sheet.write(row_ini + 1, col_ini, u'Nómina general', STYLES['title'])
        for col, (name, size) in enumerate(columns, col_ini):
            sheet.write(row_ini + 2, col, name, STYLES['header'])
            if size: sheet.col(col).width = cm2width(size)
        row_ini += 3
        for payroll in sorted_slip_ids:
            sheet.write(row_ini, col_ini + 0, payroll.employee_id.identification_id, style=STYLES['text_table'])
            sheet.write(row_ini, col_ini + 1, payroll.employee_id.display_name, style=STYLES['text_table'])

            if payroll.employee_id.last_company_entry_date:
                sheet.write(row_ini, col_ini + 2, payroll.employee_id.last_company_entry_date, STYLES['date_table'])
            else:
                sheet.write(row_ini, col_ini + 2, "", style=STYLES['text_table'])

            sheet.write(row_ini, col_ini + 3, payroll.worked_days, style=STYLES['text_table'])

            if payroll.employee_id.department_id:
                sheet.write(row_ini, col_ini + 4, payroll.employee_id.department_id.name, style=STYLES['text_table'])
            else:
                sheet.write(row_ini, col_ini + 4, "", style=STYLES['text_table'])

            if payroll.employee_id.job_id.position_id:
                sheet.write(row_ini, col_ini + 5, payroll.employee_id.job_id.position_id.name, style=STYLES['text_table'])
            else:
                sheet.write(row_ini, col_ini + 5, "", style=STYLES['text_table'])

            for n in range(6, len(columns)):
                sheet.write(row_ini, col_ini + n, self.get_value_payroll_calculation(payroll.id, columns[col_ini + n][0]), style=STYLES['text_table'])
            row_ini += 1
        return self.env['base.file.report'].show_excel(book, self.name + u'.xls')
    
    @api.model
    def get_value_payroll_calculation(self, payroll_id, name):
        """
        Este método devuelve el valor de la regla salarial configurada en la informacion adicional del contrato
        """
        total = 0.0
        line_ids = self.env['hr.payslip.line'].search([('slip_id', '=', payroll_id), ('name', 'ilike', name)])
        if line_ids:
            for line in line_ids:
                total += line.total
        return total
    
    
    def action_recompute_payroll(self):
        """
        Recomputa (metodo compute_sheet) cada nomina, util cuando se ha corregido reglas salariales y
        se requiere ver su efecto en las nominas antes de aprobarlas.
        """
        for payroll in self.slip_ids:
            if payroll.state == 'draft':
                payroll.compute_sheet()

    
    def action_validate_payroll(self):
        """
        Este método se encarga de enviar a estado validado el procesamiento de nóminas y las nominas asociadas
        """
        payroll_not_in_draft = []
        invalid_rule = []
        _logger.info('validando nominas')
        for payroll in self.slip_ids:
            #Verificamos que todas las nóminas esten en estado revisado
            if payroll.state != 'reviewed':
                payroll_not_in_draft.append(payroll.number)
            #Verificamos que las reglas salariales aplicadas a la nómina esten dentro de la estructura
            #salarial del contrato
            for line in payroll.line_ids:
                if line.salary_rule_id.id not in line.contract_id.struct_id.rule_ids.mapped('id'):
                    invalid_rule.append(u'Regla: ' + line.salary_rule_id.name_get()[0][1] + u'; Nómina: ' + payroll.number + u'; Empleado: ' + payroll.employee_id.address_home_id.name_get()[0][1])
        if payroll_not_in_draft:
                list1 = '\n'.join('* ' + pay for pay in payroll_not_in_draft)
                raise UserError(u'Las siguientes nóminas no se encuentran en estado revisado:\n%s' % list1)
        if invalid_rule:
                list2 = '\n'.join('* ' + rule for rule in invalid_rule)
                raise UserError(u'Las siguientes reglas salariales no pertenecen a la estructura salarial del contrato:\n%s' % list2)
        #Por tema de eficiencia se repite la siguiente línea, es mas rapido chequear todo y aprobar al final
        _logger.info('Procesando nominas')
        for payroll in self.slip_ids:
            #comento la siguiente line el metodo
            #action_payslip_done ya ejecuta la funcion compute_sheet
            #payroll.compute_sheet()
            payroll.action_payslip_done()
                
        return self.write({'state': 'done'})

    
    def action_mark_as_reviewed(self):
        for payroll in self.slip_ids:
            payroll.state = 'reviewed'
        return self.write({'state': 'reviewed'})
    
    
    def action_send_to_draft(self):
        """
        Este método se encarga de enviar a estado borrador el procesamiento de nóminas y las nominas asociadas
        """
        payroll_paid = []        
        for payroll in self.slip_ids:
            if payroll.state == 'paid':
                payroll_paid.append(payroll.number)
        if payroll_paid:
            list1 = '\n'.join('* ' + pay for pay in payroll_paid)
            raise UserError(u'Las siguientes nóminas se encuentran en estado "Pagado":\n%s' % list1)
        #Por tema de eficiencia se repite la siguiente línea, es mas rapido chequear todo y aprobar al final
        for payroll in self.slip_ids:
            payroll.action_payslip_cancel()
            payroll.action_payslip_draft() 
        self.write({'state': 'draft'})

    
    def action_send_payslip_mail(self):
        """
        Este metodo levanta el wizard de envio de mail en nominas
        """
        res = self.env.ref('hr_rxr_payroll.send_payslip_email_form_view')
        ctx = {
            'active_model': 'hr.payslip',
            'active_ids': self.slip_ids.mapped('id')
        }
        return {
            'name': u'Enviar roles de pagos por correo',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res.id or False,
            'res_model': 'wizard.send.payslip.mail',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': ctx
        }

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

    @api.onchange('date_start')
    def update_to_date(self):
        """
        Al seleccionar la fecha de inicio del periodo, cambia automáticamente la fecha de fin al último día del mes
        seleccionado.
        :return:
        """
        for rec in self:
            month = rec.date_start.month
            year = rec.date_start.year
            if month in [1, 3, 5, 7, 8, 10, 12]:
                last_day = 31
            elif month in [4, 6, 9, 11]:
                last_day = 30
            elif year % 4 == 0:
                last_day = 29
            else:
                last_day = 28

            rec.date_end = rec.date_start.replace(day=last_day)

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """

        exportFile = self.env['hr.rxr.export.file']
        for rec in self:
            lines = []
            for slip in rec.slip_ids:
                lines.append(Line({"employee_id": slip.employee_id, "value": slip.net_salary}))

            messages = exportFile._create_text_files(lines, "{} ({})".format(rec.name, rec.date_start))
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return exportFile._compress_and_show("{} ({})".format(rec.name, rec.date_start) + '.zip')

    # Columns
    journal_id = fields.Many2one(default=get_journal_wage_id)
    state = fields.Selection(selection_add=[('reviewed', 'Revisado'),('done', 'Done')])

    name = fields.Char(states={'draft': [('readonly', False)], 'reviewed': [('readonly', True)], 'done': [('readonly', True)]})
    date_start = fields.Date(states={'draft': [('readonly', False)], 'reviewed': [('readonly', True)], 'done': [('readonly', True)]})
    date_end = fields.Date(states={'draft': [('readonly', False)], 'reviewed': [('readonly', True)], 'done': [('readonly', True)]})
    credit_note = fields.Boolean(states={'draft': [('readonly', False)], 'reviewed': [('readonly', True)], 'done': [('readonly', True)]})


class PayslipImport(models.TransientModel):
    _inherit = 'base_import.import'

    
    def do(self, fields, columns, options, dryrun=False):
        res = super(PayslipImport, self).do(fields, columns, options, dryrun)
        # Una vez importadas las nóminas, ejecuto la confirmación de cada una de ellas para generar los asientos y
        # cambiar su estado.
        if self.res_model == 'hr.payslip':
            if not dryrun:
                slips = self.env['hr.payslip'].browse(res['ids'])
                for slip in slips:
                    if slip.import_done_state:
                        slip.with_context(without_compute_sheet=True).action_payslip_done()
        return res


# class PayslipDetailsReport(models.AbstractModel):
#     _inherit = 'report.hr_payroll.report_payslipdetails'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Adiciona al dictionary de valores el empleado responsable de Recursos Humanos o False si no está definido.
#         """
#
#         ICPSudo = self.env['ir.config_parameter'].sudo()
#         responsible = False
#         if ICPSudo.get_param('hr.responsible'):
#             if ICPSudo.get_param('hr.responsible') != '':
#                 responsible_id = int(ICPSudo.get_param('hr.responsible'))
#                 responsible = self.env['hr.employee'].sudo().browse(responsible_id)
#
#         result = super(PayslipDetailsReport, self)._get_report_values(docids, data)
#         result['hr_responsible']= responsible
#         return result


# def multi_compute(data):
#     dbname = data.get('dbname')
#     uid = data.get('uid')
#     with api.Environment.manage():
#         with odoo.registry(dbname).cursor() as new_cr:
#             env = api.Environment(new_cr, uid, {})
#
#             payslips = env['hr.payslip']
#
#             for employee in env['hr.employee'].browse(data.get('employee_ids')):
#                 slip_data = env['hr.payslip'].onchange_employee_id(data.get('from_date'),
#                                                                         data.get('to_date'),
#                                                                         employee.id, contract_id=False)
#                 res = {
#                     'employee_id': employee.id,
#                     'name': slip_data['value'].get('name'),
#                     'struct_id': slip_data['value'].get('struct_id'),
#                     'contract_id': slip_data['value'].get('contract_id'),
#                     'payslip_run_id': data.get('active_id'),
#                     'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
#                     'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
#                     'date_from': data.get('from_date'),
#                     'date_to': data.get('to_date'),
#                     'credit_note': data.get('credit_note'),
#                     'company_id': employee.company_id.id,
#                     'journal_id': data.get('journal_id'),
#                 }
#                 payslips += env['hr.payslip'].create(res)
#
#             payslips.compute_sheet()

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    """ Haciendo esta función multihilos para incrementar el rendimiento al procesar múltiples empleados."""
    
    def compute_sheet(self):
        start = datetime.now()
        print("Start: {}".format(start))

        journal_id = False
        if self.env.context.get('active_id'):
            journal_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id')).journal_id.id

        # payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        # for employee in self.env['hr.employee'].browse(data['employee_ids']):
        #     slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
        #     res = {
        #         'employee_id': employee.id,
        #         'name': slip_data['value'].get('name'),
        #         'struct_id': slip_data['value'].get('struct_id'),
        #         'contract_id': slip_data['value'].get('contract_id'),
        #         'payslip_run_id': active_id,
        #         'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
        #         'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
        #         'date_from': from_date,
        #         'date_to': to_date,
        #         'credit_note': run_data.get('credit_note'),
        #         'company_id': employee.company_id.id,
        #         'journal_id': journal_id,
        #     }
        #     payslips += self.env['hr.payslip'].create(res)

        slip_data = {'employee_ids': data['employee_ids'], 'from_date': from_date, 'to_date': to_date,
                     'active_id': active_id, 'journal_id': journal_id, 'credit_note': run_data.get('credit_note'),
                     'dbname': self.env.cr.dbname, 'uid': self.env.uid}

        def split_data(data, wanted_parts=1):
            alist = data.get('employee_ids')
            split_list = []
            length = len(alist)

            for i in range(wanted_parts):
                data_chunk = data.copy()
                sublist = alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
                if len(sublist) > 0:
                    data_chunk.update({'employee_ids': sublist})
                    split_list.append(data_chunk)

            return split_list

        # Obteniendo de los parámetros de sistema la cantidad de hilos que correrán concurrentes.
        threads = 10
        ICPSudo = self.env['ir.config_parameter'].sudo()
        responsible = False
        if ICPSudo.get_param('hr.payslip.run.threads'):
            if ICPSudo.get_param('hr.payslip.run.threads') != '':
                threads = int(ICPSudo.get_param('hr.payslip.run.threads', 10))

        # Dividiendo los datos en tantos hilos se empleen
        parts = split_data(slip_data, threads)

        # Ejecutando método de cálculo de forma concurrente
        threads = []
        for idx, part in enumerate(parts):
            threads.append(threading.Thread(target=self.multi_compute, args=(part,)))
            threads[idx].start()
            print('\tT{} started at {}'.format(idx, datetime.now()))

        # Esperando que terminen todos los hilos para continuar.
        for idx, thread in enumerate(threads):
            thread.join()
            print('\tT{} ended at {}'.format(idx, datetime.now()))

        # payslips.compute_sheet()
        print("Ended at {}".format(datetime.now() - start))
        return {'type': 'ir.actions.act_window_close'}

    def multi_compute(self, data):
        """ Este método realiza la creación de la nómina para cada empleado y su cómputo."""

        dbname = data.get('dbname')
        uid = data.get('uid')
        with api.Environment.manage():
            with odoo.registry(dbname).cursor() as new_cr:
                env = api.Environment(new_cr, uid, {})

                payslips = env['hr.payslip']

                for employee in env['hr.employee'].browse(data.get('employee_ids')):
                    print("\t\tStart proc employee: {} {}".format(employee.display_name, datetime.now()))
                    slip_data = env['hr.payslip'].onchange_employee_id(data.get('from_date'),
                                                                       data.get('to_date'),
                                                                       employee.id, contract_id=False)
                    res = {
                        'employee_id': employee.id,
                        'name': slip_data['value'].get('name'),
                        'struct_id': slip_data['value'].get('struct_id'),
                        'contract_id': slip_data['value'].get('contract_id'),
                        'payslip_run_id': data.get('active_id'),
                        'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                        'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                        'date_from': data.get('from_date'),
                        'date_to': data.get('to_date'),
                        'credit_note': data.get('credit_note'),
                        'company_id': employee.company_id.id,
                        'journal_id': data.get('journal_id'),
                    }
                    # payslips += env['hr.payslip'].create(res)
                    payslip = env['hr.payslip'].create(res)
                    payslip.compute_sheet()
                    print("\t\tEnd proc employee: {} {}".format(employee.display_name, datetime.now()))
                # print("\t\tCompute start {}".format(datetime.now()))
                # payslips.compute_sheet()
                # print("\t\tCompute end  {}".format(datetime.now()))
