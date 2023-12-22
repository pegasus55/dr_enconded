# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class CorrectUserAttendanceState(models.TransientModel):
    _name = "correct.user.attendance.state"
    _description = 'Correct user attendance state'

    def convert_time_to_utc(self, dt, tz_name=None):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find
        the timezone in context or the login user record

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
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)

    def search_user_attendance(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].search([('active', '=', True),
                                                        ('employee_admin', '=', False),
                                                        ('state', 'in', ['affiliate', 'temporary', 'intern'])])
        if self.date_from and self.date_to and self.start and self.end and self.attendance_state_id:
            result = []

            self.user_attendance_ids = [(6, 0, result)]

            hours_start = int(self.start)
            hours_fraction_start = self.start - int(self.start)
            minutes_start = hours_fraction_start * 60
            minutes_fraction_start = minutes_start - int(minutes_start)
            seconds_start = minutes_fraction_start * 60

            hours_end = int(self.end)
            hours_fraction_end = self.end - int(self.end)
            minutes_end = hours_fraction_end * 60
            minutes_fraction_end = minutes_end - int(minutes_end)
            seconds_end = minutes_fraction_end * 60

            for e in employees:
                date_i = self.date_from + relativedelta(hour=0, minute=0, second=0)
                date_f = self.date_to + relativedelta(hour=23, minute=59, second=59)
                date_i = self.convert_time_to_utc(date_i, e.tz)
                date_f = self.convert_time_to_utc(date_f, e.tz)

                user_attendance_ids = self.env['user.attendance'].search([
                    ('employee_id', '=', e.id),
                    ('attendance_state_id', '!=', self.attendance_state_id.id),
                    ('timestamp', '>=', date_i),
                    ('timestamp', '<=', date_f),
                ], order='employee_id, timestamp')

                for ua in user_attendance_ids:
                    date_start = ua.timestamp + relativedelta(
                        hour=hours_start, minute=int(minutes_start), second=int(seconds_start))
                    date_start = self.convert_time_to_utc(date_start, e.tz)
                    date_end = ua.timestamp + relativedelta(
                        hour=hours_end, minute=int(minutes_end), second=int(seconds_end))
                    date_end = self.convert_time_to_utc(date_end, e.tz)
                    if ua.timestamp >= date_start and ua.timestamp <= date_end:
                        result.append(ua.id)

            self.user_attendance_ids = [(6, 0, result)]

    def get_attendance_state_ids(self, device):
        attendance_states = {}
        if len(device.attendance_device_state_line_ids) > 0:
            for attendance_state in device.attendance_device_state_line_ids:
                attendance_states[attendance_state.attendance_state_id.code] = attendance_state.attendance_state_id.id
        else:
            config_parameter = self.env['ir.config_parameter'].sudo()
            if config_parameter.get_param('attendance.state.ids'):
                if config_parameter.get_param('attendance.state.ids') != '':
                    for id in config_parameter.get_param('attendance.state.ids').split(','):
                        attendance_state_id = int(id)
                        attendance_state = self.env['attendance.state'].sudo().search([
                            ('id', '=', attendance_state_id)], limit=1)
                        if len(attendance_state) > 0:
                            attendance_states[attendance_state.code] = attendance_state.id
        return attendance_states
    
    def action_correct_user_attendance_state(self):
        for ua in self.user_attendance_ids:
            ua.status = self.replace_attendance_state_id.code
            attendance_states = self.get_attendance_state_ids(ua.device_id)
            ua.attendance_state_id = attendance_states[self.replace_attendance_state_id.code]

        tree_view_id = self.env.ref('hr_dr_schedule.view_attendance_data_tree').id
        form_view_id = self.env.ref('hr_dr_schedule.view_attendance_data_form').id
        search_view_id = self.env.ref('hr_dr_schedule.user_attendance_data_search_view').id
        return {
                'type': 'ir.actions.act_window',
                'name': 'Todas las marcaciones',
                'res_model': 'user.attendance',
                'target': 'current',
                'view_mode': 'tree',
                'context': {'search_default_group_by_employee': True, 'search_default_filter_last_period': 1,
                            'search_default_group_by_day': True},
                'search_view_id': [search_view_id, 'search'],
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')]
                }

    @api.onchange('department_ids')
    def _onchange_departments(self):
        employees = self.env['hr.employee'].sudo().search([('department_id', 'in', self.department_ids.ids)])
        result = [e.id for e in employees]
        self.employee_ids = [(6, 0, result)]

    @api.onchange('employee_ids', 'date_from', 'date_to', 'start', 'end', 'attendance_state_id')
    def _onchange_input_user_attendance(self):
        self.search_user_attendance()

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]
        self.user_attendance_ids = [(6, 0, [])]

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
    start = fields.Float(string="Inicio", required=True)
    end = fields.Float(string="Fin", required=True)
    attendance_state_id = fields.Many2one('attendance.state', string='Tipo de evento distinto a',
                                          help='Campo técnico para vincular el tipo de evento en el dispositivo',
                                          required=True)
    activity_id = fields.Many2one('attendance.activity', string='Actividad',
                                  related='attendance_state_id.activity_id')
    code = fields.Integer(string='Código', related='attendance_state_id.code')
    replace_attendance_state_id = fields.Many2one('attendance.state', string='Reemplazar por el tipo de evento',
                                                  required=True)
    replace_activity_id = fields.Many2one('attendance.activity', string='Actividad',
                                          related='replace_attendance_state_id.activity_id')
    replace_code = fields.Integer(string='Código', related='replace_attendance_state_id.code')
    _MODE = [
        ('employee', 'Colaborador'),
        ('department', 'Departamento')
    ]
    input_mode = fields.Selection(_MODE, string='Modo', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    employee_ids = fields.Many2many('hr.employee', string='Colaboradores')
    user_attendance_ids = fields.Many2many('user.attendance', string='Marcaciones')