# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from datetime import datetime
from calendar import isleap
from calendar import monthrange


class RetiredEmployeeSalary(models.Model):
    _name = 'retired.employee.salary'
    _description = 'Retired collaborator salary'
    _inherit = ['hr.generic.request']
    _order = "period_start desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_retired_employee_salary',
            'confirm_direct': 'hr_dr_payroll_base.email_template_confirm_direct_approve_retired_employee_salary',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_retired_employee_salary',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_retired_employee_salary',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancel_retired_employee_salary',
            'paid': 'hr_dr_payroll_base.email_template_retired_employee_salary_notify_treasury'
        }
    _hr_notifications_mode_param = 'retired.employee.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.salary.second.administrator'

    def _default_period_start(self):
        period_start = datetime.utcnow().date() + relativedelta(day=1)
        return period_start

    def _default_period_end(self):
        max_days_month = calendar.monthrange(datetime.utcnow().year, datetime.utcnow().month)[1]
        period_end = datetime.utcnow().date() + relativedelta(day=max_days_month)
        return period_end

    @api.onchange('period_start')
    def on_change_period_start(self):
        if self.period_start:
            max_days_month = calendar.monthrange(self.period_start.year, self.period_start.month)[1]
            self.period_end = self.period_start + relativedelta(day=max_days_month)

    def unlink(self):
        for res in self:
            if res.state != 'draft':
                raise ValidationError(_('You can only delete retired collaborator salary in draft status.'))
        return super(RetiredEmployeeSalary, self).unlink()

    def name_get(self):
        result = []
        for res in self:
            result.append(
                (
                    res.id,
                    _("{} - {}").format(res.period_start, res.period_end)
                )
            )
        return result

    def _get_value_and_days_to_pay(self, e):
        days_to_pay = 0
        value = 0
        if e.departure_date:
            if e.departure_date < self.period_start:
                days_to_pay = 30
                value = e.pension
            elif self.period_start <= e.departure_date < self.period_end:
                difference = self.period_end - e.departure_date
                days_to_pay = difference.days

                if self.period_end.month in [1, 3, 5, 7, 8, 10, 12]:
                    days_to_pay = days_to_pay - 1

                if self.period_end.month == 2:
                    if isleap(self.period_end.year):
                        days_to_pay = days_to_pay + 1
                    else:
                        days_to_pay = days_to_pay + 2

                period_days = 30
                value = round(e.pension * days_to_pay / period_days, 2)
            else:
                days_to_pay = 0
                value = 0
        return days_to_pay, value

    def _get_value_and_days_to_pay_death(self, e):
        days_to_pay = 0
        value = 0
        if e.date_of_death:
            if e.date_of_death < self.period_start:
                days_to_pay = 30
                value = e.pension
            elif self.period_start <= e.date_of_death < self.period_end:
                difference = e.date_of_death - self.period_start
                days_to_pay = difference.days + 1

                if self.period_end.month in [1, 3, 5, 7, 8, 10, 12]:
                    days_to_pay = days_to_pay - 1

                if self.period_end.month == 2:
                    if isleap(self.period_end.year):
                        days_to_pay = days_to_pay + 1
                    else:
                        days_to_pay = days_to_pay + 2

                if days_to_pay > 30:
                    days_to_pay = 30

                if days_to_pay < 0:
                    days_to_pay = 0

                period_days = 30
                value = round(days_to_pay * e.pension / period_days, 2)
            else:
                days_to_pay = 0
                value = 0

        return days_to_pay, value

    def action_create_update_lines(self, delete_actual_lines=True):
        if delete_actual_lines:
            line_ids = self.env['retired.employee.salary.line'].with_context(
                active_test=False).search([('retired_employee_salary_id', '=', self.id)])
            if line_ids:
                line_ids.unlink()

        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', False),
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['retired']),
            ('departure_date', '<', self.period_end),
            ('single_payment_after_death', '=', False),
        ])

        for e in employees:
            if e.departure_date:
                if e.date_of_death:
                    date_of_death_in_period = e.date_of_death + relativedelta(year=self.period_start.year,
                                                                              month=self.period_start.month)
                    rd = relativedelta(date_of_death_in_period, e.date_of_death)
                    if rd.years == 0 and rd.months == 0:
                        # Se está pagando el mes en que murió, se debe pagar un proporcional
                        days_to_pay, value = self._get_value_and_days_to_pay_death(e)
                        self.env['retired.employee.salary.line'].create({
                            'retired_employee_salary_id': self.id,
                            'employee_id': e.id,
                            'end_date': e.departure_date,
                            'date_of_death': e.date_of_death,
                            'days_to_pay': days_to_pay,
                            'value': value,
                            'automatic': True,
                        })
                    else:
                        if rd.years == 0 and 12 >= rd.months > 0 or rd.years == 1 and rd.months == 0:
                            self.env['retired.employee.salary.line'].create({
                                'retired_employee_salary_id': self.id,
                                'employee_id': e.id,
                                'end_date': e.departure_date,
                                'date_of_death': e.date_of_death,
                                'days_to_pay': (self.period_end - self.period_start).days + 1,
                                'value': e.pension,
                                'automatic': True,
                            })
                        else:
                            days_to_pay, value = self._get_value_and_days_to_pay(e)
                            self.env['retired.employee.salary.line'].create({
                                'retired_employee_salary_id': self.id,
                                'employee_id': e.id,
                                'end_date': e.departure_date,
                                'date_of_death': e.date_of_death,
                                'days_to_pay': days_to_pay,
                                'value': value,
                                'automatic': True,
                            })
                else:
                    days_to_pay, value = self._get_value_and_days_to_pay(e)
                    self.env['retired.employee.salary.line'].create({
                        'retired_employee_salary_id': self.id,
                        'employee_id': e.id,
                        'end_date': e.departure_date,
                        'days_to_pay': days_to_pay,
                        'value': value,
                        'automatic': True,
                    })
            else:
                raise ValidationError(_('You must set the departure date for the collaborator {}.').format(e.name))

        self.write({
            'state': 'calculated',
        })

    def mark_as_reviewed(self):
        self.state = 'reviewed'

    def mark_as_draft(self):
        super(RetiredEmployeeSalary, self).mark_as_draft()
        line_ids = self.env['retired.employee.salary.line'].with_context(
            active_test=False).search([('retired_employee_salary_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

    def action_done(self):
        self.write({'state': 'done'})

    def action_paid(self):
        pass

    def action_view_payment(self):
        pass

    def action_cancel(self):
        pass

    period_start = fields.Date(string='Period start', required=True, default=_default_period_start, tracking=True)
    period_end = fields.Date(string='Period end', required=True, default=_default_period_end, tracking=True)
    date = fields.Date(string='Posting date', default=fields.Date.today(), help='', tracking=True)
    state = fields.Selection(selection_add=[
        ('calculated', 'Calculated'),
        ('reviewed', 'Reviewed'),
        ('done', 'Done')])
    retired_employee_salary_line_ids = fields.One2many('retired.employee.salary.line', 'retired_employee_salary_id',
                                                       string="Retired collaborator salary detail")


class RetiredEmployeeSalaryLine(models.Model):
    _name = 'retired.employee.salary.line'
    _description = 'Retired collaborator salary detail'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('res_employee_id_uniq', 'UNIQUE (retired_employee_salary_id,employee_id)',
         'The collaborator cannot be repeated for the same retired salary payment.')
    ]

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.departure_date
            self.automatic = False
            days_to_pay, value = self.retired_employee_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value

    retired_employee_salary_id = fields.Many2one('retired.employee.salary', string="Retired collaborator salary",
                                                 required=True, readonly=True, ondelete='cascade')
    state = fields.Selection(related='retired_employee_salary_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True,
                                  ondelete='cascade')
    end_date = fields.Date(string='Retired date', tracking=True)
    date_of_death = fields.Date(string='Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)
    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class RetiredEmployeeThirteenthSalary(models.Model):
    _name = 'retired.employee.thirteenth.salary'
    _description = 'Retired collaborator thirteenth salary'
    _inherit = ['hr.generic.request']
    _order = "period_start desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_retired_employee_thirteenth_salary',
            'confirm_direct':
                'hr_dr_payroll_base.email_template_confirm_direct_approve_retired_employee_thirteenth_salary',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_retired_employee_thirteenth_salary',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_retired_employee_thirteenth_salary',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancel_retired_employee_thirteenth_salary',
            'paid': 'hr_dr_payroll_base.email_template_retired_employee_thirteenth_salary_notify_treasury'
        }

    _hr_notifications_mode_param = 'retired.employee.thirteenth.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.thirteenth.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.thirteenth.salary.second.administrator'

    def _default_year(self):
        return datetime.utcnow().year

    @api.onchange('year')
    def on_change_year(self):
        if self.year:
            period_start = datetime.utcnow().date() + relativedelta(day=1, month=12, year=self.year - 1)
            period_end = datetime.utcnow().date() + relativedelta(day=30, month=11, year=self.year)
            self.period_start = period_start
            self.period_end = period_end

    def unlink(self):
        for rets in self:
            if rets.state != 'draft':
                raise ValidationError(_('You can only delete retired collaborator thirteenth salary in draft status.'))
        return super(RetiredEmployeeThirteenthSalary, self).unlink()

    def name_get(self):
        result = []
        for rets in self:
            result.append(
                (
                    rets.id,
                    _("{} {}").format(rets.year, dict(self._fields['state'].selection).get(rets.state) )

                )
            )
        return result

    def _get_value_and_days_to_pay(self, e):
        days_to_pay = 0
        value = 0

        if e.departure_date:
            date_start = self.period_start
            date_end = self.period_end
            if e.departure_date < date_start:
                days_to_pay = 360
                value = e.pension
            elif e.departure_date >= date_start and e.departure_date < date_end:
                days_to_pay = 0
                for i in range(0, 12):
                    date_start_i = date_start + relativedelta(months=i)
                    date_start_f = date_start + relativedelta(months=i)
                    days_of_month = monthrange(date_start_i.year, date_start_i.month)
                    date_start_f = date_start_f + relativedelta(day=days_of_month[1])

                    if e.departure_date >= date_start_i and e.departure_date <= date_start_f:

                        difference = date_start_f - e.departure_date
                        days_to_pay_per_month = difference.days

                        if date_start_f.month in [1, 3, 5, 7, 8, 10, 12]:
                            days_to_pay_per_month = days_to_pay_per_month - 1

                        if date_start_f.month == 2:
                            if isleap(date_start_f.year):
                                days_to_pay_per_month = days_to_pay_per_month + 1
                            else:
                                days_to_pay_per_month = days_to_pay_per_month + 2

                        if days_to_pay_per_month > 30:
                            days_to_pay_per_month = 30

                        if days_to_pay_per_month < 0:
                            days_to_pay_per_month = 0

                        days_to_pay = days_to_pay + days_to_pay_per_month

                    else:
                        if e.departure_date < date_start_i:
                            days_to_pay = days_to_pay + 30

                period_days = 360
                value = days_to_pay * e.pension / period_days
            else:
                days_to_pay = 0
                value = 0

        return days_to_pay, value

    def action_create_update_lines(self, delete_actual_lines=True):
        if delete_actual_lines:
            line_ids = self.env['retired.employee.thirteenth.salary.line'].with_context(
                active_test=False).search([('retired_employee_thirteenth_salary_id', '=', self.id)])
            if line_ids:
                line_ids.unlink()

        limit_date = datetime.utcnow().date() + relativedelta(day=30, month=11, year=self.year)

        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', False),
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['retired']),
            ('departure_date', '<', limit_date),
            ('single_payment_after_death', '=', False),
        ])

        for e in employees:
            if e.departure_date:
                if e.date_of_death:
                    if e.date_of_death >= self.period_start and e.date_of_death <= self.period_end:
                        self.env['retired.employee.thirteenth.salary.line'].create({
                            'retired_employee_thirteenth_salary_id': self.id,
                            'employee_id': e.id,
                            'end_date': e.departure_date,
                            'date_of_death': e.date_of_death,
                            'days_to_pay': (self.period_end - self.period_start).days + 1,
                            'value': e.pension,
                            'automatic': True,
                        })
                else:
                    days_to_pay, value = self._get_value_and_days_to_pay(e)

                    self.env['retired.employee.thirteenth.salary.line'].create({
                        'retired_employee_thirteenth_salary_id': self.id,
                        'employee_id': e.id,
                        'end_date': e.departure_date,
                        'days_to_pay': days_to_pay,
                        'value': value,
                        'automatic': True,
                    })
            else:
                raise ValidationError(_('You must set the retirement date for the collaborator {}.'.format(e.name)))

        self.write({
            'state': 'calculated',
        })

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        return self

    def mark_as_draft(self):
        super(RetiredEmployeeThirteenthSalary, self).mark_as_draft()
        line_ids = self.env['retired.employee.thirteenth.salary.line'].with_context(
            active_test=False).search([('retired_employee_thirteenth_salary_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

    def action_done(self):
        self.write({'state': 'done'})

    def action_paid(self):
        pass

    def action_view_payment(self):
        pass

    def action_cancel(self):
        pass

    year = fields.Integer(string='Year', required=True, default=_default_year, tracking=True)
    state = fields.Selection(selection_add=[
        ('calculated', 'Calculated'),
        ('reviewed', 'Reviewed'),
        ('done', 'Done')])
    period_start = fields.Date(string='Period start', tracking=True)
    period_end = fields.Date(string='Period end', tracking=True)
    date = fields.Date(string='Posting date', default=fields.Date.today(), help='', tracking=True)
    retired_employee_thirteenth_salary_line_ids = fields.One2many(
        'retired.employee.thirteenth.salary.line', 'retired_employee_thirteenth_salary_id',
        string="Retired collaborator thirteenth salary detail")


class RetiredEmployeeThirteenthSalaryLine(models.Model):
    _name = 'retired.employee.thirteenth.salary.line'
    _description = 'Retired collaborator thirteenth salary detail'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('rets_employee_id_uniq', 'UNIQUE (retired_employee_thirteenth_salary_id,employee_id)',
         'The collaborator cannot be repeated for the same payment of the thirteenth salary.')
    ]

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.departure_date
            self.automatic = False
            days_to_pay, value = self.retired_employee_thirteenth_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value

    retired_employee_thirteenth_salary_id = fields.Many2one('retired.employee.thirteenth.salary',
                                                            string="Retired collaborator thirteenth salary",
                                                            required=True, readonly=True, ondelete='cascade')
    state = fields.Selection(related='retired_employee_thirteenth_salary_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True,
                                  ondelete='cascade')
    end_date = fields.Date(string='Retired date', tracking=True)
    date_of_death = fields.Date(string='Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)
    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class RetiredEmployeeFourteenthSalary(models.Model):
    _name = 'retired.employee.fourteenth.salary'
    _description = 'Retired employee fourteenth salary'
    _inherit = ['hr.generic.request']
    _order = "period_start desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_retired_employee_fourteenth_salary',
            'confirm_direct':
                'hr_dr_payroll_base.email_template_confirm_direct_approve_retired_employee_fourteenth_salary',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_retired_employee_fourteenth_salary',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_retired_employee_fourteenth_salary',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancel_retired_employee_fourteenth_salary',
            'paid': 'hr_dr_payroll_base.email_template_retired_employee_fourteenth_salary_notify_treasury'
        }
    _hr_notifications_mode_param = 'retired.employee.fourteenth.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.fourteenth.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.fourteenth.salary.second.administrator'

    def _default_year(self):
        return datetime.utcnow().year

    @api.onchange('region', 'year')
    def on_change_region_year(self):
        if self.region and self.year:
            if self.region == 'coast' or self.region == 'island':
                max_days_february = calendar.monthrange(self.year, 2)[1]
                period_start = datetime.utcnow().date() + relativedelta(day=1, month=3, year=self.year - 1)
                period_end = datetime.utcnow().date() + relativedelta(day=max_days_february, month=2, year=self.year)
            elif self.region == 'sierra' or self.region == 'eastern':
                period_start = datetime.utcnow().date() + relativedelta(day=1, month=8, year=self.year - 1)
                period_end = datetime.utcnow().date() + relativedelta(day=31, month=7, year=self.year)
            self.period_start = period_start
            self.period_end = period_end

    def unlink(self):
        for rets in self:
            if rets.state != 'draft':
                raise ValidationError(_('You can only delete retired employee fourteenth salary in draft status.'))
        return super(RetiredEmployeeFourteenthSalary, self).unlink()

    def name_get(self):
        result = []
        for refs in self:
            result.append(
                (
                    refs.id,
                    _("{} {}").format(refs.year,dict(self._fields['region'].selection).get(refs.region))

                )
            )
        return result

    def _get_value_and_days_to_pay(self, e):
        days_to_pay = 0
        value = 0

        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', self.year),
        ], limit=1)

        if sbu:
            # if self.region == 'coast' or self.region == 'island':
            #     max_days_february = calendar.monthrange(self.year, 2)[1]
            #     date_start = datetime.utcnow().date() + relativedelta(day=1, month=3, year=self.year - 1)
            #     date_end = datetime.utcnow().date() + relativedelta(day=max_days_february, month=2, year=self.year)
            # elif self.region == 'sierra' or self.region == 'eastern':
            #     date_start = datetime.utcnow().date() + relativedelta(day=1, month=8, year=self.year - 1)
            #     date_end = datetime.utcnow().date() + relativedelta(day=31, month=7, year=self.year)

            if e.departure_date < self.period_start:
                # difference = self.period_end - self.period_start
                # days_to_pay = difference.days + 1
                days_to_pay = 360
                value = sbu.value
            elif e.departure_date >= self.period_start and e.departure_date < self.period_end:
                # difference = self.period_end - e.end_date
                # days_to_pay = difference.days
                date_start = self.period_start

                days_to_pay = 0

                for i in range(0, 12):

                    date_start_i = date_start + relativedelta(months=i)
                    date_start_f = date_start + relativedelta(months=i)
                    days_of_month = monthrange(date_start_i.year, date_start_i.month)
                    date_start_f = date_start_f + relativedelta(day=days_of_month[1])

                    if e.departure_date >= date_start_i and e.departure_date <= date_start_f:

                        difference = date_start_f - e.departure_date
                        days_to_pay_per_month = difference.days

                        if date_start_f.month in [1, 3, 5, 7, 8, 10, 12]:
                            days_to_pay_per_month = days_to_pay_per_month - 1

                        if date_start_f.month == 2:
                            if isleap(date_start_f.year):
                                days_to_pay_per_month = days_to_pay_per_month + 1
                            else:
                                days_to_pay_per_month = days_to_pay_per_month + 2

                        if days_to_pay_per_month > 30:
                            days_to_pay_per_month = 30

                        if days_to_pay_per_month < 0:
                            days_to_pay_per_month = 0

                        days_to_pay = days_to_pay + days_to_pay_per_month

                    else:
                        if e.departure_date < date_start_i:
                            days_to_pay = days_to_pay + 30

                # period_days = (self.period_end - self.period_start).days + 1
                period_days = 30
                value = days_to_pay * sbu.value / period_days
            else:
                days_to_pay = 0
                value = 0
        else:
            raise ValidationError(_('Debe establecer el salario básico unificado para el año {}.').format(str(self.year)))

        return days_to_pay, value

    def action_create_update_lines(self, delete_actual_lines=True):
        if delete_actual_lines:
            line_ids = self.env['retired.employee.fourteenth.salary.line'].with_context(
                active_test=False).search([('retired_employee_fourteenth_salary_id', '=', self.id)])
            if line_ids:
                line_ids.unlink()

        if self.region == 'coast' or self.region == 'island':
            max_days_february = calendar.monthrange(self.year, 2)[1]
            limit_date = datetime.utcnow().date() + relativedelta(day=max_days_february, month=2, year=self.year)
        elif self.region == 'sierra' or self.region == 'eastern':
            limit_date = datetime.utcnow().date() + relativedelta(day=31, month=7, year=self.year)

        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', False),
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['retired']),
            ('address_id.state_id.region', '=', self.region),
            ('departure_date', '<', limit_date),
            ('single_payment_after_death', '=', False),
        ])
        for e in employees:
            if e.departure_date:
                if e.date_of_death:
                    if e.date_of_death >= self.period_start and e.date_of_death <= self.period_end:
                        sbu = self.env['hr.sbu'].sudo().search([
                            ('fiscal_year', '=', self.year),
                        ], limit=1)
                        if sbu:
                            self.env['retired.employee.fourteenth.salary.line'].create({
                                'retired_employee_fourteenth_salary_id': self.id,
                                'employee_id': e.id,
                                'end_date': e.departure_date,
                                'date_of_death': e.date_of_death,
                                'region': e.address_id.state_id.region,
                                'days_to_pay': (self.period_end - self.period_start).days + 1,
                                'value': sbu.value,
                                'automatic': True,
                            })
                        else:
                            raise ValidationError(_('Debe establecer el salario básico unificado para el año {}.').
                                                  format(str(self.year)))
                else:
                    days_to_pay, value = self._get_value_and_days_to_pay(e)
                    self.env['retired.employee.fourteenth.salary.line'].create({
                        'retired_employee_fourteenth_salary_id': self.id,
                        'employee_id': e.id,
                        'end_date': e.departure_date,
                        'region': e.address_id.state_id.region,
                        'days_to_pay': days_to_pay,
                        'value': value,
                        'automatic': True,
                    })
            else:
                raise ValidationError(_('Debe establecer la fecha de jubilación para el colaborador {}.').
                                      format(e.name))

        self.write({
            'state': 'calculated',
        })

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        # self.sudo().write({
        #     'state': 'reviewed',
        # })
        return self

    def mark_as_draft(self):
        super(RetiredEmployeeFourteenthSalary, self).mark_as_draft()
        line_ids = self.env['retired.employee.fourteenth.salary.line'].with_context(
            active_test=False).search([('retired_employee_fourteenth_salary_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

    def action_done(self):
        self.write({'state': 'done'})

    def action_paid(self):
        pass

    def action_view_payment(self):
        pass

    def action_cancel(self):
        pass

    period_start = fields.Date(string='Period start', tracking=True)
    period_end = fields.Date(string='Period end', tracking=True)
    date = fields.Date(string='Posting date', default=fields.Date.today(), help='', tracking=True)
    year = fields.Integer(string='Year', required=True, default=_default_year, tracking=True)
    state = fields.Selection(selection_add=[
        ('calculated', 'Calculated'),
        ('reviewed', 'Reviewed'),
        ('done', 'Done')])
    region = fields.Selection([
        ('sierra', 'Sierra'),
        ('coast', 'Coast'),
        ('eastern', 'East'),
        ('island', 'Island / Galapagos')
    ], string='Region', required=True, tracking=True)
    retired_employee_fourteenth_salary_line_ids = fields.One2many(
        'retired.employee.fourteenth.salary.line', 'retired_employee_fourteenth_salary_id',
        string="Retired collaborator fourteenth salary detail")


class RetiredEmployeeFourteenthSalaryLine(models.Model):
    _name = 'retired.employee.fourteenth.salary.line'
    _description = 'Retired collaborator fourteenth salary detail'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('refs_employee_id_uniq', 'UNIQUE (retired_employee_fourteenth_salary_id,employee_id)',
         'The collaborator cannot be repeated for the same payment of the fourteenth salary.')
    ]

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.departure_date
            self.region = self.employee_id.address_id.state_id.region
            self.automatic = False
            days_to_pay, value = self.retired_employee_fourteenth_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value

    retired_employee_fourteenth_salary_id = fields.Many2one('retired.employee.fourteenth.salary',
                                                            string="Retired collaborator fourteenth salary",
                                                            required=True, readonly=True, ondelete='cascade')
    state = fields.Selection(related='retired_employee_fourteenth_salary_id.state',
                             store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True,
                                  ondelete='cascade')
    region = fields.Selection([
        ('sierra', 'Sierra'),
        ('coast', 'Coast'),
        ('eastern', 'East'),
        ('island', 'Island / Galapagos')
    ], string='Region', required=True, tracking=True)
    end_date = fields.Date(string='Retired date', tracking=True)
    date_of_death = fields.Date(string='Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)
    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)