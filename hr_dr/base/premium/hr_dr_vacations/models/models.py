# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from xlsxwriter.utility import xl_rowcol_to_cell
import pytz, logging
from datetime import datetime, time, timedelta

_logger = logging.getLogger(__name__)


class EmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    @api.model
    def get_vacations_signature_mode(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        signature_mode = config_parameter.get_param('vacations.signature.mode', default='')
        return signature_mode

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].sudo().search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'

    def format_long_date_sp(self, datetime_instance):
        """
        Recibe una fecha y devuelve su representación en forma de texto de la forma '[día] de [mes] de [año]' para el
        idioma español.
        """
        months = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
                  7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}

        return datetime_instance.strftime('%d de {} de %Y').format(months[datetime_instance.month])


class Employee(models.Model):
    _inherit = 'hr.employee'

    cutoff_date = fields.Date('Cutoff date')
    vacations_cutoff_date = fields.Float(string='Vacations available at the cutoff date', digits='Vacations')
    vacations_taken_cutoff_date = fields.Float(string='Vacations taken at the cutoff date', digits='Vacations')
    total_vacations_accumulated_cutoff_date = fields.Float(string='Total vacations accumulated at the cutoff date',
                                                           digits='Vacations')
    total_vacations_available = fields.Float(string='Total vacations available', digits='Vacations')
    total_vacations_available_including_proportional_period = fields.Float(
        string='Total vacations available (including proportional period)', digits='Vacations')
    vacation_planning_request_ids = fields.One2many('hr.vacation.planning.request', 'employee_requests_id',
                                                    string="Vacation planning request",
                                                    readonly=True)
    vacation_execution_request_ids = fields.One2many('hr.vacation.execution.request', 'employee_requests_id',
                                                     string="Vacation execution request",
                                                     readonly=True)
    vacation_detail_ids = fields.One2many('hr.employee.vacation.detail', 'employee_id', string="Vacation detail")
    total_days_in_company_in_previous_periods_except_last = fields.Integer(
        string='Total days in company in previous periods except last', store=True, readonly=True,
        compute='compute_total_days_in_company_in_previous_periods_except_last', tracking=True)

    # Base para el cálculo proporcional de vacaciones, 360.
    def get_vacation_base_calculation(self):
        acronym = 'CBDPCV'
        module = self.env.ref('base.module_' + self._module)
        vacation_base_calculation = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if vacation_base_calculation:
            vacation_base_calculation = vacation_base_calculation.integer_value
            return vacation_base_calculation
        else:
            # Error de configuración, comuníquese con el administrador. Normativa asignada al colaborador: {}.
            # Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Normativa: {},
            # Módulo del nomenclador: {}, Siglas del nomenclador: {}.
            raise ValidationError(_("Configuration error, contact administrator. "
                                    "Normative assigned to the collaborator: {}. "
                                    "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                                    "Nomenclature Module: {}, Nomenclature Acronym: {}.")
                                  .format(self.normative_id.name, self.normative_id.name, module.display_name, acronym)
                                  )

    # Número de días estandar de vacaciones que se acumulan en un período completo.
    # 15 ó 30 en función de la normativa del colaborador.
    def get_vacation_standard_accumulated(self):
        acronym = 'CDVAA'
        module = self.env.ref('base.module_' + self._module)

        vacation_standard_accumulated = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if vacation_standard_accumulated:
            vacation_standard_accumulated = vacation_standard_accumulated.integer_value
            return vacation_standard_accumulated
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Años de antigüedad a partir de los cuales se suman años adicionales de vacaciones.
    def _get_min_years_for_additional_vacation(self):
        acronym = 'CAAPCIDAV'
        module = self.env.ref('base.module_' + self._module)
        min_years_for_additional_vacation = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if min_years_for_additional_vacation:
            min_years_for_additional_vacation = min_years_for_additional_vacation.integer_value
            return min_years_for_additional_vacation
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Máximo de días incrementados por antigüedad en cada período.
    def _get_max_days_allows_vacation_increase(self):
        acronym = 'CMDAQSIPA'
        module = self.env.ref('base.module_' + self._module)

        max_days_allows_vacation_increase = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if max_days_allows_vacation_increase:
            max_days_allows_vacation_increase = max_days_allows_vacation_increase.integer_value
            return max_days_allows_vacation_increase
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Número de días laborales de vacaciones que se acumulan en un período completo.
    # 11 ó 22 en función de la normativa del colaborador.
    def get_vacation_standard_worked_accumulated(self):
        acronym = 'CDLTAA'
        module = self.env.ref('base.module_' + self._module)
        standard_labor_accumulated = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if standard_labor_accumulated:
            standard_labor_accumulated = standard_labor_accumulated.integer_value
            return standard_labor_accumulated
        else:
            raise ValidationError(
                _(
                    "Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                    "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                    "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Número de días no laborales de vacaciones que se acumulan en un período completo.
    # 4 ó 8 en función de la normativa del colaborador.
    def _get_vacation_standard_not_worked_accumulated(self):
        acronym = 'CDNLTAA'
        module = self.env.ref('base.module_' + self._module)
        standard_no_labor_accumulated = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if standard_no_labor_accumulated:
            standard_no_labor_accumulated = standard_no_labor_accumulated.integer_value
            return standard_no_labor_accumulated
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Cantidad de períodos completos de vacaciones que se pueden acumular sin perder las vacaciones.
    def _get_max_complete_period_vacation_accumulated(self):
        acronym = 'CMPCVPA'
        module = self.env.ref('base.module_' + self._module)

        max_complete_period_vacation_accumulated = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if max_complete_period_vacation_accumulated:
            max_complete_period_vacation_accumulated = max_complete_period_vacation_accumulated.integer_value
            return max_complete_period_vacation_accumulated
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Tomar en cuenta la antigüedad para el cálculo de vacaciones.
    def _get_take_antiquity_vacation_calculation(self):
        acronym = 'TCLAPECV'
        module = self.env.ref('base.module_' + self._module)

        take_antiquity_vacation_calculation = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if take_antiquity_vacation_calculation:
            take_antiquity_vacation_calculation = take_antiquity_vacation_calculation.boolean_value
            return take_antiquity_vacation_calculation
        else:
            raise ValidationError(_("Configuration error, contact administrator. Normative assigned to "
                                    "the collaborator: {}. A valid combination must exist for "
                                    "'hr.normative.nomenclature' --> Normative: {}, Nomenclature Module: {}, "
                                    "Nomenclature Acronym: {}.")
                                  .format(self.normative_id.name, self.normative_id.name, module.display_name, acronym))

    # Tomar en cuenta la edad para el cálculo de vacaciones.
    def _get_take_age_vacation_calculation(self):
        acronym = 'TCLEPECV'
        module = self.env.ref('base.module_' + self._module)

        take_age_vacation_calculation = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if take_age_vacation_calculation:
            take_age_vacation_calculation = take_age_vacation_calculation.boolean_value
            return take_age_vacation_calculation
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    # Tener en cuenta períodos anteriores de trabajo con el empleador actual para antigüedad en vacaciones.
    def _get_take_previous_periods_vacation_calculation(self):
        acronym = 'TCPATEAPAV'
        module = self.env.ref('base.module_' + self._module)

        take_previous_periods_vacation_calculation = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if take_previous_periods_vacation_calculation:
            take_previous_periods_vacation_calculation = take_previous_periods_vacation_calculation.boolean_value
            return take_previous_periods_vacation_calculation
        else:
            raise ValidationError(
                _("Configuration error, contact administrator. Normative assigned to the collaborator: {}. "
                  "A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, "
                  "Nomenclature Module: {}, Nomenclature Acronym: {}.").format(
                    self.normative_id.name,
                    self.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    @api.depends('company_history_ids', 'company_history_ids.employee_id', 'company_history_ids.date_from',
                 'company_history_ids.date_to')
    def compute_total_days_in_company_in_previous_periods_except_last(self):
        for employee in self:
            time_worked_total_day = 0
            for ch in employee.company_history_ids:
                if ch.id != employee.company_history_ids[len(employee.company_history_ids)-1].id:
                    time_worked_total_day += ch.time_worked_total_day
            employee.update({
                'total_days_in_company_in_previous_periods_except_last': time_worked_total_day,
            })

    def has_assigned_shifts(self, date):
        date_i = date + relativedelta(hour=0, minute=0, second=0)
        date_f = date + relativedelta(hour=23, minute=59, second=59)
        count_assigned_shifts = self.env['hr.employee.shift'].sudo().search_count([
            ('employee_id', '=', self.id),
            ('planned_start', '>=', date_i),
            ('planned_start', '<=', date_f)
        ])
        if count_assigned_shifts > 0:
            return True
        else:
            return False

    def get_assigned_shifts(self, date):
        date_i = date + relativedelta(hour=0, minute=0, second=0)
        date_f = date + relativedelta(hour=23, minute=59, second=59)
        assigned_shifts = self.env['hr.employee.shift'].sudo().search([
            ('employee_id', '=', self.id),
            ('planned_start', '>=', date_i),
            ('planned_start', '<=', date_f)
        ])
        return assigned_shifts

    def _get_increase_by_age(self, period_type, date_from, date_to):
        take_age_vacation_calculation = self._get_take_age_vacation_calculation()

        if take_age_vacation_calculation:

            # Base para el calculo proporcional de vacaciones, 360
            vacation_base_calculation = self.get_vacation_base_calculation()

            if period_type == 'complete':
                birthday_in_period = self.birthday + relativedelta(year=date_from.year)
                if not (birthday_in_period >= date_from and birthday_in_period <= date_to):
                    birthday_in_period = self.birthday + relativedelta(year=date_to.year)
                #
                rd = relativedelta(birthday_in_period, self.birthday)
                increase_by_age = 0
                if rd.years < 16:
                    increase_by_age += 5
                elif rd.years == 16:
                    x16_1 = ((abs((birthday_in_period - date_from).days)+1) * 5) / vacation_base_calculation
                    increase_by_age += x16_1
                    x16_2 = ((abs((date_to - birthday_in_period).days)+1) * 3) / vacation_base_calculation
                    increase_by_age += x16_2
                    if increase_by_age > 5:
                        increase_by_age = 5
                elif rd.years == 17:
                    increase_by_age += 3
                elif rd.years == 18:
                    x18_1 = ((abs((birthday_in_period - date_from).days)+1) * 3) / vacation_base_calculation
                    increase_by_age += x18_1
                    if increase_by_age > 3:
                        increase_by_age = 3
                return increase_by_age
            elif period_type == 'proportional':

                birthday_in_period = self.birthday + relativedelta(year=date_from.year)
                if not (birthday_in_period >= date_from and birthday_in_period <= date_to):
                    birthday_in_period = self.birthday + relativedelta(year=date_to.year)
                if not (birthday_in_period >= date_from and birthday_in_period <= date_to):
                    birthday_in_period = self.birthday + relativedelta(year=date_to.year, month=date_to.month,
                                                                       day=date_to.day)

                rd = relativedelta(birthday_in_period, self.birthday)
                increase_by_age = 0
                if rd.years < 16:
                    x16 = ((abs((date_to - date_from).days)+1) * 5) / vacation_base_calculation
                    increase_by_age += x16
                elif rd.years == 16:
                    x16_1 = ((abs((birthday_in_period - date_from).days)+1) * 5) / vacation_base_calculation
                    increase_by_age += x16_1
                    x16_2 = ((abs((date_to - birthday_in_period).days)+1) * 3) / vacation_base_calculation
                    increase_by_age += x16_2
                elif rd.years == 17:
                    x17 = ((abs((date_to - date_from).days)+1) * 3) / vacation_base_calculation
                    increase_by_age += x17
                elif rd.years == 18:
                    x18_1 = ((abs((birthday_in_period - date_from).days)+1) * 3) / vacation_base_calculation
                    increase_by_age += x18_1
                return increase_by_age
        else:
            return 0

    def _get_accumulated_by_seniority(self, period_type, period_count, number_of_days_proportional_period):
        take_antiquity_vacation_calculation = self._get_take_antiquity_vacation_calculation()

        if take_antiquity_vacation_calculation:

            # Años de antigüedad a partir de los cuales se suman días adicionales de vacaciones.
            min_years_for_additional_vacation = self._get_min_years_for_additional_vacation()
            # Máximo de días incrementados por antigüedad en cada período.
            max_days_allows_vacation_increase = self._get_max_days_allows_vacation_increase()
            # Base para el cálculo proporcional de vacaciones, 360.
            vacation_base_calculation = self.get_vacation_base_calculation()
            # Tener en cuenta períodos anteriores de trabajo con el empleador actual para antigüedad en vacaciones.
            take_previous_periods_vacation_calculation = self._get_take_previous_periods_vacation_calculation()

            date_increase_seniority = self.last_company_entry_date + relativedelta(years=min_years_for_additional_vacation)

            if take_previous_periods_vacation_calculation:
                period_count += int(self.total_time_in_company_years)

            accumulated_by_seniority = 0
            if period_count <= min_years_for_additional_vacation:
                accumulated_by_seniority = 0
            else:
                if period_count - min_years_for_additional_vacation <= max_days_allows_vacation_increase:
                    accumulated_by_seniority = period_count - min_years_for_additional_vacation
                else:
                    accumulated_by_seniority = max_days_allows_vacation_increase

            if period_type == 'complete':
                return accumulated_by_seniority
            elif period_type == 'proportional':
                proportional_accumulated_by_seniority = number_of_days_proportional_period * accumulated_by_seniority / vacation_base_calculation
                if proportional_accumulated_by_seniority > accumulated_by_seniority:
                    proportional_accumulated_by_seniority = accumulated_by_seniority

                return proportional_accumulated_by_seniority
        else:
            return 0

    def _get_accumulated_by_seniority2(self, period_type, period_count, date_from, date_to,
                                       number_of_days_proportional_period):
        take_antiquity_vacation_calculation = self._get_take_antiquity_vacation_calculation()

        if take_antiquity_vacation_calculation:

            # Años de antigüedad a partir de los cuales se suman días adicionales de vacaciones.
            min_years_for_additional_vacation = self._get_min_years_for_additional_vacation()
            # Máximo de días incrementados por antigüedad en cada período.
            max_days_allows_vacation_increase = self._get_max_days_allows_vacation_increase()
            # Base para el cálculo proporcional de vacaciones, 360.
            vacation_base_calculation = self.get_vacation_base_calculation()
            # Tener en cuenta períodos anteriores de trabajo con el empleador actual para antigüedad en vacaciones.
            take_previous_periods_vacation_calculation = self._get_take_previous_periods_vacation_calculation()

            date_increase_seniority = self.last_company_entry_date + relativedelta(years=min_years_for_additional_vacation)

            if take_previous_periods_vacation_calculation:
                date_increase_seniority = date_increase_seniority - relativedelta(
                    days=self.total_days_in_company_in_previous_periods_except_last)

            if date_increase_seniority < date_from:
                ev_details = self.env['hr.employee.vacation.detail'].search(
                    [('employee_id', '=', self.id)], order='date_from desc')
                for detail in ev_details:
                    if detail.id != ev_details[0].id:
                        if date_increase_seniority < date_from:
                            pass

                pass
                # if period_type == 'complete':
                #     return accumulated_by_seniority
                # elif period_type == 'proportional':
                #     proportional_accumulated_by_seniority = number_of_days_proportional_period * accumulated_by_seniority / vacation_base_calculation
                #     if proportional_accumulated_by_seniority > accumulated_by_seniority:
                #         proportional_accumulated_by_seniority = accumulated_by_seniority
            elif date_increase_seniority >= date_from and date_increase_seniority <= date_to:
                pass
            elif date_increase_seniority > date_to:
                return 0

            accumulated_by_seniority = 0
            if period_count <= min_years_for_additional_vacation:
                accumulated_by_seniority = 0
            else:
                if period_count - min_years_for_additional_vacation <= max_days_allows_vacation_increase:
                    accumulated_by_seniority = period_count - min_years_for_additional_vacation
                else:
                    accumulated_by_seniority = max_days_allows_vacation_increase

            if period_type == 'complete':
                return accumulated_by_seniority
            elif period_type == 'proportional':
                proportional_accumulated_by_seniority = number_of_days_proportional_period * accumulated_by_seniority / vacation_base_calculation
                if proportional_accumulated_by_seniority > accumulated_by_seniority:
                    proportional_accumulated_by_seniority = accumulated_by_seniority

                return proportional_accumulated_by_seniority
        else:
            return 0

    def _get_total_accumulated_by_complete_period(self, period_count, date_from, date_end):

        # Número de días estandar de vacaciones que se acumulan en un período completo.
        vacation_standard_accumulated = self.get_vacation_standard_accumulated()
        # Incremento por antigüedad.
        accumulated_by_seniority = self._get_accumulated_by_seniority('complete', period_count, 0)
        # Incremento por edad.
        increase_by_age = self._get_increase_by_age('complete', date_from, date_end)

        return vacation_standard_accumulated + accumulated_by_seniority + increase_by_age

    def _get_total_accumulated_in_all_period_assuming_proportionals_as_complete(self):
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')

        total_accumulated_in_all_period = 0
        for detail in ev_details:
            if detail.type == 'complete':
                total_accumulated_in_all_period += self._get_total_accumulated_by_complete_period(detail.sequence,
                                                                                                  detail.date_from,
                                                                                                  detail.date_to)
            elif detail.type == 'proportional':
                date_to = detail.date_from + relativedelta(years=1) - relativedelta(days=1)
                total_accumulated_in_all_period += self._get_total_accumulated_by_complete_period(detail.sequence,
                                                                                                  detail.date_from,
                                                                                                  date_to)
        return total_accumulated_in_all_period

    def _get_total_accumulated_in_all_period(self):
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')
        total_accumulated_in_all_period = 0
        for detail in ev_details:
            total_accumulated_in_all_period += detail.total_accumulated
        return round(total_accumulated_in_all_period, 2)

    def create_vacation_period(self, date_to):
        # Base para el cálculo proporcional de vacaciones, 360.
        vacation_base_calculation = self.get_vacation_base_calculation()
        # Número de dias standard de vacaciones que se acumulan en un período completo.
        # 15 ó 30 en función de la normativa del colaborador.
        vacation_standard_accumulated = self.get_vacation_standard_accumulated()
        date_from = self.last_company_entry_date
        if date_from:
            period_count = 0
            while date_from <= date_to:
                rd = relativedelta(date_to + relativedelta(days=1), date_from)
                if rd.years >= 1:
                    period_count += 1
                    date_end_period = date_from + relativedelta(years=1) - relativedelta(days=1)

                    evd = self.env['hr.employee.vacation.detail'].create({
                        'employee_id': self.id,
                        'sequence': period_count,
                        'type': 'complete',
                        'date_from': date_from,
                        'date_to': date_end_period,
                        'standard_accumulated': vacation_standard_accumulated,
                        'accumulated_by_seniority': 0,
                        'increase_by_age': 0
                    })
                    # Incremento por edad.
                    evd.increase_by_age = self._get_increase_by_age('complete', date_from, date_end_period)
                    # Incremento por antigüedad.
                    evd.accumulated_by_seniority = self._get_accumulated_by_seniority('complete', period_count,0)

                    evd.vacation_execution = evd.get_vacation_execution() + evd.get_vacation_execution_occupy_from_another_period()
                    evd.permissions = evd.get_permissions()
                else:
                    # Proporcional último período.
                    difference = date_to - date_from
                    number_of_days_last_period = difference.days + 1
                    period_count += 1

                    accumulated_new_period = number_of_days_last_period * vacation_standard_accumulated / vacation_base_calculation
                    if accumulated_new_period > vacation_standard_accumulated:
                        accumulated_new_period = vacation_standard_accumulated

                    evd = self.env['hr.employee.vacation.detail'].create({
                        'employee_id': self.id,
                        'sequence': period_count,
                        'type': 'proportional',
                        'date_from': date_from,
                        'date_to': date_to,
                        'standard_accumulated': accumulated_new_period,
                        'accumulated_by_seniority': 0,
                        'increase_by_age': 0
                    })
                    # Incremento por edad.
                    evd.increase_by_age = self._get_increase_by_age('proportional', date_from, date_to)
                    # Incremento por antigüedad.
                    evd.accumulated_by_seniority = self._get_accumulated_by_seniority('proportional', period_count,
                                                                                      number_of_days_last_period)
                    evd.vacation_execution = evd.get_vacation_execution() + evd.get_vacation_execution_occupy_from_another_period()
                    evd.permissions = evd.get_permissions()
                    evd.permissions += evd.get_permissions_in_the_future()
                    evd.vacation_execution += evd.get_vacation_execution_in_the_future()
                date_from = date_from + relativedelta(years=1)

    def _get_vacations_available(self):
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')
        total_vacations_available = 0
        total_vacations_available_including_proportional_period = 0
        for detail in ev_details:
            if detail.type == 'complete':
                total_vacations_available += detail.available
            if detail.type == 'proportional':
                total_vacations_available_including_proportional_period += detail.available
        return total_vacations_available, total_vacations_available_including_proportional_period

    def update_vacations_available(self):
        total_vacations_available, total_vacations_available_including_proportional_period = self._get_vacations_available()
        self.total_vacations_available = total_vacations_available
        self.total_vacations_available_including_proportional_period = total_vacations_available + total_vacations_available_including_proportional_period

    def update_ready_to_lost(self):
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id),
             ('type', '=', 'complete')], order='date_from')

        max_complete_period_vacation_accumulated = self._get_max_complete_period_vacation_accumulated()

        for detail in ev_details:
            if detail.sequence + max_complete_period_vacation_accumulated <= len(ev_details):
                detail.ready_to_lost = True
            else:
                break

    def generate_update_vacation_period(self, date_to):
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')
        if len(ev_details) == 0:
            # Intentamos generar los detalles.
            self.create_vacation_period(date_to)
        else:
            # Existen detalles, validar un posible cambio de fecha y de ser así
            # eliminar todos los detalles de ese colaborador.
            if ev_details[0].date_from == self.last_company_entry_date:
                # Las fechas coinciden.
                # Base para el cálculo proporcional de vacaciones, 360.
                vacation_base_calculation = self.get_vacation_base_calculation()
                # Número de días estandar de vacaciones que se acumulan en un período completo.
                # 15 ó 30 en función de la normativa del colaborador.
                vacation_standard_accumulated = self.get_vacation_standard_accumulated()

                last_detail = ev_details[len(ev_details)-1]
                last_date_from = last_detail.date_from
                last_date_from = last_date_from + relativedelta(years=1)

                today = datetime.utcnow()
                tz_name = self.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    raise ValidationError(
                        _("Local time zone is not defined. You may need to set a time zone in your user's preferences."))
                tz = pytz.timezone(tz_name)
                today = pytz.utc.localize(today, is_dst=None).astimezone(tz)
                today = today.date()

                if today > last_detail.date_to:
                    if last_date_from <= date_to:
                        # El último período pasa a ser completo si es que ya no lo era
                        # y se crea un nuevo período proporcional.
                        if last_detail.type == 'proportional':
                            last_detail.date_to = last_date_from - relativedelta(days=1)
                            last_detail.type = 'complete'
                            last_detail.standard_accumulated = vacation_standard_accumulated

                            last_detail.accumulated_by_seniority = self._get_accumulated_by_seniority('complete', last_detail.sequence, 0)
                            last_detail.increase_by_age = self._get_increase_by_age('complete', last_detail.date_from, last_detail.date_to)
                            last_detail.vacation_execution = last_detail.get_vacation_execution() + last_detail.get_vacation_execution_occupy_from_another_period()
                            last_detail.permissions = last_detail.get_permissions()
                            if last_detail.type == 'proportional':
                                last_detail.permissions += last_detail.get_permissions_in_the_future()
                                last_detail.vacation_execution += last_detail.get_vacation_execution_in_the_future()

                        # Creando el nuevo período proporcional.
                        difference = date_to - last_date_from
                        number_of_days_last_period = difference.days + 1
                        accumulated_new_period = number_of_days_last_period * vacation_standard_accumulated / vacation_base_calculation
                        if accumulated_new_period > vacation_standard_accumulated:
                            accumulated_new_period = vacation_standard_accumulated

                        sequence = last_detail.sequence + 1

                        accumulated_by_seniority = self._get_accumulated_by_seniority('proportional',sequence, number_of_days_last_period)
                        increase_by_age = self._get_increase_by_age('proportional', last_date_from, date_to)

                        evd = self.env['hr.employee.vacation.detail'].create({
                            'employee_id': self.id,
                            'sequence': sequence,
                            'type': 'proportional',
                            'date_from': last_date_from,
                            'date_to': date_to,
                            'standard_accumulated': accumulated_new_period,
                            'accumulated_by_seniority': accumulated_by_seniority,
                            'increase_by_age': increase_by_age,
                        })
                        evd.vacation_execution = evd.get_vacation_execution() + evd.get_vacation_execution_occupy_from_another_period()
                        evd.permissions = evd.get_permissions()
                        if evd.type == 'proportional':
                            evd.permissions += evd.get_permissions_in_the_future()
                            evd.vacation_execution += evd.get_vacation_execution_in_the_future()
                    else:
                        # Sigue el ultimo periodo como proporcional, actualizar la informacion
                        last_detail.date_to = date_to

                        difference = date_to - last_detail.date_from
                        number_of_days_last_period = difference.days + 1
                        update_vacation_standard_accumulated = number_of_days_last_period * vacation_standard_accumulated / vacation_base_calculation
                        if update_vacation_standard_accumulated > vacation_standard_accumulated:
                            update_vacation_standard_accumulated = vacation_standard_accumulated

                        last_detail.standard_accumulated = update_vacation_standard_accumulated
                        last_detail.accumulated_by_seniority = self._get_accumulated_by_seniority('proportional', last_detail.sequence,number_of_days_last_period)
                        last_detail.increase_by_age = self._get_increase_by_age('proportional', last_detail.date_from, last_detail.date_to)
                        last_detail.vacation_execution = last_detail.get_vacation_execution() + last_detail.get_vacation_execution_occupy_from_another_period()
                        last_detail.permissions = last_detail.get_permissions()
                        if last_detail.type == 'proportional':
                            last_detail.permissions += last_detail.get_permissions_in_the_future()
                            last_detail.vacation_execution += last_detail.get_vacation_execution_in_the_future()

                for detail in ev_details:
                    if detail.type == 'complete':
                        detail.accumulated_by_seniority = self._get_accumulated_by_seniority(detail.type,detail.sequence,0)
                    elif detail.type == 'proportional':
                        difference = detail.date_to - detail.date_from
                        number_of_days = difference.days + 1
                        detail.accumulated_by_seniority = self._get_accumulated_by_seniority(detail.type,detail.sequence, number_of_days)

                    detail.increase_by_age = self._get_increase_by_age(detail.type, detail.date_from,detail.date_to)
                    detail.vacation_execution = detail.get_vacation_execution() + detail.get_vacation_execution_occupy_from_another_period()
                    detail.permissions = detail.get_permissions()
                    if detail.type == 'proportional':
                        detail.permissions += detail.get_permissions_in_the_future()
                        detail.vacation_execution += detail.get_vacation_execution_in_the_future()
            else:
                # Cambio de fecha.
                # Eliminar todos los detalles.
                for detail in ev_details:
                    detail.unlink()

                # Quitar la fecha de corte y el saldo de vacaciones a la fecha de corte.
                self.cutoff_date = ''
                self.vacations_cutoff_date = 0
                self.total_vacations_accumulated_cutoff_date = 0
                self.vacations_taken_cutoff_date = 0

                # Reconstruir los detalles.
                self.create_vacation_period(date_to)

        self.update_vacations_available()

        self.update_ready_to_lost()
    
    def action_create_update_vacation_period(self):
        for record in self:
            tz_name = record.tz or self._context.get('tz') or self.env.user.tz
            if not tz_name:
                raise ValidationError(
                    _("Local time zone is not defined. "
                      "You may need to set a time zone in collaborator or user's preferences."))
            else:
                date_to = datetime.utcnow()
                tz = pytz.timezone(tz_name)
                date_to = pytz.utc.localize(date_to, is_dst=None).astimezone(tz)
                date_to = date_to - relativedelta(days=1)
                record.generate_update_vacation_period(date_to.date())
        return True

    def _cron_create_update_vacation_period(self):
        employees = self.search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])])
        for e in employees:
            date_to = datetime.utcnow()
            tz_name = e.tz or self._context.get('tz') or self.env.user.tz
            if not tz_name:
                message = "ERROR: Function: _cron_create_update_vacation_period(). " \
                          "Local time zone is not defined. " \
                          "You may need to set a time zone in collaborator or user's preferences. " \
                          "Employee: {}".format(e.name)
                _logger.error(message)
                tz_name = 'America/Guayaquil'
                tz = pytz.timezone(tz_name)
                date_to = pytz.utc.localize(date_to, is_dst=None).astimezone(tz)
                date_to = date_to - relativedelta(days=1)
                e.generate_update_vacation_period(date_to.date())
            else:
                tz = pytz.timezone(tz_name)
                date_to = pytz.utc.localize(date_to, is_dst=None).astimezone(tz)
                date_to = date_to - relativedelta(days=1)
                e.generate_update_vacation_period(date_to.date())

    def _get_total_accumulated_to_cutoff_date(self):

        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')

        # Base para el cálculo proporcional de vacaciones, 360.
        vacation_base_calculation = self.get_vacation_base_calculation()

        # Número de días estandar de vacaciones que se acumulan en un período completo.
        # 15 ó 30 en función de la normativa del colaborador.
        vacation_standard_accumulated = self.get_vacation_standard_accumulated()

        total_accumulated_to_cutoff_date = 0
        for detail in ev_details:

            if self.cutoff_date >= detail.date_from and self.cutoff_date <= detail.date_to:
                # La fecha de corte esta dentro de este período.

                number_of_days_period = (self.cutoff_date - detail.date_from).days + 1

                accumulated_period = number_of_days_period * vacation_standard_accumulated / vacation_base_calculation
                if accumulated_period > vacation_standard_accumulated:
                    accumulated_period = vacation_standard_accumulated

                total_accumulated_to_cutoff_date += accumulated_period

                accumulated_by_seniority = self._get_accumulated_by_seniority('proportional', detail.sequence, number_of_days_period)
                total_accumulated_to_cutoff_date += accumulated_by_seniority

                increase_by_age = self._get_increase_by_age('proportional', detail.date_from, self.cutoff_date)
                total_accumulated_to_cutoff_date += increase_by_age

                break
            else:
                total_accumulated_to_cutoff_date += detail.total_accumulated

        return total_accumulated_to_cutoff_date

    def register_vacation_initial_balance(self):
        # Eliminar y reconstruir los períodos a la fecha actual.
        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)])
        for detail in ev_details:
            detail.unlink()

        today = datetime.utcnow()
        tz_name = self.tz or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise ValidationError(
                _("Local time zone is not defined. You may need to set a time zone in your user's preferences."))
        tz = pytz.timezone(tz_name)
        today = pytz.utc.localize(today, is_dst=None).astimezone(tz)
        today = today - relativedelta(days=1)
        self.create_vacation_period(today.date())

        total_accumulated_to_cutoff_date = self._get_total_accumulated_to_cutoff_date()
        vacation_taken_at_cutoff_date = total_accumulated_to_cutoff_date - self.vacations_cutoff_date

        while round(vacation_taken_at_cutoff_date, 2) > self._get_total_accumulated_in_all_period():
            # Reconstruir los períodos.
            ev_details = self.env['hr.employee.vacation.detail'].search(
                [('employee_id', '=', self.id)], order='date_from')
            last_detail = ev_details[len(ev_details) - 1]
            date_to = last_detail.date_to + relativedelta(days=1)
            for detail in ev_details:
                detail.unlink()
            self.create_vacation_period(date_to)

        self.total_vacations_accumulated_cutoff_date = total_accumulated_to_cutoff_date
        self.vacations_taken_cutoff_date = vacation_taken_at_cutoff_date

        ev_details = self.env['hr.employee.vacation.detail'].search(
            [('employee_id', '=', self.id)], order='date_from')
        for detail in ev_details:
            if vacation_taken_at_cutoff_date > 0:
                if vacation_taken_at_cutoff_date >= detail.total_accumulated:
                    detail.taken = detail.total_accumulated
                    vacation_taken_at_cutoff_date -= detail.total_accumulated
                else:
                    detail.taken = vacation_taken_at_cutoff_date
                    vacation_taken_at_cutoff_date -= vacation_taken_at_cutoff_date
            else:
                break

        self.update_vacations_available()

    def _cron_register_vacation_initial_balance(self):
        employees = self.search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])])
        for e in employees:
            e.register_vacation_initial_balance()

    def _cron_register_vacation_lost(self):
        register_vacation_lost = self.env['ir.config_parameter'].sudo().get_param(
            "vacation.lost.automatic.discount")
        if register_vacation_lost == '1':
            employees = self.search([
                ('active', '=', True),
                ('employee_admin', '=', False),
                ('state', 'in', ['affiliate', 'temporary', 'intern'])])
            for e in employees:
                ev_details = self.env['hr.employee.vacation.detail'].search(
                    [('employee_id', '=', e.id), ('type', '=', 'complete')], order='date_from')
                for detail in ev_details:
                    if detail.ready_to_lost and detail.available > 0:
                        detail.lost = detail.available
                        # TODO Que hacer con la provision de vacaciones si esta implementado nomina.

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].sudo().search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'

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
            period = self._create_last_vacation_period(first_date, date_to, len(vacations_detail_ids))
            total_vacations += period.available
            period.sudo().unlink()
        return total_vacations


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    cutoff_date = fields.Date(readonly=True)
    vacations_cutoff_date = fields.Float(readonly=True)
    vacations_taken_cutoff_date = fields.Float(readonly=True)
    total_vacations_accumulated_cutoff_date = fields.Float(readonly=True)
    total_vacations_available = fields.Float(readonly=True)
    total_vacations_available_including_proportional_period = fields.Float(readonly=True)
    total_days_in_company_in_previous_periods_except_last = fields.Integer(readonly=True)


