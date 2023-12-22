# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.dr_license_customer.models.models import License
import math


import logging
_logger = logging.getLogger(__name__)


class Util:

    @staticmethod
    def seconds2hms(seconds, precision=2):
        _AVG_HOUR = 3600.0
        _AVG_MINUTE = 60.0

        negative = True
        if seconds >= 0:
            negative = False
        seconds = abs(seconds)

        hours_d = float(round(seconds / _AVG_HOUR, precision))

        hours, remainder = divmod(seconds, _AVG_HOUR)
        hours = int(hours)

        minutes, remainder = divmod(remainder, _AVG_MINUTE)
        minutes = int(minutes)

        seconds = int(remainder)

        cadena = ""
        if negative:
            cadena = "- {}:{}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                         "0{}".format(minutes) if minutes <= 9 else minutes,
                                         "0{}".format(seconds) if seconds <= 9 else seconds)
        else:
            cadena = "{}:{}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                       "0{}".format(minutes) if minutes <= 9 else minutes,
                                       "0{}".format(seconds) if seconds <= 9 else seconds)

        return {'hd': hours_d, 'h': hours, 'm': minutes, 's': seconds, 'c': cadena}

    @staticmethod
    def hours2hm(hours):
        negative = True
        if hours >= 0:
            negative = False
        hours = abs(hours)

        minutes = int(round(((hours - int(hours))*60), 0))
        hours = int(hours)

        cadena = ""
        if negative:
            cadena = "- {}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                      "0{}".format(minutes) if minutes <= 9 else minutes)
        else:
            cadena = "{}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                    "0{}".format(minutes) if minutes <= 9 else minutes)

        return {'h': hours, 'm': minutes, 'c': cadena}


class ResourceCalendar(models.Model):
    _name = 'resource.calendar'
    _inherit = ['resource.calendar', 'mail.thread']

    @api.onchange('attendance_ids')
    def _onchange_attendance_ids(self):
        attendances = self.attendance_ids.filtered(
            lambda attendance: not attendance.date_from and not attendance.date_to)
        hour_amount = 0.0
        for attendance in attendances:
            hour_amount += attendance.hour_to - attendance.hour_from
        self.hours_per_week = round(hour_amount, 2)

    courtesy_start = fields.Float(string='Cortesía al inicio', default=5,
                                  digits='Schedule', tracking=True)
    courtesy_end = fields.Float(string='Cortesía al fin', default=0, digits='Schedule', tracking=True)
    consider_overtime_start_schedule = fields.Boolean(string='Considerar horas extras al inicio de la jornada',
                                                      default=False, tracking=True)
    consider_overtime_end_schedule = fields.Boolean(string='Considerar horas extras al finalizar la jornada',
                                                    default=True, tracking=True)
    consider_hour_night = fields.Boolean(string='Considerar horas nocturnas', default=True, tracking=True)
    max_hours_before_start = fields.Integer(
        string='Cantidad máxima de horas antes del inicio planificado', default=6,
        help="Cantidad máxima de horas antes del inicio planificado donde es permitido registrar una marcación.",
        required=True, tracking=True)
    max_hours_after_end = fields.Integer(
        string='Cantidad máxima de horas después del fin planificado', default=6,
        help="Cantidad máxima de horas después del fin planificado donde es permitido registrar una marcación.",
        required=True, tracking=True)
    hours_per_week = fields.Float("Horas de trabajo por semana", tracking=True)


class Employee(models.Model):
    _inherit = 'hr.employee'

    turn_employee_ids = fields.One2many('hr.employee.shift', 'employee_id', string="Turnos")


