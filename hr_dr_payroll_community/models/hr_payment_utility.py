# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round as round
from datetime import date, datetime, time, timedelta
import base64, io, csv
import time
from dateutil.relativedelta import relativedelta
import calendar


HEAD = [
    'Cédula',
    'Nombres',
    'Apellidos',
    'Género (Masculino=M ó Femenino=F)',
    'Ocupación',
    'Cargas familiares',
    'Días laborados (360 días equivalen a un año)',
    'Tipo de Pago Utilidad(Pago Directo=P. Depósito MDT=D Para Declaraciones < 2015 y Depósito Empresa = E para Declaraciones >= 2015. Acreditación en Cuenta=A. Retención Pago Directo=RP. Retención Depósito MDT=RD. Retención Acreditación en Cuenta=RA)',
    'JORNADA PARCIAL PERMANENTE(Ponga una X si el trabajador tiene un JORNADA PARCIAL PERMANENTE)',
    'DETERMINE EN HORAS LA JORNADA PARCIAL PERMANENTE SEMANAL ESTIPULADO EN EL CONTRATO',
    'DISCAPACITADOS(Ponga una X si el trabajador tiene discapacidad)',
    'RUC DE LA EMPRESA COMPLEMENTARIA O DE UNIFICACION',
    'DECIMOTERCERO VALOR PROPORCIONAL AL TIEMPO LABORADO YEAR',
    'DECIMOCUARTO VALOR PROPORCIONAL AL TIEMPO LABORADO YEAR',
    'PARTICIPACION DE UTILIDADES LAST_YEAR',
    'SALARIOS PERCIBIDOS YEAR',
    'FONDOS DE RESERVA YEAR',
    'COMISIONES YEAR',
    'BENEFICIOS ADICIONALES EN EFECTIVO YEAR',
    'Anticipo de Utilidad',
    'Retención Judicial',
    'Impuesto Retención',
    'Información MDT(No ingrese datos en esta columna)',
    'Tipo de Pago Salario Digno(Pago Directo=P. Depósito MDT=D Para Declaraciones < 2015 y Depósito Empresa = E para Declaraciones >= 2015. Acreditación en Cuenta=A)'
]


class Line(object):
    """Clase auxiliar para la generación de ficheros"""
    def __init__(self, dict):
        self.__dict__ = dict