class RegisterVacationInitialBalance(models.TransientModel):
    _name = 'hr.register.vacation.initial.balance'
    _description = 'Register vacation initial balance'

    # @api.onchange('vacations_cutoff_date', 'hours_per_day')
    # def onchange_vacations_cutoff_date_hours_per_day(self):
    #     if self.vacations_cutoff_date and self.hours_per_day:
    #         self.vacations_cutoff_date_days = int(self.vacations_cutoff_date)
    #
    #         hours = self.vacations_cutoff_date - int(self.vacations_cutoff_date)
    #         hours = hours * self.hours_per_day
    #         self.vacations_cutoff_date_hours = int(hours)
    #
    #         minutes = hours - int(hours)
    #         self.vacations_cutoff_date_minutes = int(minutes * 60)

    @api.onchange('vacations_cutoff_date_days',
                  'vacations_cutoff_date_hours',
                  'vacations_cutoff_date_minutes',
                  'hours_per_day')
    def onchange_vacations_cutoff_dhm_date_hours_per_day(self):
        if self.hours_per_day and \
                (self.vacations_cutoff_date_days or
                 self.vacations_cutoff_date_hours or self.vacations_cutoff_date_minutes):
            precision = self.env['decimal.precision'].sudo().precision_get('Vacations')
            self.vacations_cutoff_date = round(self.vacations_cutoff_date_days +
                                               self.vacations_cutoff_date_hours / self.hours_per_day +
                                               self.vacations_cutoff_date_minutes / (self.hours_per_day * 60),
                                               precision)

    employee_id = fields.Many2one('hr.employee', string="Collaborator", default=lambda self: self._context.get('active_id'),
                                  required=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working hours', readonly=True,
                                           related='employee_id.resource_calendar_id')
    hours_per_day = fields.Float(string='Average working hours per day', readonly=True,
                                 related='employee_id.resource_calendar_id.hours_per_day')
    cutoff_date = fields.Date('Cutoff date', required=True)
    vacations_cutoff_date = fields.Float(string='Vacations available at the cutoff date', required=True,
                                         digits='Vacations')
    detailed_income = fields.Boolean(string='Detailed income', default=False)
    vacations_cutoff_date_days = fields.Integer(string='Vacations available at the cutoff date (Days)')
    vacations_cutoff_date_hours = fields.Integer(string='Vacations available at the cutoff date (Hours)')
    vacations_cutoff_date_minutes = fields.Integer(string='Vacations available at the cutoff date (Minutes)')
    register_provisioned_vacations = fields.Boolean(string='Register provisioned vacations', default=False)
    provisioned_value = fields.Float(string='Provisioned value', digits='Vacations')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related='company_id.currency_id')
    
    def action_accept(self):
        # TODO Realizar asiento contable de provision de vacaciones
        self.employee_id.cutoff_date = self.cutoff_date
        self.employee_id.vacations_cutoff_date = self.vacations_cutoff_date
        self.employee_id.register_vacation_initial_balance()