class EmployeeShift(models.Model):
    _name = "hr.employee.shift"
    _description = 'Employee shift'
    _inherit = ['mail.thread']
    _order = "employee_id, planned_start"

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

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        return super(EmployeeShift, self).create(vals_list)

    def write(self, vals):
        self.validate_module()
        return super(EmployeeShift, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(EmployeeShift, self).unlink()

    def _get_percentage_by_hour_extra(self, id_hour_extra, employee=None):
        employee_id = employee or self.employee_id
        acronym = 'PRPH'
        module = self.env.ref('base.module_' + 'hr_dr_schedule')

        percentage = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', 'hr.hour.extra')]).id),
            ('res_id', '=', id_hour_extra),
            ('current', '=', True)
        ], limit=1)
        if percentage:
            percentage = percentage.float_value
            return percentage
        else:
            message = _(
                "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. "
                "Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, "
                "Módulo del nomenclador: {}, Siglas del nomenclador: {}, Modelo: {}, ID: {}.").format(
                self.employee_id.normative_id.name,
                self.employee_id.normative_id.name,
                module.display_name, acronym,
                self.env['ir.model'].sudo().search([('model', '=', 'hr.hour.extra')]).id, id_hour_extra)
            raise ValidationError(message)

    def _get_percentage_by_hour_night(self, id_hour_night):
        acronym = 'PRPH'
        module = self.env.ref('base.module_' + 'hr_dr_schedule')

        percentage = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', 'hr.hour.night')]).id),
            ('res_id', '=', id_hour_night),
            ('current', '=', True)
        ], limit=1)
        if percentage:
            percentage = percentage.float_value
            return percentage
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. "
                    "Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, "
                    "Módulo del nomenclador: {}, Siglas del nomenclador: {}, Modelo: {}, ID: {}.").format(
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym,
                    self.env['ir.model'].sudo().search([('model', '=', 'hr.hour.extra')]).id,
                    id_hour_night)
            )

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
                _("La zona horaria local no está definida. "
                  "Es posible que deba establecer una zona horaria en el colaborador "
                  "o en las preferencias de su usuario."))
        tz = pytz.timezone(tz_name)
        return pytz.utc.localize(utc_dt, is_dst=None).astimezone(tz)

    def delete_hour_night_by_day_and_employee(self, date, employee):
        employee_hour_night = self.env['hr.employee.hour.night'].search([
            ('employee_id', '=', employee.id),
            ('date', '=', date),
        ])
        if employee_hour_night:
            employee_hour_night.unlink()

    def create_hour_extra_day_not_shift(self, employee, attendance_period, date, date_i, date_f, 
                                        delete_actual_compute_attendance):
        if delete_actual_compute_attendance:
            employee_hour_extra = self.env['hr.employee.hour.extra'].search([
                ('employee_id', '=', employee.id),
                ('date', '=', date),
            ])
            if employee_hour_extra:
                employee_hour_extra.unlink()

        user_attendance_ids = self.env['user.attendance'].search([
            ('employee_id', '=', employee.id),
            ('timestamp', '>=', date_i),
            ('timestamp', '<=', date_f),
        ], order="timestamp asc")

        if len(user_attendance_ids) >= 2:
            global_result = dict()
            for i in range(1, len(user_attendance_ids), 2):
                start = self.convert_utc_time_to_tz(user_attendance_ids[i-1].timestamp, employee.tz)
                end = self.convert_utc_time_to_tz(user_attendance_ids[i].timestamp, employee.tz)

                start_time = start.hour * 3600 + start.minute * 60 + start.second
                end_time = end.hour * 3600 + end.minute * 60 + end.second

                hour_extra = self._get_amount_by_hour_extra(start_time, end_time, True, employee)

                for k in hour_extra.keys():
                    if k in global_result:
                        global_result[k] = global_result.get(k, 0) + hour_extra.get(k, 0)
                    else:
                        global_result[k] = + hour_extra.get(k, 0)

            if 'sum' in global_result:
                del global_result['sum']

            for k in global_result.keys():
                percentage = self._get_percentage_by_hour_extra(k, employee)
                self.env['hr.employee.hour.extra'].create({
                    'employee_id': employee.id,
                    'department_employee_id': employee.department_id.id,
                    'user_manager_department_employee_id': employee.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': global_result.get(k, 0),
                    'amount': global_result.get(k, 0),
                    'percentage_increase': percentage,
                    'hour_extra_id': k,
                    'attendance_period_id': attendance_period.id
                })

    def compute_attendance(self, date, attendance_period_id, delete_actual_compute_attendance):
        # HORAS EXTRAS
        result = self._get_amount_hour_extra_id(date)
        sum_HE = result.get('sum', 0)
        difference_TR_TP = self.time_real - self.time_planned

        if 'sum' in result:
            del result['sum']

        if delete_actual_compute_attendance:
            employee_hour_extra = self.env['hr.employee.hour.extra'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '=', date),
            ])
            if employee_hour_extra:
                employee_hour_extra.unlink()

        if sum_HE <= difference_TR_TP:
            # Crear las horas extras
            for k in result.keys():
                percentage = self._get_percentage_by_hour_extra(k)
                self.env['hr.employee.hour.extra'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result.get(k, 0),
                    'amount': result.get(k, 0),
                    'percentage_increase': percentage,
                    'hour_extra_id': k,
                    'attendance_period_id': attendance_period_id.id
                })
        else:
            difference_sum_HE_vs_difference_TR_TP = sum_HE - difference_TR_TP

            for k in result.keys():
                percentage = result.get(k, 0) * 100 / sum_HE
                amount_discount = difference_sum_HE_vs_difference_TR_TP * percentage/100

                percentage = self._get_percentage_by_hour_extra(k)

                self.env['hr.employee.hour.extra'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result.get(k, 0),
                    'amount': result.get(k, 0) - amount_discount,
                    'percentage_increase': percentage,
                    'hour_extra_id': k,
                    'attendance_period_id': attendance_period_id.id
                })

        # HORAS NOCTURNAS
        result_HN = self._get_amount_hour_night_id(date)
        sum_HN = result_HN.get('sum', 0)
        if 'sum' in result_HN:
            del result_HN['sum']

        if delete_actual_compute_attendance:
            employee_hour_night = self.env['hr.employee.hour.night'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '=', date),
            ])
            if employee_hour_night:
                employee_hour_night.unlink()

        if sum_HN > self.time_planned and sum_HN > self.time_real:
            # Recortar las horas nocturnas pq no pueden ser mas que lo planificado y lo trabajado
            if self.time_planned < self.time_real:
                difference = sum_HN - self.time_planned
            else:
                difference = sum_HN - self.time_real

            for k in result_HN.keys():
                percentage = result_HN.get(k, 0) * 100 / sum_HN
                amount_discount = difference * percentage / 100

                percentage = self._get_percentage_by_hour_night(k)
                self.env['hr.employee.hour.night'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result_HN.get(k, 0),
                    'amount': result_HN.get(k, 0) - amount_discount,
                    'percentage_increase': percentage,
                    'hour_night_id': k,
                    'attendance_period_id': attendance_period_id.id
                })
        elif sum_HN > self.time_planned:
            # Recortar las horas nocturnas pq no pueden ser mas que lo planificado
            difference = sum_HN - self.time_planned
            for k in result_HN.keys():
                percentage = result_HN.get(k, 0) * 100 / sum_HN
                amount_discount = difference * percentage / 100

                percentage = self._get_percentage_by_hour_night(k)
                self.env['hr.employee.hour.night'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result_HN.get(k, 0),
                    'amount': result_HN.get(k, 0) - amount_discount,
                    'percentage_increase': percentage,
                    'hour_night_id': k,
                    'attendance_period_id': attendance_period_id.id
                })
        elif sum_HN > self.time_real:
            # Recortar las horas nocturnas pq no pueden ser mas que lo trabajado
            difference = sum_HN - self.time_real
            for k in result_HN.keys():
                percentage = result_HN.get(k, 0) * 100 / sum_HN
                amount_discount = difference * percentage / 100

                percentage = self._get_percentage_by_hour_night(k)
                self.env['hr.employee.hour.night'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result_HN.get(k, 0),
                    'amount': result_HN.get(k, 0) - amount_discount,
                    'percentage_increase': percentage,
                    'hour_night_id': k,
                    'attendance_period_id': attendance_period_id.id
                })
        else:
            for k in result_HN.keys():
                percentage = self._get_percentage_by_hour_night(k)
                self.env['hr.employee.hour.night'].create({
                    'employee_id': self.employee_id.id,
                    'department_employee_id': self.employee_id.department_id.id,
                    'user_manager_department_employee_id': self.employee_id.department_id.manager_id.user_id.id,
                    'date': date,
                    'amount_initial': result_HN.get(k, 0),
                    'amount': result_HN.get(k, 0),
                    'percentage_increase': percentage,
                    'hour_night_id': k,
                    'attendance_period_id': attendance_period_id.id
                })

        # MARCAR LA ASISTENCIA COMO COMPUTADA PARA QUE EL CRON NO LA COMPUTE NUEVAMENTE
        self.attendance_computed = True

    def _get_amount_hour_extra_id(self, date):
        is_holiday = False
        holidays = self.env['hr.holiday'].search_count([
            ('date', '=', date)
        ])
        if holidays > 0:
            is_holiday = True

        global_result = dict()

        if self.resource_calendar_id.consider_overtime_start_schedule and self._get_consider_hour_extra('IJ'):
            # Considerar horas extras al inicio de la jornada
            if self.difference_total_seconds_start > 0:
                start = self.convert_utc_time_to_tz(self.real_start, self.employee_id.tz).hour * 3600 + \
                        self.convert_utc_time_to_tz(self.real_start, self.employee_id.tz).minute * 60 + \
                        self.convert_utc_time_to_tz(self.real_start, self.employee_id.tz).second
                end = self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz).hour * 3600 + \
                      self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz).minute * 60 + \
                      self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz).second

                consider_hour_extra_from = self._get_consider_hour_extra_from('IJ')

                if start > end:
                    # Salto de dia
                    first_part = self._get_amount_by_hour_extra(start, 24*3600, is_holiday)
                    second_part = self._get_amount_by_hour_extra(0, end, is_holiday)
                    if first_part.get('sum', 0) + second_part.get('sum', 0) >= consider_hour_extra_from * 60:

                        for k in first_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + first_part.get(k, 0)
                            else:
                                global_result[k] = + first_part.get(k, 0)

                        for k in second_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + second_part.get(k, 0)
                            else:
                                global_result[k] = + second_part.get(k, 0)
                else:
                    only_part = self._get_amount_by_hour_extra(start, end, is_holiday)
                    if only_part.get('sum', 0) >= consider_hour_extra_from * 60:
                        for k in only_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + only_part.get(k, 0)
                            else:
                                global_result[k] = + only_part.get(k, 0)

        if self.resource_calendar_id.consider_overtime_end_schedule and self._get_consider_hour_extra('FJ'):
            # Considerar horas extras al fin de la jornada
            if self.difference_total_seconds_end > 0:

                start = self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz).hour*3600 + \
                        self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz).minute*60 + \
                        self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz).second
                end = self.convert_utc_time_to_tz(self.real_end, self.employee_id.tz).hour*3600 + \
                      self.convert_utc_time_to_tz(self.real_end, self.employee_id.tz).minute*60 + \
                      self.convert_utc_time_to_tz(self.real_end, self.employee_id.tz).second

                consider_hour_extra_from = self._get_consider_hour_extra_from('FJ')

                if end < start:
                    # Salto de dia
                    first_part = self._get_amount_by_hour_extra(start, 24*3600, is_holiday)
                    second_part = self._get_amount_by_hour_extra(0, end, is_holiday)

                    if first_part.get('sum', 0) + second_part.get('sum', 0) >= consider_hour_extra_from*60:
                        for k in first_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + first_part.get(k, 0)
                            else:
                                global_result[k] = + first_part.get(k, 0)

                        for k in second_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + second_part.get(k, 0)
                            else:
                                global_result[k] = + second_part.get(k, 0)
                else:
                    only_part = self._get_amount_by_hour_extra(start, end, is_holiday)
                    if only_part.get('sum', 0) >= consider_hour_extra_from * 60:
                        for k in only_part.keys():
                            if k in global_result:
                                global_result[k] = global_result.get(k, 0) + only_part.get(k, 0)
                            else:
                                global_result[k] = + only_part.get(k, 0)

        consider_HE_ID = self._get_consider_hour_extra('ID')
        consider_HE_FD = self._get_consider_hour_extra('FD')

        consider_HE_ID_from = self._get_consider_hour_extra_from('ID')
        consider_HE_FD_from = self._get_consider_hour_extra_from('FD')
        for b in self.break_ids:
            if consider_HE_ID:
                # Se considera sobretiempo al inicio del descanso
                if b.difference_total_seconds_start > 0:
                    start = self.convert_utc_time_to_tz(b.planned_start, self.employee_id.tz).hour * 3600 + \
                            self.convert_utc_time_to_tz(b.planned_start, self.employee_id.tz).minute * 60 + \
                            self.convert_utc_time_to_tz(b.planned_start, self.employee_id.tz).second
                    end = self.convert_utc_time_to_tz(b.real_start, self.employee_id.tz).hour * 3600 + \
                          self.convert_utc_time_to_tz(b.real_start, self.employee_id.tz).minute * 60 + \
                          self.convert_utc_time_to_tz(b.real_start, self.employee_id.tz).second

                    if start > end:
                        # Salto de dia
                        first_part = self._get_amount_by_hour_extra(start, 24*3600, is_holiday)
                        second_part = self._get_amount_by_hour_extra(0, end, is_holiday)
                        if first_part.get('sum', 0) + second_part.get('sum', 0) >= consider_HE_ID_from * 60:

                            for k in first_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + first_part.get(k, 0)
                                else:
                                    global_result[k] = + first_part.get(k, 0)

                            for k in second_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + second_part.get(k, 0)
                                else:
                                    global_result[k] = + second_part.get(k, 0)
                    else:
                        only_part = self._get_amount_by_hour_extra(start, end, is_holiday)
                        if only_part.get('sum', 0) >= consider_HE_ID_from * 60:
                            for k in only_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + only_part.get(k, 0)
                                else:
                                    global_result[k] = + only_part.get(k, 0)

            if consider_HE_FD:
                # Se considera sobretiempo al finalizar el descanso
                if b.difference_total_seconds_end > 0:
                    start = b.real_end.hour * 3600 + b.real_end.minute * 60 + b.real_end.second
                    end = b.planned_end.hour * 3600 + b.planned_end.minute * 60 + b.planned_end.second

                    if start > end:
                        # Salto de dia
                        first_part = self._get_amount_by_hour_extra(start, 24*3600, is_holiday)
                        second_part = self._get_amount_by_hour_extra(0, end, is_holiday)
                        if first_part.get('sum', 0) + second_part.get('sum', 0) >= consider_HE_FD_from * 60:

                            for k in first_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + first_part.get(k, 0)
                                else:
                                    global_result[k] = + first_part.get(k, 0)

                            for k in second_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + second_part.get(k, 0)
                                else:
                                    global_result[k] = + second_part.get(k, 0)
                    else:
                        only_part = self._get_amount_by_hour_extra(start, end, is_holiday)
                        if only_part.get('sum', 0) >= consider_HE_FD_from * 60:
                            for k in only_part.keys():
                                if k in global_result:
                                    global_result[k] = global_result.get(k, 0) + only_part.get(k, 0)
                                else:
                                    global_result[k] = + only_part.get(k, 0)

        return global_result

    def _get_amount_hour_night_id(self, date):
        global_result = dict()

        is_holiday = False
        holidays = self.env['hr.holiday'].search_count([
            ('date', '=', date)
        ])
        if holidays > 0:
            is_holiday = True

        if not is_holiday:
            if self.resource_calendar_id.consider_hour_night:
                if self.real_start and self.real_end:
                    # Hay inicio y fin de marcacion
                    if self.difference_total_seconds_start > 0:
                        date_start = self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz)
                    else:
                        date_start = self.convert_utc_time_to_tz(self.real_start, self.employee_id.tz)

                    if self.difference_total_seconds_end > 0:
                        date_end = self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz)
                    else:
                        date_end = self.convert_utc_time_to_tz(self.real_end, self.employee_id.tz)

                    start = date_start.hour * 3600 + date_start.minute * 60 + date_start.second
                    end = date_end.hour * 3600 + date_end.minute * 60 + date_end.second
                elif self.real_start:
                    # Solo hay la marcacion de inicio
                    if self.difference_total_seconds_start > 0:
                        date_start = self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz)
                    else:
                        date_start = self.convert_utc_time_to_tz(self.real_start, self.employee_id.tz)

                    date_end = self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz)

                    start = date_start.hour * 3600 + date_start.minute * 60 + date_start.second
                    end = date_end.hour * 3600 + date_end.minute * 60 + date_end.second
                elif self.real_end:
                    # Solo hay la marcacion de fin
                    date_start = self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz)

                    if self.difference_total_seconds_end > 0:
                        date_end = self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz)
                    else:
                        date_end = self.convert_utc_time_to_tz(self.real_end, self.employee_id.tz)

                    start = date_start.hour * 3600 + date_start.minute * 60 + date_start.second
                    end = date_end.hour * 3600 + date_end.minute * 60 + date_end.second
                else:
                    # No hay marcacion ni de inicio ni de fin
                    date_start = self.convert_utc_time_to_tz(self.planned_start, self.employee_id.tz)
                    date_end = self.convert_utc_time_to_tz(self.planned_end, self.employee_id.tz)

                    start = date_start.hour * 3600 + date_start.minute * 60 + date_start.second
                    end = date_end.hour * 3600 + date_end.minute * 60 + date_end.second

                if start > end:
                    # Salto de dia
                    first_part = self._get_amount_by_hour_night(start, 24 * 3600)
                    second_part = self._get_amount_by_hour_night(0, end)

                    for k in first_part.keys():
                        if k in global_result:
                            global_result[k] = global_result.get(k, 0) + first_part.get(k, 0)
                        else:
                            global_result[k] = + first_part.get(k, 0)

                    for k in second_part.keys():
                        if k in global_result:
                            global_result[k] = global_result.get(k, 0) + second_part.get(k, 0)
                        else:
                            global_result[k] = + second_part.get(k, 0)
                else:
                    only_part = self._get_amount_by_hour_night(start, end)

                    for k in only_part.keys():
                        if k in global_result:
                            global_result[k] = global_result.get(k, 0) + only_part.get(k, 0)
                        else:
                            global_result[k] = + only_part.get(k, 0)

        return global_result

    def _get_amount_by_hour_extra(self, start, end, is_holiday, employee=None):
        result = dict()

        employee_id = employee or self.employee_id

        is_holiday = not is_holiday
        hr_hour_extra = self.env['hr.hour.extra'].search([
            ('assigned_schedule', '=', is_holiday),
            ('active', '=', True),
        ])

        for he in hr_hour_extra:
            apply = False
            for normative_id in he.normative_ids:
                if normative_id == employee_id.normative_id:
                    apply = True
                    break
            if apply:
                if start >= he.start * 3600 and start <= he.end * 3600 \
                        and end >= he.start * 3600 and end <= he.end * 3600:
                    # Inicio y fin del rango pasado esta dentro de este tipo de hora extra
                    if he.id in result:
                        result[he.id] = result.get(he.id, 0) + (end-start)
                    else:
                        result[he.id] = (end-start)
                    break

                elif start >= he.start * 3600 and start <= he.end * 3600:
                    # Inicio del rango pasado esta dentro de este tipo de hora extra
                    if he.id in result:
                        result[he.id] = result.get(he.id, 0) + (he.end-start)
                    else:
                        result[he.id] = (he.end-start)

                elif end >= he.start * 3600 and end <= he.end * 3600:
                    # Fin del rango pasado esta dentro de este tipo de hora extra
                    if he.id in result:
                        result[he.id] = result.get(he.id, 0) + (end-he.start)
                    else:
                        result[he.id] = (end-he.start)

        sum = 0
        for k in result.keys():
            sum += result.get(k, 0)
        result['sum'] = sum

        return result

    def _get_amount_by_hour_night(self, start, end):
        result = dict()

        hr_hour_night = self.env['hr.hour.night'].search([
            ('active', '=', True),
        ])

        for hn in hr_hour_night:

            apply = False
            for normative_id in hn.normative_ids:
                if normative_id == self.employee_id.normative_id:
                    apply = True
                    break

            if apply:
                if hn.start < hn.end:

                    if start >= hn.start*3600 and start <= hn.end*3600 and end >= hn.start*3600 and end <= hn.end*3600:
                        # Inicio y fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end-start)
                        else:
                            result[hn.id] = (end-start)
                        break
                    elif start >= hn.start*3600 and start <= hn.end*3600:
                        # Inicio del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (hn.end*3600-start)
                        else:
                            result[hn.id] = (hn.end*3600-start)
                    elif end >= hn.start*3600 and end <= hn.end*3600:
                        # Fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end-hn.start*3600)
                        else:
                            result[hn.id] = (end-hn.start*3600)

                else:
                    # La configuracion de la hora nocturna en si tiene salto de dia
                    hn_firts_part_i = hn.start * 3600
                    hn_firts_part_f = 24 * 3600

                    if start >= hn_firts_part_i and start <= hn_firts_part_f and end >= hn_firts_part_i and end <= hn_firts_part_f:
                        # Inicio y fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end - start)
                        else:
                            result[hn.id] = (end - start)
                        break
                    elif start >= hn_firts_part_i and start <= hn_firts_part_f:
                        # Inicio del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (hn_firts_part_f - start)
                        else:
                            result[hn.id] = (hn_firts_part_f - start)
                    elif end >= hn_firts_part_i and end <= hn_firts_part_f:
                        # Fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end - hn_firts_part_i)
                        else:
                            result[hn.id] = (end - hn_firts_part_i)


                    hn_second_part_i = 0
                    hn_second_part_f = hn.end * 3600

                    if start >= hn_second_part_i and start <= hn_second_part_f and end >= hn_second_part_i and end <= hn_second_part_f:
                        # Inicio y fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end - start)
                        else:
                            result[hn.id] = (end - start)
                        break
                    elif start >= hn_second_part_i and start <= hn_second_part_f:
                        # Inicio del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (hn_second_part_f - start)
                        else:
                            result[hn.id] = (hn_second_part_f - start)
                    elif end >= hn_second_part_i and end <= hn_second_part_f:
                        # Fin del rango pasado esta dentro de este tipo de hora nocturna
                        if hn.id in result:
                            result[hn.id] = result.get(hn.id, 0) + (end - hn_second_part_i)
                        else:
                            result[hn.id] = (end - hn_second_part_i)

        sum = 0
        for k in result.keys():
            sum += result.get(k, 0)
        result['sum'] = sum

        return result

    def convert_time_to_utc(self, dt, tz_name=None):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

        @return: an instance of datetime object
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise ValidationError(
                _("La zona horaria local no está definida. "
                  "Es posible que deba establecer una zona horaria en el colaborador "
                  "o en las preferencias de su usuario."))
        local = pytz.timezone(tz_name)
        local_dt = local.localize(dt, is_dst=None)
        return local_dt.astimezone(pytz.utc)

    def _cron_compute_attendance(self):
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])
        ])

        today = datetime.utcnow().date()
        today = today - relativedelta(days=1)
        attendance_period = self.env['hr.attendance.period'].search([
            ('state', '=', 'open'),
            ('start', '<=', today),
            ('end', '>=', today),
        ], limit=1)
        for employee in employees:
            if attendance_period:
                date_from = attendance_period.start
                while date_from <= attendance_period.end:
                    date_i = date_from + relativedelta(hour=0, minute=0, second=0)
                    date_f = date_from + relativedelta(hour=23, minute=59, second=59)

                    date_i = self.convert_time_to_utc(date_i, employee.tz)
                    date_f = self.convert_time_to_utc(date_f, employee.tz)

                    employee_shift = self.env['hr.employee.shift'].search([
                        ('employee_id', '=', employee.id),
                        ('planned_start', '>=', date_i),
                        ('planned_start', '<=', date_f)
                    ])
                    if len(employee_shift) == 0:
                        # Buscar rangos de timbradas para ese día y poner la hora extra para días sin horario
                        self.env['hr.employee.shift'].create_hour_extra_day_not_shift(employee, attendance_period,
                                                                                      date_from, date_i, date_f, True)
                    else:
                        for es in employee_shift:
                            if not es.attendance_computed:
                                es.compute_attendance(date_from, attendance_period, True)

                    date_from = date_from + relativedelta(days=1)

    def _get_percentage_penalty(self, mode):
        if mode == 'IJ':
            acronym = 'PPIJEM'
        elif mode == 'FJ':
            acronym = 'PPFJEM'
        elif mode == 'ID':
            acronym = 'PPIDEM'
        elif mode == 'FD':
            acronym = 'PPFDEM'

        module = self.env.ref('base.module_' + self._module)

        percentage = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if percentage:
            percentage = percentage.float_value
            return percentage
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. "
                    "Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, "
                    "Módulo del nomenclador: {}, Siglas del nomenclador: {}.").format(
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def _get_consider_hour_extra(self, mode):
        if mode == 'ID':
            acronym = 'CHEAIDD'
        elif mode == 'FD':
            acronym = 'CHEAFED'
        elif mode == 'IJ':
            acronym = 'CHEAIDLJ'
        elif mode == 'FJ':
            acronym = 'CHEAFLJ'
        module = self.env.ref('base.module_' + self._module)

        result = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if result:
            result = result.boolean_value
            return result
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, Módulo del nomenclador: {}, Siglas del nomenclador: {}.").format
                    (
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def get_consider_plus_overtime_in_break_as_tt(self):
        acronym = 'CSPEDCTT'
        module = self.env.ref('base.module_' + self._module)

        result = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if result:
            result = result.boolean_value
            return result
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, Módulo del nomenclador: {}, Siglas del nomenclador: {}.").format
                    (
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def _get_consider_negative_overtime_in_break_as_tnt(self):
        acronym = 'CSNEDCTNT'
        module = self.env.ref('base.module_' + self._module)

        result = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if result:
            result = result.boolean_value
            return result
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, Módulo del nomenclador: {}, Siglas del nomenclador: {}.").format
                    (
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def _get_consider_hour_extra_from(self, mode):
        if mode == 'ID':
            acronym = 'CHEAIDDAPD'
        elif mode == 'FD':
            acronym = 'CHEAFEDAPD'
        elif mode == 'IJ':
            acronym = 'CHEAIDLJAPD'
        elif mode == 'FJ':
            acronym = 'CHEAFLJAPD'
        module = self.env.ref('base.module_' + self._module)

        result = self.env['hr.normative.nomenclature'].search([
            ('normative_id', '=', self.employee_id.normative_id.id),
            ('nomenclature_id.module_id', '=', module.id),
            ('nomenclature_id.acronym', '=', acronym),
            ('current', '=', True)
        ], limit=1)
        if result:
            result = result.integer_value
            return result
        else:
            raise ValidationError(
                _(
                    "Error de configuración, comuníquese con el administrador. Regulación asignada al colaborador: {}. Debe existir una combinación vigente para 'hr.normative.nomenclature' --> Regulación: {}, Módulo del nomenclador: {}, Siglas del nomenclador: {}.").format
                    (
                    self.employee_id.normative_id.name,
                    self.employee_id.normative_id.name,
                    module.display_name,
                    acronym
                )
            )

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    def any_attendance_not_assigned(self, type):
        attendance_ids = self.env['user.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('timestamp', '>=', self.start_from),
            ('timestamp', '<=', self.end_to),
            ('status', '=', type)
        ], order="timestamp asc")

        for a in attendance_ids:
            if not a.assigned:
                return True
        return False

    def _some_break_without_attendance_start(self):
        for b in self.break_ids:
            if not b.real_start:
                return True
        return False

    def _some_break_without_attendance_end(self):
        for b in self.break_ids:
            if not b.real_end:
                return True
        return False

    def assign_attendance(self, mode):
        # Obtener el modo de asignación de marcaciones
        # ('1', 'Una tecla de función por tipo de evento')
        # ('2', 'Una tecla de función por actividad')
        # ('3', 'Sin tecla de función')
        # Solo se implementará para el 1. A futuro se implementarán en 2 y el 3

        # mode
        # 1 Cron
        # 2 Acción de usuario

        attendance_mode = self.env['ir.config_parameter'].sudo().get_param('attendance.mode', '')
        if attendance_mode == '':
            if mode == 1:
                message = "ERROR: Función: assign_attendance(). " \
                          "Debe definir el algoritmo de asignación de marcación en la configuración " \
                          "del módulo de asistencia."
                _logger.error(message)
            else:
                raise UserError(_(
                    'Debe definir el algoritmo de asignación de marcación en la configuración '
                    'del módulo de asistencia.'))
        else:
            self.real_start = False
            self.real_end = False
            for b in self.break_ids:
                b.real_start = False
                b.real_end = False

        if attendance_mode == '1':
            # Marcación de inicio
            real_start = self.env['user.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('timestamp', '>=', self.start_from),
                ('timestamp', '<=', self.end_to),
                ('status', '=', 0)
            ], order="timestamp asc", limit=1)
            self.env.cr.execute("""
                            update user_attendance
                            set assigned = False
                            where employee_id=%s and timestamp >= %s and timestamp <= %s and status = 0
                            """, (self.employee_id.id, self.start_from, self.end_to)
                                )
            if real_start:
                self.real_start = real_start.timestamp
                real_start.assigned = True

            # Marcación de fin
            real_end = self.env['user.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('timestamp', '>=', self.start_from),
                ('timestamp', '<=', self.end_to),
                ('status', '=', 1)
            ], order="timestamp desc", limit=1)
            self.env.cr.execute("""
                            update user_attendance
                            set assigned = False
                            where employee_id=%s and timestamp >= %s and timestamp <= %s and status = 1
                            """, (self.employee_id.id, self.start_from, self.end_to)
                                )
            if real_end:
                self.real_end = real_end.timestamp
                real_end.assigned = True

            # Marcación de inicio de descanso
            user_attendance_start_break_ids = self.env['user.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('timestamp', '>=', self.start_from),
                ('timestamp', '<=', self.end_to),
                ('status', '=', 2)
            ], order="timestamp asc")
            self.env.cr.execute("""
                            update user_attendance
                            set assigned = False
                            where employee_id=%s and timestamp >= %s and timestamp <= %s and status = 2
                            """, (self.employee_id.id, self.start_from, self.end_to)
                                )

            while self.any_attendance_not_assigned(2) and self._some_break_without_attendance_start():
                difference_start = math.inf
                user_attendance_start_break = False
                start_break = False

                for b in self.break_ids:
                    if b.real_start:
                        continue
                    planned_start_break = b.planned_start
                    for ua_sb in user_attendance_start_break_ids:
                        if difference_start > abs((planned_start_break - ua_sb.timestamp).total_seconds()):
                            difference_start = abs((planned_start_break - ua_sb.timestamp).total_seconds())
                            user_attendance_start_break = ua_sb
                            start_break = b

                if start_break and user_attendance_start_break:
                    start_break.real_start = user_attendance_start_break.timestamp
                    user_attendance_start_break.assigned = True

            # Marcación de fin de descanso
            user_attendance_end_break_ids = self.env['user.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('timestamp', '>=', self.start_from),
                ('timestamp', '<=', self.end_to),
                ('status', '=', 3)
            ], order="timestamp asc")
            self.env.cr.execute("""
                            update user_attendance
                            set assigned = False
                            where employee_id=%s and timestamp >= %s and timestamp <= %s and status = 3
                            """, (self.employee_id.id, self.start_from, self.end_to)
                                )

            while self.any_attendance_not_assigned(3) and self._some_break_without_attendance_end():
                difference_end = math.inf
                user_attendance_end_break = False
                end_break = False

                for b in self.break_ids:
                    if b.real_end:
                        continue
                    planned_end_break = b.planned_end
                    for ua_eb in user_attendance_end_break_ids:
                        if difference_end > abs((planned_end_break - ua_eb.timestamp).total_seconds()):
                            difference_end = abs((planned_end_break - ua_eb.timestamp).total_seconds())
                            user_attendance_end_break = ua_eb
                            end_break = b

                if end_break and user_attendance_end_break:
                    end_break.real_end = user_attendance_end_break.timestamp
                    user_attendance_end_break.assigned = True

            self.attendance_assigned = True
            self.attendance_computed = False
        elif attendance_mode == '2':
            if mode == 1:
                message = "No definido."
                _logger.error(message)
            else:
                raise UserError(_('No definido'))
        elif attendance_mode == '3':
            if mode == 1:
                message = "No definido."
                _logger.error(message)
            else:
                raise UserError(_('No definido'))

    def _cron_assign_attendance(self):
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])
        ])
        today = datetime.utcnow().date()
        today = today - relativedelta(days=1)
        attendance_period = self.env['hr.attendance.period'].search([
            ('state', '=', 'open'),
            ('start', '<=', today),
            ('end', '>=', today),
        ], limit=1)
        if attendance_period:
            for employee in employees:
                if attendance_period:
                    date_from = attendance_period.start
                    while date_from <= attendance_period.end:

                        date_i = date_from + relativedelta(hour=0, minute=0, second=0)
                        date_f = date_from + relativedelta(hour=23, minute=59, second=59)

                        date_i = self.convert_time_to_utc(date_i, employee.tz)
                        date_f = self.convert_time_to_utc(date_f, employee.tz)

                        employee_shift = self.env['hr.employee.shift'].search([
                            ('employee_id', '=', employee.id),
                            ('planned_start', '>=', date_i),
                            ('planned_start', '<=', date_f)
                        ])
                        for es in employee_shift:
                            if not es.attendance_assigned:
                                es.assign_attendance(1)

                        date_from = date_from + relativedelta(days=1)
    
    def name_get(self):
        result = []
        for employeeShift in self:
            planned_start = self.convert_utc_time_to_tz(employeeShift.planned_start,
                                                        employeeShift.employee_id.tz).strftime("%H:%M:%S")
            planned_end = self.convert_utc_time_to_tz(employeeShift.planned_end,
                                                      employeeShift.employee_id.tz).strftime("%H:%M:%S")
            result.append(
                (
                    employeeShift.id,
                    _("{} {} - {}").format(employeeShift.employee_id.name, planned_start, planned_end)

                )
            )
        return result

    def get_total_seconds_planned(self):
        if self.planned_start and self.planned_end:
            total_seconds = (self.planned_end - self.planned_start).total_seconds()

            for shiftBreak in self.break_ids:
                total_seconds -= shiftBreak.time_planned

            return total_seconds
        return 0

    @api.depends('planned_start', 'planned_end', 'real_start', 'real_end', 'break_ids')
    def _compute_shift(self):
        for shift in self:
            if shift.planned_start and shift.planned_end:
                total_seconds = shift.get_total_seconds_planned()
                shift.time_planned = total_seconds
                result = Util.seconds2hms(total_seconds)
                shift.time_planned_hms = result['c']
            else:
                shift.time_planned = 0
                shift.time_planned_hms = '00:00:00'

            if shift.real_start and shift.real_end:
                total_seconds = (shift.real_end - shift.real_start).total_seconds()

                for shiftBreak in shift.break_ids:

                    difference = shiftBreak.time_planned - shiftBreak.time_real
                    if difference > 0:
                        # Ocupó en el descanso menos tiempo del planificado
                        if shift.get_consider_plus_overtime_in_break_as_tt():
                            total_seconds -= shiftBreak.time_real
                        else:
                            total_seconds -= shiftBreak.time_planned
                    else:
                        # Ocupó en el descanso mas tiempo del planificado
                        if shift.get_consider_negative_overtime_in_break_as_TNT():
                            total_seconds -= shiftBreak.time_real
                        else:
                            total_seconds -= shiftBreak.time_planned

                shift.time_real = total_seconds
                result = Util.seconds2hms(total_seconds)
                shift.time_real_hms = result['c']
            else:
                if self.planned_end and self.planned_start:
                    total_seconds = (self.planned_end - self.planned_start).total_seconds()

                    if shift.difference_total_seconds_start < 0:
                        total_seconds -= abs(shift.difference_total_seconds_start)
                    else:
                        total_seconds += abs(shift.difference_total_seconds_start)

                    if shift.difference_total_seconds_end < 0:
                        total_seconds -= abs(shift.difference_total_seconds_end)
                    else:
                        total_seconds += abs(shift.difference_total_seconds_end)

                    for shiftBreak in shift.break_ids:
                        total_seconds -= shiftBreak.time_real

                    shift.time_real = total_seconds
                    result = Util.seconds2hms(total_seconds)
                    shift.time_real_hms = result['c']
                else:
                    shift.time_real_hms = '00:00:00'

            shift.difference_total = shift.difference_total_seconds_start + shift.difference_total_seconds_end
            result = Util.seconds2hms(shift.difference_total_seconds_start + shift.difference_total_seconds_end)
            shift.difference_total_hms = result['c']

    @api.depends('break_ids')
    def _compute_break(self):
        for turn in self:
            turn.breaks_count = len(turn.break_ids)

            total_time_planned = 0
            total_time_real = 0
            total_time_difference = 0
            total_early_start = 0
            total_late_end = 0
            for descanso in turn.break_ids:
                total_time_planned += descanso.time_planned
                total_time_real += descanso.time_real
                total_time_difference += (descanso.difference_total_seconds_end + 
                                          descanso.difference_total_seconds_start)

                if descanso.difference_total_seconds_start < 0:
                    total_early_start += 1

                if descanso.difference_total_seconds_end < 0:
                    total_late_end += 1

            turn.breaks_total_time_planned = total_time_planned
            result = Util.seconds2hms(total_time_planned)
            turn.breaks_total_time_planned_hms = result['c']

            turn.breaks_total_time_real = total_time_real
            result = Util.seconds2hms(total_time_real)
            turn.breaks_total_time_real_hms = result['c']

            turn.breaks_total_time_difference = total_time_difference
            result = Util.seconds2hms(total_time_difference)
            turn.breaks_total_time_difference_hms = result['c']

            turn.breaks_early_start_count = total_early_start
            turn.breaks_late_end_count = total_late_end

    @api.depends('planned_start')
    def _compute_year_planned_start(self):
        for turn in self:
            if turn.planned_start:
                turn.year_planned_start = str(turn.planned_start.year)

    @api.depends('planned_start', 'planned_end', 'break_ids', 'real_start')
    def _compute_start(self):
        for turn in self:
            if turn.planned_start:
                if turn.real_start:
                    difference = turn.planned_start - turn.real_start
                    total_seconds = difference.total_seconds()
                    turn.difference_total_seconds_start = total_seconds
                    if total_seconds < 0:
                        if abs(total_seconds) > turn.courtesy_start * 60:
                            turn.late_start = True
                        else:
                            turn.late_start = False
                    else:
                        turn.late_start = False

                    result = Util.seconds2hms(total_seconds)
                    turn.difference_hour_start = result['h']
                    turn.difference_minute_start = result['m']
                    turn.difference_second_start = result['s']
                    turn.difference_start = result['c']
                else:
                    percentage = turn._get_percentage_penalty('IJ')
                    total_seconds = (-1) * turn.get_total_seconds_planned() * percentage / 100
                    turn.difference_total_seconds_start = total_seconds
                    if total_seconds < 0:
                        if abs(total_seconds) > turn.courtesy_start * 60:
                            turn.late_start = True
                        else:
                            turn.late_start = False
                    else:
                        turn.late_start = False

                    result = Util.seconds2hms(total_seconds)
                    turn.difference_hour_start = result['h']
                    turn.difference_minute_start = result['m']
                    turn.difference_second_start = result['s']
                    turn.difference_start = result['c']
            else:
                turn.late_start = False
                turn.difference_hour_start = '00'
                turn.difference_minute_start = '00'
                turn.difference_second_start = '00'
                turn.difference_start = '00:00:00'
                turn.difference_total_seconds_start = -1

    @api.depends('planned_start', 'planned_end', 'break_ids', 'real_end')
    def _compute_end(self):
        for turn in self:
            if turn.planned_end:
                if turn.real_end:
                    difference = turn.real_end - turn.planned_end
                    total_seconds = difference.total_seconds()
                    turn.difference_total_seconds_end = total_seconds
                    if total_seconds < 0:
                        if abs(total_seconds) > turn.courtesy_end * 60:
                            turn.early_end = True
                        else:
                            turn.early_end = False
                    else:
                        turn.early_end = False

                    result = Util.seconds2hms(total_seconds)
                    turn.difference_hour_end = result['h']
                    turn.difference_minute_end = result['m']
                    turn.difference_second_end = result['s']
                    turn.difference_end = result['c']
                else:
                    percentage = turn._get_percentage_penalty('FJ')
                    total_seconds = (-1) * turn.get_total_seconds_planned() * percentage / 100
                    turn.difference_total_seconds_end = total_seconds
                    if total_seconds < 0:
                        if abs(total_seconds) > turn.courtesy_end * 60:
                            turn.early_end = True
                        else:
                            turn.early_end = False
                    else:
                        turn.early_end = False

                    result = Util.seconds2hms(total_seconds)
                    turn.difference_hour_end = result['h']
                    turn.difference_minute_end = result['m']
                    turn.difference_second_end = result['s']
                    turn.difference_end = result['c']
            else:
                turn.early_end = False
                turn.difference_hour_end = '00'
                turn.difference_minute_end = '00'
                turn.difference_second_end = '00'
                turn.difference_end = '00:00:00'
                turn.difference_total_seconds_end = -1

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.department_employee_id = rec.sudo().employee_id.department_id

    @api.onchange('planned_start')
    def _onchange_planned_start(self):
        for rec in self:
            if rec.planned_start and rec.resource_calendar_id:
                rec.start_from = rec.planned_start - timedelta(hours=rec.resource_calendar_id.max_hours_before_start)
                rec.dayofweek = str(rec.planned_start.weekday())

    @api.onchange('planned_end')
    def _onchange_planned_end(self):
        for rec in self:
            if rec.planned_end and rec.resource_calendar_id:
                rec.end_to = rec.planned_end + timedelta(hours=rec.resource_calendar_id.max_hours_after_end)

    @api.onchange('resource_calendar_id')
    def _onchange_resource_calendar_id(self):
        for rec in self:
            rec.courtesy_start = rec.resource_calendar_id.courtesy_start
            rec.courtesy_end = rec.resource_calendar_id.courtesy_end
            if rec.planned_start:
                rec.start_from = rec.planned_start - timedelta(hours=rec.resource_calendar_id.max_hours_before_start)
            if rec.planned_end:
                rec.end_to = rec.planned_end + timedelta(hours=rec.resource_calendar_id.max_hours_after_end)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeShift, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        # Adiciono al filtro 'Último periodo' el dominio, limitando el inicio planificado al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)
            if last_period.id:
                start = last_period.start

                # Selecciono el día siguiente para que al comparar y incluya el día final
                end = (datetime.combine(last_period.end, datetime.min.time()) + relativedelta(days=1)).date()

                doc = etree.XML(res['arch'])
                for node in doc.xpath("//filter[@name='filter_last_period']"):
                    node.set('domain', "[('planned_start', '>=', '{}'),('planned_start', '<', '{}')]"
                             .format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

                res['arch'] = etree.tostring(doc)
        return res

    attendance_assigned = fields.Boolean(string='Asistencia asignada', default=False, tracking=True)
    attendance_computed = fields.Boolean(string='Asistencia calculada', default=False, tracking=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string="Horario", required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, default=_default_employee,
                                  tracking=True, ondelete='cascade')
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador", related='employee_id.user_id',
                                       store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador",
        related='employee_id.department_id.manager_id.user_id', store=True)

    break_ids = fields.One2many('hr.employee.shift.break', 'employee_shift_id', string="Descansos")
    breaks_count = fields.Integer(string='Total descansos', readonly=True, compute=_compute_break)
    breaks_early_start_count = fields.Integer(string='Total inicio antes', readonly=True, compute=_compute_break)
    breaks_late_end_count = fields.Integer(string='Total fin después', readonly=True, compute=_compute_break)
    breaks_total_time_planned = fields.Integer(string='Tiempo total planificado descansos',
                                               readonly=True, compute=_compute_break)
    breaks_total_time_planned_hms = fields.Char(string='Tiempo total planificado descansos',
                                                readonly=True, compute=_compute_break)
    breaks_total_time_real = fields.Integer(string='Tiempo total real descansos', readonly=True,
                                            compute=_compute_break)
    breaks_total_time_real_hms = fields.Char(string='Tiempo total real descansos', readonly=True,
                                             compute=_compute_break)
    breaks_total_time_difference = fields.Integer(string='Tiempo total diferencia descansos', readonly=True,
                                                  compute=_compute_break)
    breaks_total_time_difference_hms = fields.Char(string='Tiempo total diferencia descansos', readonly=True,
                                                   compute=_compute_break)

    planned_start = fields.Datetime('Inicio planificado', required=True, tracking=True)
    year_planned_start = fields.Char(string='Año', readonly=True,
                                     compute=_compute_year_planned_start, store=True)
    dayofweek = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo')
    ], 'Día de la semana', required=True, index=True, default='0', tracking=True)
    real_start = fields.Datetime('Inicio real', tracking=True)
    courtesy_start = fields.Float(string='Cortesía al inicio', digits='Schedule', tracking=True)
    start_from = fields.Datetime('Inicio desde', help="Puede registrar una marcación desde.", tracking=True)

    difference_total_seconds_start = fields.Integer(string='Diferencia total al inicio', readonly=True,
                                                    compute=_compute_start)
    difference_hour_start = fields.Integer(string='Diferencia en hora al inicio', readonly=True,
                                           compute=_compute_start)
    difference_minute_start = fields.Integer(string='Diferencia en minuto al inicio', readonly=True,
                                             compute=_compute_start)
    difference_second_start = fields.Integer(string='Diferencia en segundo al inicio', readonly=True,
                                             compute=_compute_start)
    late_start = fields.Boolean(string='Inicio tarde', readonly=True, compute=_compute_start)
    difference_start = fields.Char(string='Diferencia al inicio', readonly=True, compute=_compute_start)

    planned_end = fields.Datetime('Fin planificado', required=True, tracking=True)
    real_end = fields.Datetime('Fin real', tracking=True)
    courtesy_end = fields.Float(string='Cortesía al fin', digits='Schedule', tracking=True)
    end_to = fields.Datetime('Fin hasta', help="Puede registrar una marcación hasta.", tracking=True)

    difference_total_seconds_end = fields.Integer(string='Diferencia total al fin', readonly=True, compute=_compute_end)
    difference_hour_end = fields.Integer(string='Diferencia en hora al fin', readonly=True, compute=_compute_end)
    difference_minute_end = fields.Integer(string='Diferencia en minuto al fin', readonly=True, compute=_compute_end)
    difference_second_end = fields.Integer(string='Diferencia en segundo al fin', readonly=True, compute=_compute_end)
    early_end = fields.Boolean(string='Fin temprano', readonly=True, compute=_compute_end)
    difference_end = fields.Char(string='Diferencia al fin', readonly=True, compute=_compute_end)

    time_planned = fields.Integer(string='Tiempo planificado', readonly=True, compute=_compute_shift)
    time_planned_hms = fields.Char(string='Tiempo planificado', readonly=True, compute=_compute_shift)
    time_real = fields.Integer(string='Tiempo real', readonly=True, compute=_compute_shift)
    time_real_hms = fields.Char(string='Tiempo real', readonly=True, compute=_compute_shift)
    difference_total = fields.Integer(string='Diferencia total', readonly=True, compute=_compute_shift)
    difference_total_hms = fields.Char(string='Diferencia total', readonly=True, compute=_compute_shift)


