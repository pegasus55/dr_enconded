# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from .common import convert_utc_time_to_tz
from odoo.exceptions import UserError, ValidationError


class EmployeeCompanyHistory(models.Model):
    _name = 'hr.employee.company.history'
    _inherit = ['mail.thread']
    _order = "employee_id, date_from desc"
    _description = 'Employee company history'

    @api.model_create_multi
    def create(self, vals_list):
        company_history = super(EmployeeCompanyHistory, self).create(vals_list)

        if company_history.date_to:
            if company_history.date_from > company_history.date_to:
                # La fecha de inicio del período trabajado en la empresa tiene que ser
                # menor o igual que la fecha de fin.
                raise UserError(
                    _('The start date of the period worked in a company must be less than or equal to the end date.'))

        company_history_search = self.env['hr.employee.company.history'].search(
            [('employee_id', '=', company_history.employee_id.id), ('id', '!=', company_history.id)])

        date_to = datetime.utcnow()
        tz_name = company_history.employee_id.tz or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise UserError(_("Local time zone is not defined. You may need to set a time zone in "
                              "your collaborator or user's preferences."))
        date_to = convert_utc_time_to_tz(date_to, tz_name)
        date_to = date_to.date()

        for chs in company_history_search:
            if not company_history.date_to and not chs.date_to:
                # Existe un período de trabajo en la empresa sin fecha de fin.
                # Antes de crear un nuevo período debe cerrar el anterior.
                raise UserError(_('There is a work period in a company with no end date. '
                                  'Before creating a new period, you must close the previous one.'))

            if not chs.date_to:
                if company_history.date_from >= chs.date_from:
                    raise UserError(_('There is already a work period in a company for the specified period of time.'))

            if not company_history.date_to:
                company_history_date_to = date_to
                if company_history_date_to < company_history.date_from:
                    company_history_date_to = company_history.date_from
            else:
                company_history_date_to = company_history.date_to

            if not chs.date_to:
                chs_date_to = date_to
                if chs_date_to < chs.date_from:
                    chs_date_to = chs.date_from
            else:
                chs_date_to = chs.date_to

            if (company_history.date_from >= chs.date_from and company_history.date_from <= chs_date_to) or \
                    (company_history_date_to >= chs.date_from and company_history_date_to <= chs_date_to) or \
                    (company_history_date_to < chs_date_to and company_history.date_from > chs.date_from):
                # Ya existe un período de trabajo en la empresa para el lapso de tiempo especificado.
                raise UserError(_('There is already a work period in a company for the specified period of time.'))

        return company_history

    def write(self, vals):
        company_history = super(EmployeeCompanyHistory, self).write(vals)

        if self.date_to:
            if self.date_from > self.date_to:
                # La fecha de inicio del período trabajado en la empresa tiene que ser
                # menor o igual que la fecha de fin.
                raise UserError(_('The start date of the period worked in a company must be '
                                  'less than or equal to the end date.'))

        date_to = datetime.utcnow()
        tz_name = self.employee_id.tz or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            raise UserError(_("Local time zone is not defined. You may need to set a time zone in "
                              "your collaborator or user's preferences."))
        date_to = convert_utc_time_to_tz(date_to, tz_name)
        date_to = date_to.date()

        company_history_search = self.env['hr.employee.company.history'].search(
            [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)])
        for chs in company_history_search:

            if not self.date_to and not chs.date_to:
                # Existe un período de trabajo en la empresa sin fecha de fin.
                # Antes de crear un nuevo período debe cerrar el anterior.
                raise UserError(_('There is a work period in a company with no end date. Before creating a new period, '
                                  'you must close the previous one.'))

            if not chs.date_to:
                if self.date_from >= chs.date_from:
                    raise UserError(
                        _('There is already a work period in a company for the specified period of time.'))

            if not self.date_to:
                company_history_date_to = date_to
                if company_history_date_to < self.date_from:
                    company_history_date_to = self.date_from
            else:
                company_history_date_to = self.date_to

            if not chs.date_to:
                chs_date_to = date_to
                if chs_date_to < chs.date_from:
                    chs_date_to = chs.date_from
            else:
                chs_date_to = chs.date_to

            if (self.date_from >= chs.date_from and self.date_from <= chs_date_to) or \
                    (company_history_date_to >= chs.date_from and company_history_date_to <= chs_date_to) or \
                    (company_history_date_to < chs_date_to and self.date_from > chs.date_from):
                raise UserError(
                    _('There is already a work period in the company for the specified period of time.'))

        return company_history

    @api.depends('date_from', 'date_to')
    def _compute_time_worked(self):
        for company_history in self:
            date_to = False
            if company_history.date_to:
                date_to = company_history.date_to
            else:
                date_to = datetime.utcnow()
                tz_name = company_history.employee_id.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    raise UserError(_("Local time zone is not defined. You may need to set a time zone in "
                                      "your collaborator or user's preferences."))
                date_to = convert_utc_time_to_tz(date_to, tz_name)
                date_to = date_to.date()

            if company_history.date_from and date_to:
                date_to = date_to + relativedelta(days=1)
                rd = relativedelta(date_to, company_history.date_from)
                company_history.time_worked = _("{} year(s) {} month(s) {} day(s)").format(rd.years, rd.months, rd.days)
                company_history.time_worked_year = rd.years
                company_history.time_worked_month = rd.months
                company_history.time_worked_day = rd.days
                company_history.time_worked_total_day = (date_to - company_history.date_from).days
            else:
                company_history.time_worked = _("{} year(s) {} month(s) {} day(s)").format(0, 0, 0)
                company_history.time_worked_year = 0
                company_history.time_worked_month = 0
                company_history.time_worked_day = 0
                company_history.time_worked_total_day = 0

    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, ondelete='cascade',
                                  tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', help='Leave blank if you still work in this department.', tracking=True)
    time_worked = fields.Char(string="Time worked", compute=_compute_time_worked)
    time_worked_year = fields.Integer(string="Years worked", compute=_compute_time_worked)
    time_worked_month = fields.Integer(string="Months worked", compute=_compute_time_worked)
    time_worked_day = fields.Integer(string="Days worked", compute=_compute_time_worked)
    time_worked_total_day = fields.Integer(string="Total days worked", compute=_compute_time_worked)