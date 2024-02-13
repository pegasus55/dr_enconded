# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round as round
from datetime import datetime
import io
import base64, csv
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from .common import convert_utc_time_to_tz

HEAD = [
    'Cédula (Ejm.:0502366503)',
    "Nombres",
    'Apellidos',
    'Genero (Masculino=M ó Femenino=F)',
    'Ocupación',
    'Cargas familiares',
    'Días laborados (360 días equivalen a un año)',
    'Tipo de Pago Utilidad(Pago Directo=P, Depósito MDT=D Para Declaraciones < 2015 y Depósito Empresa = E para Declaraciones >= 2015, Acreditación en Cuenta=A, Retención Pago Directo=RP, Retención Depósito MDT=RD, Retención Acreditación en Cuenta=RA)',
    'JORNADA PARCIAL PERMANENTE(Ponga una X si el trabajador tiene un JORNADA PARCIAL PERMANENTE)',
    'DETERMINE EN HORAS LA JORNADA PARCIAL PERMANENTE SEMANAL ESTIPULADO EN EL CONTRATO',
    'DISCAPACITADOS(Ponga una X si el trabajador tienediscapacidad)',
    'RUC DE LA EMPRESA COMPLEMENTARIA O DE UNIFICACION',
    'DECIMOTERCERO VALOR PROPORCIONAL AL TIEMPO LABORADO YEAR',
    'DECIMOCUARTO VALOR PROPORCIONAL AL TIEMPO LABORADO DEL YEAR',
    'PARTICIPACION DE UTILIDADES LAST_YEAR',
    'SALARIOS PERCIBIDOS YEAR',
    'FONDOS DE RESERVA YEAR',
    'COMISIONES DEL YEAR',
    'BENEFICIOS ADICIONALES EN EFECTIVO YEAR',
    'Anticipo de Utilidad',
    'Retencion Judicial',
    'Impuesto Retencion',
    'Sobresueldo / Gratificaciones YEAR',
    'Tipo de Pago Salario Digno(Pago Directo=P, Depósito MDT=D Para Declaraciones < 2015 y Depósito Empresa = E para Declaraciones >= 2015, Acreditación en Cuenta=A)'
]