class EmployeeShiftBreak(models.Model):
    _name = "hr.employee.shift.break"
    _description = 'Employee shift break'
    _inherit = ['mail.thread']
    _order = "employee_shift_id, planned_start"

    @api.depends('planned_start', 'real_start')
    def _compute_start(self):
        for shiftBreak in self:
            if shiftBreak.planned_start:
                if shiftBreak.real_start:
                    difference = shiftBreak.real_start - shiftBreak.planned_start
                    total_seconds = difference.total_seconds()
                    shiftBreak.difference_total_seconds_start = total_seconds
                    if total_seconds < 0:
                        shiftBreak.early_start = True
                    else:
                        shiftBreak.early_start = False

                    result = Util.seconds2hms(total_seconds)
                    shiftBreak.difference_hour_start = result['h']
                    shiftBreak.difference_minute_start = result['m']
                    shiftBreak.difference_second_start = result['s']
                    shiftBreak.difference_start = result['c']
                else:
                    percentage = shiftBreak.employee_shift_id._get_percentage_penalty('ID')
                    # Asegurando un valor para 'total_seconds_planned' cuando no se han llenado los campos planned_start
                    # y planned_end.
                    total_seconds_planned = shiftBreak.get_total_seconds_planned()
                    if total_seconds_planned is None:
                        total_seconds_planned = 0

                    total_seconds = (-1) * (total_seconds_planned) * percentage / 100

                    shiftBreak.difference_total_seconds_start = total_seconds
                    if total_seconds < 0:
                        shiftBreak.early_start = True
                    else:
                        shiftBreak.early_start = False

                    result = Util.seconds2hms(total_seconds)
                    shiftBreak.difference_hour_start = result['h']
                    shiftBreak.difference_minute_start = result['m']
                    shiftBreak.difference_second_start = result['s']
                    shiftBreak.difference_start = result['c']
            else:
                shiftBreak.difference_total_seconds_start = -1
                shiftBreak.difference_hour_start = '00'
                shiftBreak.difference_minute_start = '00'
                shiftBreak.difference_second_start = '00'
                shiftBreak.difference_start = '00:00:00'
                shiftBreak.early_start = False

    def get_total_seconds_planned(self):
        if self.planned_start and self.planned_end:
            total_seconds = (self.planned_end - self.planned_start).total_seconds()
            return total_seconds
        else:
            return 0

    @api.depends('planned_start', 'planned_end', 'real_start', 'real_end')
    def _compute_break(self):
        for shiftBreak in self:
            if shiftBreak.planned_start and shiftBreak.planned_end:
                total_seconds = shiftBreak.get_total_seconds_planned()
                shiftBreak.time_planned = total_seconds
                result = Util.seconds2hms(total_seconds)
                shiftBreak.time_planned_hms = result['c']
            else:
                shiftBreak.time_planned = 0
                shiftBreak.time_planned_hms = '00:00:00'

            if shiftBreak.real_start and shiftBreak.real_end:
                total_seconds = (shiftBreak.real_end - shiftBreak.real_start).total_seconds()
                shiftBreak.time_real = total_seconds
                result = Util.seconds2hms(total_seconds)
                shiftBreak.time_real_hms = result['c']
            else:
                total_seconds = shiftBreak.get_total_seconds_planned()
                if shiftBreak.difference_total_seconds_start < 0:
                    if shiftBreak.difference_total_seconds_start:
                        total_seconds += abs(shiftBreak.difference_total_seconds_start)
                else:
                    if shiftBreak.difference_total_seconds_start:
                        total_seconds -= abs(shiftBreak.difference_total_seconds_start)

                if shiftBreak.difference_total_seconds_end < 0:
                    if shiftBreak.difference_total_seconds_end:
                        total_seconds += abs(shiftBreak.difference_total_seconds_end)
                else:
                    if shiftBreak.difference_total_seconds_end:
                        total_seconds -= abs(shiftBreak.difference_total_seconds_end)

                if total_seconds:
                    shiftBreak.time_real = total_seconds
                    result = Util.seconds2hms(total_seconds)
                    shiftBreak.time_real_hms = result['c']
                else:
                    shiftBreak.time_real = 0
                    shiftBreak.time_real_hms = '00:00:00'

            shiftBreak.difference_total = shiftBreak.difference_total_seconds_start + shiftBreak.difference_total_seconds_end
            result = Util.seconds2hms(shiftBreak.difference_total_seconds_start + shiftBreak.difference_total_seconds_end)
            shiftBreak.difference_total_hms = result['c']

    @api.depends('planned_end', 'real_end')
    def _compute_end(self):
        for shiftBreak in self:
            if shiftBreak.planned_end:
                if shiftBreak.real_end:
                    difference = shiftBreak.planned_end - shiftBreak.real_end
                    total_seconds = difference.total_seconds()
                    shiftBreak.difference_total_seconds_end = total_seconds
                    if total_seconds < 0:
                        shiftBreak.late_end = True
                    else:
                        shiftBreak.late_end = False

                    result = Util.seconds2hms(total_seconds)
                    shiftBreak.difference_hour_end = result['h']
                    shiftBreak.difference_minute_end = result['m']
                    shiftBreak.difference_second_end = result['s']
                    shiftBreak.difference_end = result['c']
                else:
                    percentage = shiftBreak.employee_shift_id._get_percentage_penalty('FD')
                    total_seconds = (-1) * (shiftBreak.get_total_seconds_planned()) * percentage / 100
                    shiftBreak.difference_total_seconds_end = total_seconds
                    if total_seconds < 0:
                        shiftBreak.late_end = True
                    else:
                        shiftBreak.late_end = False

                    result = Util.seconds2hms(total_seconds)
                    shiftBreak.difference_hour_end = result['h']
                    shiftBreak.difference_minute_end = result['m']
                    shiftBreak.difference_second_end = result['s']
                    shiftBreak.difference_end = result['c']
            else:
                shiftBreak.difference_total_seconds_end = -1
                shiftBreak.difference_hour_end = '00'
                shiftBreak.difference_minute_end = '00'
                shiftBreak.difference_second_end = '00'
                shiftBreak.difference_end = '00:00:00'
                shiftBreak.late_end = False

    employee_shift_id = fields.Many2one('hr.employee.shift', string="Turno", ondelete='cascade')

    planned_start = fields.Datetime('Inicio planificado', required=True, tracking=True)
    real_start = fields.Datetime('Inicio real', tracking=True)
    difference_total_seconds_start = fields.Integer(string='Diferencia total al inicio', readonly=True, compute=_compute_start)
    difference_hour_start = fields.Integer(string='Diferencia en hora al inicio', readonly=True, compute=_compute_start)
    difference_minute_start = fields.Integer(string='Diferencia en minuto al inicio', readonly=True, compute=_compute_start)
    difference_second_start = fields.Integer(string='Diferencia en segundo al inicio', readonly=True, compute=_compute_start)
    early_start = fields.Boolean(string='Inicio antes', readonly=True, compute=_compute_start)
    difference_start = fields.Char(string='Diferencia al inicio', readonly=True, compute=_compute_start)

    planned_end = fields.Datetime('Fin planificado', required=True, tracking=True)
    real_end = fields.Datetime('Fin real', tracking=True)
    difference_total_seconds_end = fields.Integer(string='Diferencia total al fin', readonly=True, compute=_compute_end)
    difference_hour_end = fields.Integer(string='Diferencia en hora al fin', readonly=True, compute=_compute_end)
    difference_minute_end = fields.Integer(string='Diferencia en minuto al fin', readonly=True, compute=_compute_end)
    difference_second_end = fields.Integer(string='Diferencia en segundo al fin', readonly=True, compute=_compute_end)
    late_end = fields.Boolean(string='Fin después', readonly=True, compute=_compute_end)
    difference_end = fields.Char(string='Diferencia al fin', readonly=True, compute=_compute_end)

    time_planned = fields.Integer(string='Tiempo planificado', readonly=True, compute=_compute_break)
    time_planned_hms = fields.Char(string='Tiempo planificado', readonly=True, compute=_compute_break)
    time_real = fields.Integer(string='Tiempo real consumido', readonly=True, compute=_compute_break)
    time_real_hms = fields.Char(string='Tiempo real consumido', readonly=True, compute=_compute_break)
    difference_total = fields.Integer(string='Diferencia total', readonly=True, compute=_compute_break)
    difference_total_hms = fields.Char(string='Diferencia total', readonly=True, compute=_compute_break)


