# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class ComputeAttendance(models.TransientModel):
    _name = "hr.compute.attendance"
    _description = 'Compute attendance'

    def convert_time_to_utc(self, dt, tz_name=None):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert. In case of no tz_name passed,
        this method will try to find the timezone in context or the login user record

        @return: an instance of datetime object
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise ValidationError(_("La zona horaria local no está definida. "
                                    "Es posible que deba establecer una zona horaria en el colaborador "
                                    "o en las preferencias de su usuario."))
        local = pytz.timezone(tz_name)
        local_dt = local.localize(dt, is_dst=None)
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
    
    def action_compute_attendance(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].sudo().search([
                ('active', '=', True),
                ('employee_admin', '=', False),
                ('state', 'in', ['affiliate', 'temporary', 'intern'])
            ])
        for employee in employees:
            date_from = self.date_from
            while date_from <= self.date_to:
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
                    # Borrar las horas nocturnas para el día y colaborador actual si es que existen.
                    if self.delete_actual_compute_attendance:
                        self.env['hr.employee.shift'].delete_hour_night_by_day_and_employee(date_from, employee)
                    # Buscar rangos de timbradas para ese día y poner la hora extra para días sin horario
                    self.env['hr.employee.shift'].create_hour_extra_day_not_shift(
                        employee,
                        self.attendance_period_id,
                        date_from,
                        date_i,
                        date_f,
                        self.delete_actual_compute_attendance)
                else:
                    for es in employee_shift:
                        if self.assign_attendance_again:
                            attendance_mode = self.env['ir.config_parameter'].sudo().get_param('attendance.mode')
                            es.assign_attendance(int(attendance_mode))

                        is_holiday = False
                        holidays = self.env['hr.holiday'].search_count([
                            ('date', '=', date_from)
                        ])
                        if holidays > 0:
                            is_holiday = True

                        if is_holiday:
                            # Borrar las horas nocturnas para el dia y colaborador actual si es que existen
                            es.delete_hour_night_by_day_and_employee(date_from, employee)

                            es.create_hour_extra_day_not_shift(
                                employee,
                                self.attendance_period_id,
                                date_from,
                                date_i,
                                date_f,
                                self.delete_actual_compute_attendance)
                        else:
                            es.compute_attendance(date_from, self.attendance_period_id,
                                                  self.delete_actual_compute_attendance)

                date_from = date_from + relativedelta(days=1)

    @api.onchange('department_ids')
    def _onchange_departments(self):
        employees = self.env['hr.employee'].sudo().search([('department_id', 'in', self.department_ids.ids)])
        result = [e.id for e in employees]
        self.employee_ids = [(6, 0, result)]

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('end', '<=', datetime.utcnow().date()),
            ('state', 'in', ['open'])
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False

    @api.onchange('attendance_period_id')
    def _onchange_attendance_period_id(self):
        for rec in self:
            if rec.attendance_period_id:
                rec.date_from = rec.attendance_period_id.start
                rec.date_to = rec.attendance_period_id.end

    attendance_period_id = fields.Many2one('hr.attendance.period', string='Período de asistencia',
                                           default=_default_period_id)
    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)
    _MODE = [
        ('employee', 'Colaborador'),
        ('department', 'Departamento')
    ]
    input_mode = fields.Selection(_MODE, string='Modo', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    employee_ids = fields.Many2many('hr.employee', string='Colaboradores')
    assign_attendance_again = fields.Boolean(string='Asignar marcaciones nuevamente', default=True)
    delete_actual_compute_attendance = fields.Boolean(string='Eliminar la asistencia calculada', default=True)