class EmployeeVacationDetail(models.Model):
    _name = 'hr.employee.vacation.detail'
    _description = 'Employee vacation detail'
    _inherit = ['mail.thread']
    _order = "employee_id,date_from"
    
    def name_get(self):
        result = []
        for evd in self:
            date_from = evd.date_from.strftime("%d/%m/%Y")
            date_to = evd.date_to.strftime("%d/%m/%Y")
            result.append(
                (
                    evd.id,
                    _("{} {} - {}").format(evd.employee_id.name, date_from, date_to)

                )
            )
        return result

    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True,
                                  tracking=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', tracking=True)
    type = fields.Selection([
                ('complete', 'Complete'),
                ('proportional', 'Proportional')], string='Type', tracking=True)

    date_from = fields.Date('From', tracking=True)
    date_to = fields.Date('To', tracking=True)

    @api.depends('date_from', 'date_to')
    def _compute_total_days(self):
        for evd in self:
            days = (evd.date_to - evd.date_from).days + 1
            if days > self.employee_id.get_vacation_base_calculation():
                evd.days = self.employee_id.get_vacation_base_calculation()
            else:
                evd.days = days

    days = fields.Integer(string='Days', compute=_compute_total_days)
    standard_accumulated = fields.Float(string='Standard accumulated', digits='Vacations', tracking=True)
    accumulated_by_seniority = fields.Float(string='Increase by seniority', digits='Vacations', tracking=True)
    increase_by_age = fields.Float(string='Increase by age', digits='Vacations', tracking=True)

    @api.depends('standard_accumulated', 'accumulated_by_seniority', 'increase_by_age')
    def _compute_total_accumulated(self):
        for evd in self:

            evd.total_accumulated = evd.standard_accumulated + evd.accumulated_by_seniority + evd.increase_by_age

            vacation_standard_accumulated = evd.employee_id.get_vacation_standard_accumulated()
            vacation_standard_worked_accumulated = evd.employee_id.get_vacation_standard_worked_accumulated()

            evd.total_accumulated_worked = evd.total_accumulated * vacation_standard_worked_accumulated / vacation_standard_accumulated
            evd.total_accumulated_not_worked = evd.total_accumulated - evd.total_accumulated_worked

    total_accumulated = fields.Float(string='Total accumulated', compute=_compute_total_accumulated, digits='Vacations')
    total_accumulated_worked = fields.Float(string='Worked', compute=_compute_total_accumulated, digits='Vacations')
    total_accumulated_not_worked = fields.Float(string='Not worked', compute=_compute_total_accumulated,
                                                digits='Vacations')

    taken = fields.Float(string='Taken', digits='Vacations', tracking=True)

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

    def convert_time_to_utc(self, dt, tz_name=None):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

        @return: an instance of datetime object
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise ValidationError(
                _("Local time zone is not defined. You may need to set a time zone in your user's preferences."))
        local = pytz.timezone(tz_name)
        local_dt = local.localize(dt, is_dst=None)
        return local_dt.astimezone(pytz.utc)

    @api.depends('employee_id.vacation_execution_request_ids.state')
    def _compute_vacation_execution(self):
        for evd in self:
            evd.vacation_execution = evd.get_vacation_execution() + evd.get_vacation_execution_occupy_from_another_period()
            if evd.type == 'proportional':
                evd.vacation_execution += evd.get_vacation_execution_in_the_future()

    def get_vacation_execution(self):
        # Vacaciones que se encuentran dentro del periodo
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state','=','approved'),
            ('date_from', '>=', self.date_from),
            ('date_from', '<=', self.date_to),
            ('occupy_current_period','=',True)
        ])
        count_laboral_days = 0
        for ver in vacation_execution_request:
            date_from_iter = ver.date_from
            while date_from_iter <= ver.date_to:
                if date_from_iter <= self.date_to:
                    # El dia x de la solicitud de vacaciones esta dentro del periodo de vacaciones
                    if self.employee_id.has_assigned_shifts(date_from_iter):
                        # El dia x de la solicitud de vacaciones tiene turno asignado el colaborador
                        count_laboral_days += 1
                date_from_iter = date_from_iter + relativedelta(days=1)

        # Tomar la parte de las solicitudes de vacaciones que terminan en el periodo pero que comienzan en el perdio anterior
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('date_from', '<', self.date_from),
            ('occupy_current_period', '=', True)
        ])
        for ver in vacation_execution_request:
            date_from_iter = ver.date_from
            while date_from_iter <= ver.date_to:
                if date_from_iter >= self.date_from:
                    # El dia x de la solicitud de vacaciones esta dentro del periodo de vacaciones
                    if self.employee_id.has_assigned_shifts(date_from_iter):
                        # El dia x de la solicitud de vacaciones tiene turno asignado el colaborador
                        count_laboral_days += 1
                date_from_iter = date_from_iter + relativedelta(days=1)

        # Vacaciones que ocupan mas del periodo completo
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_to', '>', self.date_from),
            ('date_from', '<', self.date_from),
            ('occupy_current_period', '=', True)
        ])
        for ver in vacation_execution_request:
            date_from_iter = ver.date_from
            while date_from_iter <= ver.date_to:
                if date_from_iter >= self.date_from and date_from_iter <= self.date_to:
                    # El dia x de la solicitud de vacaciones esta dentro del periodo de vacaciones
                    if self.employee_id.has_assigned_shifts(date_from_iter):
                        # El dia x de la solicitud de vacaciones tiene turno asignado el colaborador
                        count_laboral_days += 1
                date_from_iter = date_from_iter + relativedelta(days=1)

        # Calcular el recargo en funcion de la proporcion del periodo
        # ve = count_laboral_days + (count_laboral_days * self.total_accumulated_not_worked / self.total_accumulated_worked)

        vacation_standard_accumulated = self.employee_id.get_vacation_standard_accumulated()
        vacation_standard_worked_accumulated = self.employee_id.get_vacation_standard_worked_accumulated()

        ve = count_laboral_days + (
                count_laboral_days * (
                    vacation_standard_accumulated - vacation_standard_worked_accumulated) / vacation_standard_worked_accumulated)


        return ve

    def get_vacation_execution_in_the_future(self):
        count_laboral_days = 0
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_from', '>', self.date_to),
            ('occupy_current_period', '=', True),
        ])

        for ver in vacation_execution_request:
            date_from_iter = ver.date_from
            while date_from_iter <= ver.date_to:
                if self.employee_id.has_assigned_shifts(date_from_iter):
                    # El dia x de la solicitud de vacaciones tiene turno asignado el colaborador
                    count_laboral_days += 1
                date_from_iter = date_from_iter + relativedelta(days=1)

        # Calcular el recargo en funcion de la proporcion del periodo
        # ve = count_laboral_days + (count_laboral_days * self.total_accumulated_not_worked / self.total_accumulated_worked)

        vacation_standard_accumulated = self.employee_id.get_vacation_standard_accumulated()
        vacation_standard_worked_accumulated = self.employee_id.get_vacation_standard_worked_accumulated()

        ve = count_laboral_days + (
                    count_laboral_days * (vacation_standard_accumulated-vacation_standard_worked_accumulated) / vacation_standard_worked_accumulated)


        return ve

    def get_vacation_execution_occupy_from_another_period(self):
        vacation_execution_request_occupy_period = self.env['hr.vacation.execution.request.occupy.period'].search([
            ('period_id', '=', self.id),
        ])
        result = 0
        for verop in vacation_execution_request_occupy_period:
            if verop.vacation_execution_request_id.occupy_current_period == False and verop.vacation_execution_request_id.state == 'approved':
                result += verop.amount

        return result

    vacation_execution = fields.Float(string='Vacation execution', compute=_compute_vacation_execution, store=True,
                                      digits='Vacations')

    @api.depends('employee_id.permission_request_ids.state')
    def _compute_permissions(self):
        for evd in self:
            evd.permissions = evd.get_permissions()
            if evd.type == 'proportional':
                evd.permissions += evd.get_permissions_in_the_future()

    def _get_vacation_discount_this_permission(self, permission_type_id):
        acronym = 'DDV'
        module = self.env.ref('base.module_' + 'hr_dr_permissions')
        configuration = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', 'hr.permission.type')]).id),
            ('res_id', '=', permission_type_id),
            ('current', '=', True)
        ], limit=1)
        if configuration:
            return configuration.boolean_value
        else:
            raise ValidationError(
                _(
                    "Configuration error, contact administrator. Normative assigned to the collaborator.: {}. A valid combination must exist for 'hr.normative.nomenclature' --> Normative: {}, Nomenclature Module: {}, Nomenclature Acronym: {}.").format
                    (
                    self.employee_requests_id.normative_id.name,
                    self.employee_requests_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def get_permissions(self):

        sum_permission_time = 0

        # Permisos que inician dentro del periodo y pueden terminar en ese mismo periodo o en el siguiente periodo
        # Considerar solo los dias del permiso que estan dentro del periodo
        permission_requests = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state','=','approved'),
            ('date_from', '>=', self.date_from),
            ('date_from', '<=', self.date_to),
            ('is_head', '=', False),
        ])
        for pr in permission_requests:
            if self._get_vacation_discount_this_permission(pr.permission_type_id.id):
                datetime_from = self._get_datetime(pr.date_from, 0)
                datetime_to = self._get_datetime(pr.date_to, 0)
                days_between = (datetime_to - datetime_from).days

                for i in range(days_between + 1):
                    current_date = (datetime_from + timedelta(days=i)).date()
                    if current_date <= self.date_to:
                        # El dia x de la solicitud de permiso esta dentro del detalle de vacaciones

                        datetime_from_x = pr.datetime_from
                        datetime_to_x = pr.datetime_to

                        if days_between > 0:
                            # Permiso de mas de un dia
                            if i == 0:
                                # Primer dia de permiso
                                permission_day = 0
                            elif i == days_between:
                                # Ultimo dia de permiso
                                permission_day = 2
                            else:
                                permission_day = 1
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, False,
                                                                                           permission_day,
                                                                                           datetime_from_x,
                                                                                           datetime_to_x)
                        else:
                            # Permiso de un solo dia
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, True, -1,
                                                                                           datetime_from_x,
                                                                                           datetime_to_x)
                        sum_permission_time += real_time_taken_base

        # Permisos que inician antes del periodo y terminan dentro del periodo
        # Considerar solo los dias del permiso que estan dentro del periodo
        permission_requests = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('date_from', '<', self.date_from),
            ('is_head', '=', False),
        ])
        for pr in permission_requests:
            if self._get_vacation_discount_this_permission(pr.permission_type_id.id):
                datetime_from = self._get_datetime(pr.date_from, 0)
                datetime_to = self._get_datetime(pr.date_to, 0)
                days_between = (datetime_to - datetime_from).days
                for i in range(days_between + 1):
                    current_date = (datetime_from + timedelta(days=i)).date()
                    if current_date >= self.date_from:
                        # El dia x de la solicitud de permiso esta dentro del periodo de vacaciones

                        datetime_from_x = pr.datetime_from
                        datetime_to_x = pr.datetime_to

                        if days_between > 0:
                            # Permiso de mas de un dia
                            if i == 0:
                                # Primer dia de permiso
                                permission_day = 0
                            elif i == days_between:
                                # Ultimo dia de permiso
                                permission_day = 2
                            else:
                                permission_day = 1
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, False,
                                                                                           permission_day,
                                                                                           datetime_from_x,
                                                                                           datetime_to_x)
                        else:
                            # Permiso de un solo dia
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, True, -1,
                                                                                           datetime_from_x,
                                                                                           datetime_to_x)
                        sum_permission_time += real_time_taken_base

        # Permisos que inician antes del periodo y terminan despues del periodo
        # Considerar solo los dias del permiso que estan dentro del periodo
        permission_requests = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_to', '>', self.date_to),
            ('date_from', '<', self.date_from),
            ('is_head', '=', False),
        ])
        for pr in permission_requests:
            if self._get_vacation_discount_this_permission(pr.permission_type_id.id):
                datetime_from = self._get_datetime(pr.date_from, 0)
                datetime_to = self._get_datetime(pr.date_to, 0)
                days_between = (datetime_to - datetime_from).days


                for i in range(days_between + 1):
                    current_date = (datetime_from + timedelta(days=i)).date()
                    if current_date >= self.date_from and current_date <= self.date_to:
                        # El dia x de la solicitud de permiso esta dentro del periodo de vacaciones

                        datetime_from_x = pr.datetime_from
                        datetime_to_x = pr.datetime_to

                        if days_between > 0:
                            # Permiso de mas de un dia
                            if i == 0:
                                # Primer dia de permiso
                                permission_day = 0
                            elif i == days_between:
                                # Ultimo dia de permiso
                                permission_day = 2
                            else:
                                permission_day = 1
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, False, permission_day,
                                                                                       datetime_from_x,
                                                                                       datetime_to_x)
                        else:
                            # Permiso de un solo dia
                            real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, True, -1,
                                                                                           datetime_from_x,
                                                                                           datetime_to_x)
                        sum_permission_time += real_time_taken_base

        # sum_permission_time += (
        #         sum_permission_time * self.total_accumulated_not_worked / self.total_accumulated_worked)

        vacation_standard_accumulated = self.employee_id.get_vacation_standard_accumulated()
        vacation_standard_worked_accumulated = self.employee_id.get_vacation_standard_worked_accumulated()

        sum_permission_time = sum_permission_time + (
                sum_permission_time * (
                    vacation_standard_accumulated - vacation_standard_worked_accumulated) / vacation_standard_worked_accumulated)


        return sum_permission_time

    def get_permissions_in_the_future(self):
        sum_permission_time = 0
        # Permisos que se encuentran a futuro del ultimo periodo
        permission_requests = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date_from', '>', self.date_to),
            ('is_head', '=', False),
        ])
        for pr in permission_requests:
            if self._get_vacation_discount_this_permission(pr.permission_type_id.id):
                datetime_from = self._get_datetime(pr.date_from, 0)
                datetime_to = self._get_datetime(pr.date_to, 0)
                days_between = (datetime_to - datetime_from).days

                for i in range(days_between + 1):
                    current_date = (datetime_from + timedelta(days=i)).date()

                    datetime_from_x = pr.datetime_from
                    datetime_to_x = pr.datetime_to

                    if days_between > 0:
                        # Permiso de mas de un dia
                        if i == 0:
                            # Primer dia de permiso
                            permission_day = 0
                        elif i == days_between:
                            # Ultimo dia de permiso
                            permission_day = 2
                        else:
                            permission_day = 1
                        real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, False,
                                                                                       permission_day,
                                                                                       datetime_from_x,
                                                                                       datetime_to_x)
                    else:
                        # Permiso de un solo dia
                        real_time_taken_base = self.get_real_time_taken_in_permissions(current_date, True, -1,
                                                                                       datetime_from_x,
                                                                                       datetime_to_x)

                    sum_permission_time += real_time_taken_base

        # sum_permission_time += (
        #         sum_permission_time * self.total_accumulated_not_worked / self.total_accumulated_worked)

        vacation_standard_accumulated = self.employee_id.get_vacation_standard_accumulated()
        vacation_standard_worked_accumulated = self.employee_id.get_vacation_standard_worked_accumulated()

        sum_permission_time = sum_permission_time + (
                sum_permission_time * (
                vacation_standard_accumulated - vacation_standard_worked_accumulated) / vacation_standard_worked_accumulated)

        return sum_permission_time

    def _get_datetime(self, s_date, s_time, adjust_local_timezone=False):
        """
        Crea un objeto datetime.datetime dados una fecha y una hora.

        :param s_date: Ojeto datetime.date con la fecha a combinar.
        :param s_time: Objeto float con la representación de la hora.
        :return: Objeto datetime compuesto por la fecha  a combinar.
        """

        # Convierto la hora de inicio en un objeto datetime.time
        hours = int(s_time)
        minutes = round((s_time * 60) % 60)
        # seconds = int((s_time * 3600) % 60)
        start_time = time(hours, minutes, 0, tzinfo=pytz.UTC)
        # start_time = start_time.replace(tzinfo=pytz.UTC)

        if adjust_local_timezone:
            # Al utilizar datetime en lugar de date el ajustará la hora según la zona horaria local, así que calcularé la
            # diferencia en minutos entre la zona local y la UTC y la adicionaré para que no desajuste las fechas y horas.

            # Determinando la cantidad de segundos de diferencia entre UTC y la zona horaria local.
            diff_to_utc = self._get_seconds_to_utc()

            return datetime.combine(s_date, start_time) + timedelta(seconds=diff_to_utc)
        else:
            return datetime.combine(s_date, start_time)

    def _get_seconds_to_utc(self):
        """
        Determina la cantidad de segundos de diferencia entre la zona horaria local y la UTC.

        :return: Segundos existentes entre las zonas horarias.
        """

        # Obtengo la zona local del usuario autenticado en Odoo
        zone = self.employee_id.tz or self._context.get('tz') or self.env.user.tz
        user_tz = pytz.timezone(zone)

        d = datetime.now()
        user_dt = d.astimezone(user_tz).replace(tzinfo=None)
        utc_dt = d.astimezone(pytz.utc).replace(tzinfo=None)
        return (utc_dt - user_dt).total_seconds()

    def get_real_time_taken_in_permissions(self, current_date, one_day, permission_day, permission_from, permission_to):
        # one_day True si el permiso es de un dia
        # permission_day
        #     -1 No aplica permiso de un dia
        #     0 Dia inicial del permiso
        #     1 Dia intermedio del permiso
        #     2 Dia final del permiso

        time_taken_base = 0
        assigned_shifts = self.employee_id.get_assigned_shifts(current_date)

        time_planned_x = 0
        time_taken_x = 0

        for ash in assigned_shifts:

            time_planned_x += ash.time_planned

            planned_start = self.convert_utc_time_to_tz(ash.planned_start, self.employee_id.tz)
            planned_end = self.convert_utc_time_to_tz(ash.planned_end, self.employee_id.tz)

            permission_from = self.convert_utc_time_to_tz(permission_from, self.employee_id.tz)
            permission_to = self.convert_utc_time_to_tz(permission_to, self.employee_id.tz)

            if one_day:
                # Permiso de un solo dia
                if permission_from >= planned_start and permission_to <= planned_end:
                    # El permiso esta contenido completamente en el turno
                    time_taken_x += (permission_to - permission_from).total_seconds()
                elif (permission_from >= planned_start and permission_from <= planned_end) and permission_to > planned_end:
                    # El inicio del permiso esta dentro del turno y el fin es mayor que el fin del turno
                    time_taken_x += (planned_end - permission_from).total_seconds()
                elif permission_from < planned_start and (permission_to >= planned_start and permission_to <= planned_end):
                    # El inicio del permiso es menor que el inicion del turno y el fin del permiso esta dentro del turno
                    time_taken_x += (permission_to - planned_start).total_seconds()
                elif permission_from < planned_start and permission_to > planned_end:
                    # El inicio del permiso es menor que el inicio del turno y el fin del permiso es mayor que el fin del turno
                    time_taken_x += (planned_end - planned_start).total_seconds()

                for breaks in ash.break_ids:

                    b_planned_start = self.convert_utc_time_to_tz(breaks.planned_start, self.employee_id.tz)
                    b_planned_end = self.convert_utc_time_to_tz(breaks.planned_end, self.employee_id.tz)

                    if (b_planned_start >= permission_from and b_planned_start <= permission_to) and (
                            b_planned_end >= permission_from and b_planned_end <= permission_to):
                        # El inicio y el fin del descanso estan contenidos en el permiso
                        time_taken_x -= (b_planned_end - b_planned_start).total_seconds()
                    elif b_planned_start < permission_from and b_planned_end > permission_to:
                        # El inicio del descanso es menor que el inicio del permiso y el fin del descanso es mayor que el fin del permiso
                        time_taken_x -= (permission_to - permission_from).total_seconds()
                    elif (b_planned_start >= permission_from and b_planned_start <= permission_to) and b_planned_end > permission_to:
                        # El inicio del descando esta contenido en el permiso y el fin del descanso es mayor que el fin del permiso
                        time_taken_x -= (permission_to - b_planned_start).total_seconds()
                    elif b_planned_start < permission_from and (
                            b_planned_end >= permission_from and b_planned_end <= permission_to):
                        # El inicio del descanso es menor que el inicio del permiso y el fin del descanso esta contenido en el permiso
                        time_taken_x -= (b_planned_end - permission_from).total_seconds()
            else:
                # Permiso de mas de un dia
                if permission_day != -1:
                    if permission_day == 0:
                        # Dia inicial
                        if permission_from < planned_start:
                            time_taken_x += (planned_end - planned_start).total_seconds()
                        elif permission_from >= planned_start and permission_from <= planned_end:
                            time_taken_x += (planned_end - permission_from).total_seconds()

                        for breaks in ash.break_ids:
                            b_planned_start = self.convert_utc_time_to_tz(breaks.planned_start, self.employee_id.tz)
                            b_planned_end = self.convert_utc_time_to_tz(breaks.planned_end, self.employee_id.tz)

                            if (b_planned_start >= permission_from and b_planned_start <= planned_end) and (
                                    b_planned_end >= permission_from and b_planned_end <= planned_end):
                                # El inicio y el fin del descanso estan contenidos en el permiso
                                time_taken_x -= (b_planned_end - b_planned_start).total_seconds()
                            elif b_planned_start < permission_from and b_planned_end > planned_end:
                                # El inicio del descanso es menor que el inicio del permiso y el fin del descanso es mayor que el fin del permiso
                                time_taken_x -= (planned_end - permission_from).total_seconds()
                            elif (b_planned_start >= permission_from and b_planned_start <= planned_end) and b_planned_end > planned_end:
                                # El inicio del descando esta contenido en el permiso y el fin del descanso es mayor que el fin del permiso
                                time_taken_x -= (planned_end - b_planned_start).total_seconds()
                            elif b_planned_start < permission_from and (
                                    b_planned_end >= permission_from and b_planned_end <= planned_end):
                                # El inicio del descanso es menor que el inicio del permiso y el fin del descanso esta contenido en el permiso
                                time_taken_x -= (b_planned_end - permission_from).total_seconds()

                    elif permission_day == 1:
                        # Dia intermedio
                        time_taken_x += (planned_end - planned_start).total_seconds()
                        for breaks in ash.break_ids:
                            b_planned_start = self.convert_utc_time_to_tz(breaks.planned_start, self.employee_id.tz)
                            b_planned_end = self.convert_utc_time_to_tz(breaks.planned_end, self.employee_id.tz)

                            time_taken_x -= (b_planned_end - b_planned_start).total_seconds()
                    elif permission_day == 2:
                        # Dia final
                        if permission_to > planned_end:
                            time_taken_x += (planned_end - planned_start).total_seconds()
                        elif permission_to >= planned_start and permission_to <= planned_end:
                            time_taken_x += (permission_to - planned_start).total_seconds()

                        for breaks in ash.break_ids:
                            b_planned_start = self.convert_utc_time_to_tz(breaks.planned_start, self.employee_id.tz)
                            b_planned_end = self.convert_utc_time_to_tz(breaks.planned_end, self.employee_id.tz)

                            if (b_planned_start >= planned_start and b_planned_start <= permission_to) and (
                                    b_planned_end >= planned_start and b_planned_end <= permission_to):
                                # El inicio y el fin del descanso estan contenidos en el permiso
                                time_taken_x -= (b_planned_end - b_planned_start).total_seconds()
                            elif b_planned_start < planned_start and b_planned_end > permission_to:
                                # El inicio del descanso es menor que el inicio del permiso y el fin del descanso es mayor que el fin del permiso
                                time_taken_x -= (permission_to - planned_start).total_seconds()
                            elif (b_planned_start >= planned_start and b_planned_start <= permission_to) and b_planned_end > permission_to:
                                # El inicio del descando esta contenido en el permiso y el fin del descanso es mayor que el fin del permiso
                                time_taken_x -= (permission_to - b_planned_start).total_seconds()
                            elif b_planned_start < planned_start and (
                                    b_planned_end >= planned_start and b_planned_end <= permission_to):
                                # El inicio del descanso es menor que el inicio del permiso y el fin del descanso esta contenido en el permiso
                                time_taken_x -= (b_planned_end - planned_start).total_seconds()

        # Cuanto representa realmente lo tomado de lo planificado. Se realiza para las personas que trabajan con distinta duracion de jornada.
        fraction_time_taken_on_time_planned = time_taken_x / time_planned_x

        return fraction_time_taken_on_time_planned

    permissions = fields.Float(string='Permission execution', compute=_compute_permissions, store=True,
                               digits='Vacations')
    lost = fields.Float(string='Lost', digits='Vacations', tracking=True)
    ready_to_lost = fields.Boolean(string='Ready to lost', default=False, tracking=True)
    
    def open_register_lost(self):
        view = self.env.ref('hr_dr_vacations.register_vacations_lost_form')
        context = dict(self._context or {})
        context['employee_vacation_detail_id'] = self.id
        context['lost'] = self.available
        action = {
            'name': 'Register vacations lost',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'register.vacations.lost',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }
        return action

    paid = fields.Float(string='Paid', digits='Vacations')

    def open_register_paid(self):
        view = self.env.ref('hr_dr_vacations.register_vacations_paid_form')
        context = dict(self._context or {})
        context['employee_vacation_detail_id'] = self.id
        action = {
            'name': 'Register vacations paid',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'register.vacations.paid',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }
        return action

    @api.depends('total_accumulated', 'taken', 'lost', 'paid', 'vacation_execution', 'permissions')
    def _compute_available(self):
        for evd in self:
            evd.available = round(evd.total_accumulated - evd.taken - evd.lost - evd.paid - evd.vacation_execution - evd.permissions , 2)
    available = fields.Float(string='Available', compute=_compute_available, store=True, digits='Vacations')


