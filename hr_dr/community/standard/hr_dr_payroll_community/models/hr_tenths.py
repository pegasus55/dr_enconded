# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
# from odoo.addons.l10n_ec.models.auxiliar_functions import convert_datetime_to_ECT, get_name_only_characters
import base64, io, csv
import time
import pytz
import calendar


HEADXIV = [
    'Cédula',
    'Nombres',
    'Apellidos',
    'Genero (Masculino=M ó Femenino=F)',
    'Ocupación (código iess)',
    'Días laborados (360 días equivalen a un año)',
    'Tipo de Pago(Pago Directo=P. Acreditación en Cuenta=A. Retención Pago Directo=RP. Retención Acreditación en Cuenta=RA)',
    'Solo si el trabajador posee JORNADA PARCIAL PERMANENTE ponga una X',
    'DETERMINE EN HORAS LA JORNADA PARCIAL PERMANENTE SEMANAL ESTIPULADO EN EL CONTRATO',
    'Solo si su trabajador posee algún tipo de discapacidad ponga una X',
    'Fecha de Jubilación',
    'Valor Retención',
    'SOLO SI SU TRABAJADOR MENSUALIZA EL PAGO DE LA DECIMOCUARTA REMUNERACION PONGA UNA X'
]
HEADXIII = [
    'Cédula',
    'Nombres',
    'Apellidos',
    'Genero (Masculino=M ó Femenino=F)',
    'Ocupación (código iess)',
    'Total ganado',
    'Días laborados (360 días equivalen a un año)',
    'Tipo de Depósito(Pago Directo=P. Acreditación en Cuenta=A. Retención Pago Directo=RP. Retención Acreditación en Cuenta=RA)',
    'Solo si el trabajador posee JORNADA PARCIAL PERMANENTE ponga una X',
    'DETERMINE EN HORAS LA JORNADA PARCIAL PERMANENTE SEMANAL ESTIPULADO EN EL CONTRATO',
    'Solo si su trabajador posee algún tipo de discapacidad ponga una X',
    'Ingrese el valor retenido',
    'SOLO SI SU TRABAJADOR MENSUALIZA EL PAGO DE LA DECIMOTERCERA REMUNERACION PONGA UNA X'
]


class Line(object):
    """Clase auxiliar para la generación de ficheros"""
    def __init__(self, dict):
        self.__dict__ = dict


