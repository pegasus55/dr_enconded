# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time, timedelta
from .common import convert_utc_time_to_tz
from odoo.exceptions import UserError, ValidationError


class EmployeeDepartmentHistory(models.Model):
    _name = 'hr.employee.department.history'
    _inherit = ['mail.thread']
    _order = "employee_id, date_from desc"
    _description = 'Employee department history'

    @api.model_create_multi
    def create(self, vals_list):
        department_history = super(EmployeeDepartmentHistory, self).create(vals_list)

        if department_history.date_to:
            if department_history.date_from > department_history.date_to:
                # La fecha de inicio del período trabajado en un departamento tiene que ser
                # menor o igual que la fecha de fin.
                raise UserError(
                    _('The start date of the period worked in a department must be less than or equal '
                      'to the end date.'))

        department_history_search = self.env['hr.employee.department.history'].search(
            [('employee_id', '=', department_history.employee_id.id), ('id', '!=', department_history.id)])

        date_to = datetime.utcnow()
        tz_name = department_history.employee_id.tz or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise UserError(_("Local time zone is not defined. You may need to set a time zone in "
                              "your collaborator or user's preferences."))
        date_to = convert_utc_time_to_tz(date_to, tz_name)
        date_to = date_to.date()

        for dhs in department_history_search:
            if not department_history.date_to and not dhs.date_to:
                # Existe un período de trabajo en un departamento sin fecha de fin.
                # Antes de crear un nuevo período debe cerrar el anterior.
                raise UserError(_('There is a work period in a department with no end date. '
                                  'Before creating a new period, you must close the previous one.'))

            if not dhs.date_to:
                if department_history.date_from >= dhs.date_from:
                    raise UserError(
                        _('There is already a work period in a department for the specified period of time.'))

            if not department_history.date_to:
                department_history_date_to = date_to
                if department_history_date_to < department_history.date_from:
                    department_history_date_to = department_history.date_from
            else:
                department_history_date_to = department_history.date_to

            if not dhs.date_to:
                dhs_date_to = date_to
                if dhs_date_to < dhs.date_from:
                    dhs_date_to = dhs.date_from
            else:
                dhs_date_to = dhs.date_to

            if (department_history.date_from >= dhs.date_from and department_history.date_from <= dhs_date_to) or \
                    (department_history_date_to >= dhs.date_from and department_history_date_to <= dhs_date_to) or \
                    (department_history.date_from < dhs.date_from and department_history_date_to > dhs_date_to):
                # Ya existe un período de trabajo en un departamento para el lapso de tiempo especificado.
                raise UserError(_('There is already a work period in a department for the specified period of time.'))

        return department_history

    def write(self, vals):
        department_history = super(EmployeeDepartmentHistory, self).write(vals)

        if self.date_to:
            if self.date_from > self.date_to:
                # La fecha de inicio del período trabajado en un departamento tiene que ser
                # menor o igual que la fecha de fin.
                raise UserError(
                    _('The start date of the period worked in a department must be less than or equal '
                      'to the end date.'))

        department_history_search = self.env['hr.employee.department.history'].search(
            [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)])

        date_to = datetime.utcnow()
        tz_name = self.employee_id.tz or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise UserError(_(
                "Local time zone is not defined. You may need to set a time zone in your collaborator or user's preferences."))
        date_to = convert_utc_time_to_tz(date_to, tz_name)
        date_to = date_to.date()

        for dhs in department_history_search:
            if not self.date_to and not dhs.date_to:
                # Existe un período de trabajo en un departamento sin fecha de fin.
                # Antes de crear un nuevo período debe cerrar el anterior.
                raise UserError(_('There is a work period in a department with no end date. '
                                  'Before creating a new period, you must close the previous one.'))

            if not dhs.date_to:
                if self.date_from >= dhs.date_from:
                    raise UserError(
                        _('There is already a work period in a department for the specified period of time.'))

            if not self.date_to:
                department_history_date_to = date_to
                if department_history_date_to < self.date_from:
                    department_history_date_to = self.date_from
            else:
                department_history_date_to = self.date_to

            if not dhs.date_to:
                dhs_date_to = date_to
                if dhs_date_to < dhs.date_from:
                    dhs_date_to = dhs.date_from
            else:
                dhs_date_to = dhs.date_to

            if (self.date_from >= dhs.date_from and self.date_from <= dhs_date_to) or \
                    (department_history_date_to >= dhs.date_from and department_history_date_to <= dhs_date_to) or \
                    (department_history_date_to < dhs_date_to and self.date_from > dhs.date_from):
                # Ya existe un período de trabajo en un departamento para el lapso de tiempo especificado.
                raise UserError(_('There is already a work period in a department for the specified period of time.'))

        return department_history

    @api.depends('date_from', 'date_to')
    def _compute_time_worked(self):
        for department_history in self:
            date_to = False
            if department_history.date_to:
                date_to = department_history.date_to
            else:
                date_to = datetime.utcnow()
                tz_name = department_history.employee_id.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    raise UserError(_("Local time zone is not defined. You may need to set a time zone in "
                                      "your collaborator or user's preferences."))
                date_to = convert_utc_time_to_tz(date_to, tz_name)
                date_to = date_to.date()

            if department_history.date_from and date_to:
                date_to = date_to + relativedelta(days=1)
                rd = relativedelta(date_to, department_history.date_from)
                department_history.time_worked = _("{} year(s) {} month(s) {} day(s)").format(rd.years, rd.months, rd.days)
                department_history.time_worked_year = rd.years
                department_history.time_worked_month = rd.months
                department_history.time_worked_day = rd.days
            else:
                department_history.time_worked = _("{} year(s) {} month(s) {} day(s)").format(0, 0, 0)
                department_history.time_worked_year = 0
                department_history.time_worked_month = 0
                department_history.time_worked_day = 0

    employee_id = fields.Many2one('hr.employee', string="Collaborator", ondelete='cascade', required=True,
                                  tracking=True, default=lambda self: self._context.get('active_id'))
    department_id = fields.Many2one('hr.department', string='Department', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', help='Leave blank if you still work in this department.', tracking=True)
    time_worked = fields.Char(string="Time worked", compute=_compute_time_worked)
    time_worked_year = fields.Integer(string="Years worked", compute=_compute_time_worked)
    time_worked_month = fields.Integer(string="Months worked", compute=_compute_time_worked)
    time_worked_day = fields.Integer(string="Days worked", compute=_compute_time_worked)