class EmployeeHourExtra(models.Model):
    _name = "hr.employee.hour.extra"
    _description = 'Employee extra hour'
    _order = "employee_id, date asc"
    _inherit = ['mail.thread']

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
        for rec in self:
            date = rec.date.strftime(self.get_date_format())
            result.append(
                (
                    rec.id,
                    _("{} {} {} {}").format(rec.employee_id.display_name, date, rec.amount_hms, rec.hour_extra_id.name)
                )
            )
        return result

    @api.depends('amount_initial')
    def compute_amount_initial(self):
        for ehe in self:
            result = Util.seconds2hms(ehe.amount_initial)
            ehe.amount_initial_hd = result['hd']
            ehe.amount_initial_hms = result['c']

    @api.depends('amount')
    def compute_amount(self):
        for ehe in self:
            result = Util.seconds2hms(ehe.amount)
            ehe.amount_hd = result['hd']
            ehe.amount_hms = result['c']

    @api.depends('amount_approved')
    def compute_amount_approved_hms(self):
        for ehe in self:
            result = Util.seconds2hms(ehe.amount_approved)
            ehe.amount_approved_hd = result['hd']
            ehe.amount_approved_hms = result['c']

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeHourExtra, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)

            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))

            res['arch'] = etree.tostring(doc)

        return res

    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, tracking=True)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador",
                                       related='employee_id.user_id', store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador", tracking=True)
    date = fields.Date('Fecha', required=True, tracking=True)
    employee_reason = fields.Text(string="Motivo", tracking=True)
    amount_initial = fields.Float(string='Cantidad inicial', required=True, digits='Schedule', tracking=True)
    amount_initial_hd = fields.Float(string='Cantidad inicial (Valor decimal)', readonly=True, store=True,
                                     compute=compute_amount_initial, digits='Schedule')
    amount_initial_hms = fields.Char(string='Cantidad inicial', readonly=True, store=True,
                                     compute=compute_amount_initial)
    amount = fields.Float(string='Cantidad', required=True, digits='Schedule', tracking=True)
    amount_hd = fields.Float(string='Cantidad (Valor decimal)', readonly=True, store=True,
                             compute=compute_amount, digits='Schedule')
    amount_hms = fields.Char(string='Cantidad', readonly=True, store=True, compute=compute_amount)
    amount_approved = fields.Float(string='Cantidad aprobada', tracking=True)
    amount_approved_hd = fields.Float(string='Cantidad aprobada (Valor decimal)',
                                      readonly=True, store=True, compute=compute_amount_approved_hms, digits='Schedule')
    amount_approved_hms = fields.Char(string='Cantidad aprobada', readonly=True, store=True,
                                      compute=compute_amount_approved_hms)
    percentage_increase = fields.Float(string='Porcentaje de incremento', digits='Schedule', tracking=True)
    hour_extra_id = fields.Many2one('hr.hour.extra', string="Tipo de hora extra", required=True, tracking=True)
    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", tracking=True)
    employee_shift_id = fields.Many2one('hr.employee.shift', string="Turno", tracking=True)
    _STATE = [
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]
    state = fields.Selection(_STATE, string='Estado', default='draft', readonly=True,
                             help='', tracking=True)


