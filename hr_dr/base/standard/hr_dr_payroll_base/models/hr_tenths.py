# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64, io, csv
import pytz
import calendar

HEAD_D14 = [
    'Cédula (Ejm.:0502366503)',
    'Nombres',
    'Apellidos',
    'Genero (Masculino=M ó Femenino=F)',
    'Ocupación (codigo iess)',
    'Días laborados (360 días equivalen a un año)',
    'Tipo de Pago(Pago Directo=P,Acreditación en Cuenta=A,Retencion Pago Directo=RP,Retencion Acreditación en Cuenta=RA)',
    'Solo si el trabajador posee JORNADA PARCIAL PERMANENTE ponga una X',
    'DETERMINE EN HORAS LA JORNADA PARCIAL PERMANENTE SEMANAL ESTIPULADO EN EL CONTRATO',
    'Solo si su trabajador posee algún tipo de discapacidad ponga una X',
    'Fecha de Jubilación',
    'Valor Retencion',
    'SOLO SI SU TRABAJADOR MENSUALIZA EL PAGO DE LA DECIMOCUARTA REMUNERACION PONGA UNA X'
]

HEAD_D13 = [
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
    _description = 'Tenths'
    _inherit = ['hr.generic.request']
    _order = "date_from desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_payment_tenth',
            'confirm_direct':
                'hr_dr_payroll_base.email_template_confirm_direct_approve_payment_tenth',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_payment_tenth',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_payment_tenth',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancelled_payment_tenth',
            'paid': 'hr_dr_payroll_base.email_template_tenths_notify_treasury'
        }
    _hr_notifications_mode_param = 'payment.tenth.notifications.mode'
    _hr_administrator_param = 'payment.tenth.administrator'
    _hr_second_administrator_param = 'payment.tenth.second.administrator'

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
        result = []
        for record in self:
            format_date = record.get_date_format()
            date_from = ''
            if record.date_from:
                date_from = record.date_from.strftime(format_date)

            date_to = ''
            if record.date_to:
                date_to = record.date_to.strftime(format_date)

            name = _('Sierra - East (Fourteenth salary)')
            if record.type_tenth == 'sierra_oriente_fourteenth_salary':
                name = _('Sierra - East (Fourteenth salary)')
            elif record.type_tenth == 'costa_fourteenth_salary':
                name = _('Coast - Galapagos (Fourteenth salary)')
            elif record.type_tenth == 'thirteenth_salary':
                name = _('Thirteenth salary')

            result.append(
                (record.id, "{} {} - {}".format(name, date_from, date_to))
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

    @api.onchange('type_tenth', 'date')
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
            name = _('Coast - Galapagos (Fourteenth salary)')
        elif self.type_tenth == 'sierra_oriente_fourteenth_salary':
            date_from = today + relativedelta(day=1, month=8, year=today.year - 1)
            date_to = today + relativedelta(day=31, month=7, year=today.year)
            name = _('Sierra - East (Fourteenth salary)')
        elif self.type_tenth == 'thirteenth_salary':
            date_from = today + relativedelta(day=1, month=12, year=today.year - 1)
            date_to = today + relativedelta(day=30, month=11, year=today.year)
            name = _('Thirteenth salary')

        if date_from:
            self.date_from = date_from
            date_from_str = self.date_from.strftime(format_date)
        if date_to:
            self.date_to = date_to
            date_to_str = self.date_to.strftime(format_date)

        name = _('{} {} - {}').format(name, date_from_str, date_to_str)
        self.name = name

    @api.onchange('date_to')
    def onchange_date_to(self):
        if self.date_to:
            self.fiscal_year = self.date_to.year
            sbu = self.get_unified_basic_salary()

            self.value_sbu = sbu.value
            self.value_sbu_previous_fiscal_year = sbu.value_previous_fiscal_year
            self.percent_increase_sbu = sbu.percent_increase
    
    def action_calculate(self):
        pass
        
    def action_done(self):
        """
        Pasamos a estado hecho.
        """
        self.write({'state': 'done'})

    def action_cancel(self):
        """
        Pasamos a estado cancelado.
        """
        self.cancel_request()

    def mark_as_draft(self):
        super(HrTenth, self).mark_as_draft()
        line_ids = self.env['hr.tenth.line'].with_context(
            active_test=False).search([('tenth_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()
    
    def get_unified_basic_salary(self):
        """
        Obtenemos el salario básico unificado para el período que se genera el pago de décimos.
        """
        year = datetime.strptime(self.date_to.isoformat(), '%Y-%m-%d').year

        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if sbu:
            return sbu
        else:
            raise ValidationError(_('You must establish the unified basic salary for the year {}.').format(str(year)))

    def get_advance_amount(self, type_tenth, partner_id, date_from, date_to):
        pass

    def get_judicial_withholding(self, employee_id):
        pass

    def action_view_payment(self):
        pass
    
    def decimo4toReportCVS(self, line):
        """
        Genera las líneas del archivo CSV, para el reporte de décimo cuarto salario.
        """

        # TODO Los días trabajados se están prorrateando en base a las horas diarias y a las horas diarias estándar
        #  del último contrato del colaborador. Un posible cambio sería hacer ese cálculo en base al contrato que
        #  tenía el colaborador en cada nómina. Por ejemplo puede que durante un período trabajara medio tiempo,
        #  por ende si trabaja los 30 días a efectos de legalización del D14 solo trabajó 15 días.
        #  Por otro lado puede que durante otro período trabajara a tiempo completo, por ende si trabaja 30 días
        #  a fectos de legalización de D14 cuentan los 30 días trabajados.
        identification_id = line.employee_id.identification_id
        if line.employee_id.identification_type.name == "Pasaporte":
            identification_id = '#UIO' + identification_id

        gender = ''
        if line.employee_id.gender == 'male':
            gender = 'M'
        elif line.employee_id.gender == 'female':
            gender = 'F'

        sector_code = ''
        if line.employee_id.contract_id.IESS_sector_code:
            sector_code = line.employee_id.contract_id.IESS_sector_code.IESS_code

        permanent_part_time = False
        hours_permanent_part_time = 0
        worked_days = line.worked_days
        if line.employee_id.contract_id.daily_hours < line.employee_id.contract_id.standard_daily_hours:
            permanent_part_time = True
            hours_permanent_part_time = int(line.employee_id.contract_id.weekly_hours)
            # worked_days = (
            #         worked_days *
            #         line.employee_id.contract_id.daily_hours / line.employee_id.contract_id.standard_daily_hours
            # )

        row = []
        row.append(identification_id)
        row.append(line.employee_id.names)
        row.append(line.employee_id.surnames)
        row.append(gender)
        row.append(sector_code)
        row.append(int(worked_days))
        row.append(line.payment_method)
        row.append('X' if permanent_part_time else '')
        row.append(hours_permanent_part_time if permanent_part_time else '')
        row.append('X' if line.employee_id.disability else '')
        row.append('')
        row.append(line.judicial_withholding if line.judicial_withholding > 0 else '')
        row.append('X' if line.employee_id.contract_id.payment_fourteenth_salary == 'monthly' else '')
        return row
    
    def decimo3roReportCVS(self, line):
        """
        Genera las líneas del archivo CSV, para el reporte de décimo tercer salario.
        """
        identification_id = line.employee_id.identification_id
        if line.employee_id.identification_type.name == "Pasaporte":
            identification_id = '#UIO' + identification_id

        gender = ''
        if line.employee_id.gender == 'male':
            gender = 'M'
        elif line.employee_id.gender == 'female':
            gender = 'F'

        sector_code = ''
        if line.employee_id.contract_id.IESS_sector_code:
            sector_code = line.employee_id.contract_id.IESS_sector_code.IESS_code

        permanent_part_time = False
        hours_permanent_part_time = 0
        worked_days = line.worked_days
        if line.employee_id.contract_id.daily_hours < line.employee_id.contract_id.standard_daily_hours:
            permanent_part_time = True
            hours_permanent_part_time = int(line.employee_id.contract_id.weekly_hours)
            # worked_days = (
            #         worked_days *
            #         line.employee_id.contract_id.daily_hours / line.employee_id.contract_id.standard_daily_hours
            # )

        row = []
        row.append(identification_id)
        row.append(line.employee_id.names)
        row.append(line.employee_id.surnames)
        row.append(gender)
        row.append(sector_code)
        row.append("{0:.2f}".format(float_round(line.taxable_income, 2)))
        row.append(int(worked_days))
        row.append(line.payment_method)
        row.append('X' if permanent_part_time else '')
        row.append(hours_permanent_part_time if permanent_part_time else '')
        row.append('X' if line.employee_id.disability else '')
        row.append(line.judicial_withholding if line.judicial_withholding > 0 else '')
        row.append('X' if line.employee_id.contract_id.payment_thirteenth_salary == 'monthly' else '')
        return row
    
    def get_provision_CSV(self):
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=';')
        if self.type_tenth in ['sierra_oriente_fourteenth_salary', 'costa_fourteenth_salary']:
            writer.writerow(HEAD_D14)
            name = 'Décimo cuarto sueldo.csv'
        else:
            writer.writerow(HEAD_D13)
            name = 'Décimo tercer sueldo.csv'
        row = []
        tenth_line_ids = self.env['hr.tenth.line'].search([('tenth_id', '=', self.id)])
        line_ids = sorted(tenth_line_ids, key=lambda x: x.mapped('employee_id').mapped('name'))
        for line in line_ids:
            valor = line.monthly_amount + line.provisioned_amount
            if valor == 0 and line.worked_days == 0:
                continue
            if self.type_tenth in ['sierra_oriente_fourteenth_salary', 'costa_fourteenth_salary']:
                row = self.decimo4toReportCVS(line)
            else:
                row = self.decimo3roReportCVS(line)
            writer.writerow(row)

        out = buf.getvalue()
        try:
            out = out.decode('utf-8')
        except AttributeError:
            pass
        out = base64.encodebytes(out.encode('iso-8859-1'))

        buf.close()
        return self.env['base.file.report'].show(out, name)
    
    def action_paid(self):
        pass

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

    def get_name_type_tenth(self):
        return dict(self._fields['type_tenth'].selection).get(self.type_tenth)

    def _compute_total_payment_employee(self):
        for provision in self:
            total_payment = 0
            for tenth_line in provision.tenth_line_ids:
                total_payment = total_payment + tenth_line.amount_to_receive
            provision.total_payment_employee = total_payment

    def _compute_total_payment_beneficiary(self):
        for provision in self:
            total_payment = 0
            for tenth_line in provision.judicial_withholding_summary_ids:
                total_payment = total_payment + tenth_line.retained_judicial_withholding
            provision.total_payment_beneficiary = total_payment

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        department = 'Dirección de Talento Humano'
        management_responsible = self.sudo().employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        local_context['type_tenth'] = self.get_name_type_tenth()[0]
        return local_context

    def _default_employee(self):
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate'])], limit=1)

    name = fields.Char(string='Name', readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    date = fields.Date(string='Posting date', default=fields.Date.context_today, index=True,
                       help='Date for the generation of the accounting entry.', tracking=True)
    TYPE_TENTH = [
        ('sierra_oriente_fourteenth_salary', _('Sierra - East (Fourteenth salary)')),
        ('costa_fourteenth_salary', _('Coast - Galapagos (Fourteenth salary)')),
        ('thirteenth_salary', _('Thirteenth salary'))
    ]
    type_tenth = fields.Selection(TYPE_TENTH, string='Type of tenth', help='', tracking=True)
    fiscal_year = fields.Integer(string='Fiscal year', required=True, help='', tracking=True)
    value_sbu = fields.Monetary(string='Value SBU', required=True, tracking=True, currency_field='currency_id')
    value_sbu_previous_fiscal_year = fields.Monetary(string='Value SBU for the previous fiscal year',
                                                     required=True, tracking=True, currency_field='currency_id')
    percent_increase_sbu = fields.Float(string='Percent increase SBU')
    date_from = fields.Date(string='Period start', help='', tracking=True)
    date_to = fields.Date(string='Period end', help='', tracking=True)
    tenth_line_ids = fields.One2many('hr.tenth.line', 'tenth_id', string='Details', help='')
    judicial_withholding_summary_ids = fields.One2many('hr.tenth.judicial.withholding.summary', 'tenth_id',
                                                       string='judicial.withholding.summary', help='')
    state = fields.Selection(selection_add=[
        ('calculated', _('Calculated')),
        ('reviewed', _('Reviewed')),
        ('done', _('Done'))])
    total_payment_employee = fields.Monetary(compute='_compute_total_payment_employee',
                                             string='Total payable to collaborators',
                                             currency_field='currency_id')
    total_payment_beneficiary = fields.Monetary(compute='_compute_total_payment_beneficiary',
                                                string='Total payable to beneficiaries',
                                                currency_field='currency_id')


class HrTenthLine(models.Model):
    _name = 'hr.tenth.line'
    _description = 'Tenth line'
    _inherit = ['mail.thread']
    _order = "tenth_id desc,state,employee_id"
    _rec_name = "employee_id"

    @api.depends('amount', 'monthly_amount', 'advance_amount', 'retained_judicial_withholding')
    def compute_amount_to_receive(self):
        for rec in self:
            if rec.tenth_id.type_tenth in ('costa_fourteenth_salary', 'sierra_oriente_fourteenth_salary'):
                rec.amount_to_receive = (
                        rec.amount - (rec.monthly_amount + rec.advance_amount) - rec.retained_judicial_withholding
                )
            else:
                rec.amount_to_receive = (
                        rec.amount - (rec.monthly_amount + rec.advance_amount) - rec.retained_judicial_withholding
                )
    
    def action_view_account_form_lines(self):
        """
        Accion para mostrar los asientos relacionados a los décimos.
        """
        pass

    @api.depends('payment_method_employee',
                 'judicial_withholding_ids',
                 'judicial_withholding_ids.partner_id',
                 'judicial_withholding_ids.partner_id.payment_method')
    def compute_payment_method(self):
        for rec in self:
            rec.payment_method = ''
            if len(rec.judicial_withholding_ids) > 0:
                rec.payment_method = 'RA'
                for jw in rec.judicial_withholding_ids:
                    if jw.partner_id.payment_method == 'CHQ':
                        rec.payment_method = 'RP'
                        break
                    elif rec.payment_method_employee == 'EFE':
                        rec.payment_method = 'RP'
                        break
            else:
                if rec.payment_method_employee == 'CHQ':
                    rec.payment_method = 'P'
                elif rec.payment_method_employee == 'EFE':
                    rec.payment_method = 'P'
                elif rec.payment_method_employee == 'CTA':
                    rec.payment_method = 'A'

    @api.depends('employee_id')
    def _get_current_contract(self):
        """
        El contrato vigente a la fecha de liquidación del décimo, utilizado para determinar el grupo contable
        retorna un objeto hr.contract
        """
        for line in self:
            contract_id = False
            contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', line.employee_id.id),
                ('state', 'in', ['open', 'close'])],
                order='date_start DESC', limit=1
            )
            line.contract_id = contract_id
    
    def make_move(self):
        pass
    
    def _compute_move_lines(self, move_header):
        pass
    
    def _create_account_moves(self, move_dict, line_ids):
        pass

    tenth_id = fields.Many2one('hr.tenth', string='Tenth', index=True, ondelete='cascade', tracking=True)
    type_tenth = fields.Selection(string='Type of tenth', related='tenth_id.type_tenth', tracking=True)
    company_id = fields.Many2one(related='tenth_id.company_id', string='Company')
    currency_id = fields.Many2one(related='tenth_id.currency_id', string='Currency')

    state = fields.Selection(string='Status', tracking=True, related='tenth_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string='Collaborator', required=True, ondelete='cascade', help='',
                                  tracking=True)
    employee_state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
        ('unemployed', _('Unemployed')),
        ('retired', _('Retired'))
    ], string='Collaborator status', tracking=True)
    payment_method_employee = fields.Selection(string='Payment method defined in the employee',
                                               related='employee_id.payment_method', help='', tracking=True)

    taxable_income = fields.Monetary(string='Taxable income', help='', tracking=True, currency_field='currency_id')
    worked_days = fields.Float(string='Worked days', digits='Payroll', help='', tracking=True)
    amount = fields.Monetary(string='Amount', help='', tracking=True, currency_field='currency_id')
    by_increment_sbu = fields.Monetary(string='By increment in SBU', help='', tracking=True,
                                       currency_field='currency_id')
    provisioned_amount = fields.Monetary(string='Provisioned', help='', tracking=True, currency_field='currency_id')
    monthly_amount = fields.Monetary(string='Monthly', help='', tracking=True, currency_field='currency_id')
    judicial_withholding = fields.Monetary(string='Judicial withholding', tracking=True, help='',
                                           currency_field='currency_id')
    retained_judicial_withholding = fields.Monetary(string='Retained judicial withholding', tracking=True, help='',
                                                    currency_field='currency_id')
    discounted_judicial_withholding = fields.Monetary(string='Discounted judicial withholding', tracking=True, help='',
                                                      currency_field='currency_id')
    advance_amount = fields.Monetary(string='Tenth advance', tracking=True, help='', currency_field='currency_id')
    amount_to_receive = fields.Monetary(string='To receive', compute='compute_amount_to_receive',
                                        help='', tracking=True,
                                        currency_field='currency_id')
    payment_method = fields.Selection([
        ('P', _('Pago Directo')),
        ('A', _('Acreditación en Cuenta')),
        ('RP', _('Retención Pago Directo')),
        ('RA', _('Retención Acreditación en Cuenta'))],
        string='Payment method', store=True, compute=compute_payment_method,
        help='Field used for the generation of the CSV.', tracking=True)
    move_id = fields.Many2one('account.move', string='Accounting seat', help='Settlement entry', tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', compute='_get_current_contract', store=False,
                                  help='Contract valid on the date of payment.', tracking=True)
    judicial_withholding_ids = fields.One2many('hr.tenth.line.judicial.withholding', 'tenth_line_id',
                                               string='Judicial withholdings', help='')
    judicial_withholding_summary_ids = fields.One2many('hr.tenth.line.judicial.withholding.summary', 'tenth_line_id',
                                                       string='Judicial withholding summary', help='')