class HrPaymentUtility(models.Model):
    _name = 'hr.payment.utility'
    _description = 'Payment utility'
    #_inherit = ['hr.dr.export.file']
    _inherit = ['hr.generic.request']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc"

    _hr_mail_templates = {'confirm': 'hr_dr_payroll.email_template_confirm_payment_utility',
                          'approve': 'hr_dr_payroll.email_template_confirm_approve_payment_utility',
                          'reject': 'hr_dr_payroll.email_template_confirm_reject_payment_utility',
                          'cancel': 'hr_dr_payroll.email_template_confirm_cancelled_payment_utility',
                          'paid': 'hr_dr_payroll.email_template_paid_payment_utility'}
    _hr_notifications_mode_param = 'payment.utility.notifications.mode'
    _hr_administrator_param = 'payment.utility.administrator'
    _hr_second_administrator_param = 'payment.utility.second.administrator'

    # TODO: Solo puede existir un pago de utilidades en estado pagado por año fiscal

    def _default_start_date(self):
        start_date = datetime.utcnow().date() + relativedelta(day=1,month=1,years=-1)
        return start_date

    def _default_date(self):
        date = datetime.utcnow()
        date = self.convert_utc_time_to_tz(date)
        return date

    @api.onchange('start_date')
    def onchange_start_date(self):
        if self.start_date:
            self.end_date = self.start_date + relativedelta(day=31, month=12)
            self.fiscal_year = self.start_date.year

    @api.onchange('utility_value','percent_employee','percent_family')
    def onchange_utility_value(self):
        if self.utility_value:
            precision = self.env['decimal.precision'].precision_get('Payroll')
            self.utility_value_to_distribute = round(
                (self.utility_value * (self.percent_employee + self.percent_family) / 100),precision)

    # El inicio del periodo debe ser el primero de enero del año seleccionado.
    @api.constrains('start_date')
    def _check_start_date(self):
        for utility in self:
            if utility.start_date:
                if int(utility.start_date.day) != 1 or int(utility.start_date.month) != 1:
                    raise ValidationError(
                        'The beginning of the period must be the first of January of the selected year.')
        return True

    @api.onchange('start_date','utility_value','percent_employee','percent_family')
    def on_change_inputs(self):
        self.line_ids = [(6, 0, [])]




    def action_calculate(self):
        """
        Este método calcula la utilidad en función de los valores ingresados

        Si la planificación de trabajo del contrato tiene 8 horas como promedio al día:
        Los días trabajados por el colaborador en el período de cálculo de utilidades,
        para efectos del cálculo de la utilidad es la suma de los dias trabajados en cada contrato dentro del período.

        Si la planificación de trabajo del contrato tiene menos de 8 horas como promedio al día:
        Se debe obtener los días trabajados en base a una regla de 3
        En 360 días del año debes trabajar 2880 horas. (8 horas diarias sin asumir descansos)
        En x(días trabajados para el cálculo de utilidad) los días trabajados según el contrato * el promedio de horas
        al día de la planificación de trabajo del contrato
        """

        # Eliminar detalles de utilidad previamente calculados
        line_ids = self.env['hr.payment.utility.line'].with_context(active_test=False).search(
            [('payment_utility_id', '=', self.id),])
        if line_ids:
            line_ids.unlink()

        results = []
        lines = self.env['hr.payment.utility.line']

        total_worked_days = 0.0
        total_family_loads = 0.0
        all_employees = self.env['hr.employee'].with_context(
            active_test=False).search([
            ('state','in',['affiliate','temporary','unemployed','retired'])])

        for e in all_employees:

            worked_days = 0
            contract_ids = self.env['hr.contract'].get_all_contract_utility(e, self.start_date, self.end_date)

            for contract in self.env['hr.contract'].browse(contract_ids):

                start_date = contract.date_start
                if self.start_date > contract.date_start:
                    start_date = self.start_date

                end_date = self.end_date
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
                total_worked_days += worked_days
                family_loads = self.get_family_loads_by_employee(e)
                total_family_loads += worked_days * family_loads
                results.append({'employee_id': e.id, 'employee_state': e.state, 'worked_days': worked_days,
                                'family_loads': family_loads})

        self.total_worked_days = total_worked_days
        self.total_family_loads = total_family_loads

        for result in results:
            employee = self.env['hr.employee'].browse(result.get('employee_id'))
            employee_state = result.get('employee_state')
            worked_days = result.get('worked_days')
            family_loads = result.get('family_loads')
            vals = self.get_line_utility(employee, employee_state, worked_days, family_loads)
            line = lines.new(vals)
            lines += line
        self.line_ids = lines

        self.state = 'calculated'

        return True

    def notify_treasury(self):
        emails = set()
        config_parameter = self.env['ir.config_parameter'].sudo()
        if config_parameter.get_param('treasury.managers.ids'):
            if config_parameter.get_param('treasury.managers.ids') != '':
                for id in config_parameter.get_param('treasury.managers.ids').split(','):
                    employee_id = int(id)
                    employee = self.env['hr.employee'].sudo().search([('id', '=', employee_id)], limit=1)
                    if len(employee) > 0:
                        if employee.work_email != '':
                            emails.add(employee.work_email)
                        else:
                            emails.add(employee.private_email)
        emails_to = ','.join(emails)

        template = self.env.ref('hr_dr_payroll.email_template_utility_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def _family_load_apply_utility(self, fl):
        def calculte_children_age(children, end_date):
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=end_date.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years

        if ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son') and calculte_children_age(fl, self.end_date) < 18) or \
                ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son') and fl.disability) or \
                (fl.relationship == 'spouse' or fl.relationship == 'wife' or fl.relationship == 'husband' or fl.relationship == 'cohabitant'):
            return True
        return False

    def get_family_loads_by_employee(self, employee):
        """
        Retorna el número de cargas familiarias que se deben tener en cuenta para el cálculo de las utilidades.
        """
        def calculte_children_age(children, end_date):
            """
            Este método calcula la edad en base a la fecha de nacimiento y la fecha de corte de las utilidades.
            """
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=end_date.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years

        amount_family_loads = 0
        for fl in employee.family_load_ids:
            #En el caso de los hijos no se debe preguntar la edad a la fecha, sino la edad que tenia a la fecha de corte de las utilidades
            #Por ejemplo si estoy pagando las utilidades en abril 2019 debo preguntar la edad al 31/12/2018
            #Se tiene en cuenta los hijos menores de 18 años
            if ((fl.relationship == 'daughter' or fl.relationship == 'son') and calculte_children_age(fl, self.end_date) < 18) or \
                    ((fl.relationship == 'daughter' or fl.relationship == 'son') and fl.disability) or \
                    (fl.relationship == 'spouse' or fl.relationship == 'wife' or fl.relationship == 'husband' or fl.relationship == 'cohabitant'):
                amount_family_loads += 1
        return amount_family_loads

    def get_line_utility(self, employee, employee_state, worked_days, family_loads):
        """
        Este metodo crea las lineas de la utilidad por cada colaborador.
        formula utilidad_x_cargas:
            utilidad_x_cargas = (utilidad_5_% * Factor A / Factor B )
        donde:
            utilidad_5_% = utilidad del 5 porciento / total dias trabajados.
            Factor A =  numero de dias del trabajador * numero de cargas.
            Factor B =  sumatoria de factor A de todos los trabajadores.
        """
        precision = self.env['decimal.precision'].precision_get('Payroll')
        amount_10_percent = round(((self.utility_value * (self.percent_employee / 100.00)) / self.total_worked_days)
                                  * worked_days if self.total_worked_days > 0 else 0,precision)

        amount_5_percent = 0
        judicial_withholding = 0
        amount_judicial_withholding = 0
        judicial_withholding_ids = []
        if self.total_family_loads > 0:
            amount_5_percent = round(((self.utility_value * (self.percent_family / 100.00)))
                                     * ((family_loads * worked_days) / self.total_family_loads)
                                     if self.total_family_loads > 0 else 0, precision)
            if family_loads > 0:
                for fl in employee.family_load_ids:
                    if self._family_load_apply_utility(fl) and fl.judicial_withholding_id:
                        judicial_withholding += 1

                unit = round(amount_5_percent / family_loads , precision)

                if unit * family_loads > amount_5_percent:
                    # Se redondeo por exceso la div
                    #todo
                    pass
                elif unit * family_loads < amount_5_percent:
                    # Se redondeo por defecto la div
                    pass

                for fl in employee.family_load_ids:
                    if self._family_load_apply_utility(fl) and fl.judicial_withholding_id:
                        # Crear detalle de retención judicial

                        judicial_withholding_obj = {
                            'amount': unit,
                            'family_load_id': fl.id,
                            'judicial_withholding_id': fl.judicial_withholding_id.id,
                        }

                        judicial_withholding_ids.append((0, 0, judicial_withholding_obj))


                amount_judicial_withholding = unit * judicial_withholding
        else:
            amount_5_percent = round(((self.utility_value * (self.percent_family / 100.00)) / self.total_worked_days)
                                     * worked_days if self.total_worked_days > 0 else 0,precision)

        total_utility = round(amount_10_percent + amount_5_percent, precision)
        # advace_utility = self.get_advance_utility(employee)
        advace_utility = 0
        total_receive = round(
            amount_10_percent + amount_5_percent - amount_judicial_withholding - advace_utility, precision)
        payment_mode = False
        if employee.payment_method == 'CHQ':
            payment_mode = 'P'
        elif employee.payment_method == 'CTA':
            payment_mode = 'A'

        return {
            'employee_id': employee.id,
            'state': employee_state,
            'worked_days': worked_days,
            'family_loads': family_loads,
            'judicial_withholding': judicial_withholding,
            'amount_judicial_withholding': amount_judicial_withholding,
            'amount_10_percent': amount_10_percent,
            'amount_5_percent': amount_5_percent,
            'total_utility': total_utility,
            'payment_mode': payment_mode,
            'total_receive': total_receive,
            'advance_utility': advace_utility,
            'judicial_withholding_ids': judicial_withholding_ids,
        }

    # 
    # def get_advance_utility(self, employee):
    #     advance_value = 0
    #     args = self.get_args_search('Anticipo', employee)
    #     advances = self.env['account.move.line'].search(args)
    #     if advances:
    #         advance_value = sum(advances.mapped('debit'))
    #     return advance_value
    #
    # def get_args_search(self, type, employee):
    #     args =[]
    #     if type == 'Anticipo':
    #         accounts = self.env.user.company_id.mapped('advance_utility_account_id').mapped('id')
    #         if not accounts:
    #             raise UserError(u'Por favor, configure la cuenta de anticipo de utilidades.')
    #         args = [
    #             ('account_id','in', tuple(accounts)),
    #             ('date_maturity','>=', self.start_date),
    #             ('date_maturity','<=', self.date),
    #             ('partner_id','=', employee.address_home_id.commercial_partner_id.id)
    #         ]
    #     return args

    def action_validate(self):
        """
        Creamos el asiento contable por cada colaborador y enviamos a estado validado el pago de utilidades
        """
        company = self.env.user.company_id
        if not company.utility_journal_id:
            raise ValidationError(u'Por favor, configure el diario de pago de utilidades en la compañía.')
        if not company.utility_account_id:
            raise ValidationError(u'Por favor, configure la cuenta de utilidad en la compañía.')
        if not company.judicial_retention_account_id:
            raise ValidationError(u'Por favor, configure la cuenta de retenciones judiciales en la compañía.')
        # if not company.advance_utility_account_id:
        #     raise ValidationError(u'Por favor, configure la cuenta de anticipos utilidades en la compañía.')
        if not company.employee_participation_account_id:
            raise ValidationError(u'Por favor, configure la cuenta de participación trabajadores en la compañía.')
        for line in self.line_ids:
            self.launch_make_move(line)
        # TODO: copiar automaticamente el valor al RDEP
        # utilizando el metodo action_utility_rdep
        return self.write({'state': 'done'})

    def action_utility_rdep(self):
        """
        Se copia la participacion en utilidades a la tabla del impuesto a la renta del colaborador
        en base al año de la fecha de contabilizacion de las utilidades y el año fiscal de la
        informacion del colaborador.
        """
        for utility in self:
            for line in utility.line_ids:
                # Se suma un año al año fiscal, Ej. las utilidades del 2018 se registran en el 2019.
                fiscal_year = self.fiscal_year + 1
                informations = self.env['hr.personal.expense'].search(
                    [('rent_tax_table_id.fiscal_year','=',fiscal_year), ('employee_id','=',line.employee_id.id)])
                for information in informations:
                    information.utility = line.total_utility

    def launch_make_move(self, line):
        """
        Metodo hook
        """
        line.make_move()

    def action_paid(self):
        """
        Este método levanta un wizard para registrar los pago de utilidades
        """
        res = self.env.ref('hr_dr_payroll.wizard_payment_utility_form')
        return {
            'name': u'Registrar pago de utilidades',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res and res.id or False,
            'res_model': 'wizard.payment.utility',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new'
        }

    def action_all_cancel(self):
        """
        Cancelamos y eliminamos el asiento contable y enviamos a estado cancelado el pago de utilidades
        """
        moves = self.line_ids.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        #Se setea con 0.0 la participacion en utilidades en la tabla del impuesto a la renta del colaborador
        #en base al año de la fecha de contabilizacion de las utilidades y el año fiscal de la informacion
        #del colaborador
        for line in self.line_ids:
            fiscal_year = self.fiscal_year + 1
            informations = self.env['hr.personal.expense'].search(
                [('rent_tax_table_id.fiscal_year','=',fiscal_year), ('employee_id','=',line.employee_id.id)])
            for information in informations:
                information.utility = 0.0
        return self.write({'state': 'cancelled'})

    def action_send_draft(self):
        return self.write({'state': 'draft'})

    def action_view_payment(self):
        """
        Este método muestra los pagos generados por el pago de utlidades
        """
        action = 'account.action_account_payments_payable'
        view = 'ecua_payment.view_account_payment_supplier_form'
        action = self.env.ref(action)
        result = action.read()[0]
        payment_ids = self.env['account.payment'].search([('payment_utility_id','=',self.id)]).mapped('id')
        if len(payment_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(payment_ids) + ")]"
        elif len(payment_ids) == 1:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = payment_ids[0]
        else:
            raise ValidationError(u'No existen pagos registrados.')
        return result

    def _get_d13_yearly(self, date_from, date_to, employee_id):
        """
        obtenemos el valor de decimo tercero anual del período actual de utilidad
        """

        d13 = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:

                if line.code == 'PROV_DTERCERO_MENSUAL':
                    d13 += line.total

            #
            PROV_DTERCERO = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_DTERCERO_MENSUAL')
            if not any(PROV_DTERCERO):
                d13 += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_DTERCERO_ACUMULADO').mapped('total'))

        return d13

    def _get_d14_yearly(self, date_from, date_to, employee_id):
        """
        obtenemos el valor de decimo cuarto anual del período actual de utilidad
        """
        d14 = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:

                if line.code == 'PROV_DCUARTO_MENSUAL':
                    d14 += line.total

            PROV_DCUARTO = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_DCUARTO_MENSUAL')
            if not any(PROV_DCUARTO):
                d14 += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_DCUARTO_ACUMULADO').mapped('total'))

            return d14

    def _get_last_utility(self, year, employee_id):
        """
        obtenemos el valor de utilidad
        """
        line = self.env['hr.payment.utility.line'].search(
            [('fiscal_year', '=', year-1), ('employee_id', '=', employee_id.id),
             ('state_utility', 'in', ['done','paid'])] , limit=1)
        if line:
            return line.total_utility
        else:
            return 0.00

    def _get_payment_mode_last_living_wage(self, year, employee_id):

        line = self.env['pay.living.wage.line'].search(
            [('fiscal_year', '=', year-1), ('employee_id', '=', employee_id.id),
             ('value', '>', 0), ('state', 'in', ['paid'])], limit=1)
        if line:
            return "A"
        else:
            return "P"

    def _get_salary_yearly(self, date_from, date_to, employee_id):
        """
        obtenemos el valor salario por colaborador
        """
        wage = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'BASIC' or line.code == 'VACACIONES_TOMADAS' or line.code == 'RETROACTIVO':
                    wage += line.total

            return wage

    def _get_reserve_funds_yearly(self, date_from, date_to, employee_id):
        """
        obtenemos el valor fondo de reserva del período actual de utilidad
        """
        rf = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'PROV_FOND_RESERV_MENSUAL':
                    rf += line.total

            PROV_FOND_RESERV = payslip.details_by_salary_rule_category.filtered(
                lambda x: x.code == 'PROV_FOND_RESERV_MENSUAL')
            if not any(PROV_FOND_RESERV):
                rf += sum(payslip.details_by_salary_rule_category.filtered(
                    lambda x: x.code == 'PROV_FOND_RESERV_ACUMULADO').mapped('total'))

            return rf

    def _get_commissions_yearly(self, date_from, date_to, employee_id):
        """
        obtenemos el valor de los ingresos anuales excepto el salario del período actual de utilidad
        """

        comisions = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'BONO_DE_VENTAS' or line.code == 'COMISIONES':
                    comisions += line.total

            return comisions

    def _get_additional_cash_benefits_yearly(self, date_from, date_to, employee_id):
        other_incomes = 0.00

        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'ALIMENTACION' or line.code == 'SUBSIDIO_GUARDERIA' or line.code == 'TRANSPORTE' \
                        or line.code == 'REEMPLAZOS' or line.code == 'OTROS_INGRESOS_APORTABLES' \
                        or line.code == 'BONIFICACIONES_POR_CUMPLIMIENTO' or line.code == 'BONO_VARIABLE_RENTABILIDAD':
                    other_incomes += line.total

            return other_incomes

    def action_generar_csv(self):
        self = self[0]
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=';')
        HEAD_WITH_YEAR = []
        YEAR = self.fiscal_year
        LAST_YEAR = YEAR - 1
        for h in HEAD:
            h = h.replace("LAST_YEAR", str(LAST_YEAR))
            h = h.replace("YEAR", str(YEAR))
            HEAD_WITH_YEAR.append(h)

        writer.writerow(HEAD_WITH_YEAR)
        line_ids = sorted(self.line_ids, key=lambda x: x.mapped('employee_id').mapped('surnames'))
        code_iess = self.line_ids.mapped('employee_id').filtered(lambda x: not x.mapped('contract_id').iess_sector_code)
        if code_iess:
            employees = '\n'.join('- ' + e.name for e in code_iess)
            raise UserError(u'Las siguientes empleados no tienen ingresado el código sectorial :\n%s' % employees)

        precision = self.env['decimal.precision'].precision_get('Payroll')
        for line in line_ids:
            filaemp = []

            filaemp.append(line.employee_id.identification_id)
            filaemp.append(line.employee_id.names)
            filaemp.append(line.employee_id.surnames)
            filaemp.append('M' if line.employee_id.gender == 'male' else 'F')

            codeIESS = line.employee_id.contract_id.iess_sector_code if line.employee_id.contract_id.iess_sector_code else ''
            filaemp.append(codeIESS)
            filaemp.append(line.family_loads)
            filaemp.append(int(line.worked_days))
            # filaemp.append(line.payment_mode)
            filaemp.append("A")

            JPP = False
            if line.employee_id.contract_id.resource_calendar_id.hours_per_day < 8:
                JPP = True
            filaemp.append('X' if JPP else '')
            filaemp.append(line.employee_id.contract_id.resource_calendar_id.hours_work_per_week if JPP else '')

            if line.employee_id.disability:
                filaemp.append('X')
            else:
                if line.employee_id._any_sons_disability():
                    filaemp.append('X')
                else:
                    filaemp.append('')
            filaemp.append(self.get_ruc_company_complement(line.employee_id.contract_id))

            filaemp.append(self._get_d13_yearly(self.start_date, self.end_date, line.employee_id))  # decimo tercero anual
            filaemp.append(self._get_d14_yearly(self.start_date, self.end_date, line.employee_id))  # decimo cuarto anual
            filaemp.append(self._get_last_utility(self.fiscal_year, line.employee_id))  # participacion utilidades año anterior
            filaemp.append(self._get_salary_yearly(self.start_date, self.end_date, line.employee_id))  # salarios anuales
            filaemp.append(self._get_reserve_funds_yearly(self.start_date, self.end_date, line.employee_id))  # fondos de reserva anuales
            filaemp.append(self._get_commissions_yearly(self.start_date, self.end_date, line.employee_id))  # comisiones
            filaemp.append(self._get_additional_cash_benefits_yearly(self.start_date, self.end_date, line.employee_id))  # Beneficios adicionales en efectivo
            filaemp.append(str(round(line.advance_utility, precision)))
            filaemp.append(str(round(line.amount_judicial_withholding, precision)))
            filaemp.append(0) # Impuesto a la renta por las utilidades recibidas
            filaemp.append('')

            # Salario digno
            filaemp.append(self._get_payment_mode_last_living_wage(self.fiscal_year,line.employee_id))
            writer.writerow(filaemp)

        out = buf.getvalue()
        try:
            out = out.decode('utf-8')
        except AttributeError:
            pass
        out = base64.encodebytes(out.encode('iso-8859-1'))
        buf.close()
        return self.env['base.file.report'].show(out, 'Utilidades - '+ str(self.fiscal_year) +'.csv')

    @api.model
    def get_ruc_company_complement(self, contract):
        """
        Este metodo devuelve el "RUC Empresa de Servicios", va ser implementado en modulos especificos
        """
        if contract.service_company_RUC:
            return contract.service_company_RUC
        else:
            return ""

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        return self

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """
        for rec in self:
            lines = []
            for line in rec.line_ids:
                lines.append(Line({"employee_id": line.employee_id, "value": line.total_receive}))

            messages = self._create_text_files(lines, _("Payment of utilities from {} to {}").format(
                rec.start_date.strftime("%d/%m/%Y"), rec.end_date.strftime("%d/%m/%Y")))
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return self._compress_and_show(_("Payment of utilities from {} to {}").format(
                rec.start_date.strftime("%d-%m-%Y"), rec.end_date.strftime("%d-%m-%Y")) + '.zip')

    # Fields
    start_date = fields.Date(
        string='Period start',
        default=_default_start_date,
        help='', tracking=True
        )
    end_date = fields.Date(
        string='Period end',
        help='', tracking=True
        )
    fiscal_year = fields.Integer(
        string='Fiscal year',
        tracking=True,
        help=''
        )
    state = fields.Selection(selection_add=[('calculated', 'Calculated'),('done', 'Done'),('paid', 'Paid')])
    utility_value = fields.Float(
        string='Total profit of the company',
        digits='Payroll',
        tracking=True,
        help='Total profit of the company.'
    )
    utility_value_to_distribute = fields.Float(
        string='Utility to distribute',
        digits='Payroll',
        tracking=True,
        help="It represents the sum of the percentages to be distributed among the collaborators and the family loads on the total utility of the company. Currently 15 percent of the company's total profit."
    )
    percent_employee = fields.Float(
        string='Percentage to distribute among collaborators',
        default=10,
        digits='Payroll',
        tracking=True,
        help=''
        )
    percent_family = fields.Float(
        string='Percentage to be distributed among family loads',
        default=5,
        digits='Payroll',
        tracking=True,
        help=''
        )
    date = fields.Date(
        string='Posting date',
        #default=fields.Date.today(),
        default=_default_date,
        help='Date for the generation of the accounting entry.', tracking=True
        )
    total_worked_days = fields.Float(
        string='Total worked days',
        digits='Payroll',
        tracking=True,
        help=''
        )
    # Multiplica en cada detalle las cargas familiares por los días trabajados y se suman todos los resultados.
    total_family_loads = fields.Float(
        string='Total family loads multiplied by total days worked',
        digits='Payroll',
        tracking=True,
        help='Multiply in each detail the family loads by the days worked and add all the results.'
        )
    line_ids = fields.One2many(
        'hr.payment.utility.line',
        'payment_utility_id',
        help=''
        )


class HrPaymentUtilityLine(models.Model):
    _name = 'hr.payment.utility.line'
    _description = 'Payment utility detail'
    _inherit = ['mail.thread']
    _order = "payment_utility_id,state,employee_id"

    def make_move(self):
        name = u'Utilidades del año ' + str(self.payment_utility_id.fiscal_year)
        move_header = {
            'journal_id': self.env.user.company_id.utility_journal_id.id,
            'date': self.payment_utility_id.date,
            'ref': name,
            'narration': name + u'. Colaborador: ' + self.employee_id.name
        }
        move_lines = self._compute_move_lines(move_header)
        move = self._create_account_moves(move_header, move_lines)
        self.move_id = move.id

    def _compute_move_lines(self, move_header, division=False):
        """
        Crea las lineas de asiento contable
        """
        # TODO: si se aumenta mas campos tomar en cuenta que el
        # division utiliza un subjeto con los mismos campos.
        line = self
        if division:
            line = division
        line_ids = []
        name = move_header['ref']
        partner = line.employee_id.address_home_id.commercial_partner_id
        company = self.env.user.company_id
        # Asiento de retenciones judiciales
        if line.amount_judicial_withholding:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': company.judicial_retention_account_id.id,
                'credit': line.amount_judicial_withholding
            }))
        # Asiento de anticipo utilidades
        if line.advance_utility:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': company.advance_utility_account_id.id,
                'credit': line.advance_utility
            }))
        # Asiento de participación trabajadores
        if line.total_receive:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': company.employee_participation_account_id.id,
                'credit': line.total_receive,
            }))
        # Asiento de utilidad
        if line.total_utility > 0.0:
            line_ids.append((0, 0, {
                'name': name,
                'partner_id': partner.id,
                'account_id': company.utility_account_id.id,
                'debit': line.total_utility
            }))
        return line_ids

    def _create_account_moves(self, move_dict, line_ids):
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return move

    _PAYMENT_MODE = [
        ('P', u'Pago Directo'),
        ('D', u'Depósito MDT'),
        ('E', u'Depósito Empresa'),
        ('A', u'Acreditación en Cuenta'),
        ('RP', u'Retención Pago Directo'),
        ('MDT', u'Retención Depósito MDT'),
        ('RA', u'Retención Acreditación en Cuenta')
    ]
    # Columns
    employee_id = fields.Many2one(
        'hr.employee',
        string='Collaborator',
        ondelete='cascade',
        help='', tracking=True
    )
    state = fields.Selection([
        ('affiliate', 'Affiliate'),
        ('temporary', 'Temporary'),
        ('intern', 'Intern'),
        ('unemployed', 'Unemployed'),
        ('retired', 'Retired')
    ], string='Employee state', tracking=True)
    worked_days = fields.Float(
        string='Worked days',
        digits='Payroll',
        help='', tracking=True
        )
    family_loads = fields.Float(
        string='Number of family loads',
        digits='Payroll',
        help='', tracking=True
        )
    judicial_withholding = fields.Float(
        string='Number of judicial withholding',
        digits='Payroll',
        help='', tracking=True
    )
    advance_utility = fields.Float(
        string='Utility advance',
        digits='Payroll',
        help='', tracking=True
    )
    amount_judicial_withholding = fields.Float(
        string='Judicial withholding',
        digits='Payroll',
        help='', tracking=True
    )
    amount_10_percent = fields.Float(
        string='To receive based on the percentage to distribute among collaborators',
        digits='Payroll',
        help='', tracking=True
        )
    amount_5_percent = fields.Float(
        string='To receive based on the percentage to be distributed among family loads',
        digits='Payroll',
        help='', tracking=True
        )
    total_utility = fields.Float(
        string='Utility',
        digits='Payroll',
        help='', tracking=True
        )
    payment_mode = fields.Selection(
        _PAYMENT_MODE,
        string='Payment mode',
        help='', tracking=True
        )
    total_receive = fields.Float(
        string='To receive',
        digits='Payroll',
        help='', tracking=True
        )
    move_id = fields.Many2one(
        'account.move',
        string='Accounting seat',
        help='', tracking=True
        )
    payment_utility_id = fields.Many2one(
        'hr.payment.utility',
        string='Payment utility',
        ondelete='cascade',
        index=True,
        help=''
    )
    state_utility = fields.Selection(related='payment_utility_id.state', store="True")
    fiscal_year = fields.Integer(
        related='payment_utility_id.fiscal_year',
        store="True",
        string='Fiscal year',
        tracking=True,
        help=''
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)
    judicial_withholding_ids = fields.One2many(
        'utility.line.judicial.withholding',
        'utility_line_id',
        help=''
    )


class UtilityLineJudicialWithholdings(models.Model):
    _name = 'utility.line.judicial.withholding'
    _description = 'Utility detail judicial withholding'
    _inherit = ['mail.thread']
    _order = "utility_line_id"

    utility_line_id = fields.Many2one(
        'hr.payment.utility.line',
        string='Utility detail',
        ondelete='cascade',
        help='', tracking=True
    )
    amount = fields.Float(
        string='Amount',
        digits='Payroll',
        help='', tracking=True
    )
    family_load_id = fields.Many2one(
        'hr.employee.family.load',
        string='Family load',
        help='', tracking=True
    )
    judicial_withholding_id = fields.Many2one(
        'hr.judicial.withholding',
        string='Judicial withholding',
        help='', tracking=True
    )