class RegisterReasonEmployeeHourExtra(models.TransientModel):
    _name = 'register.reason.hr.employee.hour.extra'
    _description = 'Register reason for employee extra hour'

    employee_hour_extra_id = fields.Many2one('hr.employee.hour.extra',
                                                          string='Hora extra del colaborador', readonly=True,
                                                          default=lambda self: self._context.get('active_id'))
    employee_reason = fields.Text(string="Motivo", required=True)
    
    def action_register_reason(self):
        self.employee_hour_extra_id.employee_reason = self.employee_reason


class EmployeeHourExtraApprovalRequest(models.Model):
    _name = "employee.hour.extra.approval.request"
    _description = 'Employee extra hour approval request'
    _inherit = ['hr.generic.request']
    _order = "start desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_schedule.email_template_confirm_employee_hour_extra_approval_request',
            'approve': 'hr_dr_schedule.email_template_confirm_approve_employee_hour_extra_approval_request',
            'reject': 'hr_dr_schedule.email_template_confirm_reject_employee_hour_extra_approval_request',
            'cancel': 'hr_dr_schedule.email_template_cancel_employee_hour_extra_approval_request'
        }
    _hr_notifications_mode_param = 'hour.extra.approval.request.notifications.mode'
    _hr_administrator_param = 'hour.extra.approval.request.administrator'
    _hr_second_administrator_param = 'hour.extra.approval.request.second.administrator'

    def action_export_employee_hour_extra_approval_request(self):
        data = {
            'id': self.id
        }
        return self.env.ref('hr_dr_schedule.action_export_employee_hour_extra_approval_request_report'). \
            report_action(self, data=data)
    
    def name_get(self):
        result = []
        for ehear in self:
            result.append(
                (
                    ehear.id,
                    _("{} {}").format(ehear.employee_requests_id.name, ehear.attendance_period_id.display_name)
                )
            )
        return result

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('end', '<=', datetime.utcnow().date()),
            ('state', 'in', ['open'])
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False
    
    def action_generate_details(self):
        if self.detail_ids:
            self.detail_ids.unlink()

        employee_hour_extra = self.env['hr.employee.hour.extra'].search([
            '&', ('state', 'in', ['draft']), '&', ('attendance_period_id', '=', self.attendance_period_id.id), '|',
            ('user_manager_department_employee_id', '=', self.user_employee_requests_id.id), ('user_employee_id', '=', self.env.uid)
        ])

        for ehe in employee_hour_extra:
            result = Util.seconds2hms(ehe.amount)

            self.env['employee.hour.extra.approval.request.detail'].create({
                'approval_request_id': self.id,
                'employee_hour_extra_id': ehe.id,
                'amount_approved_hd': float(result['hd']),
                'amount_approved_h': int(result['h']),
                'amount_approved_m': int(result['m']),
                'amount_approved_s': int(result['s']),
            })

        return True

    # 
    # def action_generate_details_by_admin(self):
    #     if self.detail_ids:
    #         self.detail_ids.unlink()
    #
    #     employee_hour_extra = self.env['hr.employee.hour.extra'].search([
    #         '&', ('state', 'in', ['draft']),('attendance_period_id', '=', self.attendance_period_id.id)
    #     ])
    #
    #     for ehe in employee_hour_extra:
    #         result = Util.seconds2hms(ehe.amount)
    #
    #         self.env['employee.hour.extra.approval.request.detail'].create({
    #             'approval_request_id': self.id,
    #             'employee_hour_extra_id': ehe.id,
    #             'amount_approved': ehe.amount / 3600.0,
    #             'amount_approved_h': int(result['h']),
    #             'amount_approved_m': int(result['m']),
    #             'amount_approved_s': int(result['s']),
    #         })
    #
    #     return True

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    def mark_as_pending_employee_hour_extra(self):
        for detail in self.detail_ids:
            detail.employee_hour_extra_id.state = 'pending'

    def mark_as_approved(self):
        result = super(EmployeeHourExtraApprovalRequest, self).mark_as_approved()

        for detail in self.detail_ids:
            detail.employee_hour_extra_id.amount_approved = detail.amount_approved_h * 3600 + \
                                                            detail.amount_approved_m * 60 + \
                                                            detail.amount_approved_s
            detail.employee_hour_extra_id.state = 'approved'

        # Enviar mail de aprobacion de solicitud
        self.send_mail_approve_hour_extra_approval_request()
        # template = self.env.ref('hr_dr_schedule.email_template_confirm_approve_employee_hour_extra_approval_request', False)
        # local_context = self.env.context.copy()
        # template.with_context(local_context).send_mail(self.id, force_send=True)

        return result

    def send_mail_approve_hour_extra_approval_request(self):
        """ Envía email de aprobación de solicitud """
        template = self.env.ref('hr_dr_schedule.email_template_confirm_approve_employee_hour_extra_approval_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def mark_as_rejected(self, reason):
        result = super(EmployeeHourExtraApprovalRequest, self).mark_as_rejected(reason)

        for detail in self.detail_ids:
            detail.employee_hour_extra_id.state = 'rejected'

        # Enviar el mail de rechazo al solicitante
        template = self.env.ref('hr_dr_schedule.email_template_confirm_reject_employee_hour_extra_approval_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

        return result

    def get_local_context(self, id):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Solicitud de aprobación de horas extras")
        local_context['request'] = _("ha realizado una solicitud de aprobación de horas extras.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id


        local_context['details'] = "Solicitud de aprobación de horas extras. Período desde el {} hasta el {}.".format(self.attendance_period_id.start.strftime("%d/%m/%Y"), self.attendance_period_id.end.strftime("%d/%m/%Y"))


        local_context['commentary'] = self.commentary

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('hr_dr_schedule.hour_extra_approval_request_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_dr_schedule.menu_hr_schedule_main').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        return local_context

    def send_mail_confirm_hour_extra_approval_request(self):
        template = self.env.ref('hr_dr_schedule.email_template_confirm_employee_hour_extra_approval_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def _send_notification_to(self, employee_id, level=0):
        """
        Crea la notificación al usuario recibido como parámetro.
        Si la notificación es de primer nivel, envía un email al usuario.

        :param employee_id: Identificador del colaborador que aprueba la notificación.
        :param level: Nivel de aprobación que ya tiene la petición (un nivel menos que el que tendrá esta notificación).
        """

        notification = self.env['hr.notifications'].create({
            'level': level + 1,
            'employee_requests_id': self.employee_requests_id.id,
            'employee_approve_id': employee_id,
            'state': 'pending',
            'send': True if not level else False,
            'res_id': self.id,
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
        })

        if not level:
            # Enviar email de aprobacion / denegacion solo si el colaborador tiene el primer nivel de notificación.
            notification.send_mail(self.get_local_context(notification.id))

    def _send_notifications_bd(self, department, propagate=0, level=0):
        """
        Crea las notificaciones basadas en departamentos para cada administrador de departamento y administradores
        adicionales según los niveles de propagación que se hayan definido.

        Por defecto se enviará una notificación al o a los administradores de departamento de jerarquía inmediata
        superior a quien realiza la solicitud.

        :param department: Departamento a notificar.
        :param propagate: Número de niveles a propagar la notificación. Si el campo 'propagate' tiene un valor positivo,
            esta notificación se extenderá a tantos niveles por encima del departamento ya enviado como se indique en el
            valor (siempre que estos existan). Si el valor de 'propagate' es negativo, entonces la notificación se
            extenderá a todos los niveles superiores al departamento.
        :param level: Nivel de la útlima notificación realizada.

        :return: Retorna un número indicando los niveles de notificación completados.
        """

        scheme_exists = False
        superior_department = department.parent_id

        if self.employee_requests_id.department_id == department and self.is_department_manager(self.employee_requests_id):
            # El usuario pertenece a este departamento y es el administrador o uno de los administradores adicionales del mismo.

            if superior_department:
                # La notificación se realiza en el dpto. superior
                level = self._send_notifications_bd(superior_department, propagate)
        else:
            superior_manager = department.manager_id  # Responsable del departamento
            if superior_manager:
                # Existe responsable superior
                scheme_exists = True
                self._send_notification_to(superior_manager.id, level)

            # Verificamos que este instaldo el modulo 'hr_dr_department_additional_manager' y por ende exista el campo
            # 'additional_manager_ids'
            if 'hr_dr_department_additional_manager' in self.env.registry._init_modules:
                additional_managers = department.additional_manager_ids
                if additional_managers:
                    for additional_manager in additional_managers:
                        scheme_exists = True
                        self._send_notification_to(additional_manager.id, level)

            if scheme_exists:
                level += 1
                if propagate != 0:
                    # Existe una estructura superior y las notificaciones aún deben propagarse hacia el nivel superior.
                    level = self._send_notifications_bd(superior_department, propagate - 1, level)

        return level

    def _admin_confirm_hour_extra_approval_request(self, administrator, level=0):
        """
        Gestiona el cambio de estado de la notificación y el envío de correos electrónicos cuando el modo de
        notificación incluye al administrador.

        :param administrator: Identificador del administrador.
        :param level: Nivel de la última notificación realizada.
        """

        admin_made_request = self.employee_requests_id.id.__str__() == administrator

        if not level and admin_made_request:
            # El único nivel de aprobación es del administrador y este es quien realizó la solicitud.
            self.mark_as_approved()
            # self.state = 'approved'
            # # Enviando correo de aprobación automática
            # self.send_mail_approve_hour_extra_approval_request()
        else:
            self.state = 'pending'

            # Enviando correo de confirmación de solicitud
            self.send_mail_confirm_hour_extra_approval_request()

            # Si el administrador realizó la petición no lo incluyo en los niveles de aprobación
            if not admin_made_request:
                self._send_notification_to(administrator, level)

    def confirm_hour_extra_approval_request(self):
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if create_edit_without_restrictions == False:
            amount_days_after_cdfr_to_HEAR = 1
            include_weekend_and_holidays = False

            cutoff_date = self.attendance_period_id.end

            while amount_days_after_cdfr_to_HEAR > 0:
                cutoff_date = cutoff_date + relativedelta(years=1)
                if include_weekend_and_holidays == True:
                    amount_days_after_cdfr_to_HEAR -= 1
                else:
                    holidays = self.env['hr.holiday'].search_count([
                        ('date', '=', cutoff_date)
                    ])
                    if holidays == 0 and cutoff_date.weekday() != 5 and cutoff_date.weekday() != 6:

                        amount_days_after_cdfr_to_HEAR -= 1

            if datetime.utcnow().date() < self.attendance_period_id.end:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se puede realizar a partir del {}.").format(self.attendance_period_id.end))

            if datetime.utcnow().date() > cutoff_date:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se podía realizar hasta el {}.").format(cutoff_date))

        notifications_mode = self.env['ir.config_parameter'].sudo().get_param(
            "hour.extra.approval.request.notifications.mode")
        administrator = self.env['ir.config_parameter'].sudo().get_param(
            "hour.extra.approval.request.administrator")

        if notifications_mode == 'Administrator':
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            self._admin_confirm_hour_extra_approval_request(administrator)
        elif notifications_mode == 'One_level_bd':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            if level > 0:
                self.state = 'pending'
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()
            else:
                # self.state = 'approved'
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                self.mark_as_approved()
                # self.send_mail_approve_hour_extra_approval_request()
        elif notifications_mode == 'One_level_br':
            self.mark_as_pending_employee_hour_extra()
            if self.employee_requests_id.parent_id:
                # Tiene un responsable
                self.state = 'pending'

                self._send_notification_to(self.employee_requests_id.parent_id.id)

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()
            else:
                self.mark_as_approved()
                # self.state = 'approved'
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                # self.send_mail_approve_hour_extra_approval_request()
        elif notifications_mode == 'One_level_bc':
            self.mark_as_pending_employee_hour_extra()
            if self.employee_requests_id.coach_id:
                # Tiene un monitor
                self.state = 'pending'

                self._send_notification_to(self.employee_requests_id.coach_id.id)

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()

            else:
                self.mark_as_approved()
                # self.state = 'approved'
                # Enviar correo de aprobación automática porque no hay esquema de aprobación
                # self.send_mail_approve_hour_extra_approval_request()
        elif notifications_mode == 'One_level_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            self._admin_confirm_hour_extra_approval_request(administrator, level)
        elif notifications_mode == 'One_level_br_and_administrator':
            manager = self.employee_requests_id.parent_id  # El responsable de quien realiza la solicitud
            self.mark_as_pending_employee_hour_extra()
            if manager:
                # Tiene un responsable
                self._send_notification_to(manager.id)

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()

                self._admin_confirm_hour_extra_approval_request(administrator, 1)

            else:
                self._admin_confirm_hour_extra_approval_request(administrator)
        elif notifications_mode == 'One_level_bc_and_administrator':
            coach = self.employee_requests_id.coach_id  # El monitor de quien realiza la solicitud
            self.mark_as_pending_employee_hour_extra()
            if coach:
                # Tiene un monitor
                self._send_notification_to(coach.id)

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()

                self._admin_confirm_hour_extra_approval_request(administrator, 1)

            else:
                self._admin_confirm_hour_extra_approval_request(administrator)
        elif notifications_mode == 'Two_levels_bd':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=1)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            if level > 0:
                self.state = 'pending'

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()

            else:
                self.mark_as_approved()
                # self.state = 'approved'
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                # self.send_mail_approve_hour_extra_approval_request()
        elif notifications_mode == 'Two_levels_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=1)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            self._admin_confirm_hour_extra_approval_request(administrator, level)
        elif notifications_mode == 'All_levels_bd':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=-1)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            if level > 0:
                self.state = 'pending'

                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()

            else:
                self.mark_as_approved()
                # self.state = 'approved'
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                # self.send_mail_approve_hour_extra_approval_request()
        elif notifications_mode == 'All_levels_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=-1)
            self.mark_as_pending_employee_hour_extra()
            self.confirm_request()
            self._admin_confirm_hour_extra_approval_request(administrator, level)
        elif notifications_mode == 'Personalized':
            esqueme_notifications = self.env['hr.scheme.notifications'].sudo().search([
                ('active', '=', True),
                ('employee_requests_id', '=', self.employee_requests_id.id),
                ('model_id', '=', self.env['ir.model'].sudo().search([('model', '=', self._name)]).id)
            ], order='level asc')
            self.mark_as_pending_employee_hour_extra()
            if len(esqueme_notifications) == 0:
                self.mark_as_approved()
                # self.state = 'approved'
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                # self.send_mail_approve_hour_extra_approval_request()
            else:
                self.state = 'pending'
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_hour_extra_approval_request()
                for en in esqueme_notifications:
                    self._send_notification_to(en.employee_approve_id.id, en.level - 1)
        return self

    def cancel_hour_extra_approval_request(self):
        self.cancel_request()
        # Iterar por las notificaciones asociadas y cancelarlas
        notification_ids = self.env['hr.notifications'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('state', '=', 'pending'),
            ('processed', '=', False)
        ])
        for notification in notification_ids:
            notification.state = 'cancelled'
        return self

    @api.model_create_multi
    def create(self, vals_list):
        employeeHourExtraApprovalRequest = super(EmployeeHourExtraApprovalRequest, self).create(vals_list)
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            amount_days_after_cdfr_to_HEAR = 1
            include_weekend_and_holidays = False

            cutoff_date = employeeHourExtraApprovalRequest.attendance_period_id.end

            while amount_days_after_cdfr_to_HEAR > 0:
                cutoff_date = cutoff_date + relativedelta(years=1)
                if include_weekend_and_holidays == True:
                    amount_days_after_cdfr_to_HEAR -= 1
                else:
                    holidays = self.env['hr.holiday'].search_count([
                        ('date', '=', cutoff_date)
                    ])
                    if holidays == 0 and cutoff_date.weekday() != 5 and cutoff_date.weekday() != 6:
                        amount_days_after_cdfr_to_HEAR -= 1

            if datetime.utcnow().date() < employeeHourExtraApprovalRequest.attendance_period_id.end:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se puede realizar a partir del {}.").format(
                        employeeHourExtraApprovalRequest.attendance_period_id.end))

            if datetime.utcnow().date() > cutoff_date:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se podía realizar hasta el {}.").format(cutoff_date))

        return employeeHourExtraApprovalRequest
    
    def write(self, vals):
        employeeHourExtraApprovalRequest = super(EmployeeHourExtraApprovalRequest, self).write(vals)
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            amount_days_after_cdfr_to_HEAR = 1
            include_weekend_and_holidays = False

            cutoff_date = self.attendance_period_id.end

            while amount_days_after_cdfr_to_HEAR > 0:
                cutoff_date = cutoff_date + relativedelta(years=1)
                if include_weekend_and_holidays == True:
                    amount_days_after_cdfr_to_HEAR -= 1
                else:
                    holidays = self.env['hr.holiday'].search_count([
                        ('date', '=', cutoff_date)
                    ])
                    if holidays == 0 and cutoff_date.weekday() != 5 and cutoff_date.weekday() != 6:
                        amount_days_after_cdfr_to_HEAR -= 1

            if datetime.utcnow().date() < self.attendance_period_id.end:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se puede realizar a partir del {}.").format(
                        self.attendance_period_id.end))

            if datetime.utcnow().date() > cutoff_date:
                raise ValidationError(
                    _("La solicitud de aprobación de horas extras se podía realizar hasta el {}.").format(cutoff_date))


        return employeeHourExtraApprovalRequest
    
    def unlink(self):
        for employeeHourExtraApprovalRequest in self:
            if employeeHourExtraApprovalRequest.state != 'draft':
                raise ValidationError('Solo puede eliminar solicitudes de aprobación horas extras en estado borrador.')
        return super(EmployeeHourExtraApprovalRequest, self).unlink()

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeHourExtraApprovalRequest, self).\
            fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)

            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))

            res['arch'] = etree.tostring(doc)

        return res

    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", required=True,
                                           default=_default_period_id, tracking=True)
    start = fields.Date(string="Inicio del período", related='attendance_period_id.start', store=True, tracking=True)
    end = fields.Date(string="Fin del período", related='attendance_period_id.end', store=True, tracking=True)
    detail_ids = fields.One2many('employee.hour.extra.approval.request.detail', 'approval_request_id',
                                 string="Detalles")