class HrTenthJudicialWithholdingSummary(models.Model):
    _name = 'hr.tenth.judicial.withholding.summary'
    _description = 'Tenth judicial withholding summary'
    _inherit = ['mail.thread']
    _order = "tenth_id desc"

    tenth_id = fields.Many2one('hr.tenth', string='Tenth', index=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='tenth_id.company_id', string='Company')
    currency_id = fields.Many2one(related='tenth_id.currency_id', string='Currency')
    retained_judicial_withholding = fields.Monetary(string='Retained judicial withholding', tracking=True,
                                                    currency_field='currency_id')
    discounted_judicial_withholding = fields.Monetary(string='Discounted judicial withholding', tracking=True,
                                                      currency_field='currency_id')
    partner_id = fields.Many2one('res.partner', string='Beneficiary', tracking=True)


class HrTenthLineJudicialWithholding(models.Model):
    _name = 'hr.tenth.line.judicial.withholding'
    _description = 'Tenth line judicial withholding'
    _inherit = ['mail.thread']
    _order = "tenth_line_id"

    tenth_line_id = fields.Many2one('hr.tenth.line', string='Tenth detail', ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='tenth_line_id.company_id', string='Company')
    currency_id = fields.Many2one(related='tenth_line_id.currency_id', string='Currency')
    ORIGIN = [
        ('of_the_payroll', _('Of the payroll')),
        ('of_the_historical', _('Of the historical')),
    ]
    origin = fields.Selection(ORIGIN, string='Origin', default='of_the_payroll', tracking=True)
    retained_judicial_withholding = fields.Monetary(string='Retained judicial withholding', tracking=True,
                                                    currency_field='currency_id')
    discounted_judicial_withholding = fields.Monetary(string='Discounted judicial withholding', tracking=True,
                                                      currency_field='currency_id')
    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding', tracking=True)
    family_load_id = fields.Many2one('hr.employee.family.load', string='Family load', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Beneficiary', tracking=True)


class HrTenthLineJudicialWithholdingSummary(models.Model):
    _name = 'hr.tenth.line.judicial.withholding.summary'
    _description = 'Tenth line judicial withholding summary'
    _inherit = ['mail.thread']
    _order = "tenth_line_id"

    tenth_line_id = fields.Many2one('hr.tenth.line', string='Tenth detail', ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='tenth_line_id.company_id', string='Company')
    currency_id = fields.Many2one(related='tenth_line_id.currency_id', string='Currency')
    retained_judicial_withholding = fields.Monetary(string='Retained judicial withholding', tracking=True,
                                                    currency_field='currency_id')
    discounted_judicial_withholding = fields.Monetary(string='Discounted judicial withholding', tracking=True,
                                                      currency_field='currency_id')
    partner_id = fields.Many2one('res.partner', string='Beneficiary', tracking=True)