class HrTenth(models.Model):
    _name = 'hr.tenth'
    _description = 'Tenth'
    _inherit = ['hr.generic.request']
    _order = "date_from desc"

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'
    
    def name_get(self):
        format_date = self.get_date_format()
        date_from = ''
        if self.date_from:
            date_from = self.date_from.strftime(format_date)
        date_to = ''
        if self.date_to:
            date_to = self.date_to.strftime(format_date)
        result = []
        if self.type_tenth == 'sierra_oriente_fourteenth_salary':
            name = u'Sierra - Oriente (Décimo cuarto salario)'
        elif self.type_tenth == 'costa_fourteenth_salary':
            name = u'Costa - Galápagos (Décimo cuarto salario)'
        elif self.type_tenth == 'thirteenth_salary':
            name = u'Décimo tercer salario'

        for header in self:
            result.append(
                (header.id, "{} {} - {}".format(name, date_from, date_to))
            )
        return result

    def convert_utc_time_to_tz(self, utc_dt, tz_name=None):
        """
        Method to convert UTC time to local time
        :param utc_dt: datetime in UTC
        :param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

        :return: datetime object presents local time
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise ValidationError(
                _("Local time zone is not defined. You may need to set a time zone in your user's preferences."))
        tz = pytz.timezone(tz_name)
        return pytz.utc.localize(utc_dt, is_dst=None).astimezone(tz)

    @api.onchange('type_tenth','date')
    def onchange_type_tenth(self):
        if self.tenth_line_ids:
            self.tenth_line_ids.unlink()

        if self.date:
            today = self.date
        else:
            today = self.convert_utc_time_to_tz(datetime.utcnow())
            today = today.date()

        name = ''
        date_from_str = ''
        date_to_str = ''
        format_date = self.get_date_format()
        date_from = False
        date_to = False
        if self.type_tenth == 'costa_fourteenth_salary':
            max_days_february = calendar.monthrange(today.year, 2)[1]
            date_from = today + relativedelta(day=1, month=3, year=today.year - 1)
            date_to = today + relativedelta(day=max_days_february, month=2, year=today.year)
            name = u'Costa - Galápagos (Décimo cuarto salario)'
        elif self.type_tenth == 'sierra_oriente_fourteenth_salary':
            date_from = today + relativedelta(day=1, month=8, year=today.year - 1)
            date_to = today + relativedelta(day=31, month=7, year=today.year)
            name = u'Sierra - Oriente (Décimo cuarto salario)'
        elif self.type_tenth == 'thirteenth_salary':
            date_from = today + relativedelta(day=1, month=12, year=today.year - 1)
            date_to = today + relativedelta(day=30, month=11, year=today.year)
            name = u'Décimo tercer salario'

        if date_from:
            self.date_from = date_from
            date_from_str = self.date_from.strftime(format_date)
        if date_to:
            self.date_to = date_to
            date_to_str = self.date_to.strftime(format_date)

        name = _('{} {} - {}').format(name, date_from_str, date_to_str)
        self.name = name
    
    def action_calcular(self):
        """
        Calculamos el valor a recibir en base a la siguiente formula
            valor a recibir = amount - monthly_amount - judicialwithhold - dvance_amount
            donde :
            amount -> valor de décimo correspondinte al período de calculo.
            monthly_amount -> valor mensualizado
            judicialwithhold -> retencion judicial
            dvance_amount -> Anticipos
        """
        res = {'value': {'tenth_line_ids': []}, 'warning': {}, 'domain': {}}
        newlines = self.env['hr.tenth.line']

        if self.tenth_line_ids:
            self.tenth_line_ids.unlink()

        query = self.get_listuser()
        self.env.cr.execute(query)
        query_results = self.env.cr.dictfetchall()
        items =[]
        for index in range(0, len(query_results)):
            employee_id = self.env['hr.employee'].browse(query_results[index].get('employee_id'))
            #Solo empleados en estado activo
            if employee_id.active:
                provisioned_amount = 0.00
                monthly_amount = 0.00
                partner_id = employee_id.address_home_id.commercial_partner_id.id
                if not partner_id:
                    raise ValidationError(_("Employee {0} does not have a comercial partner defined.")
                                          .format(employee_id.name))
                # partner_id = employee_id.address_home_id.id
                #Provision y mensualizacion del colaborador para el período del décimo segun los apuntes contables
                provisioned_amount, monthly_amount = self._get_provisioned_values_per_employee(
                                employee_id, self.type_tenth, self.date_from, self.date_to)

                #Anticipos del colaborador para el período del décimo segun los apuntes contables
                #advanceamount = self.getProvision(partner_id, 'advance', self.date_from, self.date_to)
                self.env.cr.execute("""
                    select 
                        contract_id,
                        sum(worked_days) as worked_day 
                    from hr_payslip 
                    where date_from >= %s and date_from <= %s and employee_id = %s and state in ('done', 'paid')
                    group by contract_id
                """, (self.date_from, self.date_to, employee_id.id,))
                records = self.env.cr.dictfetchall()
                total_worked_days = 0.0
                amount = 0.0
                for record in records:
                    contract = self.env['hr.contract'].browse(record.get('contract_id'))
                    if contract.state == 'open':
                        total_worked_days += record.get('worked_day')
                for record in records:
                    contract = self.env['hr.contract'].browse(record.get('contract_id'))
                    if contract.state == 'open':
                        if not contract.iess_output_documents_id:
                            if self.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
                                if total_worked_days < 360:
                                    amount += float_round((float_round(self.getSBU() / 12, 2)) * (contract.hours_week / 40) * (record.get('worked_day') / 30), 2)
                                else:
                                    amount += float_round((self.getSBU() / 12) * (contract.hours_week / 40) * (record.get('worked_day') / 30), 2)
                            elif self.type_tenth in ('thirteenth_salary'):
                                #Se buscan todos los ingresos del empledo que generan beneficios sociales
                                category = self.env.ref('hr_dr_payroll.salary_rule_category_01')
                                self.env.cr.execute("""
                                    select
                                        sum(t.total) as total
                                    from(
                                        select 
                                            round(sum(total) / 12, 2)  as total
                                        from hr_payslip p join 
                                            hr_payslip_line l 
                                                on p.id=l.slip_id join
                                            hr_contract c
                                                on p.contract_id=c.id
                                        where p.date_from >= %s and p.date_to <= %s and category_id=%s and p.employee_id=%s and p.contract_id=%s and p.state in ('done', 'paid')
                                        group by date_from) as t
                                """, (self.date_from, self.date_to, category.id, contract.employee_id.id, contract.id,))
                                total = self.env.cr.fetchall()
                                amount += total[0][0]

                #caso diferencia por centavos, agregando margen de tolerancia
                if self.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
                    xiv_exclude_dif_less_than = self.env.user.company_id.xiv_exclude_dif_less_than
                    SBU = self.getSBU()
                    if amount > SBU and xiv_exclude_dif_less_than != 0:
                        sbu_max = SBU + xiv_exclude_dif_less_than
                        sbu_min = SBU - xiv_exclude_dif_less_than 
                        if sbu_min <= amount <= sbu_max:
                            amount = SBU
                vals = {
                    'employee_id': employee_id.id,
                    'worked_days': total_worked_days,
                    'amount': amount,
                    'provisioned_amount': provisioned_amount,
                    'monthly_amount': monthly_amount,
                    #'advance_amount': advanceamount,
                    'company_currency_id': self.currency_id
                    #'amount_to_receive': amount - monthly_amount, es un campo funcional, no hace falta computarlo
                }
                new_line = newlines.new(vals)
                newlines += new_line

        self.tenth_line_ids = newlines
        self.write({
            'state':'calculated',
        })
        if self.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
            xiv_exclude_dif_less_than = self.env.user.company_id.xiv_exclude_dif_less_than
            for line in self.tenth_line_ids:
                if line.amount_to_receive >= -1 * xiv_exclude_dif_less_than and line.amount_to_receive <= xiv_exclude_dif_less_than:
                    line.amount -= abs(line.amount_to_receive)
        else:
            xiii_exclude_dif_less_than = self.env.user.company_id.xiii_exclude_dif_less_than
            for line in self.tenth_line_ids:
                if line.amount_to_receive >= -1 * xiii_exclude_dif_less_than and line.amount_to_receive <= xiii_exclude_dif_less_than:
                    line.amount -= abs(line.amount_to_receive)
        return res
    
    def _get_provisioned_values_per_employee(self, employee_id, type_tenth, date_from, date_to):
        """
        Distribucion de decimos provisionados y mensualizados en base a los
        apuntes contables.
        
        Calculo para decimo Cuarto
        Para la distribucion de decimos se utilizo los siguientes escenarios.
        DEBE     HABER    TOTAL     CASO
        160.80 - 32.16  = 128.64 | Mensualizado parcial.
        160.80 - 160.80 = 0.00   | Provisionado.
        160.80 - 0.00   = 160.80 | Mensualizado.
        
        Caso 1: Se mensualizo 160.80 y acumulo 32.16, el valor real mensualizado es 128.64.
        Caso 2: Cuando se provisiona, los asientos contables van al gasto y a la cuenta de decimos.
        Caso 3: Cuando se mensualiza, los asientos contables van al gasto.
        
        Calculo para decimo tercero
        @param employee_id : Id colaborador
        @param type_tenth : Tipo de provisión (decimo Tercero y cuarto)
        @param date_from date_to : Rango de fecha a obtener la provision
        @return: valor provisionado y valor mensualizado
        """
        provisioned_amount = 0.00
        monthly_amount = 0.00
        partner_id = employee_id.address_home_id.commercial_partner_id.id
        #TODO: estandarizar el calculo de decimo cuarto,
        #tomar como ejemplo del calculo de decimo tercero.
        #mantengo la logica anterior de decimo Cuarto.
        if type_tenth in ['sierra_oriente_fourteenth_salary', 'costa_fourteenth_salary']:
            #SQL Obtine la diferencia entre lo provisionado y mensualizado.
            sqlmove = self.getProvision(partner_id, 'provisioned',date_from, date_to)
            self.env.cr.execute(sqlmove)
            move_line = self.env.cr.dictfetchall()
            if any(move_line) and move_line[0]['total'] > 0.0:
                #Mensualizado y mensualizado parcial
                if move_line[0]['credit'] < move_line[0]['debit']:
                    #Mensualizado parcial
                    if move_line[0]['total'] < move_line[0]['credit']:
                        provisioned_amount = move_line[0]['credit'] - move_line[0]['total']
                        monthly_amount = move_line[0]['total']
                    else:
                        provisioned_amount = 0.00
                        monthly_amount = move_line[0]['total']
                
            else:
                #Valor total provisionado o sin valores
                monthly_amount = 0.00
                provisioned_amount = move_line[0]['credit'] if any(move_line) else 0.00
                
        elif type_tenth == 'thirteenth_salary':
            #Realizamos un analisis mes sobre mes pues en proyecto X
            #se provisiona y se netea la cta mes sobre mes inclusive para empleados
            #que acumulan, de esta forma se netea el efecto de esta pseudo-provision
            #
            #obtenemos los rangos de meses a evaluar:
            #basado en https://stackoverflow.com/questions/51293632/how-do-i-divide-a-date-range-into-months-in-python
            dt_start = datetime.strptime(date_from.isoformat(), '%Y-%m-%d')
            dt_end = datetime.strptime(date_to.isoformat(), '%Y-%m-%d')
            one_day = timedelta(1)
            start_dates = [dt_start]
            end_dates = []
            today = dt_start
            while today <= dt_end:
                #print(today)
                tomorrow = today + one_day
                if tomorrow.month != today.month:
                    start_dates.append(tomorrow)
                    end_dates.append(today)
                today = tomorrow
            end_dates.append(dt_end)
            for start, end in zip(start_dates, end_dates):
                journals = self.getjournalreport('provisioned') #diarios involucrados, ejemplo SUELDOS
                #El valor provisionado corresponde al NETO en la cta de provision con los diarios de SUELDOS
                start = datetime.strftime(start,'%Y-%m-%d')
                end = datetime.strftime(end,'%Y-%m-%d')
                accounts = self.env.user.company_id.xiii_provision_account #para la provision solo nos interesa esta cta
                self.env.cr.execute(""" 
                    SELECT aml.partner_id,
                           sum(credit) as credit,
                           sum(debit) as debit,
                           sum(debit) - sum(credit) as Total 
                    FROM account_move_line aml 
                        join account_move am on aml.move_id = am.id and am.journal_id in %s
                    WHERE account_id in %s
                        and aml.partner_id = %s
                        and aml.date >= %s and aml.date <= %s
                        group by aml.partner_id;
                    """, (tuple(journals),
                          tuple(accounts.ids),
                          partner_id,
                          start,
                          end,))
                move_line = self.env.cr.dictfetchall()
                if move_line and move_line[0]['total'] != 0.0: #si es cero es que se neteo en el mes, caso especial de AD
                    #Si las nominas que existan en el período analizado pertenecen a un 
                    #contrato finalizado(fue liquidado y no es objeto de analisis)
                    payslips = self.env['hr.payslip'].search([
                        ('date_from','>=',start),
                        ('date_to','<=',end),
                        ('employee_id','=',employee_id.id),
                        ('state','in',['done', 'paid'])
                    ])
                    if payslips:
                        if not payslips[0].contract_id.iess_output_documents_id:
                            provisioned_amount += move_line[0]['total'] * (-1)
                    else:
                        provisioned_amount += move_line[0]['total'] * (-1)
                    continue #si el valor fue provisionado ya no necesito evaluar la opcion mensualizado
                    #es mas si evaluo me va a dar datos errados
                #El valor mensualizado corresponde al NETO en las ctas de egreso con los diarios de rol
                accounts = self.env.user.company_id.xiii_adjust_admin_account + \
                           self.env.user.company_id.xiii_adjust_sales_account + \
                           self.env.user.company_id.xiii_adjust_direct_account + \
                           self.env.user.company_id.xiii_adjust_indirect_account
                self.env.cr.execute(""" 
                    SELECT aml.partner_id,
                           sum(credit) as credit,
                           sum(debit) as debit,
                           sum(debit) - sum(credit) as Total 
                    FROM account_move_line aml 
                        join account_move am on aml.move_id = am.id and am.journal_id in %s
                    WHERE account_id in %s
                        and aml.partner_id = %s
                        and aml.date >= %s and aml.date <= %s
                        group by aml.partner_id;
                    """, (tuple(journals),
                          tuple(accounts.ids),
                          partner_id,
                          start,
                          end,))
                move_line = self.env.cr.dictfetchall()
                if move_line:
                    monthly_amount += move_line[0]['total']
        else:
            pass#raise #Caso no contemplado
        return provisioned_amount, monthly_amount
        
    def action_done(self):
        """
        Creamos el asiento contable por cada colaborador.
        """
        if self.type_tenth == 'costa_fourteenth_salary' or self.type_tenth == 'sierra_oriente_fourteenth_salary':
            if not self.env.user.company_id.journal_fourteenth_id:
                raise ValidationError(u'Por favor, agregue el diario de liquidación de décimo cuarto en la compañía.')
        elif self.type_tenth == 'thirteenth_salary':
            if not self.env.user.company_id.journal_thirteenth_id:
                raise ValidationError(u'Por favor, agregue el diario de liquidación de décimo tercero en la compañía.')
        employes = []
        for line in self.tenth_line_ids:
            if line.amount_to_receive < 0.0:
                employes.append(line.employee_id.name)
        if employes:
            list = '\n'.join('* ' + employee for employee in employes)
            raise UserError(u'El total a recibir de los siguientes empleados es menor que cero, revise los valores provisionados, '
                            u'los roles de pagos o alternativamente remueva los empleados afectados:\n%s' % list)
        self.tenth_line_ids.make_move()
        return self.write({'state': 'done'})

    def action_cancel(self):
        """
        Pasamos a estado cancelado
        """
        moves = self.tenth_line_ids.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        return self.write({'state': 'cancel'})
    
    
    def action_draft(self):
        """
        Devolvemos a estado borrador
        """
        #if self.filtered(lambda payslip: payslip.state != 'paid'):
        #    raise ValidationError(u'La nómina debe estar pagada para regresarla al estado confirmado.')
        return self.write({'state': 'draft'})
    
    def getSBU(self):
        """
        Obtenemos el sueldo basico unificado para el período que se genera el pago de décimos.
        """
        year = datetime.strptime(self.date_to.isoformat(), '%Y-%m-%d').year

        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if sbu:
            return sbu.value
        else:
            raise ValidationError(u'Debe establecer el salario básico unificado para el año {}.'.format(str(year)))
            
    def get_listuser(self):
        """
        utilizamos SQL para obtener los campos de necesario para el décimo tercero y décimo cuarto.
        décimo cuarto, colaborador, dias trabajados en base a la nomina, valor a pagar décimo tercer sueldo  ((SBU*360)/ dias trabajados)
        """
        if self.type_tenth in ('sierra_oriente_fourteenth_salary', 'costa_fourteenth_salary'):
            return ("""
                select distinct hc.employee_id, hc.payment_period_fourteenth, nom.worked_day from( 
                    select employee_id, payment_period_fourteenth from hr_contract 
                        where payment_fourteenth_salary in ('monthly', 'accumulated') and ((date_end >= '%s' and date_end <= '%s') or date_end is null)
                ) hc left join (
                    select employee_id, sum(worked_days) as worked_day 
                        from hr_payslip where date_from >= '%s' and date_from <= '%s'
                        group by employee_id
                ) nom on hc.employee_id = nom.employee_id
                join hr_employee he on he.id = hc.employee_id 
                where hc.payment_period_fourteenth = '%s'
                """%(self.date_from, self.date_to, self.date_from, self.date_to, self.type_tenth))
        elif self.type_tenth in ('thirteenth_salary'):
            return ("""
                select distinct hc.employee_id, nom.worked_day from( 
                    select employee_id from hr_contract 
                        where payment_thirteenth_salary in ('monthly', 'accumulated') and ((date_end >= '%s' and date_end <= '%s') or date_end is null)
                ) hc left join (
                    select employee_id, sum(worked_days) as worked_day 
                        from hr_payslip where date_from >= '%s' and date_from <= '%s'
                        group by employee_id
                ) nom on hc.employee_id = nom.employee_id
                join hr_employee he on he.id = hc.employee_id
                """%(self.date_from, self.date_to, self.date_from, self.date_to))

    def getProvision(self, partner_id, type, date_from, date_to):
        """
        Metodo en base a las cuentas contables, diarios y fecha inicio y fecha fin
        obtiene los valores de las provisiones de décimos o anticipos.
        @param partner_id: Identificacion del colaborador a obtener la informacion
        @param type: (provisiones y avances)
        @param date_from: fecha inicio del la consulta de datos
        @param date_to: fecha fin del la consulta de datos
        """
        #Obtiene los diarios y cuentas contables
        #relacionados con las provisiones y avances.
        journals = self.getjournalreport(type)
        accounts = self.getaccountreport(type)
        if type == 'provisioned':
            #SQL Utilizado en para decimo cuarto.
            return """ 
                    SELECT aml.partner_id,
                           sum(credit) as credit,
                           sum(debit) as debit,
                           sum(debit) - sum(credit) as Total 
                    FROM account_move_line aml 
                        join account_move am on aml.move_id = am.id and am.journal_id in (%s)
                    WHERE account_id in (%s) 
                        and aml.partner_id = %s
                        and aml.date >= '%s' and aml.date <= '%s'
                        group by aml.partner_id;
            """%(', '.join( str(jrnl) for jrnl in journals),
                 ', '.join( str(acc) for acc in accounts),
                 partner_id, date_from, date_to)
        elif type == 'advance':
            advances = self.env['account.move.line'].search([
                            ('journal_id','in', tuple(journals)),
                            ('account_id','in', tuple(accounts)),
                            ('date_maturity','>=', date_from),
                            ('date_maturity','<=', date_to),
                            ('partner_id','=',partner_id)
                        ]
                    )
            return sum(advances.mapped('debit'))
    
    
    def action_view_payment(self):
        """
        Este método muestra los pagos generados por el pago de provisiones
        """
        action = 'account.action_account_payments_payable'
        view = 'ecua_payment.view_account_payment_supplier_form'
        action = self.env.ref(action)
        result = action.read()[0]
        payment_ids = self.env['account.payment'].search([('payment_provision_id','=',self.id)]).mapped('id')
        if len(payment_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(payment_ids) + ")]"
        elif len(payment_ids) == 1:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = payment_ids[0]
        else:
            raise ValidationError(u'No existen pagos registrados.')
        return result
    
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
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de mano de obra directa en la compañía.')
                if not self.env.user.company_id.xiv_adjust_indirect_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de mano de obra indirecta en la compañía.')
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
        elif self.type_tenth in ('thirteenth_salary'):
            if type == 'provisioned':
                if not self.env.user.company_id.xiii_provision_account:
                    raise ValidationError(u'Por favor, configure la cuenta de provisiones de décimos en la compañía.')
                if not self.env.user.company_id.xiii_adjust_admin_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste administrativa en la compañía.')
                if not self.env.user.company_id.xiii_adjust_sales_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de ventas en la compañía.')
                if not self.env.user.company_id.xiii_adjust_direct_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de mano de obra directa en la compañía.')
                if not self.env.user.company_id.xiii_adjust_indirect_account:
                    raise ValidationError(u'Por favor, configure la cuenta de ajuste de mano de obra indirecta en la compañía.')
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
                #agregamos los diarios que se utilizaran 
                #en la busqueda de los apuntes contables
                if not self.env.user.company_id.journal_wage_id:
                    raise ValidationError(u'Por favor, configure el diario de salarios en la compañía.')
                #Diario de sueldos.
                journal.append(self.env.user.company_id.journal_wage_id.id) 
            if type == 'advance':
                self.env.cr.execute("""select distinct journal_id from hr_advance""")
                journals = self.env.cr.dictfetchall()
                for index in range(0, len(journals)):
                    journal.append(journals[index].get('journal_id'))
        return journal

    
    def decimo4toReportCVS(self, line):
        """
        Genera las lineas del archivo CVs, para el reporte de décimo4to
        """
        dataemployee = line.employee_id.address_home_id.commercial_partner_id
        hparcialc = True
        if line.employee_id.contract_id.monthly_hours == 240.00:
            hparcialc = False
        codeIESS = line.employee_id.contract_id.iess_sector_code if line.employee_id.contract_id.iess_sector_code else ''
        filaemp = []
        vat = dataemployee.vat
        if line.employee_id.country_id and self.env.user.company_id.country_id and line.employee_id.country_id != self.env.user.company_id.country_id:
            vat = u'#UIO' + vat
        filaemp.append(vat)
        filaemp.append(line.employee_id.names)
        filaemp.append(line.employee_id.surnames)
        filaemp.append('M' if line.employee_id.gender == 'male' else 'F')
        filaemp.append(codeIESS)#codigo IESS 
        filaemp.append(int(line.worked_days))
        filaemp.append(line.payment_method)
        filaemp.append('X' if hparcialc else '')
        filaemp.append(20 if hparcialc else '')
        filaemp.append('X' if line.employee_id.disability_type in('own','surrogate') else '') #discapacidad
        filaemp.append('')
        filaemp.append(line.judicialwithhold)
        filaemp.append('X' if line.monthly_amount else '')
        return filaemp
    
    
    def decimo3roReportCVS(self, line):
        """
        Genera las lineas del archivo CVs, para el reporte de décimo3ro
        """
        dataemployee = line.employee_id.address_home_id.commercial_partner_id
        hparcialc = True
        if line.employee_id.contract_id.monthly_hours == 240.00:
            hparcialc = False
        hours_week = 20
        worked_days = line.worked_days
        contract_ids = self.env['hr.payslip'].get_contract(line.employee_id, line.tenth_id.date_from, line.tenth_id.date_to)
        if contract_ids:
            contract = self.env['hr.contract'].browse(contract_ids[0])
            hours_week = int(contract.hours_week)
            # Calculo de horas parciales.
            if contract.monthly_hours < 240 and worked_days > 0:
                worked_days = round((contract.monthly_hours/8) * ((worked_days * 12)/360.00),0)
        codeIESS = line.employee_id.contract_id.iess_sector_code if line.employee_id.contract_id.iess_sector_code else ''
        filaemp = []
        vat = dataemployee.vat
        if line.employee_id.country_id and self[0].env.user.company_id.country_id and line.employee_id.country_id != self[0].env.user.company_id.country_id:
            vat = u'#UIO' + vat
        base_gravable = 0.0
        category = self.env.ref('hr_dr_payroll.salary_rule_category_01')
        #Filtros
        domain = [('date_from','>=',line.tenth_id.date_from),
                  ('date_to','<=',line.tenth_id.date_to),
                  ('employee_id','=', line.employee_id.id ),
                  ('state','in', ('done', 'paid') )]    
        #Roles
        payrolls =  self.env['hr.payslip'].search(domain)
        payrolls.mapped('contract_id.contract_date_end')
        payrolls_current_contract = self.env['hr.payslip'] #empty recordset
        for rol in payrolls:
            #a veces el colaborador tuvo un reingreso, solo se toman en cuenta los roles del ultimo contrato
            if not rol.contract_id.contract_date_end:
                #si el contrato esta vigente
                payrolls_current_contract += rol
            elif rol.contract_id.contract_date_end >= line.tenth_id.date_to:
                #si el contrato fue terminado posterior a la fecha que reportamos
                payrolls_current_contract += rol
            else:
                #cuando el contrato ha sido terminado antes de reportar
                #ya fue liquidado el decimo y por tanto no se reporta
                pass
        #Se buscan todos los ingresos del empledo que generan beneficios sociales
        base_gravable =  sum(payrolls_current_contract.mapped('line_ids').filtered(
                                        lambda x: x.category_id.id in category.ids
                                    ).mapped('amount'))
        filaemp.append(vat)
        filaemp.append(line.employee_id.names)
        filaemp.append(line.employee_id.surnames)
        filaemp.append('M' if line.employee_id.gender == 'male' else 'F')
        filaemp.append(codeIESS)
        filaemp.append("{0:.2f}".format(float_round(base_gravable, 2)))#redondea a dos decimales y trunca a 2
        filaemp.append(int(worked_days))
        filaemp.append(line.payment_method)
        filaemp.append('X' if hparcialc else '')
        filaemp.append(hours_week if hparcialc else '')
        filaemp.append('X' if line.employee_id.disability_type in('own','surrogate') else '')
        filaemp.append(line.judicialwithhold)
        filaemp.append('X' if line.monthly_amount else '')
        return filaemp
    
    
    def get_provision_CSV(self):
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=';')
        fourteenth = self.filtered(lambda x: x.type_tenth != 'thirteenth_salary')
        thirteenth = self.filtered(lambda x: x.type_tenth == 'thirteenth_salary')
        if fourteenth and thirteenth:
            buf.close()
            raise ValidationError (u'Seleccione los mismos tipos de provisiones para generar el reporte.')
        if fourteenth:
            writer.writerow(HEADXIV)
            listaobj = fourteenth
            name = u'Pago de XIV sueldo.csv'
        if thirteenth:
            writer.writerow(HEADXIII)
            listaobj = thirteenth
            name = u'Pago de XIII sueldo.csv'
        filaemp = []
        tenth_line_ids = self.env['hr.tenth.line'].search([('tenth_id','in',listaobj.ids)])
        line_ids = sorted(tenth_line_ids, key=lambda x: x.mapped('employee_id').mapped('name'))
        for line in line_ids:
            valor = line.monthly_amount + line.provisioned_amount
            if valor == 0 and line.worked_days == 0:
                continue
            if fourteenth:
                filaemp = self.decimo4toReportCVS(line)
            if thirteenth:
                filaemp = self.decimo3roReportCVS(line)
            writer.writerow(filaemp)

        out = buf.getvalue()
        try:
            out = out.decode('utf-8')
        except AttributeError:
            pass
        out = base64.encodebytes(out.encode('iso-8859-1'))

        buf.close()
        return self.env['base.file.report'].show(out, name)

    
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

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """

        exportFile = self.env['hr.dr.export.file']
        for rec in self:
            lines = []
            for line in rec.tenth_line_ids:
                lines.append(Line({"employee_id": line.employee_id, "value": line.amount_to_receive}))

            messages = exportFile._create_text_files(lines, "{} ({} - {})".format(rec.type_tenth, rec.date_from, rec.date_to))
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return exportFile._compress_and_show("{} ({} - {})".format(rec.type_tenth, rec.date_from, rec.date_to) + '.zip')

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

        template = self.env.ref('hr_dr_payroll.email_template_tenths_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        local_context['type_tenth'] = self.get_name_type_tenth()[0]
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        return self

    def get_name_type_tenth(self):
        return dict(self._fields['type_tenth'].selection).get(self.type_tenth)
    
    # 
    # def _compute_total_payment(self):
    #     """
    #     Obtiene el valor pagado y setear el estado a "Pagado"
    #     """
    #     #TODO: mejorar el algoritmo de actualizar el estado
    #     for provision in self:
    #         payment_ids = self.env['account.payment'].sudo().search([('payment_provision_id','=',self.id)])
    #         if payment_ids:
    #             provision.total_payment = sum(payment_ids.mapped('amount'))
    #             total_provision = sum(self.tenth_line_ids.mapped('amount_to_receive'))
    #             if float_compare(provision.total_payment, total_provision, 2) == 0:
    #                 state = 'paid'
    #             else:
    #                 state = 'done'
    #             self.env.cr.execute("""
    #                 UPDATE hr_provision_salary
    #                 SET state = %s
    #                 WHERE id = %s
    #             """, (state, self.id))
    
    #Columns

    name = fields.Char(
        string='Name',
        readonly=True,
        states={'draft': [('readonly', False)]}, tracking=True
        )
    date = fields.Date(
        string='Posting date',
        default=fields.Date.context_today,
        index=True,
        copy=False,
        help='Date for the generation of the accounting entry.', tracking=True
        )
    TYPE_TENTH = [
        ('sierra_oriente_fourteenth_salary', 'Sierra - Oriente (Décimo cuarto salario)'),
        ('costa_fourteenth_salary', 'Costa  - Galápagos (Décimo cuarto salario)'),
        ('thirteenth_salary', 'Décimo tercer salario')
    ]
    type_tenth = fields.Selection(TYPE_TENTH,
        string='Type of tenth',
        copy=False,
        help='', tracking=True
        )
    date_from = fields.Date(
        string='Period start',
        help='', tracking=True
        )
    date_to = fields.Date(
        string='Period end',
        help='', tracking=True
        )
    tenth_line_ids = fields.One2many(
        'hr.tenth.line',
        'tenth_id',
        string='Details',
        copy=True,
        help=''
        )
    state = fields.Selection(selection_add=[('calculated', 'Calculated'),('paid', 'Paid')])
    # total_payment = fields.Monetary(
    #     compute='_compute_total_payment',
    #     string='Total Pago',
    #     currency_field='currency_id'
    #     )


class HrTenthLine(models.Model):
    _name = 'hr.tenth.line'
    _description = 'Tenth line'
    _inherit = ['mail.thread']
    _order = "tenth_id desc,state,employee_id"

    # @api.depends('amount','provisioned_amount','monthly_amount','judicialwithhold','advance_amount')
    @api.depends('amount', 'provisioned_amount', 'monthly_amount', 'judicialwithhold')
    def compute_amount_to_receive(self):
        pass
        # if self.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
        #     self.amount_to_receive = self.amount - self.monthly_amount - self.judicialwithhold
        #     #self.amount_to_receive = self.amount - self.monthly_amount - self.judicialwithhold - self.advance_amount
        #     self.difference = self.amount - self.provisioned_amount - self.monthly_amount
        # else:
        #     self.amount_to_receive = self.amount - self.monthly_amount - self.judicialwithhold
        #     #self.amount_to_receive = self.amount - self.monthly_amount - self.judicialwithhold - self.advance_amount
        #     #self.amount_to_receive = self.provisioned_amount - self.monthly_amount - self.judicialwithhold - self.advance_amount
        #     #los valores de la provision salen en negativos con el nuevo calculo
        #     #no se toma en cuenta el caso de los mensualizados
        #     if abs(self.provisioned_amount) != 0:
        #         self.difference = self.amount - self.provisioned_amount - self.monthly_amount
    
    
    def action_view_account_form_lines(self):
        """
        Accion para mostrar los asientos relacionados a los décimos.
        """
        self.ensure_one()
        #Obtiene las cuentas y diarios para la consulta de décimos.
        journals = self.tenth_id.getjournalreport('provisioned')
        accounts = self.tenth_id.getaccountreport('provisioned')
        action = {
            'name': u'Cuentas de décimos',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'domain': [('date', '>=', self.tenth_id.date_from),
                       ('date', '<=', self.tenth_id.date_to),
                       ('partner_id','=', self.employee_id.address_home_id.commercial_partner_id.id),
                       ('account_id','in', tuple(accounts)),
                       ('journal_id','in', tuple(journals))
                       ],
            'context':{'default_journal_id': tuple(journals),
                       'default_account_id': tuple(accounts)},
            'target': 'current'
        }
        return action

    @api.depends('payment_method_employee')
    def compute_payment_method(self):
        pass
        # if self.payment_method_employee == 'CHQ':
        #     self.payment_method = 'P'
        # elif self.payment_method_employee == 'CTA':
        #     self.payment_method = 'A'

    @api.depends('employee_id', 'tenth_id')
    def _get_current_contract(self):
        """
        El contrato vigente a la fecha de liquidacion del décimo, utilizado para determinar el grupo contable
        returna un objeto hr.contract
        """
        for line in self:
            contract_id = False
            #Para el caso que la ultima version del contrato este en ejecucion y no tenga seteada la fecha de vigencia
            contract_ids = self.env['hr.contract'].search([
                    ('employee_id','=',line.employee_id.id),
                    ('date_start','<=',line.tenth_id.date_to),
                    ('date_end','=',False),
                    ('state','in',['open','close']),],
                order='date_start DESC',
                )
            if not contract_ids:
                #para el caso de que ya no hay contratos vigentes (date_end seteado)
                contract_ids = self.env['hr.contract'].search([
                    ('employee_id','=',line.employee_id.id),
                    ('date_start','<=',line.tenth_id.date_to),
                    ('date_end','<=',line.tenth_id.date_to),
                    ('state','in',['open','close']),],
                    order='date_start DESC',
                    )
            if contract_ids:
                contract_id = contract_ids[0]
            line.contract_id = contract_id

    
    def make_move(self):
        """
        Crea el movimiento contable correspondiente al registro
        """
        for line in self:
            if line.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
                name = _("%s's XIV salary") % (line.employee_id.name)
                journal_id = self.env.user.company_id.journal_fourteenth_id.id
            else:
                name = _("%s's XIII salary") % (line.employee_id.name)
                journal_id = self.env.user.company_id.journal_thirteenth_id.id
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
        Computa las lineas de asiento contable 
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
        # self.judicialwithhold
        # if not float_is_zero(self.judicialwithhold, precision_digits=precision):
        #     line_ids.append((0, 0, {
        #         'name': name,
        #         'partner_id': partner_id,
        #         'account_id': earnings_attachment_account_id,
        #         'credit': self.judicialwithhold
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
        Metodo auxiliar para crear el asiento contable
        """
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        move.post()
        return move
    
    #Columns
    name = fields.Text(
        string='Description', tracking=True
        )
    tenth_id = fields.Many2one(
        'hr.tenth',
        string='Tenth',
        index=True,
        ondelete='cascade', tracking=True
        )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Collaborator',
        required=True,
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
    amount = fields.Float(
        string='Amount',
        
        store=True,
        help='', tracking=True
        )
    provisioned_amount = fields.Float(
        string='Provisioned',
        
        store=True,
        help='', tracking=True
        )
    monthly_amount = fields.Float(
        string='Monthly',
        
        store=True,
        help='', tracking=True
        )
    judicialwithhold = fields.Float(
        string='Judicial withholding',
        
        store=True,
        tracking=True,
        help=''
        )
    advance_amount = fields.Float(
        string='Tenth advance',
        
        store=True,
        tracking=True,
        help=''
        )
    amount_to_receive = fields.Float(
        string='To receive',
        
        store=True,
        compute='compute_amount_to_receive',
        help='', tracking=True
        )
    # La diferencia entre lo registrado en la contabilidad y el cálculo real, útil para hacer un asiento de ajuste por la diferencia.
    difference = fields.Float(
        string='Difference',
        
        store=True,
        compute='compute_amount_to_receive',
        help='The difference between what is recorded in the accounting and the actual calculation, useful to make an adjusting entry for the difference.', tracking=True
        )    
    payment_method_employee = fields.Selection(
        string='Payment method defined in the employee',
        related='employee_id.payment_method',
        
        store=True,
        help='', tracking=True)
    payment_method = fields.Selection([
        ('P','Pago Directo'),
        ('A','Acreditación en Cuenta'),
        ('RP','Retención Pago Directo'),
        ('RA','Retención Acreditación en Cuenta')],
        string='Payment method',
        
        store=True,
        compute=compute_payment_method,
        help='Field used for the generation of the CSV.', tracking=True
        )
    # Asiento contable
    # Asiento de liquidación
    move_id = fields.Many2one(
        'account.move', 
        string='Accounting seat',
        help='Settlement entry', tracking=True
        )
    # Contrato vigente a la fecha de liquidación.
    contract_id = fields.Many2one(
        'hr.contract', 
        string='Contract',
        compute='_get_current_contract',
        
        store=False,
        help='Contract in force at the settlement date.', tracking=True
        )