class Line(object):
    """Clase auxiliar para la generación de ficheros"""
    def __init__(self, dict):
        self.__dict__ = dict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _any_sons_disability(self):
        for fl in self.family_load_ids:
            if ((fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter') and
                    fl.disability):
                return True
        return False

    is_external_service_personnel = fields.Boolean(string='Is external service personnel', default=False)
    surnames = fields.Char(string='Surnames')
    names = fields.Char(string='Names')
    gender = fields.Selection([
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other'))
    ], string='Gender')
    occupation = fields.Many2one('hr.sector.table', string='Occupation')
    disability = fields.Boolean(string='Disability', tracking=True)
    family_load_ids = fields.One2many('res.partner.family.load', 'partner_id', string='Family loads')
    judicial_withholding_ids = fields.One2many('res.partner.judicial.withholding', 'partner_id',
                                               string='Judicial withholdings')


class ResPartnerFamilyLoad(models.Model):
    _name = 'res.partner.family.load'
    _description = 'Partner family load'
    _inherit = ['mail.thread']
    _order = "partner_id"

    def compute_age(self):
        for efl in self:
            if efl.date_of_birth:
                today = datetime.utcnow()
                tz_name = efl.partner_id.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    raise ValidationError(_(
                        "Local time zone is not defined. You may need to set a time zone "
                        "in your employee or user's preferences."))
                today = convert_utc_time_to_tz(today, tz_name)
                today = today.date()
                age = today.year - efl.date_of_birth.year
                birthday = efl.date_of_birth + relativedelta(years=age)
                if birthday > today:
                    age = age - 1
                efl.age = age
            else:
                efl.age = 0

    age = fields.Integer(string='Age', compute='compute_age', store=False)
    name = fields.Char(string='Name', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of birth', tracking=True)
    _RELATIONSHIP = [
        ('parent', _('Parent')),
        ('mother', _('Mother')),
        ('father', _('Father')),
        ('siblings', _('Siblings')),
        ('sister', _('Sister')),
        ('brother', _('Brother')),
        ('spouses', _('Spouses')),
        ('wife', _('Wife')),
        ('husband', _('Husband')),
        ('cohabitant', _('Cohabitant')),
        ('children', _('Children')),
        ('daughter', _('Daughter')),
        ('son', _('Son')),
        ('other', _('Other'))
    ]
    relationship = fields.Selection(_RELATIONSHIP, string='Relationship', required=True, tracking=True)
    disability = fields.Boolean(string='Disability', tracking=True)
    disability_conadis = fields.Char(string='Disability conadis', tracking=True)
    disability_percentage = fields.Float(string='Percentage of disability', digits='Employee', tracking=True)
    disability_description = fields.Text(string='Disability description', tracking=True)
    id_type = fields.Many2one('l10n_latam.identification.type', required=True, tracking=True,
                              string="Identification type",
                              domain="[('country_id', '=?', country_id)]",
                              default=lambda self: self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False),
                              help="The type of identification.")
    identification = fields.Char(string='Identification', tracking=True, required=True)
    insured = fields.Boolean(string='Insured')
    phone = fields.Char(string='Phone')
    address = fields.Char(string='Address')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade', tracking=True)
    country_id = fields.Many2one('res.country', related='partner_id.country_id', readonly=True, string="Country")
    active = fields.Boolean(string='Active', default=True, tracking=True)


class ResPartnerJudicialWithholding(models.Model):
    _name = 'res.partner.judicial.withholding'
    _description = 'Partner judicial withholding'
    _inherit = ['mail.thread']
    _order = "partner_id"
    _sql_constraints = [
        ('family_load_id_unique',
         'UNIQUE(family_load_id)',
         "A family load cannot appear in more than one judicial withholding."),
    ]

    def name_get(self):
        return [(record.id,
                 "{}: {} - {} - {}".format(record.beneficiary_id.name, record.card_code, record.judicial_process_number,
                                           record.approval_identifier)) for record in self]

    @api.onchange('beneficiary_id')
    def on_change_partner_id(self):
        if self.beneficiary_id:
            self.representative_name = self.beneficiary_id.name
            self.representative_id_type = self.beneficiary_id.l10n_latam_identification_type_id
            self.representative_identification = self.beneficiary_id.vat

    @api.constrains('value')
    def _constrain_value(self):
        if self.value <= 0:
            raise ValidationError('The value of judicial withholding must be greater than zero.')

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade', tracking=True)
    family_load_id = fields.Many2one('res.partner.family.load', string='Family load', required=True,
                                     domain="[('partner_id', '=', partner_id)]",
                                     ondelete='cascade', tracking=True)
    card_code = fields.Char(string='Card code', required=True, tracking=True)
    judicial_process_number = fields.Char(string='Judicial process number', required=True, tracking=True)
    approval_identifier = fields.Char(string='Approval identifier (NUT)', required=True, tracking=True)
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', required=True, tracking=True)
    representative_name = fields.Char(string='Representative name', tracking=True, required=True)
    representative_id_type = fields.Many2one(
        'l10n_latam.identification.type', required=True, tracking=True, string="Representative identification type",
        domain="[('country_id', '=?', country_id)]",
        default=lambda self: self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False),
        help="The type of identification of the beneficiary.")
    representative_identification = fields.Char(string='Representative identification', required=True, tracking=True)
    value = fields.Monetary(string='Value', required=True, tracking=True, currency_field='currency_id')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', readonly=True, string="Country")
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)