class ExportEmployeeHourExtraApprovalRequestXls(models.AbstractModel):
    _name = 'report.hr_dr_schedule.export_employee_h_e_a_r'
    _description = 'Report employee hour extra approval request'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        ehear = self.env['employee.hour.extra.approval.request'].search([('id', '=', data['id'])], limit=1)

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
        th_red_props = label_props.copy()
        th_red_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#FF0000', 'font_color': '#FFFFFF',
                         'border': True, 'text_wrap': True})
        th_green_props = label_props.copy()
        th_green_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#008000', 'font_color': '#FFFFFF',
                             'border': True, 'text_wrap': True})
        td_props = text_props.copy()
        td_props.update({'border': True})
        td_info_props = td_props.copy()
        td_info_props.update({'align': 'left', 'italic': True, 'font_color': '#7F7f7F'})
        date_props = text_props.copy()
        date_props.update({'num_format': 'dd/mm/yyyy'})
        number_props = text_props.copy()
        number_props.update({'num_format': '#,##0.00'})
        money_props = text_props.copy()
        money_props.update({'num_format': '#,##0.00'})
        td_date_props = date_props.copy()
        td_date_props.update({'border': True})
        td_number_props = number_props.copy()
        td_number_props.update({'align': 'right', 'border': True})
        td_money_props = money_props.copy()
        td_money_props.update({'align': 'right', 'border': True})
        reference_props = text_props.copy()
        reference_props.update({'font_size': 8})

        title = workbook.add_format(title_props)
        header1 = workbook.add_format(h1_props)
        header2 = workbook.add_format(h2_props)
        label = workbook.add_format(label_props)
        text = workbook.add_format(text_props)
        date_format = workbook.add_format(date_props)
        number_format = workbook.add_format(number_props)
        money_format = workbook.add_format(money_props)
        table_header = workbook.add_format(th_props)
        table_header_red = workbook.add_format(th_red_props)
        table_header_green = workbook.add_format(th_green_props)
        table_cell = workbook.add_format(td_props)
        table_info_cell = workbook.add_format(td_info_props)
        table_date_format = workbook.add_format(td_date_props)
        table_number_format = workbook.add_format(td_number_props)
        table_money_format = workbook.add_format(td_money_props)
        reference = workbook.add_format(reference_props)

        sheet = workbook.add_worksheet(_('Aprobación de horas extras'))

        sheet.center_horizontally()

        col_end = 13
        # Estableciendo el ancho de las columnas
        sheet.set_column('A:A', 7.0)
        sheet.set_column('B:B', 30.0)
        sheet.set_column('C:C', 15.0)
        sheet.set_column('D:D', 30.0)
        sheet.set_column('E:E', 15.0)
        sheet.set_column('F:F', 15.0)
        sheet.set_column('G:G', 30.0)
        sheet.set_column('H:H', 15.0)
        sheet.set_column('I:I', 50.0)
        sheet.set_column('J:J', 15.0)
        sheet.set_column('K:K', 15.0)
        sheet.set_column('L:L', 15.0)
        sheet.set_column('M:M', 15.0)
        sheet.set_column('N:N', 15.0)

        # Escribiendo encabezado de informe
        sheet.merge_range(0, 0, 0, col_end, self.env.user.company_id.name, title)
        sheet.merge_range(1, 0, 1, col_end, _('Solicitante: {}').format(ehear.employee_requests_id.display_name),
                          header2)
        sheet.merge_range(2, 0, 2, col_end, _('Período: {}').format(ehear.attendance_period_id.display_name), header2)
        sheet.merge_range(3, 0, 3, col_end,
                          _('Lea los comentarios en cada columna. Las columnas de color rojo no se importan, '
                            'por ende no tiene sentido modificarlas. '
                            'Solo las columnas de color verde se importan.'), reference)

        # Escribiendo los encabezados de la tabla
        row = 4
        sheet.write(row, 0, _('Id'), table_header_red)
        sheet.write(row, 1, _('Colaborador'), table_header_red)
        sheet.write(row, 2, _('Identificación'), table_header_red)
        sheet.write(row, 3, _('Departamento'), table_header_red)
        sheet.write(row, 4, _('Fecha'), table_header_red)
        sheet.write(row, 5, _('Cantidad generada (HH:MM:SS)'), table_header_red)
        sheet.write(row, 6, _('Tipo de hora extra'), table_header_red)
        sheet.write(row, 7, _('Porcentaje'), table_header_red)
        sheet.write(row, 8, _('Motivo'), table_header_red)
        sheet.write(row, 9, _('Aprobado (Valor decimal)'), table_header_green)
        sheet.write_comment(row, 9, _('En esta columna debe especificar las horas extras como un valor decimal. '
                                      'Si se imgresan valores aquí, debe ingresar 0 en las 3 columnas siguientes.'))
        sheet.write(row, 10, _('Aprobado (HH)'), table_header_green)
        sheet.write_comment(row, 10, _("En esta columna debe especificar la cantidad de horas de las horas extras como "
                                       "un valor sin decimales. Si se imgresan valores aquí, debe ingresar 0 en la "
                                       "columna 'Aprobado (Valor decimal)'."))
        sheet.write(row, 11, _('Aprobado (MM)'), table_header_green)
        sheet.write_comment(row, 11,
                            _("En esta columna debe especificar la cantidad de minutos de las horas extras como "
                              "un valor sin decimales. Si se imgresan valores aquí, debe ingresar 0 en la "
                              "columna 'Aprobado (Valor decimal)'."))
        sheet.write(row, 12, _('Aprobado (SS)'), table_header_green)
        sheet.write_comment(row, 12,
                            _("En esta columna debe especificar la cantidad de segundos de las horas extras como "
                              "un valor sin decimales. Si se imgresan valores aquí, debe ingresar 0 en la "
                              "columna 'Aprobado (Valor decimal)'."))
        sheet.write(row, 13, _('Cantidad aprobada (HH:MM:SS)'), table_header_red)

        row += 1

        for line in ehear.detail_ids:
            sheet.write(row, 0, line.id, table_cell)
            sheet.write(row, 1, line.employee_id.display_name, table_cell)
            if line.employee_id.identification_id:
                sheet.write(row, 2, line.employee_id.identification_id, table_cell)
            else:
                sheet.write(row, 2, '-', table_cell)
            if line.employee_id.department_id:
                sheet.write(row, 3, line.employee_id.department_id.name, table_cell)
            else:
                sheet.write(row, 3, '-', table_cell)
            sheet.write(row, 4, line.date, table_date_format)
            sheet.write(row, 5, line.amount_hms, table_cell)
            sheet.write(row, 6, line.hour_extra_id.name, table_cell)
            sheet.write(row, 7, line.percentage_increase, table_number_format)
            if line.employee_reason:
                sheet.write(row, 8, line.employee_reason, table_cell)
            else:
                sheet.write(row, 8, '', table_cell)
            sheet.write(row, 9, line.amount_approved_hd, table_number_format)
            sheet.write(row, 10, line.amount_approved_h, table_number_format)
            sheet.write(row, 11, line.amount_approved_m, table_number_format)
            sheet.write(row, 12, line.amount_approved_s, table_number_format)
            sheet.write(row, 13, line.amount_approved_hms, table_cell)

            row += 1

        sheet.fit_to_pages(1, 0)


