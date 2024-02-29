# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from dateutil.relativedelta import relativedelta
import datetime
import pytz
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class AssignSchedule(models.TransientModel):
    _name = "hr.assign.schedule"
    _description = 'Assign schedule'

    def convert_time_to_utc(self, dt, tz_name=None):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find
        the timezone in context or the login user record

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
    
    def action_assign_schedule(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].sudo().search([('active', '=', True),
                                                               ('employee_admin', '=', False),
                                                               ('state', 'in', ['affiliate', 'temporary', 'intern'])])
        if not self.line_ids:
            raise UserError(_("Debe especificar al menos un horario."))

        if self.delete_actual_shift:
            dt_date_from = self.date_from + relativedelta(hour=0, minute=0, second=0)
            dt_date_to = self.date_to + relativedelta(hour=23, minute=59, second=59)
            employee_ids = [id for id in employees.ids]
            actual_employee_shift = self.env['hr.employee.shift'].sudo().search([
                ('employee_id', 'in', employee_ids),
                ('planned_start', '>=', dt_date_from),
                ('planned_start', '<=', dt_date_to)
            ])
            for aes in actual_employee_shift:
                aes.unlink()

        for employee in employees:
            date_from = self.date_from
            while date_from <= self.date_to:
                for line in self.line_ids:
                    frequency = int(line.frequency)
                    while frequency > 0 and date_from <= self.date_to:
                        rc_attendances = self.env['resource.calendar.attendance'].sudo().search([
                            ('calendar_id', '=', line.resource_calendar_id.id),
                            ('dayofweek', '=', str(date_from.weekday()))
                        ], order='sequence')

                        if len(rc_attendances) > 0:
                            planned_start = datetime.time(int(rc_attendances[0].hour_from),
                                                          int((rc_attendances[0].hour_from -
                                                               int(rc_attendances[0].hour_from)) * 60), 0)
                            planned_end = datetime.time(int(rc_attendances[len(rc_attendances)-1].hour_to),
                                                        int((rc_attendances[len(rc_attendances)-1].hour_to -
                                                             int(rc_attendances[len(rc_attendances)-1].hour_to)) * 60)
                                                        , 0)

                            dt_planned_start = datetime.datetime.combine(date_from, planned_start)
                            if planned_start > planned_end:
                                dt_planned_end = datetime.datetime.combine(date_from + relativedelta(days=1),
                                                                           planned_end)
                            else:
                                dt_planned_end = datetime.datetime.combine(date_from, planned_end)

                            dt_planned_start = self.convert_time_to_utc(dt_planned_start, employee.tz)
                            dt_planned_end = self.convert_time_to_utc(dt_planned_end, employee.tz)

                            employee_shift = self.env['hr.employee.shift'].sudo().create({
                                'resource_calendar_id': line.resource_calendar_id.id,
                                'courtesy_start': line.resource_calendar_id.courtesy_start,
                                'courtesy_end': line.resource_calendar_id.courtesy_end,
                                'employee_id': employee.id,
                                'department_employee_id': employee.department_id.id,
                                'dayofweek': str(date_from.weekday()),
                                'planned_start': dt_planned_start,
                                'planned_end': dt_planned_end,
                                'start_from': dt_planned_start - relativedelta(
                                    hours=line.resource_calendar_id.max_hours_before_start),
                                'end_to': dt_planned_end + relativedelta(
                                    hours=line.resource_calendar_id.max_hours_after_end),
                            })

                            order = 0
                            if len(rc_attendances) > 1:
                                for rca in rc_attendances:
                                    if order > 0:
                                        previous_rca = rc_attendances[order - 1]

                                        break_planned_start = datetime.time(int(previous_rca.hour_to),
                                                                            int((previous_rca.hour_to -
                                                                                 int(previous_rca.hour_to)) * 60), 0)
                                        dt_break_planned_start = datetime.datetime.combine(date_from,
                                                                                           break_planned_start)
                                        dt_break_planned_start_utc = self.convert_time_to_utc(dt_break_planned_start,
                                                                                              employee.tz)

                                        break_planned_end = datetime.time(int(rca.hour_from),
                                                                          int((rca.hour_from -
                                                                               int(rca.hour_from)) * 60), 0)
                                        dt_break_planned_end = datetime.datetime.combine(date_from, break_planned_end)
                                        dt_break_planned_end_utc = self.convert_time_to_utc(dt_break_planned_end,
                                                                                            employee.tz)

                                        create_break = True
                                        day_break = False
                                        if dt_break_planned_start.hour > dt_break_planned_end.hour:
                                            day_break = True
                                            if dt_break_planned_start.hour == 23 and \
                                                    dt_break_planned_start.minute == 59 and \
                                                    dt_break_planned_end.hour == 0 and dt_break_planned_end.minute == 0:
                                                create_break = False

                                        if create_break:
                                            if day_break:
                                                dt_break_planned_end = datetime.datetime.combine(
                                                    date_from + relativedelta(days=1), break_planned_end)
                                                dt_break_planned_end_utc = self.convert_time_to_utc(
                                                    dt_break_planned_end,
                                                    employee.tz)
                                                self.env['hr.employee.shift.break'].sudo().create({
                                                    'employee_shift_id': employee_shift.id,
                                                    'planned_start': dt_break_planned_start_utc,
                                                    'planned_end': dt_break_planned_end_utc,
                                                })
                                            else:
                                                self.env['hr.employee.shift.break'].sudo().create({
                                                    'employee_shift_id': employee_shift.id,
                                                    'planned_start': dt_break_planned_start_utc,
                                                    'planned_end': dt_break_planned_end_utc,
                                                })
                                    order += 1

                        frequency -= 1
                        date_from = date_from + relativedelta(days=1)

        tree_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_tree').id
        form_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_form').id
        search_view_id = self.env.ref('hr_dr_schedule.hr_employee_shift_search').id
        return {
                'type': 'ir.actions.act_window',
                'name': 'Todos los turnos',
                'res_model': 'hr.employee.shift',
                'target': 'current',
                'view_mode': 'tree',
                'context': {'search_default_filter_last_period': True, 'search_default_group_department_employee_id': 1,
                            'search_default_group_employee_id': 1, 'search_default_group_year_planned_start': 1},
                'search_view_id': [search_view_id, 'search'],
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')]
                }

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        employees = self.env['hr.employee'].sudo().search([
            ('department_id', 'in', self.department_ids.ids)])
        result = [e.id for e in employees]
        self.employee_ids = [(6, 0, result)]

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]

    @api.onchange('date_from')
    def _onchange_date_from(self):
        for rec in self:
            if rec.date_from:
                rec.dayofweek_from = str(rec.date_from.weekday())

    @api.onchange('date_to')
    def _onchange_date_to(self):
        for rec in self:
            if rec.date_to:
                rec.dayofweek_to = str(rec.date_to.weekday())

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
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
    dayofweek_from = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo')
    ], 'Día de la semana', required=True, index=True, default='0')
    date_to = fields.Date('Hasta', required=True)
    dayofweek_to = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo')
    ], 'Día de la semana', required=True, index=True, default='0')
    _MODE = [
        ('employee', 'Colaborador'),
        ('department', 'Departamento')
    ]
    input_mode = fields.Selection(_MODE, string='Modo', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departamentos')
    employee_ids = fields.Many2many('hr.employee', string='Colaboradores')
    line_ids = fields.One2many('hr.assign.schedule.line', 'assign_schedule_id', 'Detalle')
    delete_actual_shift = fields.Boolean(string='Eliminar turnos asignados', default=True)


class AssignScheduleLine(models.TransientModel):
    _name = "hr.assign.schedule.line"
    _description = 'Assign schedule detail'
    _order = "sequence"
    _sql_constraints = [(
        'assign_schedule_id_sequence_unique', 'UNIQUE (assign_schedule_id,sequence)',
        'El orden con el que se asignan los horarios no puede repetirse.'
    )]

    assign_schedule_id = fields.Many2one('hr.assign.schedule', 'Cabecera')
    sequence = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Orden', required=True, default='1')
    resource_calendar_id = fields.Many2one('resource.calendar', string="Horario", required=True)
    frequency = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),
    ], string='Frecuencia', required=True, default='7')