class VacationPlanningRequest(models.Model):
    _name = "hr.vacation.planning.request"
    _description = 'Vacation planning request'
    _order = "department_employee_requests_id,employee_requests_id,state,date_from"
    _inherit = ['hr.generic.request']

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_vacations.email_template_confirm_vacation_planning_request',
            'confirm_direct': 'hr_dr_vacations.email_template_confirm_direct_approve_vacations_planning_request',
            'approve': 'hr_dr_vacations.email_template_confirm_approve_vacation_planning_request',
            'reject': 'hr_dr_vacations.email_template_confirm_reject_vacation_planning_request',
            'cancel': 'hr_dr_vacations.email_template_confirm_cancel_vacation_planning_request'
        }
    _hr_notifications_mode_param = 'planning.vacations.notifications.mode'
    _hr_administrator_param = 'planning.vacations.notifications.administrator'
    _hr_second_administrator_param = 'planning.vacations.notifications.second.administrator'

    date_from = fields.Date('From', required=True, tracking=True)
    date_to = fields.Date('To', required=True, tracking=True)
    parent_id = fields.Many2one('hr.vacation.planning.request', string='Parent vacation planning request',
                                readonly=True, tracking=True)

    @api.depends('date_to')
    def _compute_date_incorporation(self):
        for record in self:
            if record.date_to:
                record.date_incorporation = record.date_to + relativedelta(days=1)
            else:
                record.date_incorporation = False
    date_incorporation = fields.Date('Incorporation date', store=True, readonly=True,
                                     compute=_compute_date_incorporation, tracking=True)
    state = fields.Selection(selection_add=[('replanned', 'Replanned')])

    @api.depends('date_from', 'date_to')
    def _compute_number_of_days(self):
        for record in self:
            if record.date_from and record.date_to:
                difference = record.date_to - record.date_from
                record.number_of_days = difference.days + 1
            else:
                record.number_of_days = 0
    number_of_days = fields.Integer(string="Days planned", compute=_compute_number_of_days, readonly=True,
                                    store=True, tracking=True)
    
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (
                    record.id,
                    _("{} {} Day(s) {}").format(record.employee_requests_id.name, record.number_of_days,
                                                dict(self._fields['state'].selection).get(record.state))
                )
            )
        return result

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        # Solicitud de planificación de vacaciones
        local_context['subject'] = _("Vacation planning request")
        # ha realizado una solicitud de planificación de vacaciones.
        local_context['request'] = _("have made a vacation planning request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id

        # Solicitud de planificación de vacaciones desde el {} hasta el {}. Días planificados: {}.
        # Fecha de incorporación: {}.
        local_context['details'] = _(
            "Vacation planning request from {} until {}. Planned days: {}. Incorporation date: {}.").format(
            self.date_from.strftime("%d/%m/%Y"), self.date_to.strftime("%d/%m/%Y"), self.number_of_days,
            self.date_incorporation.strftime("%d/%m/%Y"))
        local_context['commentary'] = self.commentary
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref(
            'hr_dr_vacations.vacation_planning_request_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_dr_vacations.menu_hr_vacations').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url
        department = 'Dirección de Talento Humano'
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        return local_context

    def _check_restrictions(self, instance=None):
        """
        Valida las restricciones que pueda tener el modelo.

        @:param instance Instancia del modelo a validar.
        """

        # Si no recibe una instancia del modelo específica asume que es la actual.
        if instance is None:
            instance = self
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')

        if not create_edit_without_restrictions:
            configurations = instance.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', instance.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=',
                 instance.env.ref('base.module_' + instance._module).id),
                ('res_model_id', '=',
                 instance.env['ir.model'].sudo().search([('model', '=', instance._name)]).id),
                ('current', '=', True)
            ])
            for configuration in configurations:
                if configuration.nomenclature_id.acronym == 'CMIDPSV':
                    if configuration.integer_value > instance.number_of_days:
                        raise ValidationError(
                            _("You cannot a make vacation planning of less than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'CMADPSV':
                    if configuration.integer_value < instance.number_of_days:
                        raise ValidationError(
                            _("You cannot make a vacation planning of more than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'FIPV':
                    if datetime.utcnow().date() < datetime(datetime.utcnow().date().year,
                                                           configuration.date_value.month,
                                                           configuration.date_value.day).date():
                        raise ValidationError(
                            _("Vacation planning can only be requested from {}.").format(
                                datetime(datetime.utcnow().date().year, configuration.date_value.month,
                                         configuration.date_value.day).date()))
                elif configuration.nomenclature_id.acronym == 'FFPV':
                    if datetime.utcnow().date() > datetime(datetime.utcnow().date().year,
                                                           configuration.date_value.month,
                                                           configuration.date_value.day).date():
                        raise ValidationError(
                            _("Vacation planning can only be requested up to {}.").format(
                                datetime(datetime.utcnow().date().year, configuration.date_value.month,
                                         configuration.date_value.day).date()))
                elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
                    if configuration.boolean_value:
                        backups = self.env['hr.employee.backups'].search(
                            [('employee_id', '=', instance.employee_requests_id.id)])
                        for b in backups:
                            vacation_planning_request_backups = self.env['hr.vacation.planning.request'].search([
                                ('employee_requests_id', '=', b.employee_backup_id.id),
                                ('state', 'in', ['pending', 'approved']),
                                ('active', '=', True)
                            ])
                            for vprb in vacation_planning_request_backups:
                                if (instance.date_from >= vprb.date_from and instance.date_from <= vprb.date_to) or (
                                        instance.date_to >= vprb.date_from and instance.date_to <= vprb.date_from):
                                    raise UserError(
                                        _('There is already a vacation planning in status (Pending or Approved) for the specified time span of at least one of your replacements.'))
                elif configuration.nomenclature_id.acronym == 'IPVOSA':
                    if configuration.boolean_value:
                        if datetime.utcnow().date().year + 1 != instance.date_from.year:
                            raise UserError(
                                _('The start of the vacation planning is obligatorily within the following year with respect to the moment in which it is being confirmed.'))

    def confirm_vacation_planning_request_direct(self):
        # Función solo para el administrador del módulo. No valida las configuraciones del módulo.
        # No sigue un esquema de aprobación, se considera aprobada directamente.
        self.mark_as_approved_direct()
        mail_id_confirm_request = 'hr_dr_vacations.email_template_confirm_direct_approve_vacations_planning_request'
        self.send_mail(mail_id_confirm_request)
        return self

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    @api.model
    def create(self, vals):
        self.validate_module()
        record = super(VacationPlanningRequest, self).create(vals)

        if record.date_from > record.date_to:
            # La fecha de inicio de la planificación de vacaciones tiene que ser menor o igual
            # que la fecha de fin de la planificación de vacaciones.
            raise UserError(
                _('The vacation planning start date has to be lesser than or equal to the vacation planning end date.'))

        vacation_planning_request = self.env['hr.vacation.planning.request'].search([
            ('employee_requests_id', '=', record.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', record.id)
        ])
        for vpr in vacation_planning_request:
            if (record.date_from >= vpr.date_from and record.date_from <= vpr.date_to) \
                    or (record.date_to >= vpr.date_from and record.date_to <= vpr.date_from):
                # Ya existe una planificación de vacaciones en estado (Borrador, Pendiente o Aprobado)
                # para el lapso de tiempo especificado.
                raise UserError(
                    _('There is already a vacation planning in status (Draft, Pending, or Approved) '
                      'for the specified time frame.'))

        self._check_restrictions(record)

        # if not create_edit_without_restrictions:
        #     configurations = record.env['hr.normative.nomenclature'].search([
        #         ('normative_id', '=', record.employee_requests_id.normative_id.id),
        #         ('nomenclature_id.module_id', '=', record.env.ref('base.module_' + record._module).id),
        #         ('res_model_id', '=', record.env['ir.model'].sudo().search([('model', '=', record._name)]).id),
        #         ('current', '=', True)
        #     ])
        #     for configuration in configurations:
        #         if configuration.nomenclature_id.acronym == 'CMIDPSV':
        #             if configuration.integer_value > record.number_of_days:
        #                 # No se puede realizar una planificación de vacaciones de menos de {} días.
        #                 raise ValidationError(
        #                     _("You cannot plan a vacation of less than {} days.").format(
        #                         configuration.integer_value))
        #         elif configuration.nomenclature_id.acronym == 'CMADPSV':
        #             if configuration.integer_value < record.number_of_days:
        #                 # No se puede realizar una planificación de vacaciones de más de {} días.
        #                 raise ValidationError(
        #                     _("You cannot plan a vacation of more than {} days.").format(
        #                         configuration.integer_value))
        #         elif configuration.nomenclature_id.acronym == 'FIPV':
        #             if record.create_date < datetime(
        #                     record.create_date.year, configuration.date_value.month, configuration.date_value.day):
        #                 # La planificación de vacaciones solo se puede realizar a partir del {}.
        #                 raise ValidationError(
        #                     _("Vacation planning can only be request from {}.").format(
        #                         datetime(record.create_date.year, configuration.date_value.month,
        #                                  configuration.date_value.day).date()))
        #         elif configuration.nomenclature_id.acronym == 'FFPV':
        #             if record.create_date > datetime(record.create_date.year,
        #                                                               configuration.date_value.month,
        #                                                               configuration.date_value.day):
        #                 # La planificación de vacaciones solo se puede realizar máximo hasta el {}.
        #                 raise ValidationError(
        #                     _("Vacation planning can only be request up to {}.").format(
        #                         datetime(record.create_date.year, configuration.date_value.month,
        #                                  configuration.date_value.day).date()))
        #         elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
        #             if configuration.boolean_value:
        #                 backups = self.env['hr.employee.backups'].search(
        #                     [('employee_id', '=', record.employee_requests_id.id)])
        #                 for b in backups:
        #                     vacation_planning_request_backups = self.env['hr.vacation.planning.request'].search([
        #                         ('employee_requests_id', '=', b.employee_backup_id.id),
        #                         ('state', 'in', ['pending', 'approved']),
        #                         ('active', '=', True)
        #                     ])
        #                     for vprb in vacation_planning_request_backups:
        #                         if (
        #                                 record.date_from >= vprb.date_from and record.date_from <= vprb.date_to) or (
        #                                 record.date_to >= vprb.date_from and record.date_to <= vprb.date_from):
        #                             raise UserError(
        #                                 _('There is already a vacation planning in status (Pending or Approved) for the specified time span of at least one of your replacements.'))
        #         elif configuration.nomenclature_id.acronym == 'IPVOSA':
        #             if configuration.boolean_value:
        #                 if record.create_date.year + 1 != record.date_from.year:
        #                     # El inicio de la planificación de vacaciones es obligatoriamente dentro del siguiente año respecto al momento en que se está creando.
        #                     raise UserError(
        #                         _('The start of the vacation planning is obligatorily within the following year with respect to the moment it is being created.'))

        return record
    
    def write(self, vals):
        self.validate_module()
        record = super(VacationPlanningRequest, self).write(vals)

        if self.date_from > self.date_to:
            raise UserError(
                _('The vacation planning start date has to be less than or equal to the vacation planning end date.'))

        vacation_planning_request = self.env['hr.vacation.planning.request'].search([
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', self.id)
        ])
        for vpr in vacation_planning_request:
            if (self.date_from >= vpr.date_from and self.date_from <= vpr.date_to) \
                    or (self.date_to >= vpr.date_from and self.date_to <= vpr.date_from):
                raise UserError(
                    _('There is already a vacation planning in status (Draft, Pending, or Approved) '
                      'for the specified time frame.'))

        self._check_restrictions()

        # if not create_edit_without_restrictions:
        #     configurations = self.env['hr.normative.nomenclature'].search([
        #         ('normative_id', '=', self.employee_requests_id.normative_id.id),
        #         ('nomenclature_id.module_id', '=',
        #          self.env.ref('base.module_' + self._module).id),
        #         ('res_model_id', '=',
        #          self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
        #         ('current', '=', True)
        #     ])
        #
        #     for configuration in configurations:
        #         if configuration.nomenclature_id.acronym == 'CMIDPSV':
        #             if configuration.integer_value > self.number_of_days:
        #                 raise ValidationError(
        #                     _("You cannot a vacation planning of less than {} days.").format(
        #                         configuration.integer_value))
        #         elif configuration.nomenclature_id.acronym == 'CMADPSV':
        #             if configuration.integer_value < self.number_of_days:
        #                 raise ValidationError(
        #                     _("You cannot a vacation planning of more than {} days.").format(
        #                         configuration.integer_value))
        #         elif configuration.nomenclature_id.acronym == 'FIPV':
        #             if self.write_date < datetime(self.write_date.year, configuration.date_value.month,
        #                                            configuration.date_value.day):
        #                 raise ValidationError(
        #                     _("Vacation planning can only be request from {}.").format(
        #                         datetime(self.write_date.year, configuration.date_value.month,
        #                                  configuration.date_value.day).date()))
        #         elif configuration.nomenclature_id.acronym == 'FFPV':
        #             if self.write_date > datetime(self.write_date.year, configuration.date_value.month,
        #                                            configuration.date_value.day):
        #                 raise ValidationError(
        #                     _("Vacation planning can only be request up to {}.").format(
        #                         datetime(self.write_date.year, configuration.date_value.month,
        #                                  configuration.date_value.day).date()))
        #         elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
        #             if configuration.boolean_value:
        #                 backups = self.env['hr.employee.backups'].search(
        #                     [('employee_id', '=', self.employee_requests_id.id)])
        #                 for b in backups:
        #                     vacation_planning_request_backups = self.env['hr.vacation.planning.request'].search([
        #                         ('employee_requests_id', '=', b.employee_backup_id.id),
        #                         ('state', 'in', ['pending', 'approved']),
        #                         ('active', '=', True)
        #                     ])
        #                     for vprb in vacation_planning_request_backups:
        #                         if (self.date_from >= vprb.date_from and self.date_from <= vprb.date_to) or (
        #                                 self.date_to >= vprb.date_from and self.date_to <= vprb.date_from):
        #                             raise UserError(
        #                                 _('There is already a vacation planning in status (Pending or Approved) for the specified time span of at least one of your replacements.'))
        #         elif configuration.nomenclature_id.acronym == 'IPVOSA':
        #             if configuration.boolean_value:
        #                 if self.write_date.year + 1 != self.date_from.year:
        #                     raise UserError(
        #                         _('The start of the vacation planning is obligatorily within the following year with respect to the moment it is being created.'))

        return record
    
    def unlink(self):
        self.validate_module()
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('You can only delete vacation planning requests in draft status.'))
        return super(VacationPlanningRequest, self).unlink()


class VacationExecutionRequest(models.Model):
    _name = "hr.vacation.execution.request"
    _description = 'Vacation execution request'
    _order = "department_employee_requests_id,employee_requests_id,state,date_from"
    _inherit = ['hr.generic.request']

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_vacations.email_template_confirm_vacation_execution_request',
            'confirm_direct': 'hr_dr_vacations.email_template_confirm_direct_approve_vacations_execution_request',
            'approve': 'hr_dr_vacations.email_template_confirm_approve_vacation_execution_request',
            'reject': 'hr_dr_vacations.email_template_confirm_reject_vacation_execution_request',
            'cancel': 'hr_dr_vacations.email_template_confirm_cancel_vacation_execution_request'
        }

    _hr_notifications_mode_param = 'execution.vacations.notifications.mode'
    _hr_administrator_param = 'execution.vacations.notifications.administrator'
    _hr_second_administrator_param = 'execution.vacations.notifications.second.administrator'

    @api.onchange('employee_requests_id')
    def on_change_employee_requests_id(self):
        if self.employee_requests_id:
            self.total_vacations_available = self.employee_requests_id.total_vacations_available
            self.total_vacations_available_including_proportional_period = self.employee_requests_id.total_vacations_available_including_proportional_period

            period_ids = self.env['hr.employee.vacation.detail'].search([('employee_id', '=', self.employee_requests_id.id)])
            if len(period_ids) > 0:
                self.occupy_current_period = False

    total_vacations_available = fields.Float(string='Total vacations available',digits='Vacations', tracking=True)
    total_vacations_available_including_proportional_period = fields.Float(string='Total vacations available (including proportional period)',digits='Vacations', tracking=True)

    date_from = fields.Date('From', required=True, tracking=True)
    date_to = fields.Date('To', required=True, tracking=True)
    occupy_current_period = fields.Boolean(string='Occupy current period', default=True, help="Occupy current period.")

    occupy_period_ids = fields.One2many(
        'hr.vacation.execution.request.occupy.period',
        'vacation_execution_request_id',
        string='Occupy periods'
    )

    # @api.onchange('occupy_current_period')
    # def on_change_occupy_current_period(self):
    #     if self.occupy_current_period:
    #         self.occupy_period_ids = [(6, 0, [])]

            # occupy_periods = self.env['hr.vacation.execution.request.occupy.period'].search([
            #     ('vacation_execution_request_id', '=', self.id)
            # ])
            # for occupy_period in occupy_periods:
            #     occupy_period.unlink()

    @api.depends('date_to')
    def _compute_date_incorporation(self):
        for vacationExecutionRequest in self:
            if vacationExecutionRequest.date_to:
                vacationExecutionRequest.date_incorporation = vacationExecutionRequest.date_to + relativedelta(days=1)

    date_incorporation = fields.Date('Incorporation date', store=True, readonly=True,
                                     compute=_compute_date_incorporation, tracking=True)

    @api.depends('date_from', 'date_to')
    def _compute_number_of_days(self):
        for vacationExecutiongRequest in self:
            if vacationExecutiongRequest.date_from and vacationExecutiongRequest.date_to:
                difference = vacationExecutiongRequest.date_to - vacationExecutiongRequest.date_from
                vacationExecutiongRequest.number_of_days = difference.days + 1
            else:
                vacationExecutiongRequest.number_of_days = 0
    number_of_days = fields.Integer(string="Number of days requested", compute=_compute_number_of_days, tracking=True)

    # def search_periods(self):
    #
    #     days = self.number_of_days
    #     while days > 0:
    #
    #         period_ids = self.env['hr.employee.vacation.detail'].search(
    #             [('employee_id', '=', self.employee_requests_id.id),('available', '>', 0)])
    #         for p in period_ids:
    #
    #
    #
    #             if days - p.available <= 0:
    #                 occupy_period = {
    #                     'vacation_execution_request_id': self.id,
    #                     'period_id': p.id,
    #                     'amount': days,
    #                 }
    #                 self.env['hr.vacation.execution.request.occupy.period'].create(occupy_period)
    #
    #             elif days!=0:
    #                 occupy_period = {
    #                     'vacation_execution_request_id': self.id,
    #                     'period_id': p.id,
    #                     'amount': p.available,
    #                 }
    #                 self.env['hr.vacation.execution.request.occupy.period'].create(occupy_period)
    #
    #             days = days - p.available
    #             if days < 0:
    #                 days = 0
    #                 break
    
    def name_get(self):
        result = []
        for vacationExecutionRequest in self:
            result.append(
                (
                    vacationExecutionRequest.id,
                    _("{} {} Day(s) {}").format(vacationExecutionRequest.employee_requests_id.name,
                                                vacationExecutionRequest.number_of_days,
                                                dict(self._fields['state'].selection).get(
                                                    vacationExecutionRequest.state))

                )
            )
        return result

    def get_periods(self):
        periods = ""
        if self.occupy_current_period:
            period = self.env['hr.employee.vacation.detail'].sudo().search([
                ('employee_id', '=', self.employee_requests_id.id),
                ('date_from', '<=', self.date_from),
                ('date_to', '>=', self.date_from),
                ('state', 'not in', ('cancel', 'refuse'))
            ])
        else:
            for p in self.occupy_period_ids:

                date_from = p.period_id.date_from.strftime("%d/%m/%Y")
                date_to = p.period_id.date_to.strftime("%d/%m/%Y")

                px = "{} - {} {} día(s)".format(date_from, date_to, p.amount)

                if periods == "":
                    periods = px
                else:
                    periods = periods + ', ' + px

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Vacation request") # Solicitud de vacaciones
        local_context['request'] = _("have made a vacation request.") # ha realizado una solicitud de vacaciones.
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id

        # Solicitud de vacaciones desde el {} hasta el {}. Cantidad de días disponibles incluyendo el último período: {}. Fecha de incorporación: {}.
        local_context['details'] = _(" Vacation request from {} to {}. Number of days available including the last period: {}. Incorporation date: {}.").format(self.date_from.strftime("%d/%m/%Y"), self.date_to.strftime("%d/%m/%Y"), self.number_of_days, self.total_vacations_available, self.total_vacations_available_including_proportional_period,self.date_incorporation.strftime("%d/%m/%Y"))


        local_context['commentary'] = self.commentary

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('hr_dr_vacations.vacation_execution_request_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_dr_vacations.menu_hr_vacations').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        department = 'Dirección de Talento Humano'
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department

        return local_context

    def _check_restrictions(self, instance=None):
        """
        Valida las restricciones que pueda tener el modelo.

        @:param instance Instancia del modelo a validar.
        """

        # Si no recibe una instancia del modelo específica asume que es la actual.
        if instance is None:
            instance = self
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            configurations = self.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', self.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=',
                 self.env.ref('base.module_' + self._module).id),
                ('res_model_id', '=',
                 self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
                ('current', '=', True)
            ])
            for configuration in configurations:
                if configuration.nomenclature_id.acronym == 'CMIDPSV':
                    if configuration.integer_value > self.number_of_days:
                        raise ValidationError(
                            _("You cannot a vacation planning of less than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'CMADPSV':
                    if configuration.integer_value < self.number_of_days:
                        raise ValidationError(
                            _("You cannot a vacation planning of more than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'FIPV':
                    if datetime.utcnow().date() < datetime(datetime.utcnow().date().year,
                                                           configuration.date_value.month,
                                                           configuration.date_value.day).date():
                        raise ValidationError(
                            _("Vacation planning can only be request from {}.").format(
                                datetime(datetime.utcnow().date().year, configuration.date_value.month,
                                         configuration.date_value.day).date()))
                elif configuration.nomenclature_id.acronym == 'FFPV':
                    if datetime.utcnow().date() > datetime(datetime.utcnow().date().year,
                                                           configuration.date_value.month,
                                                           configuration.date_value.day).date():
                        raise ValidationError(
                            _("Vacation planning can only be request up to {}.").format(
                                datetime(datetime.utcnow().date().year, configuration.date_value.month,
                                         configuration.date_value.day).date()))
                elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
                    if configuration.boolean_value:
                        backups = self.env['hr.employee.backups'].search(
                            [('employee_id', '=', self.employee_requests_id.id)])
                        for b in backups:
                            vacation_planning_request_backups = self.env['hr.vacation.planning.request'].search([
                                ('employee_requests_id', '=', b.employee_backup_id.id),
                                ('state', 'in', ['pending', 'approved']),
                                ('active', '=', True)
                            ])
                            for vprb in vacation_planning_request_backups:
                                if (self.date_from >= vprb.date_from and self.date_from <= vprb.date_to) or (
                                        self.date_to >= vprb.date_from and self.date_to <= vprb.date_from):
                                    raise UserError(
                                        _('There is already a vacation planning in status (Pending or Approved) for the specified time span of at least one of your replacements.'))
                elif configuration.nomenclature_id.acronym == 'IPVOSA':
                    if configuration.boolean_value:
                        if datetime.utcnow().date().year + 1 != self.date_from.year:
                            raise UserError(
                                _('The start of the vacation planning is obligatorily within the following year with respect to the moment in which it is being confirmed.'))
                elif configuration.nomenclature_id.acronym == 'AV':
                    if configuration.boolean_value == False:
                        # No se permite adelantar vacaciones
                        if self.number_of_days > self.total_vacations_available_including_proportional_period:
                            # No puede solicitar vacaciones por más días que los que tiene disponible.
                            raise UserError(
                                _('You cannot request a vacation for more days than you have available.'))
                        elif self.number_of_days > self.employee_requests_id.total_vacations_available_including_proportional_period:
                            # No puede solicitar vacaciones por más días que los que tiene disponible. La cantidad de días disponibles cambió desde que creó la solicitud hasta que la confirmó.
                            raise UserError(
                                _('You cannot request a vacation for more days than you have available. The number of days available changed from when you created the request until you confirmed it.'))

        if self.occupy_current_period == False:

            period_ids = [op.period_id.id for op in self.occupy_period_ids]
            if len(set(period_ids)) != len(period_ids):
                raise UserError(
                    _('The periods must be unique for the request.'))


            sum = 0
            for occupy_periods in self.occupy_period_ids:
                if occupy_periods.amount > occupy_periods.available:
                    # No puede ocupar más días de los disponibles en el período.
                    raise UserError(
                        _('It cannot occupy more days than are available in the period.'))
                    break
                elif occupy_periods.amount > occupy_periods.period_id.available:
                    # No puede ocupar más días de los disponibles en el período. Los datos del período cambiaron debe borrar los períodos ocupados y agregarlos nuevamente.
                    raise UserError(
                        _('It cannot occupy more days than are available in the period. The period data changed, you must delete the busy periods and add them again.'))
                    break
                else:
                    sum += occupy_periods.amount

            if sum != self.number_of_days:
                # La suma de los días acupados deber ser igual a la cantidad de días solicitados.
                raise UserError(
                    _('The sum of the days occupied must be equal to the number of days requested.'))

    def confirm_vacation_execution_request_direct(self):
        # Funcion solo para el administrador del modulo. No valida las configuraciones del modulo.
        # No sigue un esquema de aprobacion, se considera aprobada directamente.
        self.mark_as_approved_direct()
        mail_id_confirm_request = 'hr_dr_vacations.email_template_confirm_direct_approve_vacations_execution_request'
        self.send_mail(mail_id_confirm_request)
        return self
    
    def print_vacation_execution_request(self):
        return self.env.ref('hr_dr_vacations.action_vacation_execution_request_report').report_action(self)

    @api.model
    def create(self, vals):
        vacationExecutionRequest = super(VacationExecutionRequest, self).create(vals)
        #

        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')

        # if vacationExecutionRequest.occupy_current_period == False:
        #
        #     period_ids = [op.period_id.id for op in vacationExecutionRequest.occupy_period_ids]
        #     if len(set(period_ids)) != len(period_ids):
        #         # Los períodos deben ser únicos para la solicitud.
        #         raise UserError(
        #             _('The periods must be unique for the request.'))
        #
        #     sum = 0
        #     for occupy_periods in vacationExecutionRequest.occupy_period_ids:
        #         if occupy_periods.amount > occupy_periods.available:
        #             raise UserError(
        #                 _('It cannot occupy more days than are available in the period.'))
        #             break
        #         else:
        #             sum += occupy_periods.amount
        #     if sum != vacationExecutionRequest.number_of_days:
        #         raise UserError(
        #             _('The sum of the days occupied must be equal to the number of days requested.'))

        if vacationExecutionRequest.date_from > vacationExecutionRequest.date_to:
            # La fecha de inicio de la ejecución de vacaciones tiene que ser menor o igual que la fecha de fin de la ejecución de vacaciones.
            raise UserError(
                _('The start date of the holiday run has to be less than or equal to the end date of the holiday run.'))
        #
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', vacationExecutionRequest.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', vacationExecutionRequest.id)
        ])
        for ver in vacation_execution_request:
            if (
                    vacationExecutionRequest.date_from >= ver.date_from and vacationExecutionRequest.date_from <= ver.date_to) or (
                    vacationExecutionRequest.date_to >= ver.date_from and vacationExecutionRequest.date_to <= ver.date_from):
                # Ya existe una solicitud de vacaciones en estado (Borrador, Pendiente o Aprobado) para el lapso de tiempo espeficado.
                raise UserError(
                    _('There is already a vacation request in status (Draft, Pending, or Approved) for the specified time frame.'))

        #
        if create_edit_without_restrictions == False:

            configurations = vacationExecutionRequest.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', vacationExecutionRequest.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=',
                 vacationExecutionRequest.env.ref('base.module_' + vacationExecutionRequest._module).id),
                ('res_model_id', '=', vacationExecutionRequest.env['ir.model'].sudo().search(
                    [('model', '=', vacationExecutionRequest._name)]).id),
                ('current', '=', True)
            ])
            for configuration in configurations:
                if configuration.nomenclature_id.acronym == 'CMIDPSV':
                    if configuration.integer_value > vacationExecutionRequest.number_of_days:
                        raise ValidationError(
                            _("You cannot make a request for a vacation of less than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'CMADPSV':
                    if configuration.integer_value < vacationExecutionRequest.number_of_days:
                        raise ValidationError(
                            _("You cannot make a request for a vacation of more than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
                    if configuration.boolean_value:
                        backups = self.env['hr.employee.backups'].search(
                            [('employee_id', '=', vacationExecutionRequest.employee_requests_id.id)])
                        for b in backups:
                            vacation_execution_request_backups = self.env['hr.vacation.execution.request'].search(
                                [('employee_requests_id', '=', b.employee_backup_id.id),
                                 ('state', 'in', ['draft', 'pending', 'approved'])])
                            for verb in vacation_execution_request_backups:
                                if (
                                        vacationExecutionRequest.date_from >= verb.date_from and vacationExecutionRequest.date_from <= verb.date_to) or (
                                        vacationExecutionRequest.date_to >= verb.date_from and vacationExecutionRequest.date_to <= verb.date_from):
                                    raise UserError(
                                        _('There is already a vacation execution request in status (Draft, Pending, or Approved) for the specified time span of at least one of its replacements.'))
                elif configuration.nomenclature_id.acronym == 'SVSPP':
                    if configuration.boolean_value == False:
                        count_vacation_planning_request = self.env['hr.vacation.planning.request'].search_count(
                            [('employee_requests_id', '=', vacationExecutionRequest.employee_requests_id.id),
                             ('state', '=', 'approved'), ('date_from', '=', vacationExecutionRequest.date_from),
                             ('date_to', '=', vacationExecutionRequest.date_to)])
                        if count_vacation_planning_request == 0:
                            raise UserError(
                                _('There is no vacation schedule in Approved status for the specified dates.'))
                elif configuration.nomenclature_id.acronym == 'CDAPSV':
                    difference = vacationExecutionRequest.date_from - vacationExecutionRequest.create_date.date()
                    if configuration.integer_value > difference.days:
                        raise ValidationError(
                            _(
                                "A vacation request must be made at least {} days in advance.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'AV':
                    if configuration.boolean_value == False:
                        # No se permite adelantar vacaciones
                        if vacationExecutionRequest.number_of_days > vacationExecutionRequest.total_vacations_available_including_proportional_period:
                            raise UserError(
                                _('You cannot request a vacation for more days than you have available.'))


        return vacationExecutionRequest
    
    def write(self, vals):
        vacationExecutionRequest = super(VacationExecutionRequest, self).write(vals)

        # self.total_vacations_available = self.employee_requests_id.total_vacations_available
        # self.total_vacations_available_including_proportional_period = self.employee_requests_id.total_vacations_available_including_proportional_period

        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')

        # if self.occupy_current_period == False:
        #
        #     period_ids = [op.period_id.id for op in self.occupy_period_ids]
        #     if len(set(period_ids)) != len(period_ids):
        #         raise UserError(
        #             _('The periods must be unique for the request.'))
        #
        #     sum = 0
        #     for occupy_periods in self.occupy_period_ids:
        #         if occupy_periods.amount > occupy_periods.available:
        #             raise UserError(
        #                 _('It cannot occupy more days than are available in the period.'))
        #             break
        #         else:
        #             sum += occupy_periods.amount
        #     if sum != self.number_of_days:
        #         raise UserError(
        #             _('The sum of the days occupied must be equal to the number of days requested.'))

        #
        if self.date_from > self.date_to:
            raise UserError(
                _('The start date of the holiday run has to be less than or equal to the end date of the holiday run.'))
        #
        vacation_execution_request = self.env['hr.vacation.execution.request'].search([
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', self.id)
        ])
        for ver in vacation_execution_request:
            if (
                    self.date_from >= ver.date_from and self.date_from <= ver.date_to) or (
                    self.date_to >= ver.date_from and self.date_to <= ver.date_from):
                raise UserError(
                    _('There is already a vacation request in status (Draft, Pending, or Approved) for the specified time frame.'))

        #
        if create_edit_without_restrictions == False:

            configurations = self.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', self.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=',self.env.ref('base.module_' + self._module).id),
                ('res_model_id', '=',self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
                ('current', '=', True)
            ])

            for configuration in configurations:
                if configuration.nomenclature_id.acronym == 'CMIDPSV':
                    if configuration.integer_value > self.number_of_days:
                        # No se puede realizar una solicitud de vacaciones de menos de {} días.
                        raise ValidationError(
                            _("You cannot make a request for a vacation of less than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'CMADPSV':
                    if configuration.integer_value < self.number_of_days:
                        # No se puede realizar una solicitud de vacaciones de más de {} días.
                        raise ValidationError(
                            _("You cannot make a request for a vacation of more than {} days.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'TCRPPYSV':
                    if configuration.boolean_value:
                        backups = self.env['hr.employee.backups'].search(
                            [('employee_id', '=', self.employee_requests_id.id)])
                        for b in backups:
                            vacation_execution_request_backups = self.env['hr.vacation.execution.request'].search(
                                [('employee_requests_id', '=', b.employee_backup_id.id),
                                 ('state', 'in', ['draft', 'pending', 'approved'])])
                            for verb in vacation_execution_request_backups:
                                if (self.date_from >= verb.date_from and self.date_from <= verb.date_to) or (
                                        self.date_to >= verb.date_from and self.date_to <= verb.date_from):
                                    # Ya existe una solicitud de vacaciones en estado (Borrador, Pendiente o Aprobado) para el lapso de tiempo espeficado de al menos uno de sus reemplazos.
                                    raise UserError(
                                        _('There is already a vacation request in status (Draft, Pending, or Approved) for the specified time frame of at least one of your replacements.'))
                elif configuration.nomenclature_id.acronym == 'SVSPP':
                    if configuration.boolean_value == False:
                        count_vacation_planning_request = self.env['hr.vacation.planning.request'].search_count(
                            [('employee_requests_id', '=', self.employee_requests_id.id),
                             ('state', '=', 'approved'), ('date_from', '=', self.date_from),
                             ('date_to', '=', self.date_to)])
                        if count_vacation_planning_request == 0:
                            # No existe ninguna planificación de vacaciones en estado Aprobado para las fechas espeficadas.
                            raise UserError(
                                _('There is no vacation schedule in Approved status for the specified dates.'))
                elif configuration.nomenclature_id.acronym == 'CDAPSV':
                    difference = self.date_from - self.create_date
                    if configuration.integer_value > difference.days:
                        # Una solicitud de vacaciones se debe realizar por lo menos con {} días de anticipación.
                        raise ValidationError(
                            _(
                                "A vacation request must be made at least {} days in advance.").format(
                                configuration.integer_value))
                elif configuration.nomenclature_id.acronym == 'AV':
                    if configuration.boolean_value == False:
                        # No se permite adelantar vacaciones
                        if self.number_of_days > self.total_vacations_available_including_proportional_period:
                            raise UserError(
                                _('You cannot request a vacation for more days than you have available.'))

        return vacationExecutionRequest
    
    def unlink(self):
        for vacationExecutionRequest in self:
            if vacationExecutionRequest.state != 'draft':
                raise ValidationError(_('You can only delete vacation execution requests in draft status.'))
        return super(VacationExecutionRequest, self).unlink()


class VacationExecutionRequestOccupyPeriod(models.Model):
    _name = "hr.vacation.execution.request.occupy.period"
    _description = 'Vacation execution request occupy period'

    vacation_execution_request_id = fields.Many2one('hr.vacation.execution.request', string="Vacation execution request", required=True, ondelete='cascade')
    employee_requests_id = fields.Many2one('hr.employee',string="Collaborator", related='vacation_execution_request_id.employee_requests_id')

    # @api.model
    # def _getDomain(self):
    #     return [('available', '>', 0)]
    period_id = fields.Many2one('hr.employee.vacation.detail', string="Period", required=True, ondelete='cascade')

    @api.onchange('period_id')
    def on_change_period_id(self):
        if self.period_id:
            self.available = self.period_id.available
    available = fields.Float(string='Available',digits='Vacations', readonly=True)
    amount = fields.Float(string='Amount', required=True,digits='Vacations', group_operator="sum")

    # _sql_constraints = [
    #     ('vacation_execution_and_period_unique',
    #      'UNIQUE(vacation_execution_request_id, period_id)',
    #      "Para una solicitud de vacaciones los períodos ocupados deben ser únicos."),
    # ]


class ReplanningVacationPlanningRequest(models.TransientModel):
    _name = 'hr.replanning.vacation.planning.request'
    _description = 'Re-planning vacation planning request'

    # Planificación Actual.
    actual_vacation_planning_request_id = fields.Many2one('hr.vacation.planning.request',
                                                          string='Actual vacation planning request', readonly=True,
                                                          default=lambda self: self._context.get('active_id'))
    employee_requests_id = fields.Many2one('hr.employee', string="Collaborator", readonly=True,
                                           related='actual_vacation_planning_request_id.employee_requests_id')
    department_employee_requests_id = fields.Many2one('hr.department', string="Department employee requesting",
                                                      related='actual_vacation_planning_request_id.department_employee_requests_id',
                                                      readonly=True)
    date_from = fields.Date('From', readonly=True, related='actual_vacation_planning_request_id.date_from')
    date_to = fields.Date('To', readonly=True, related='actual_vacation_planning_request_id.date_to')
    date_incorporation = fields.Date('Incorporation date', readonly=True,
                                     related='actual_vacation_planning_request_id.date_incorporation')
    number_of_days = fields.Integer(string="Number of days planned", readonly=True,
                                    related='actual_vacation_planning_request_id.number_of_days')

    # Replanificación.
    commentary_new = fields.Text(string="Commentary", required=True)
    date_from_new = fields.Date('From', required=True)
    date_to_new = fields.Date('To', required=True)
    
    def action_replanning(self):

        vpr_new = self.env['hr.vacation.planning.request'].create({
            'employee_requests_id': self.employee_requests_id.id,
            'parent_id': self.actual_vacation_planning_request_id.id,
            'state': 'draft',
            'commentary': self.commentary_new,
            'date_to': self.date_to_new,
            'date_from': self.date_from_new
        })

        if vpr_new:
            vpr_new.confirm_request()
            self.actual_vacation_planning_request_id.state = 'replanned'
    
    def action_replanning_direct(self):

        vpr_new = self.env['hr.vacation.planning.request'].create({
            'employee_requests_id': self.employee_requests_id.id,
            'parent_id': self.actual_vacation_planning_request_id.id,
            'state': 'approved',
            'commentary': self.commentary_new,
            'date_to': self.date_to_new,
            'date_from': self.date_from_new
        })

        if vpr_new:
            vpr_new.confirm_vacation_planning_request_direct()
            self.actual_vacation_planning_request_id.state = 'replanned'


class PrintVacationPlanningRequest(models.TransientModel):
    _name = 'hr.print.vacation.planning.request'
    _description = 'Print vacation planning request'

    def _default_date_from(self):
        default_date_from = '%s-01-01' % datetime.now().year
        return datetime.strptime(str(default_date_from), '%Y-%m-%d').date()

    date_from = fields.Date('From', required=True, default=_default_date_from)
    date_to = fields.Date('To', required=True, compute='_date_to')

    @api.depends('date_from')
    def _date_to(self):
        default_date_to = '%s-12-31' % self.date_from.year
        self.date_to = datetime.strptime(str(default_date_to), '%Y-%m-%d').date()
    
    def action_print_vpr(self):
        data = {
            'from': self.date_from,
            'to': self.date_to,
            'all': False
        }
        return self.env.ref('hr_dr_vacations.action_print_vacation_planning_request').report_action(self, data=data)


class PrintVacationPlanningRequestAll(models.TransientModel):
    _name = 'hr.print.vacation.planning.request.all'
    _description = 'Print vacation planning request all'
    _inherit = 'hr.print.vacation.planning.request'
    
    def action_print_vpr(self):
        data = {
            'from': self.date_from,
            'to': self.date_to,
            'all': True
        }
        return self.env.ref('hr_dr_vacations.action_print_vacation_planning_request').report_action(self, data=data)


class PrintVacationPlanningRequestXls(models.AbstractModel):
    _name = 'report.hr_dr_vacations.report_vacation_xls'
    _description = 'Report vacation xls'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, lines):
        # Función para generar el xls de la Solicitud de planificación de vacaciones

        date_start = data['from']
        date_end = data['to']
        first_date = datetime.strptime(date_start, '%Y-%m-%d').date()
        last_date = datetime.strptime(date_end, '%Y-%m-%d').date()

        # Muestro todos los departamentos o solo el del colaborador autenticado.
        if data['all']:
            departments = self._get_departent_tree_list()
        else:
            departments = []

            # Si el usuario autenticado no está registrado como colaborador, no mostrará ningún departamento
            current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if current_employee:
                departments.append(current_employee.department_id)

        # employees = self.env['hr.employee'].search([])
        first_day_year = datetime.strptime(str(date_start), '%Y-%m-%d').date()
        title = workbook.add_format(
            {'font_size': 12, 'align': 'center', 'bold': True, 'font_name': 'Calibri'})
        sub_title = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'font_name': 'Calibri'})
        header = workbook.add_format(
            {'font_size': 10, 'align': 'center', 'bold': True, 'font_name': 'Calibri', 'border': True})
        text = workbook.add_format({'font_size': 10, 'align': 'left'})
        text_emphasis = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True, 'bg_color': '#DEDEDE'})
        cell_color = workbook.add_format({'fg_color': '#C00000'})

        sheet = workbook.add_worksheet('Hoja 1')
        row_ini, col_ini, col_ini_aux = 8, 1, 1
        row_aux, col_aux = 6, 2

        if calendar.isleap(first_date.year):
            feb_day = 29
        else:
            feb_day = 28

        month_day = {
            'ene': {
                'mes': 'Enero', 'dias': 31},
            'feb': {
                'mes': 'Febrero', 'dias': feb_day},
            'mar': {
                'mes': 'Marzo', 'dias': 31},
            'abr': {
                'mes': 'Abril', 'dias': 30},
            'may': {
                'mes': 'Mayo', 'dias': 31},
            'jun': {
                'mes': 'Junio', 'dias': 30},
            'jul': {
                'mes': 'Julio', 'dias': 31},
            'ago': {
                'mes': 'Agosto', 'dias': 31},
            'sep': {
                'mes': 'Septiembre', 'dias': 30},
            'oct': {
                'mes': 'Octubre', 'dias': 31},
            'nov': {
                'mes': 'Noviembre', 'dias': 30},
            'dic': {
                'mes': 'Diciembre', 'dias': 31},
        }

        # Creo un índice para referenciar el diccionario month_day
        # TODO: Revisar si no es necesario que las claves del dict month_day sean las actuales ('ene', 'feb' ...)
        #       remplazarlas por los valores numéricos de m_index y llamar directamente a month_day y eliminar m_index.
        m_index = {
            1: 'ene',
            2: 'feb',
            3: 'mar',
            4: 'abr',
            5: 'may',
            6: 'jun',
            7: 'jul',
            8: 'ago',
            9: 'sep',
            10: 'oct',
            11: 'nov',
            12: 'dic'
        }

        sheet.freeze_panes(0, 2)

        sheet.write(1, 1, _('Vacation Planning'), title) # Planificación de Vacaciones

        sheet.write(3, 1, _("From: {}").format(date_start), sub_title)
        # sheet.write(3, 2, date_start, text)
        sheet.write(4, 1, _("To: {}").format(date_end), sub_title)
        # sheet.write(4, 2, date_end, text)
        sheet.write(7, col_ini, _('Employee'), header)

        # Loop para escribir los nombres de los meses y sus días
        for index, dict_key in m_index.items():
            # Inserto los meses a partir del seleccionado
            if index >= first_date.month:
                # Inserto los días a partir del seleccionado
                first_day = 1
                if index == first_date.month:
                    first_day = first_date.day

                r = month_day.get(dict_key)
                days_in_month = r.get('dias') - first_day + 1  # días del mes que se mostrarán
                sheet.merge_range(
                    xl_rowcol_to_cell(row_aux, col_aux) + ':' + xl_rowcol_to_cell(row_aux, days_in_month + col_aux - 1),
                    r.get('mes'), header)
                col_aux += days_in_month
                for a in range(first_day, r.get('dias') + 1):
                    sheet.set_column(7, col_ini_aux + 1, 2.3)
                    sheet.write(7, col_ini_aux + 1, a, header)
                    col_ini_aux += 1
        # for r in month_day:
        #     sheet.merge_range(xl_rowcol_to_cell(row_aux, col_aux) + ':' + xl_rowcol_to_cell(row_aux, month_day[r].get(
        #         'dias') + col_aux - 1), month_day[r].get('mes'), header)
        #     col_aux += month_day[r].get('dias')
        #     for a in range(1, month_day[r].get('dias') + 1):
        #         sheet.set_column(7, col_ini_aux + 1, 2.3)
        #         sheet.write(7, col_ini_aux + 1, a, header)
        #         col_ini_aux += 1

        for d in departments:
            # Generando nombre del departamento
            sheet.set_column(row_ini, col_ini, 35)
            sheet.write(row_ini, col_ini, d.name, text_emphasis)
            row_ini += 1
            for e in d.member_ids:
                if e.active and e.state in ['affiliate', 'temporary', 'intern']:
                    # Generando cada colaborador activo del departamento
                    sheet.set_column(row_ini, col_ini, 35)
                    sheet.write(row_ini, col_ini, e.name, text)
                    for a in e.vacation_planning_request_ids:
                        if a.state == 'approved':
                            if a.date_from >= first_date and a.date_to <= last_date:
                                if a.date_from and a.date_to:
                                    init_delta = (a.date_from - first_day_year).days
                                    end_delta = (a.date_to - first_day_year).days
                                    sheet.merge_range(
                                        xl_rowcol_to_cell(row_ini, init_delta + 2) + ':' + xl_rowcol_to_cell(row_ini,
                                                                                                             end_delta + 2),
                                        '', cell_color)
                    row_ini += 1
            row_ini += 1  # Insertando una fila en blanco para separar los departamentos
        # for e in employees:
        #     sheet.set_column(row_ini, col_ini, 35)
        #     sheet.write(row_ini, col_ini, e.name, text)
        #     for a in e.vacation_planning_request_ids:
        #         if a.state == 'approved':
        #             if a.date_from >= first_date and a.date_to <= last_date:
        #                 if a.date_from and a.date_to:
        #                     init_delta = (a.date_from - first_day_year).days
        #                     end_delta = (a.date_to - first_day_year).days
        #                     sheet.merge_range(
        #                         xl_rowcol_to_cell(row_ini, init_delta + 2) + ':' + xl_rowcol_to_cell(row_ini, end_delta + 2),
        #                         '', cell_color)
        #     row_ini += 1

    def _get_departent_tree_list(self):
        """
        Obtiene un listado de todos los departamentos ordenado de forma jerárquica.

        :return: Listado de departamentos ordenado jerárquicamente
        """
        departments = self.env['hr.department'].search([])
        sorted_departments =[]

        for department in departments:
            if department not in sorted_departments:
                if department.parent_id:
                    pass
                else:
                    sorted_departments.extend(self._sort_department_children(department))

        return sorted_departments

    def _sort_department_children(self, department):
        """
        Se mueve de forma recursiva en un departamento dado y pasa toda su estructura en preorden a una lista.

        :param department: Departamento a recorrer.
        :return: Lista en preorden del departamento seleccionado y todos sus hijos.
        """
        results = [department]
        if department.child_ids:
            for child in department.child_ids:
                results.extend(self._sort_department_children(child))
        return results


class PrintVacationSummaryRequestXls(models.AbstractModel):
    _name = 'report.hr_dr_vacations.report_vacation_summary'
    _description = 'Report vacation summary'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, lines):
        """Función para generar el xls de la solicitud de resumen de vacaciones"""

        # Definiendo formatos de celdas
        text_props = {'font_size': 10, 'align': 'left', 'font_name': 'Calibri'}
        label_props = text_props.copy()
        label_props.update({'bold': True, 'align': 'right'})
        title_props = text_props.copy()
        title_props.update({'font_size': 18, 'font_name': 'Calibri Light', 'font_color': '#44546A'})
        h1_props = text_props.copy()
        h1_props.update({'font_size': 15, 'bold': True, 'font_color': '#44546A'})
        h2_props = h1_props.copy()
        h2_props.update({'font_size': 11})
        th_props = label_props.copy()
        th_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#44546A', 'font_color': '#FFFFFF',
                         'border': True, 'text_wrap': True})
        td_props = text_props.copy()
        td_props.update({'border': True})
        td_info_props = td_props.copy()
        td_info_props.update({'align': 'center', 'italic': True, 'font_color': '#7F7f7F'})
        date_props = text_props.copy()
        date_props.update({'num_format': 'dd/mm/yyyy'})
        number_props = text_props.copy()
        number_props.update({'num_format': '#,##0'})
        money_props = text_props.copy()
        money_props.update({'num_format': '#,##0.00'})
        td_date_props = date_props.copy()
        td_date_props.update({'border': True})
        td_number_props = number_props.copy()
        td_number_props.update({'align': 'right', 'border': True})
        td_money_props = money_props.copy()
        td_money_props.update({'align': 'right', 'border': True})

        title = workbook.add_format(title_props)
        header1 = workbook.add_format(h1_props)
        header2 = workbook.add_format(h2_props)
        label = workbook.add_format(label_props)
        text = workbook.add_format(text_props)
        date_format = workbook.add_format(date_props)
        number_format = workbook.add_format(number_props)
        money_format = workbook.add_format(money_props)
        table_header = workbook.add_format(th_props)
        table_cell = workbook.add_format(td_props)
        table_info_cell = workbook.add_format(td_info_props)
        table_date_format = workbook.add_format(td_date_props)
        table_number_format = workbook.add_format(td_number_props)
        table_money_format = workbook.add_format(td_money_props)

        for employee in lines:
            if not employee.last_company_entry_date:
                raise ValidationError(_('{} have no defined "Last company entry date" field.').format(employee.display_name))
            row = 0  # Número actual de la fila
            sheet = workbook.add_worksheet(employee.name)  # TODO: Cambiar por nombre de colaborador o número tal vez.

            # Dando formato a la hoja
            sheet.set_landscape()
            sheet.set_paper(9)  # A4 paper format (change to 0 for printer default)
            sheet.center_horizontally()
            sheet.set_margins(left = 0.7, right = 0.7, top = 0.75, bottom = 0.75)

            # Estableciendo el ancho de las columnas
            sheet.set_column('A:A', 7.86)
            sheet.set_column('B:B', 10.71)
            sheet.set_column('C:D', 10.14)
            sheet.set_column('E:E', 4.71)
            sheet.set_column('F:F', 11.43)
            sheet.set_column('G:H', 7.29)
            sheet.set_column('I:I', 10.43)
            sheet.set_column('J:M', 8.71)
            sheet.set_column('N:O', 9.0)
            sheet.set_column('P:P', 8.29)

            # Escribiendo información en la hoja
            sheet.write(row, 0, _("Vacations Resume"), title)
            row += 2
            sheet.write(row, 2, _("Employee:"), label)
            sheet.write(row, 3, employee.name, text)

            sheet.write(row, 11, _("Total vacations available:"), label)
            sheet.write_number(row, 12, employee.total_vacations_available, money_format)
            row += 1
            sheet.write(row, 2, _("Department:"), label)
            sheet.write(row, 3, employee.department_id.name, text)

            sheet.write(row, 11, _("Total vacations available (including proportional period):"), label)
            sheet.write_number(row, 12, employee.total_vacations_available_including_proportional_period, money_format)
            row += 1
            sheet.write(row, 2, _("Last company entry date:"), label)
            sheet.write_datetime(row, 3, employee.last_company_entry_date, date_format)

            row += 2
            sheet.write(row, 2, _("Previous periods"), header1)

            sheet.write(row, 11, _("Cutoff date"), header1)
            row += 1
            sheet.write(row, 2, _("Total time in company"), header2)

            sheet.write(row, 11, _("Vacations available:"), label)
            sheet.write_number(row, 12, employee.vacations_cutoff_date, money_format)
            row += 1
            sheet.write(row, 2, _("    Years:"), label)
            sheet.write_number(row, 3, employee.total_time_in_company_years, number_format)

            sheet.write(row, 11, _("Vacations taken:"), label)
            sheet.write_number(row, 12, employee.vacations_taken_cutoff_date, money_format)
            row += 1
            sheet.write(row, 2, _("    Months:"), label)
            sheet.write_number(row, 3, employee.total_time_in_company_months, number_format)

            sheet.write(row, 11, _("Total vacations accumulated:"), label)
            sheet.write_number(row, 12, employee.total_vacations_accumulated_cutoff_date, money_format)
            row += 1
            sheet.write(row, 2, _("    Days:"), label)
            sheet.write_number(row, 3, employee.total_time_in_company_days, number_format)
            # row es 10

            sheet.merge_range('A13:P13', _('Details'), header1)
            sheet.merge_range('A14:A15', _('Sequence'), table_header)
            sheet.merge_range('B14:B15', _('Type'), table_header)
            sheet.merge_range('C14:C15', _('From'), table_header)
            sheet.merge_range('D14:D15', _('To'), table_header)
            sheet.merge_range('E14:E15', _('Days'), table_header)
            sheet.merge_range('F14:F15', _('Standard accumulated'), table_header)
            sheet.merge_range('G14:H14', _('Increase by'), table_header)
            sheet.merge_range('I14:I15', _('Total accumulated'), table_header)
            sheet.merge_range('J14:J15', _('Worked'), table_header)
            sheet.merge_range('K14:K15', _('Not worked'), table_header)
            sheet.merge_range('L14:L15', _('Taken'), table_header)
            sheet.merge_range('M14:M15', _('Lost'), table_header)
            sheet.merge_range('N14:O14', _('Excecution'), table_header)
            sheet.merge_range('P14:P15', _('Available'), table_header)
            sheet.write(14, 6, _("Seniority"), table_header)
            sheet.write(14, 7, _("Age"), table_header)
            sheet.write(14, 13, _("Vacation"), table_header)
            sheet.write(14, 14, _("Permission"), table_header)

            row = 15

            if employee.vacation_detail_ids:
                for detail in employee.vacation_detail_ids:
                    sheet.write_number(row, 0, detail.sequence, table_number_format)
                    sheet.write(row, 1, detail.type, table_cell)
                    sheet.write_datetime(row, 2, detail.date_from, table_date_format)
                    sheet.write_datetime(row, 3, detail.date_to, table_date_format)
                    sheet.write_number(row, 4, detail.days, table_number_format)
                    sheet.write_number(row, 5, detail.standard_accumulated, table_money_format)
                    sheet.write_number(row, 6, detail.accumulated_by_seniority, table_money_format)
                    sheet.write_number(row, 7, detail.increase_by_age, table_money_format)
                    sheet.write_number(row, 8, detail.total_accumulated, table_money_format)
                    sheet.write_number(row, 9, detail.total_accumulated_worked, table_money_format)
                    sheet.write_number(row, 10, detail.total_accumulated_not_worked, table_money_format)
                    sheet.write_number(row, 11, detail.taken, table_money_format)
                    sheet.write_number(row, 12, detail.lost, table_money_format)
                    sheet.write_number(row, 13, detail.vacation_execution, table_money_format)
                    sheet.write_number(row, 14, detail.permissions, table_money_format)
                    sheet.write_number(row, 15, detail.available, table_money_format)

                    row += 1
            else:
                sheet.merge_range('A16:P16', _('There are no details for this employee yet.'), table_info_cell)

            sheet.fit_to_pages(1, 0)