class EmployeeHourExtraApprovalRequestDetail(models.Model):
    _name = "employee.hour.extra.approval.request.detail"
    _description = 'Employee extra hour approval request detail'
    _inherit = ['mail.thread']
    _order = "employee_id, date asc"

    @api.onchange('amount_approved_h', 'amount_approved_m', 'amount_approved_s')
    def on_change_amount_approved_hms(self):
        for rec in self:
            result = Util.seconds2hms(self.amount_approved_h * 3600 +
                                      self.amount_approved_m * 60 +
                                      self.amount_approved_s)
            rec.amount_approved_hd = float(result['hd'])

    def change_amount_approved_hd(self):
        hours = int(self.amount_approved_hd)
        hours_fraction = self.amount_approved_hd - int(self.amount_approved_hd)
        minutes = hours_fraction * 60
        minutes_fraction = minutes - int(minutes)
        seconds = minutes_fraction * 60
        self.amount_approved_h = hours
        self.amount_approved_m = int(minutes)
        self.amount_approved_s = int(seconds)

    @api.onchange('amount_approved_hd')
    def on_change_amount_approved_hd(self):
        for rec in self:
            if rec.amount_approved_hd:
                rec.change_amount_approved_hd()

    @api.depends('amount_approved_h', 'amount_approved_m', 'amount_approved_s')
    def compute_amount_approved_hms(self):
        for ehear in self:
            cadena = "{}:{}:{}".format("0{}".format(ehear.amount_approved_h)
                                       if ehear.amount_approved_h <= 9 else ehear.amount_approved_h,
                                       "0{}".format(ehear.amount_approved_m)
                                       if ehear.amount_approved_m <= 9 else ehear.amount_approved_m,
                                       "0{}".format(ehear.amount_approved_s)
                                       if ehear.amount_approved_s <= 9 else ehear.amount_approved_s)

            ehear.amount_approved_hms = cadena

    @api.depends('approval_request_id.state', 'approval_request_id.notification_ids')
    def compute_readonly_amount(self):
        for ehear in self:
            if ehear.approval_request_id.state == 'draft':
                ehear.readonly_amount = False
            elif ehear.approval_request_id.state == 'cancelled' or ehear.approval_request_id.state == 'approved' \
                    or ehear.approval_request_id.state == 'rejected':
                ehear.readonly_amount = True
            else:
                user_id = self.env.uid
                n = self.env['hr.notifications'].search([
                    ('state', '=', 'pending'),
                    ('send', '=', True),
                    ('processed', '=', False),
                    ('res_id', '=', ehear.approval_request_id.id),
                    ('res_model', '=', 'employee.hour.extra.approval.request'),
                    ('user_employee_approve_id', '=', user_id)
                ], limit=1)
                if n:
                    ehear.readonly_amount = False
                else:
                    ehear.readonly_amount = True

    approval_request_id = fields.Many2one('employee.hour.extra.approval.request',
                                          string="Solicitud de aprobación de hora extra",
                                          required=True, ondelete='cascade', tracking=True)
    employee_hour_extra_id = fields.Many2one('hr.employee.hour.extra',
                                             string="Hora extra del colaborador", tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Colaborador", related='employee_hour_extra_id.employee_id')
    department_employee_id = fields.Many2one('hr.department',
                                             string="Departamento del colaborador",
                                             related='employee_hour_extra_id.department_employee_id')
    date = fields.Date('Fecha', related='employee_hour_extra_id.date')
    employee_reason = fields.Text(string="Motivo", related='employee_hour_extra_id.employee_reason')
    amount = fields.Float(string='Cantidad', related='employee_hour_extra_id.amount')
    amount_hms = fields.Char(string='Cantidad', related='employee_hour_extra_id.amount_hms')
    percentage_increase = fields.Float(string='Porcentaje de incremento',
                                       related='employee_hour_extra_id.percentage_increase')
    hour_extra_id = fields.Many2one('hr.hour.extra', string="Tipo de hora extra",
                                    related='employee_hour_extra_id.hour_extra_id')
    amount_approved_hd = fields.Float(string='Aprobado', tracking=True)
    amount_approved_h = fields.Integer(string='Aprobado(h)', tracking=True)
    amount_approved_m = fields.Integer(string='Aprobado(m)', tracking=True)
    amount_approved_s = fields.Integer(string='Aprobado(s)', tracking=True)
    amount_approved_hms = fields.Char(string='Cantidad aprobada', readonly=True, compute=compute_amount_approved_hms,
                                      store=True)
    readonly_amount = fields.Boolean(string='Solo lectura', compute=compute_readonly_amount)


class EmployeeHourNight(models.Model):
    _name = "hr.employee.hour.night"
    _description = 'Employee night hour'
    _order = "employee_id, date asc"
    _inherit = ['mail.thread']

    @api.depends('amount_initial')
    def compute_amount_initial(self):
        for ehe in self:
            result = Util.seconds2hms(ehe.amount_initial)
            ehe.amount_initial_hd = result['hd']
            ehe.amount_initial_hms = result['c']

    @api.depends('amount')
    def compute_amount(self):
        for ehe in self:
            result = Util.seconds2hms(ehe.amount)
            ehe.amount_hd = result['hd']
            ehe.amount_hms = result['c']

    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, tracking=True)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador", related='employee_id.user_id',
                                       store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador", tracking=True)
    date = fields.Date('Fecha', required=True, tracking=True)
    amount_initial = fields.Float(string='Cantidad inicial', required=True, tracking=True)

    amount_initial_hd = fields.Float(string='Cantidad inicial (Valor decimal)', readonly=True, store=True,
                                     compute=compute_amount_initial, digits='Schedule')
    amount_initial_hms = fields.Char(string='Cantidad inicial', readonly=True, store=True,
                                     compute=compute_amount_initial)
    amount = fields.Float(string='Cantidad', required=True, digits='Schedule', tracking=True)

    amount_hd = fields.Float(string='Cantidad (Valor decimal)', readonly=True, store=True, compute=compute_amount,
                             digits='Schedule')
    amount_hms = fields.Char(string='Cantidad', readonly=True, store=True, compute=compute_amount)
    percentage_increase = fields.Float(string='Porcentaje de incremento', digits='Schedule', tracking=True)
    hour_night_id = fields.Many2one('hr.hour.night', string="Tipo de hora nocturna", required=True, tracking=True)
    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", tracking=True)
    employee_shift_id = fields.Many2one('hr.employee.shift', string="Turno", tracking=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeHourNight, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)

            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))

            res['arch'] = etree.tostring(doc)

        return res


class EmployeePeriodSummary(models.Model):
    _name = "hr.employee.period.summary"
    _description = 'Employee period summary'
    _inherit = ['mail.thread']
    _order = "start desc"

    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", tracking=True)
    start = fields.Date(string="Inicio del período", related='attendance_period_id.start', store=True)
    end = fields.Date(string="Fin del período", related='attendance_period_id.end', store=True)
    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, tracking=True)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador",related='employee_id.user_id',
                                       store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    hour_extra_sumary_ids = fields.One2many('hr.employee.period.summary.hour.extra', 'period_summary_id',
                                            string="Resumen de horas extras")
    hour_night_sumary_ids = fields.One2many('hr.employee.period.summary.hour.night', 'period_summary_id',
                                            string="Resumen de horas nocturnas")

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeePeriodSummary, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)

            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))

            res['arch'] = etree.tostring(doc)

        return res


class EmployeePeriodSummaryHourExtra(models.Model):
    _name = "hr.employee.period.summary.hour.extra"
    _description = 'Employee period summary extra hour'
    _inherit = ['mail.thread']

    @api.depends('amount')
    def compute_amount_hms(self):
        for he in self:
            result = Util.seconds2hms(he.amount)
            he.amount_hd = result['hd']
            he.amount_hms = result['c']

    period_summary_id = fields.Many2one('hr.employee.period.summary', string="Resumen del período del colaborador",
                                        required=True, ondelete='cascade', tracking=True)
    hour_extra_id = fields.Many2one('hr.hour.extra', string="Tipo de hora extra", required=True, tracking=True)
    amount = fields.Float(string='Cantidad', required=True, digits='Schedule', tracking=True)
    amount_hd = fields.Float(string='Cantidad (Valor decimal)', readonly=True, store=True, compute=compute_amount_hms,
                             digits='Schedule')
    amount_hms = fields.Char(string='Cantidad', readonly=True, store=True, compute=compute_amount_hms)
    percentage = fields.Float(string='Porcentaje', required=True, digits='Schedule', tracking=True)


class EmployeePeriodSummaryHourNight(models.Model):
    _name = "hr.employee.period.summary.hour.night"
    _description = 'Employee period summary night hour'
    _inherit = ['mail.thread']

    @api.depends('amount')
    def compute_amount_hms(self):
        for hn in self:
            precision = self.env['decimal.precision'].precision_get('Schedule')
            result = Util.seconds2hms(hn.amount, precision)
            hn.amount_hd = result['hd']
            hn.amount_hms = result['c']

    period_summary_id = fields.Many2one('hr.employee.period.summary', string="Resumen del período del colaborador",
                                        required=True, ondelete='cascade', tracking=True)
    hour_night_id = fields.Many2one('hr.hour.night', string="Tipo de hora nocturna", required=True, tracking=True)
    amount = fields.Float(string='Cantidad', required=True, digits='Schedule', tracking=True)
    amount_hd = fields.Float(string='Cantidad (Valor decimal)', readonly=True, store=True, compute=compute_amount_hms,
                             digits='Schedule')
    amount_hms = fields.Char(string='Cantidad', readonly=True, store=True, compute=compute_amount_hms)
    percentage = fields.Float(string='Porcentaje', required=True, digits='Schedule', tracking=True)