class HrPaymentUtility(models.Model):
    _name = 'hr.payment.utility'
    _description = 'Payment utility'
    _inherit = ['hr.generic.request']
    _rec_name = 'fiscal_year'
    _order = "fiscal_year desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_payment_utility',
            'confirm_direct':
                'hr_dr_payroll_base.email_template_confirm_direct_approve_payment_utility',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_payment_utility',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_payment_utility',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancelled_payment_utility',
            'paid': 'hr_dr_payroll_base.email_template_utility_notify_treasury'
        }
    _hr_notifications_mode_param = 'payment.utility.notifications.mode'
    _hr_administrator_param = 'payment.utility.administrator'
    _hr_second_administrator_param = 'payment.utility.second.administrator'

    def _default_start_date(self):
        start_date = datetime.utcnow().date() + relativedelta(day=1, month=1, years=-1)
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

    @api.onchange('utility_value', 'percent_employee', 'percent_family')
    def onchange_utility_value(self):
        pass

    @api.constrains('start_date')
    def _check_start_date(self):
        for utility in self:
            if utility.start_date:
                if int(utility.start_date.day) != 1 or int(utility.start_date.month) != 1:
                    raise ValidationError('The beginning of the period must be the first of January '
                                          'of the selected year.')
        return True

    @api.onchange('start_date', 'utility_value', 'percent_employee', 'percent_family')
    def on_change_inputs(self):
        self.line_ids = [(6, 0, [])]
        for external_service in self.external_service_ids:
            external_service.amount_10_percent = 0
            external_service.amount_5_percent = 0
            external_service.amount_judicial_withholding = 0

    def action_calculate(self):
        # Eliminar los detalles de utilidad previamente calculados
        line_ids = self.env['hr.payment.utility.line'].with_context(
            active_test=False).search([('payment_utility_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

        for external_service in self.external_service_ids:
            external_service.amount_10_percent = 0
            external_service.amount_5_percent = 0
            external_service.amount_judicial_withholding = 0

        config_parameter = self.env['ir.config_parameter'].sudo()
        profit_calculation_based_on = config_parameter.get_param('profit.calculation.based.on', default='')
        if profit_calculation_based_on != '':
            if profit_calculation_based_on == 'contract':
                self.calculate_by_contract()
            elif profit_calculation_based_on == 'payroll':
                self.calculate_by_payroll()
            elif profit_calculation_based_on == 'history':
                self.calculate_by_history()
            else:
                raise UserError(_('You must define the utility calculation method.'))
        else:
            raise UserError(_('You must define the utility calculation method.'))

    def _get_worked_days_by_contract(self, date_from, date_to, contract):
        # TODO Corregir
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
        else:
            date_from = datetime.strptime(date_from.isoformat(), '%Y-%m-%d')

        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
        else:
            date_to = datetime.strptime(date_to.isoformat(), '%Y-%m-%d')

        if contract:
            if not contract.date_start:
                raise UserError(_('Please enter the contract start date to continue.'))
            else:
                contract_date_start = contract.date_start
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
            if date_to.year % 4:
                worked_days += 2
            else:
                worked_days += 1
        elif date_to.day == 31:
            worked_days = 30
        worked_days -= date_from.day - 1

        return worked_days

    def last_day_of_month(self, date_from):
        date_to = datetime.strptime(date_from.isoformat(), '%Y-%m-%d').date()
        if date_to.month == 12:
            return date_to.replace(day=31)
        return date_to.replace(month=date_to.month + 1, day=1) - timedelta(days=1)

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

    def calculate_by_contract(self):
        pass

    def calculate_by_payroll(self):
        pass

    def calculate_by_history(self):
        pass

    def mark_as_draft(self):
        super(HrPaymentUtility, self).mark_as_draft()
        line_ids = self.env['hr.payment.utility.line'].with_context(
            active_test=False).search([('payment_utility_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

        for external_service in self.external_service_ids:
            external_service.amount_10_percent = 0
            external_service.amount_5_percent = 0
            external_service.amount_judicial_withholding = 0

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

        template = self.env.ref('hr_dr_payroll_base.email_template_utility_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def _family_load_apply_utility(self, fl):
        def calculate_children_age(children, end_date):
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=end_date.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years

        if ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son') and
            calculate_children_age(fl, self.end_date) < 18) or \
                ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son')
                 and fl.disability) or \
                (fl.relationship == 'spouse' or fl.relationship == 'wife' or fl.relationship == 'husband' or
                 fl.relationship == 'cohabitant'):
            return True
        return False
    
    def get_family_loads_by_employee(self, employee):
        """
        Retorna el número de cargas familiares que se deben tener en cuenta para el cálculo de las utilidades.
        """
        def calculate_children_age(children, end_date):
            """
            Este método calcula la edad con base en la fecha de nacimiento y la fecha de corte de las utilidades.
            """
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=end_date.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years

        amount_family_loads = 0
        for fl in employee.family_load_ids:
            # En el caso de los hijos no se debe preguntar la edad a la fecha,
            # sino la edad que tenía a la fecha de corte de las utilidades.
            # Por ejemplo si estoy pagando las utilidades en abril 2019 debo preguntar la edad al 31/12/2018.
            # Se tiene en cuenta los hijos menores de 18 años.
            if ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son') and
                calculate_children_age(fl, self.end_date) < 18) or \
                    ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son')
                     and fl.disability) or \
                    (fl.relationship == 'spouse' or fl.relationship == 'wife' or fl.relationship == 'husband' or
                     fl.relationship == 'cohabitant'):
                amount_family_loads += 1
        return amount_family_loads

    def get_payment_mode(self, employee):
        pass

    def get_line_utility(self, employee, employee_state, worked_days, family_loads):
        pass

    def get_advance_utility(self, employee):
        pass

    def get_args_search(self, employee):
        pass
    
    def action_validate(self):
        self.write({'state': 'done'})
    
    def action_utility_to_personal_expense(self):
        """
        Se copia la participación en utilidades a los gastos personales del colaborador
        con base al año de la fecha de contabilización de las utilidades y al año fiscal de los
        gastos personales del colaborador.
        """
        for utility in self:
            for line in utility.line_ids:
                # Se suma un año al año fiscal. Por ejemplo las utilidades del 2018 se registran en el 2019.
                fiscal_year = self.fiscal_year + 1
                personal_expense_ids = self.env['hr.personal.expense'].search([
                    ('rent_tax_table_id.fiscal_year', '=', fiscal_year),
                    ('employee_id', '=', line.employee_id.id)])
                for personal_expense in personal_expense_ids:
                    personal_expense.utility = line.total_utility

    def launch_make_move(self, line):
        line.make_move()
    
    def generate_payments(self):
        pass
    
    def action_all_cancel(self):
        """
        Cancelamos y eliminamos el asiento contable y enviamos a estado cancelado el pago de utilidades.
        """
        moves = self.line_ids.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()

        # Se hace 0 la participación en utilidades a los gastos personales del colaborador
        # con base al año de la fecha de contabilización de las utilidades y al año fiscal de los
        # gastos personales del colaborador.
        for line in self.line_ids:
            fiscal_year = self.fiscal_year + 1
            personal_expense_ids = self.env['hr.personal.expense'].search([
                ('rent_tax_table_id.fiscal_year', '=', fiscal_year),
                ('employee_id', '=', line.employee_id.id)])
            for personal_expense in personal_expense_ids:
                personal_expense.utility = 0.0
        return self.write({'state': 'cancelled'})
    
    def action_view_payment(self):
        pass

    def get_mode_by_code(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.mode
        else:
            return ""

    def get_rule_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.salary_rule_code.split()
        else:
            return []

    def get_rule_excluded_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.salary_rule_code_excluded.split()
        else:
            return []

    def get_category_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.category_code.split()
        else:
            return []
    
    def _get_d13_yearly(self, date_from, date_to, employee_id):
        pass
    
    def _get_d14_yearly(self, date_from, date_to, employee_id):
        pass

    def _get_reserve_funds_yearly(self, date_from, date_to, employee_id):
        pass

    def _get_commissions_yearly(self, date_from, date_to, employee_id):
        pass

    def _get_additional_cash_benefits_yearly(self, date_from, date_to, employee_id):
        pass

    def _get_salary_yearly(self, date_from, date_to, employee_id):
        pass
    
    def _get_last_utility(self, year, employee_id):
        """
        Obtenemos el valor de utilidad del ejercicio fiscal anterior.
        """
        line = self.env['hr.payment.utility.line'].search([
            ('fiscal_year', '=', year-1),
            ('employee_id', '=', employee_id.id),
            ('state_utility', 'in', ['done', 'paid'])], limit=1)
        if line:
            return line.total_utility
        else:
            historical = self.env['hr.historical.provision'].sudo().search([
                ('type', '=', 'payment_utility'),
                ('fiscal_year', '=', year-1),
                ('employee_id', '=', employee_id.id),
            ], limit=1)
            if historical:
                return historical.total_value
            else:
                return 0

    def _get_bonus_perks_yearly(self, date_from, date_to, employee_id):
        pass

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        return self

    def _get_payment_mode_last_living_wage(self, year, employee_id):
        payment_mode = 'A'
        line = self.env['pay.living.wage.line'].search([
            ('fiscal_year', '=', year-1),
            ('employee_id', '=', employee_id.id),
            ('value', '>', 0), ('state', 'in', ['paid'])], limit=1)
        if line:
            if line.employee_id.payment_method == 'CHQ' or line.employee_id.payment_method == 'EFE':
                payment_mode = 'P'
            elif line.employee_id.payment_method == 'undefined':
                payment_mode = 'E'
        return payment_mode

    def get_include_external_services_in_csv_file(self):
        include_external_services_in_csv_file = self.env['ir.config_parameter'].sudo().get_param(
            'include.external.services.in.csv.file', '')
        if include_external_services_in_csv_file != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('include.external.services.in.csv.file')))
        else:
            return False

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
        sector_code = self.line_ids.mapped('employee_id').filtered(
            lambda x: not x.mapped('contract_id').iess_sector_code
        )
        if sector_code:
            employees = '\n'.join('- ' + e.name for e in sector_code)
            raise UserError(_('The following collaborators do not have the sector code entered :{}').format(employees))

        precision = self.env['decimal.precision'].precision_get('Payroll')
        for line in line_ids:

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
            if line.employee_id.contract_id.daily_hours < line.employee_id.contract_id.standard_daily_hours:
                permanent_part_time = True
                hours_permanent_part_time = int(line.employee_id.contract_id.weekly_hours)

            disability = ''
            if line.employee_id.disability:
                disability = 'X'
            else:
                if line.employee_id._any_sons_disability():
                    disability = 'X'

            row = []
            row.append(identification_id)
            row.append(line.employee_id.names)
            row.append(line.employee_id.surnames)
            row.append(gender)
            row.append(sector_code)
            row.append(line.family_loads)
            row.append(int(line.worked_days))
            row.append(line.payment_mode)
            row.append('X' if permanent_part_time else '')
            row.append(hours_permanent_part_time if permanent_part_time else '')
            row.append(disability)
            row.append('')
            row.append(self._get_d13_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_d14_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_last_utility(self.fiscal_year, line.employee_id))
            row.append(self._get_salary_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_reserve_funds_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_commissions_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_additional_cash_benefits_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(str(round(line.advance_utility, precision)))
            row.append(str(round(line.amount_judicial_withholding, precision)))
            row.append(0)  # TODO
            row.append(self._get_bonus_perks_yearly(self.start_date, self.end_date, line.employee_id))
            row.append(self._get_payment_mode_last_living_wage(self.fiscal_year, line.employee_id))
            writer.writerow(row)

        if self.get_include_external_services_in_csv_file():
            for line in self.external_service_ids:
                identification_id = line.partner_id.vat
                if line.partner_id.l10n_latam_identification_type_id.name == "Pasaporte":
                    identification_id = '#UIO' + identification_id

                gender = ''
                if line.partner_id.gender == 'male':
                    gender = 'M'
                elif line.partner_id.gender == 'female':
                    gender = 'F'

                sector_code = ''
                if line.partner_id.occupation:
                    sector_code = line.partner_id.occupation.IESS_code

                disability = ''
                if line.partner_id.disability:
                    disability = 'X'
                else:
                    if line.partner_id._any_sons_disability():
                        disability = 'X'

                row = []
                row.append(identification_id)
                row.append(line.partner_id.names)
                row.append(line.partner_id.surnames)
                row.append(gender)
                row.append(sector_code)
                row.append(line.family_loads)
                row.append(int(line.worked_days))
                row.append(line.payment_mode)
                row.append('X' if line.permanent_part_time else '')
                row.append(int(line.hours_permanent_part_time) if line.permanent_part_time else '')
                row.append(disability)
                row.append(line.ruc_complementary_services_company)
                row.append(str(round(line.thirteenth_salary, precision)))
                row.append(str(round(line.fourteenth_salary, precision)))
                row.append(str(round(line.profits_previous_year, precision)))
                row.append(str(round(line.wage, precision)))
                row.append(str(round(line.reserve_funds, precision)))
                row.append(str(round(line.commissions, precision)))
                row.append(str(round(line.additional_cash_benefits, precision)))
                row.append(str(round(line.advance_utility, precision)))
                row.append(str(round(line.amount_judicial_withholding, precision)))
                row.append(0)  # TODO
                row.append(str(round(line.bonus_and_perks, precision)))
                row.append(line.payment_mode_living_wage)
                writer.writerow(row)

        out = buf.getvalue()
        try:
            out = out.decode('utf-8')
        except AttributeError:
            pass
        out = base64.encodebytes(out.encode('iso-8859-1'))
        buf.close()
        return self.env['base.file.report'].show(out, 'Utilidades - ' + str(self.fiscal_year) +'.csv')

    start_date = fields.Date(string='Period start', default=_default_start_date, tracking=True)
    end_date = fields.Date(string='Period end', tracking=True)
    fiscal_year = fields.Integer(string='Fiscal year', tracking=True)
    state = fields.Selection(
        selection_add=[
            ('calculated', _('Calculated')),
            ('reviewed', _('Reviewed')),
            ('done', _('Done')),
            ('paid', _('Paid')),
        ])
    utility_value = fields.Monetary(string='Total profit of the company', tracking=True,
                                    help='Total profit of the company.', currency_field='currency_id')
    utility_value_to_distribute = fields.Monetary(string='Utility to distribute', tracking=True,
                                                  currency_field='currency_id',
                                                  help="It represents the sum of the percentages to be distributed "
                                                       "among the collaborators and the family loads on "
                                                       "the total utility of the company.")
    percent_employee = fields.Float(string='Percentage to distribute among collaborators', default=10,
                                    digits='Payroll', tracking=True)
    percent_family = fields.Float(string='Percentage to be distributed among family loads', default=5,
                                  digits='Payroll', tracking=True)
    date = fields.Date(string='Posting date', default=_default_date,
                       help='Date for the generation of the accounting entry.', tracking=True)
    total_worked_days = fields.Float(string='Total worked days', digits='Payroll', tracking=True)
    total_worked_days_x_family_loads = fields.Float(string='Total worked days multiplied by family loads',
                                                    digits='Payroll', tracking=True,
                                                    help='Multiply in each detail the worked days by the family loads '
                                                         'and add all the results.')
    line_ids = fields.One2many('hr.payment.utility.line', 'payment_utility_id', string='Details')
    external_service_ids = fields.One2many('hr.payment.utility.external.service', 'payment_utility_id',
                                           string='External services')


class HrPaymentUtilityLine(models.Model):
    _name = 'hr.payment.utility.line'
    _description = 'Payment utility detail'
    _inherit = ['mail.thread']
    _order = "payment_utility_id,employee_id"
    _rec_name = "employee_id"
    
    def make_move(self):
        pass
    
    def _compute_move_lines(self, move_header, division=False):
        pass
    
    def _create_account_moves(self, move_dict, line_ids):
        pass

    @api.depends('payment_method_employee',
                 'judicial_withholding_ids',
                 'judicial_withholding_ids.partner_id',
                 'judicial_withholding_ids.partner_id.payment_method')
    def compute_payment_mode(self):
        for rec in self:
            rec.payment_mode = ''
            if len(rec.judicial_withholding_ids) > 0:
                rec.payment_mode = 'RA'
                for jw in rec.judicial_withholding_ids:
                    if jw.partner_id.payment_method == 'CHQ' or rec.payment_method_employee == 'EFE':
                        rec.payment_mode = 'RP'
                        break
                    elif jw.partner_id.payment_method == 'undefined':
                        rec.payment_mode = 'RD'
                        break
            else:
                if rec.payment_method_employee == 'CHQ' or rec.payment_method_employee == 'EFE':
                    rec.payment_mode = 'P'
                elif rec.payment_method_employee == 'CTA':
                    rec.payment_mode = 'A'
                elif rec.payment_method_employee == 'undefined':
                    rec.payment_mode = 'E'
    
    _PAYMENT_MODE = [
        ('P', _('Pago Directo')),
        ('D', _('Depósito MDT (Declaraciones < 2015)')),
        ('E', _('Depósito Empresa (Declaraciones >= 2015)')),
        ('A', _('Acreditación en Cuenta')),
        ('RP', _('Retención Pago Directo')),
        ('RD', _('Retención Depósito MDT')),
        ('RA', _('Retención Acreditación en Cuenta'))
    ]
    employee_id = fields.Many2one('hr.employee', string='Collaborator', ondelete='cascade', tracking=True)
    employee_state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
        ('unemployed', _('Unemployed')),
        ('retired', _('Retired'))
    ], string='Collaborator status', tracking=True)
    payment_method_employee = fields.Selection(string='Payment method defined in the employee',
                                               related='employee_id.payment_method', tracking=True)

    worked_days = fields.Float(string='Worked days', digits='Payroll', tracking=True)
    family_loads = fields.Integer(string='Number of family loads', tracking=True)
    judicial_withholding = fields.Integer(string='Number of judicial withholding', tracking=True)
    advance_utility = fields.Monetary(string='Utility advance', tracking=True, currency_field='currency_id')
    amount_judicial_withholding = fields.Monetary(string='Judicial withholding',
                                                  tracking=True, currency_field='currency_id')
    amount_10_percent = fields.Monetary(string='To receive based on the percentage to distribute among collaborators',
                                        currency_field='currency_id',
                                        tracking=True)
    amount_5_percent = fields.Monetary(string='To receive based on the percentage to be distributed among family loads',
                                       currency_field='currency_id',
                                       tracking=True)
    total_utility = fields.Monetary(string='Utility', tracking=True, currency_field='currency_id')
    payment_mode = fields.Selection(_PAYMENT_MODE, string='Payment mode', tracking=True,
                                    compute=compute_payment_mode)
    total_receive = fields.Monetary(string='To receive', digits='Payroll', tracking=True,
                                    currency_field='currency_id')

    payment_utility_id = fields.Many2one('hr.payment.utility', string='Payment utility', ondelete='cascade',
                                         index=True)
    company_id = fields.Many2one(related='payment_utility_id.company_id', string='Company')
    currency_id = fields.Many2one(related='payment_utility_id.currency_id', string='Currency')
    state_utility = fields.Selection(string='Status', related='payment_utility_id.state', store="True")
    fiscal_year = fields.Integer(related='payment_utility_id.fiscal_year', store="True", string='Fiscal year',
                                 tracking=True)
    move_id = fields.Many2one('account.move', string='Accounting seat', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    judicial_withholding_ids = fields.One2many('utility.line.judicial.withholding', 'utility_line_id',
                                               string='Judicial withholdings')


class UtilityLineJudicialWithholding(models.Model):
    _name = 'utility.line.judicial.withholding'
    _description = 'Utility detail judicial withholding'
    _inherit = ['mail.thread']
    _order = "utility_line_id"

    utility_line_id = fields.Many2one('hr.payment.utility.line', string='Utility detail', ondelete='cascade',
                                      tracking=True)
    company_id = fields.Many2one(related='utility_line_id.company_id', string='Company')
    currency_id = fields.Many2one(related='utility_line_id.currency_id', string='Currency')
    amount = fields.Monetary(string='Amount', tracking=True, currency_field='currency_id')
    judicial_withholding_id = fields.Many2one('hr.judicial.withholding', string='Judicial withholding', tracking=True)
    family_load_id = fields.Many2one('hr.employee.family.load', string='Family load', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Beneficiary', required=True, tracking=True)


class HrPaymentUtilityExternalService(models.Model):
    _name = 'hr.payment.utility.external.service'
    _description = 'Payment utility external service'
    _inherit = ['mail.thread']
    _order = "payment_utility_id,partner_id"
    _rec_name = "partner_id"

    @api.depends('partner_id',
                 'payment_method_partner',
                 'partner_id.judicial_withholding_ids.partner_id',
                 'partner_id.judicial_withholding_ids.partner_id.payment_method')
    def compute_payment_mode(self):
        for rec in self:
            rec.payment_mode = ''
            if len(rec.partner_id.judicial_withholding_ids) > 0:
                rec.payment_mode = 'RA'
                for jw in rec.partner_id.judicial_withholding_ids:
                    if jw.partner_id.payment_method == 'CHQ' or jw.partner_id.payment_method == 'EFE':
                        rec.payment_mode = 'RP'
                        break
                    elif jw.partner_id.payment_method == 'undefined':
                        rec.payment_mode = 'RD'
                        break
            else:
                if rec.payment_method_partner == 'CHQ' or rec.payment_method_partner == 'EFE':
                    rec.payment_mode = 'P'
                elif rec.payment_method_partner == 'CTA':
                    rec.payment_mode = 'A'
                elif rec.payment_method_partner == 'undefined':
                    rec.payment_mode = 'E'

    _PAYMENT_MODE = [
        ('P', _('Pago Directo')),
        ('D', _('Depósito MDT (Declaraciones < 2015)')),
        ('E', _('Depósito Empresa (Declaraciones >= 2015)')),
        ('A', _('Acreditación en Cuenta')),
        ('RP', _('Retención Pago Directo')),
        ('RD', _('Retención Depósito MDT')),
        ('RA', _('Retención Acreditación en Cuenta'))
    ]
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', tracking=True)
    payment_method_partner = fields.Selection(string='Payment method defined in the partner',
                                              related='partner_id.payment_method', tracking=True)
    worked_days = fields.Float(string='Worked days', digits='Payroll', tracking=True)
    family_loads = fields.Integer(string='Number of family loads', tracking=True)
    judicial_withholding = fields.Integer(string='Number of judicial withholding', tracking=True)
    amount_judicial_withholding = fields.Monetary(string='Judicial withholding',
                                                  tracking=True, currency_field='currency_id')
    withholding_tax = fields.Monetary(string='Withholding tax', tracking=True, currency_field='currency_id')
    amount_10_percent = fields.Monetary(string='To receive based on the percentage to distribute among collaborators',
                                        currency_field='currency_id', tracking=True)
    amount_5_percent = fields.Monetary(string='To receive based on the percentage to be distributed among family loads',
                                       currency_field='currency_id', tracking=True)
    total_utility = fields.Monetary(string='Utility', tracking=True, currency_field='currency_id')
    payment_mode = fields.Selection(_PAYMENT_MODE, string='Payment mode', tracking=True, compute=compute_payment_mode)
    total_receive = fields.Monetary(string='To receive', tracking=True, currency_field='currency_id')
    payment_utility_id = fields.Many2one('hr.payment.utility', string='Payment utility', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='payment_utility_id.company_id', string='Company')
    currency_id = fields.Many2one(related='payment_utility_id.currency_id', string='Currency')
    state_utility = fields.Selection(related='payment_utility_id.state', store="True")
    fiscal_year = fields.Integer(related='payment_utility_id.fiscal_year', store="True", string='Fiscal year',
                                 tracking=True)
    move_id = fields.Many2one('account.move', string='Accounting seat', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    permanent_part_time = fields.Boolean(string='Permanent part-time', default=False)
    hours_permanent_part_time = fields.Float(string='Hours permanent part-time', digits='Payroll')
    ruc_complementary_services_company = fields.Char(string='RUC complementary services company')
    thirteenth_salary = fields.Monetary(string='Thirteenth salary', currency_field='currency_id')
    fourteenth_salary = fields.Monetary(string='Fourteenth salary', currency_field='currency_id')
    profits_previous_year = fields.Monetary(string='Profits previous year', currency_field='currency_id')
    wage = fields.Monetary(string='Wage', currency_field='currency_id')
    reserve_funds = fields.Monetary(string='Reserve funds', currency_field='currency_id')
    commissions = fields.Monetary(string='Commissions', currency_field='currency_id')
    additional_cash_benefits = fields.Monetary(string='Additional cash benefits', currency_field='currency_id')
    bonus_and_perks = fields.Monetary(string='Bonus and perks', currency_field='currency_id')
    utility_advance = fields.Monetary(string='Utility advance', currency_field='currency_id')
    _PAYMENT_MODE_LIVING_WAGE = [
        ('P', _('Pago Directo')),
        ('D', _('Depósito MDT (Declaraciones < 2015)')),
        ('E', _('Depósito Empresa (Declaraciones >= 2015)')),
        ('A', _('Acreditación en Cuenta')),
    ]
    payment_mode_living_wage = fields.Selection(_PAYMENT_MODE_LIVING_WAGE, string='Payment mode living wage')