class AttendanceDevice(models.Model):
    _inherit = 'attendance.device'

    def get_attendance_mode(self):
        """
        Obtiene el valor del parámetro 'attendance.mode'
        :return: String con el valor de 'attendance.mode'. Los valores pueden ser:
                 '1': Una tecla de función por tipo de evento
                 '2': Una tecla de función por actividad
                 '3': Sin tecla de función
        """
        attendance_mode = self.env['ir.config_parameter'].sudo().get_param('attendance.mode')
        return attendance_mode

    def _get_default_attendance_states(self):

        att_state_ids = self.env['attendance.state']
        attendance_mode = self.get_attendance_mode()

        if attendance_mode == '1':
            attendance_device_state_code_0 = self.env.ref('hr_dr_schedule.attendance_device_state_code_0')
            if attendance_device_state_code_0:
                att_state_ids += attendance_device_state_code_0
            attendance_device_state_code_1 = self.env.ref('hr_dr_schedule.attendance_device_state_code_1')
            if attendance_device_state_code_1:
                att_state_ids += attendance_device_state_code_1

            attendance_device_state_code_2 = self.env.ref('hr_dr_schedule.attendance_device_state_code_2')
            if attendance_device_state_code_2:
                att_state_ids += attendance_device_state_code_2
            attendance_device_state_code_3 = self.env.ref('hr_dr_schedule.attendance_device_state_code_3')
            if attendance_device_state_code_3:
                att_state_ids += attendance_device_state_code_3

            attendance_device_state_code_4 = self.env.ref('hr_dr_schedule.attendance_device_state_code_4')
            if attendance_device_state_code_4:
                att_state_ids += attendance_device_state_code_4
            attendance_device_state_code_5 = self.env.ref('hr_dr_schedule.attendance_device_state_code_5')
            if attendance_device_state_code_5:
                att_state_ids += attendance_device_state_code_5
            return att_state_ids
        elif attendance_mode == '2':
            attendance_device_state_code_01 = self.env.ref('hr_dr_schedule.attendance_device_state_code_01')
            if attendance_device_state_code_01:
                att_state_ids += attendance_device_state_code_01
            attendance_device_state_code_23 = self.env.ref('hr_dr_schedule.attendance_device_state_code_23')
            if attendance_device_state_code_23:
                att_state_ids += attendance_device_state_code_23
            attendance_device_state_code_45 = self.env.ref('hr_dr_schedule.attendance_device_state_code_45')
            if attendance_device_state_code_45:
                att_state_ids += attendance_device_state_code_45
        elif attendance_mode == '3':
            attendance_device_state_code_i = self.env.ref('hr_dr_schedule.attendance_device_state_code_i')
            if attendance_device_state_code_i:
                att_state_ids += attendance_device_state_code_i

        return att_state_ids

    def _get_devices(self):
        lic = License(self.env['ir.config_parameter'].sudo().get_param)
        devices = []
        for device in lic.get_devices():
            devices.append(device['sn'])
        return devices

    def action_check_connection(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_check_connection()

    def action_attendance_download(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_attendance_download()

    def action_user_download(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_user_download()

    def action_user_upload(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_user_upload()

    def action_employee_map(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_employee_map()

    def action_finger_template_download(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_finger_template_download()

    def action_clear_data(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_clear_data()

    def action_restart(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_restart()

    def action_show_time(self):
        if self.serialnumber not in self._get_devices():
            raise UserError(_('El dispositivo {} no está incluido en su licencia.').format(self.name))
        return super(AttendanceDevice, self).action_show_time()


class AttendanceActivity(models.Model):
    _inherit = 'attendance.activity'

    code = fields.Integer(string='Código', required=True)
    active = fields.Boolean(string='Active', required=True)


class AttendanceState(models.Model):
    _inherit = 'attendance.state'

    _sql_constraints = [
        ('code_unique',
         'UNIQUE(code, activity_id, type)',
         "The Code, Activity and Activity type must be unique!"),
    ]

    active = fields.Boolean(string='Active', required=True)
    type = fields.Selection(selection_add=[('checkinout', 'Check-in-out'),
                                           ('general', 'General')], ondelete={'checkinout': 'cascade',
                                                                              'general': 'cascade'})


class UserAttendance(models.Model):
    """
    Extendiendo los campos user_employee_id y user_manager_department_employee_id en el modelo user.attendance para
    filtrar las vistas.
    """
    _inherit = 'user.attendance'

    mode = fields.Selection([('biometric', 'Biométrico'),
                             ('web', 'Web')], string='Modo', default='biometric')
    processed = fields.Boolean(string="Procesada", default=False)
    assigned = fields.Boolean(string="Asignada", default=False)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador", related='employee_id.user_id',
                                       store=True)
    # Si almaceno este campo y luego muevo al usuario de departamento o cambio el manager no se actualiza
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador",
        related='employee_id.department_id.manager_id.user_id', store=False)

    # attendance_state_id = fields.Many2one(
    #     'attendance.state', string='Tipo de evento en el sistema',
    #     help='Campo técnico para vincular el tipo de evento en el dispositivo con tipo de evento en el sistema.',
    #     required=False, index=True)

    # activity_id = fields.Many2one('attendance.activity', compute='_compute_activity_id', store=True,
    #                               index=True, default=lambda self:self.default_activity_id())
    #
    # def default_activity_id(self):
    #     for rec in self:
    #         return rec.attendance_state_id.activity_id if rec.attendance_state_id.id else None
    #
    # @api.depends('attendance_state_id')
    # def _compute_activity_id(self):
    #     for rec in self:
    #         rec.activity_id = rec.attendance_state_id.activity_id if rec.attendance_state_id.id else None

    @api.constrains('status', 'attendance_state_id')
    def constrains_status_attendance_state_id(self):
        for r in self:
            if r.status != r.attendance_state_id.code:
                pass

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(UserAttendance, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        # Adiciono al filtro 'Último periodo' el dominio, limitando la fecha de marcación al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)
            if last_period.id:
                start = last_period.start
                # Selecciono el día siguiente para que al comparar y incluya el día final
                end = (datetime.combine(last_period.end, datetime.min.time()) + relativedelta(days=1)).date()
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//filter[@name='filter_last_period']"):
                    node.set('domain', "[('timestamp', '>=', '{}'),('timestamp', '<', '{}')]"
                             .format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

                res['arch'] = etree.tostring(doc)
        return res


class UserAttendanceRequest(models.Model):
    _name = "user.attendance.request"
    _description = 'User attendance request'
    _inherit = ['hr.generic.request']
    _order = "employee_requests_id, timestamp desc"

    _hr_mail_templates = {'confirm': 'hr_dr_schedule.email_template_confirm_user_attendance_request',
                          'approve': 'hr_dr_schedule.email_template_confirm_approve_user_attendance_request',
                          'reject': 'hr_dr_schedule.email_template_confirm_reject_user_attendance_request',
                          'cancel': 'hr_dr_schedule.email_template_cancel_user_attendance_request'}
    _hr_notifications_mode_param = 'user.attendance.approval.request.notifications.mode'
    _hr_administrator_param = 'user.attendance.approval.request.administrator'
    _hr_second_administrator_param = 'user.attendance.approval.request.second.administrator'

    timestamp = fields.Datetime(string='Marcación', required=True, tracking=True)
    # Estos dos campos son dependientes del algoritmo de asignación de marcaciones
    attendance_activity_id = fields.Many2one('attendance.activity', string='Actividad de asistencia')
    attendance_state_id = fields.Many2one('attendance.state', string='Estado de asistencia')
    has_attendance_activity = fields.Boolean(compute='_compute_has_attendance_activity', store=True,
                                             default=lambda self: self.get_attendance_mode() == '2')
    has_attendance_state = fields.Boolean(compute='_compute_has_attendance_state', store=True,
                                          default=lambda self: self.get_attendance_mode() == '1')

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

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        return super(UserAttendanceRequest, self).create(vals_list)

    def write(self, vals):
        self.validate_module()
        return super(UserAttendanceRequest, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(UserAttendanceRequest, self).unlink()

    def get_attendance_mode(self):
        """
        Obtiene el valor del parámetro 'attendance.mode'
        :return: String con el valor de 'attendance.mode'. Los valores pueden ser:
                 '1': Una tecla de función por tipo de evento
                 '2': Una tecla de función por actividad
                 '3': Sin tecla de función
        """
        attendance_mode = self.env['ir.config_parameter'].sudo().get_param('attendance.mode')
        return attendance_mode

    def _compute_has_attendance_activity(self):
        attendance_mode = self.get_attendance_mode()
        for rec in self:
            rec.has_attendance_activity = (attendance_mode == '2')

    def _compute_has_attendance_state(self):
        attendance_mode = self.get_attendance_mode()
        for rec in self:
            rec.has_attendance_activity = (attendance_mode == '1')
    
    def name_get(self):
        result = []
        for rec in self:
            result.append(
                (
                    rec.id,
                    _("{} {}").format(rec.employee_requests_id.name, rec.timestamp.strftime(self.get_datetime_format()))
                )
            )
        return result

    can_modify_employee = fields.Boolean(compute='_compute_can_modify_employee',
                                         default=lambda self: self._can_modify_employee())

    def _can_modify_employee(self):
        """
        Define si el usuario puede modificar el campo employee_requests_id
        :return: True/False en dependencia de si está en un grupo que pueda modificar el campo.
        """
        if self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_supervisor') \
                or self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_manager'):
            return True
        return False

    def _compute_can_modify_employee(self):
        can_modify = self._can_modify_employee()
        for rec in self:
            rec.can_modify_employee = can_modify

    @api.constrains('timestamp')
    def _constrain_timestamp(self):
        if self.timestamp >= datetime.now():
            raise ValidationError('Lo sentimos, no puede solicitar una marcación en el futuro.')

        max_hours_in_past_to_attendance_request = int(self.env['ir.config_parameter'].sudo().get_param(
            "max.time.in.past.to.request.for.attendance"))
        if self.timestamp < (datetime.now() - timedelta(hours=max_hours_in_past_to_attendance_request)):
            raise ValidationError('Lo sentimos, no puede solicitar una marcación antes de las últimas {} horas.'
                                  .format(max_hours_in_past_to_attendance_request))

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(UserAttendanceRequest, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        # Ocultando dinámicamente las columnas attendance_activity_id y attendance_state_id según el algoritmo de
        # marcación utilizado en el sistema.
        if view_type == 'tree':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='attendance_activity_id']"):
                if self.get_attendance_mode() != '2':
                    node.set('invisible', 'True')
                    doc.remove(node)
            for node in doc.xpath("//field[@name='attendance_state_id']"):
                if self.get_attendance_mode() != '1':
                    node.set('invisible', 'True')
                    doc.remove(node)
            res['arch'] = etree.tostring(doc)

        # Limitando en la vista de formulario el campo del colaborador que solicita a solo
        # los colaboradores del departamento del usuario
        elif view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='employee_requests_id']"):
                if self.env.context.get('limit_employees', False):
                    # resource = self.env['resource.resource'].search([('user_id', '=', self.env.user.id)])
                    # employee = self.env['hr.employee'].search([('resource_id', '=', resource.id)])
                    # node.set('domain', "[('department_id, '=', {})]".format(employee.department_id.id))
                    node.set('domain', "[('department_id.manager_id.user_id', '=', uid)]")
                    # node.set('domain', "[('parent_id.user_id', '=', uid)]")
            res['arch'] = etree.tostring(doc)

        # Adiciono al filtro 'Último periodo' el dominio, limitando la fecha de marcación al último periodo existente
        elif view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)
            if last_period.id:
                start = last_period.start
                # Selecciono el día siguiente para que al comparar y incluya el día final
                end = (datetime.combine(last_period.end, datetime.min.time()) + relativedelta(days=1)).date()
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//filter[@name='filter_last_period']"):
                    node.set('domain', "[('timestamp', '>=', '{}'),('timestamp', '<', '{}')]"
                             .format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
                res['arch'] = etree.tostring(doc)
        return res

    def _create_user_attendance(self):
        """
        Crea una marcación basada en esta solicitud de marcación.
        """

        for rec in self:
            # Obteniendo el usuario de marcación
            device_user = self.env['attendance.device.user'].sudo().search([
                ('employee_id', '=', rec.employee_requests_id.id), ('active', '=', True)], limit=1)
            if not device_user.id:
                raise ValidationError(_('Lo sentimos, el colaborador solicitante ({}) '
                                        'no tiene un usuario de asistencia creado.').
                                      format(rec.employee_requests_id.display_name))

            attendance = self.env['user.attendance'].sudo().create({
                'timestamp': rec.timestamp,
                'mode': 'web',
                'user_id': device_user.id,
                # 'employee_id': rec.employee_requests_id.id,
                'status': rec.attendance_state_id.code if rec.attendance_state_id.id else
                rec.attendance_activity_id.code if rec.attendance_activity_id.id else -1,
                'attendance_state_id': rec.attendance_state_id.id if rec.attendance_state_id.id else None,
                'device_id': device_user.device_id.id,
            })

            # Actualizo en la BD el campo activity_id directamente, pues al crearlo no lo toma ya que activity_id es un
            # campo'related'.
            if rec.attendance_activity_id.id:
                self.env.cr.execute("UPDATE user_attendance SET activity_id = {} WHERE id = {}".format(
                    rec.attendance_activity_id.id, attendance.id))
                self.env.cr.commit()

    def mark_as_approved(self):
        self._create_user_attendance()
        result = super(UserAttendanceRequest, self).mark_as_approved()

        # Enviar mail de aprobacion de solicitud
        self.send_mail_approve_user_attendance_request()

        return result

    def send_mail_approve_user_attendance_request(self):
        """ Envía email de aprobación de solicitud """
        template = self.env.ref('hr_dr_schedule.email_template_confirm_approve_user_attendance_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def mark_as_rejected(self, reason):
        result = super(UserAttendanceRequest, self).mark_as_rejected(reason)

        # Enviar el mail de rechazo al solicitante
        template = self.env.ref('hr_dr_schedule.email_template_confirm_reject_user_attendance_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

        return result

    def get_local_context(self, id):
        # Revisar el contexto y dejar solo lo necesario
        local_context = self.env.context.copy()
        local_context['subject'] = _("Solicitud de aprobación de marcación")
        local_context['request'] = _("ha realizado una solicitud de aprobación de marcación.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id

        local_context['details'] = "Solicitud de aprobación de marcación; fecha de marcación: {}, motivo: {}.".format(self.timestamp.strftime(self.get_datetime_format()), self.commentary)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('hr_dr_schedule.action_user_attendance_request_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_dr_schedule.menu_hr_schedule_main').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        return local_context

    def send_mail_confirm_user_attendance_request(self):
        template = self.env.ref('hr_dr_schedule.email_template_confirm_user_attendance_request', False)
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def _send_notification_to(self, employee_id, level=0):
        """
        Crea la notificación al usuario recibido como parámetro.
        Si la notificación es de primer nivel, envía un email al usuario.

        :param employee_id: Identificador del colaborador que aprueba la notificación.
        :param level: Nivel de aprobación que ya tiene la petición (un nivel menos que el que tendrá esta notificación).
        """

        notification = self.env['hr.notifications'].create({
            'level': level + 1,
            'employee_requests_id': self.employee_requests_id.id,
            'employee_approve_id': employee_id,
            'state': 'pending',
            'send': True if not level else False,
            'res_id': self.id,
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
        })

        if not level:
            # Enviar email de aprobacion / denegacion solo si el colaborador tiene el primer nivel de notificación.
            notification.send_mail(self.get_local_context(notification.id))

    def _send_notifications_bd(self, department, propagate=0, level=0):
        """
        Crea las notificaciones basadas en departamentos para cada administrador de departamento y administradores
        adicionales según los niveles de propagación que se hayan definido.

        Por defecto se enviará una notificación al o a los administradores de departamento de jerarquía inmediata
        superior a quien realiza la solicitud.

        :param department: Departamento a notificar.
        :param propagate: Número de niveles a propagar la notificación. Si el campo 'propagate' tiene un valor positivo,
            esta notificación se extenderá a tantos niveles por encima del departamento ya enviado como se indique en el
            valor (siempre que estos existan). Si el valor de 'propagate' es negativo, entonces la notificación se
            extenderá a todos los niveles superiores al departamento.
        :param level: Nivel de la útlima notificación realizada.

        :return: Retorna un número indicando los niveles de notificación completados.
        """

        scheme_exists = False
        superior_department = department.parent_id

        if self.employee_requests_id.department_id == department and self.is_department_manager(self.employee_requests_id):
            # El usuario pertenece a este departamento y es el administrador o uno de los administradores adicionales del mismo.

            if superior_department:
                # La notificación se realiza en el dpto. superior
                level = self._send_notifications_bd(superior_department, propagate)
        else:
            superior_manager = department.manager_id  # Responsable del departamento
            if superior_manager:
                # Existe responsable superior
                scheme_exists = True
                self._send_notification_to(superior_manager.id, level)

            # Verificamos que este instaldo el modulo 'hr_dr_department_additional_manager' y por ende exista el campo
            # 'additional_manager_ids'
            if 'hr_dr_department_additional_manager' in self.env.registry._init_modules:
                additional_managers = department.additional_manager_ids
                if additional_managers:
                    for additional_manager in additional_managers:
                        scheme_exists = True
                        self._send_notification_to(additional_manager.id, level)

            if scheme_exists:
                level += 1
                if propagate != 0:
                    # Existe una estructura superior y las notificaciones aún deben propagarse hacia el nivel superior.
                    level = self._send_notifications_bd(superior_department, propagate - 1, level)

        return level

    def _admin_confirm_request(self, administrator, level=0):
        """
        Gestiona el cambio de estado de la notificación y el envío de correos electrónicos cuando el modo de
        notificación incluye al administrador.

        :param administrator: Identificador del administrador.
        :param level: Nivel de la última notificación realizada.
        """

        admin_made_request = self.employee_requests_id.id.__str__() == administrator

        if not level and admin_made_request:
            # El único nivel de aprobación es del administrador y este es quien realizó la solicitud.
            self.mark_as_approved()
            # self.state = 'approved'
            # # Enviando correo de aprobación automática
            # self.send_mail_approve_hour_extra_approval_request()
        else:
            self.state = 'pending'

            # Enviando correo de confirmación de solicitud
            self.send_mail_confirm_user_attendance_request()

            # Si el administrador realizó la petición no lo incluyo en los niveles de aprobación
            if not admin_made_request:
                self._send_notification_to(administrator, level)

    @api.model
    def get_datetime_format(self, date_only=False, time_only=False):
        """
        Obtiene el formato de fecha y hora definido en el sistema o toma por defecto %d/%m/%Y %H:%M:%S si no hay uno.

        :param: date_only: Si True solo devuelve el formato de fecha.
        :param: time_only: Si True solo devuelve el formato de hora.
        :return: Cadena de texto con el formato de fecha con las modificaciones según los parámetros.
        """
        lang = self.env.context.get("lang")
        if lang:
            langs = self.env['res.lang'].search([("code", "=", lang)])
            if date_only and langs.date_format:
                return langs.date_format
            if time_only and langs.time_format:
                return langs.time_format
            if langs.date_format and langs.time_format:
                return '{} {}'.format(langs.date_format, langs.time_format)
        return '%d/%m/%Y' if date_only else '%H:%M:%S' if time_only else '%d/%m/%Y %H:%M:%S'


class EmployeeAbsence(models.Model):
    _name = "hr.employee.absence"
    _description = 'Employee absence'
    _order = "employee_id, date asc"
    _inherit = ['mail.thread']

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeAbsence, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))
            res['arch'] = etree.tostring(doc)
        return res

    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, tracking=True)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador", related='employee_id.user_id',
                                       store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador", tracking=True)
    date = fields.Date('Fecha', required=True, tracking=True)
    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", tracking=True)
    employee_shift_id = fields.Many2one('hr.employee.shift', string="Turno", tracking=True)


class EmployeeDelay(models.Model):
    _name = "hr.employee.delay"
    _description = 'Employee delay'
    _order = "employee_id, date asc"
    _inherit = ['mail.thread']

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(EmployeeDelay, self).fields_view_get(view_id, view_type, toolbar=toolbar,
                                                         submenu=submenu)
        # Adiciono al filtro 'Último periodo' el dominio, limitándolo al último periodo existente
        if view_type == 'search':
            last_period = self.env['hr.attendance.period'].sudo().search([], order='start desc', limit=1)
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//filter[@name='filter_last_period']"):
                node.set('domain', "[('attendance_period_id.id', '=', '{}')]".format(str(last_period.id)))
            res['arch'] = etree.tostring(doc)
        return res

    @api.depends('amount')
    def compute_amount(self):
        for rec in self:
            result = Util.seconds2hms(rec.amount)
            rec.amount_hd = result['hd']
            rec.amount_hms = result['c']

    employee_id = fields.Many2one('hr.employee', string="Colaborador", required=True, tracking=True)
    user_employee_id = fields.Many2one('res.users', string="Usuario del colaborador", related='employee_id.user_id',
                                       store=True)
    department_employee_id = fields.Many2one('hr.department', string="Departamento del colaborador", tracking=True)
    user_manager_department_employee_id = fields.Many2one(
        'res.users', string="Usuario administrador del departamento del colaborador", tracking=True)
    date = fields.Date('Fecha', required=True, tracking=True)
    attendance_period_id = fields.Many2one('hr.attendance.period', string="Período", tracking=True)
    employee_shift_id = fields.Many2one('hr.employee.shift', string="Turno", tracking=True)
    event = fields.Selection([
        ('1', 'Al inicio de jornada'),
        ('2', 'Al fin de jornada'),
        ('3', 'Al inicio del descanso'),
        ('4', 'Al fin del descanso'),
        ('5', 'Al inicio del permiso'),
        ('6', 'Al fin del permiso')
    ], 'Evento', tracking=True)
    amount = fields.Float(string='Cantidad', required=True, digits='Schedule', tracking=True)
    amount_hd = fields.Float(string='Cantidad (Valor decimal)', readonly=True, store=True, compute=compute_amount,
                             digits='Schedule')
    amount_hms = fields.Char(string='Cantidad', readonly=True, store=True, compute=compute_amount)