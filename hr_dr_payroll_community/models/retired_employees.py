# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from datetime import datetime
import time
from calendar import isleap
from calendar import monthrange


def get_param_id(self, key, model):
    """
    Recibe una clave de un parámetro de configuración que contiene un id de un objeto y el modelo del mismo.
    Verifica que exista el id y lo devuelve.
    :param self: Instancia del objeto desde donde se llama
    :param key: Clave del parámetro de ir.config_parameter
    :param model: Modelo de objeto a buscar
    :return: (int|string) Id del objeto o '' si no se encuentra este.
    """
    param = self.env['ir.config_parameter'].sudo().get_param(key)
    if param and param != '':
        obj = self.env[model].sudo().browse(int(param))
        if obj and obj.id:
            return obj.id
    return ''


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    retired_employee_id = fields.Many2one('retired.employee.salary', 'Retired salary')
    retired_employee_d13_id = fields.Many2one('retired.employee.thirteenth.salary', 'Thirteenth retired salary')
    retired_employee_d14_id = fields.Many2one('retired.employee.fourteenth.salary', 'Fourteenth retired salary')


class RetiredEmployeeSalary(models.Model):
    _name = 'retired.employee.salary'
    _description = 'Retired employee salary'
    _inherit = ['hr.generic.request']
    #_inherit = ['hr.dr.export.file']
    _order = "period_start desc"

    _hr_mail_templates = {'confirm': 'hr_dr_payroll.email_template_confirm_retired_employee',
                          'approve': 'hr_dr_payroll.email_template_confirm_approve_retired_employee',
                          'reject': 'hr_dr_payroll.email_template_confirm_reject_retired_employee',
                          'cancel': 'hr_dr_payroll.email_template_confirm_cancelled_retired_employee',
                          'paid': 'hr_dr_payroll.email_template_paid_retired_employee'}
    _hr_notifications_mode_param = 'retired.employee.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.salary.second.administrator'

    retired_employee_salary_line_ids = fields.One2many('retired.employee.salary.line', 'retired_employee_salary_id',
                                                       string="Detail retired employee salary", tracking=True)

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

    period_start = fields.Date('Period start', required=True, default=_default_period_start, tracking=True)
    period_end = fields.Date('Period end', required=True, default=_default_period_end, tracking=True)

    state = fields.Selection(selection_add=[('paid', 'Paid')])

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Solicitud de aprobación de salario para jubilados")
        local_context['request'] = _("ha realizado una solicitud de aprobación de salario para jubilados.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.sudo().env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.sudo().env.ref('hr_dr_management.menu_hr_management').id

        local_context['details'] = "Solicitud de aprobación de salario para jubilados del {} al {}.".format(
            self.period_start.strftime("%d/%m/%Y"), self.period_end.strftime("%d/%m/%Y"))

        local_context['commentary'] = self.commentary

        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')
        action = self.sudo().env.ref('hr_dr_loan.loan_request_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.sudo().env.ref('hr_dr_loan.menu_hr_loans_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        department = 'Dirección de Talento Humano'
        management_responsible = self.sudo().employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        local_context['department'] = department

        return local_context

    def unlink(self):
        for res in self:
            if res.state != 'draft':
                raise ValidationError(u'You can only delete retired employee salary in draft status.')
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

    def _get_value_and_days_to_pay(self,e):

        days_to_pay = 0
        value = 0

        if e.end_date:
            if e.end_date < self.period_start:
                # difference = self.period_end - self.period_start
                # days_to_pay = difference.days + 1
                days_to_pay = 30
                value = e.pension
            elif e.end_date >= self.period_start and e.end_date < self.period_end:
                difference = self.period_end - e.end_date
                days_to_pay = difference.days

                if self.period_end.month in [1,3,5,7,8,10,12]:
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

                # period_days = (self.period_end - self.period_start).days + 1
                period_days = 30
                value = days_to_pay * e.pension / period_days
            else:
                days_to_pay = 0
                value = 0

        return days_to_pay,value

    def _get_value_and_days_to_pay_death(self,e):

        days_to_pay = 0
        value = 0

        if e.date_of_death:
            if e.date_of_death < self.period_start:
                # difference = self.period_end - self.period_start
                # days_to_pay = difference.days + 1
                days_to_pay = 30
                value = e.pension
            elif e.date_of_death >= self.period_start and e.date_of_death < self.period_end:
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

                # period_days = (self.period_end - self.period_start).days + 1
                period_days = 30
                value = days_to_pay * e.pension / period_days
            else:
                days_to_pay = 0
                value = 0

        return days_to_pay, value

    def action_create_update_lines(self,delete_actual_lines=True):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee salary can create update lines.')
        else:
            if delete_actual_lines:
                line_ids = self.env['retired.employee.salary.line'].with_context(
                    active_test=False).search([
                    ('retired_employee_salary_id', '=', self.id),
                ])
                if line_ids:
                    line_ids.unlink()

            employees = self.env['hr.employee'].sudo().search([
                ('active', '=', False),
                ('state', 'in', ['retired']),
                ('end_date', '<', self.period_end),
                ('single_payment_after_death', '=', False),
            ])

            for e in employees:
                if e.end_date:
                    if e.date_of_death:
                        date_of_death_in_period = e.date_of_death + relativedelta(
                            year=self.period_start.year, month=self.period_start.month)
                        rd = relativedelta(date_of_death_in_period, e.date_of_death)
                        if rd.years == 0 and rd.months == 0:
                            # Se esta pagando el mes en que murio, se debe pagar un proporcional
                            days_to_pay, value = self._get_value_and_days_to_pay_death(e)
                            self.env['retired.employee.salary.line'].create({
                                'retired_employee_salary_id': self.id,
                                'employee_id': e.id,
                                'end_date': e.end_date,
                                'date_of_death': e.date_of_death,
                                'days_to_pay': days_to_pay,
                                'value': value,
                                'automatic': True,
                            })
                        else:

                            if rd.years == 0 and rd.months <= 12 and rd.months > 0 or rd.years == 1 and rd.months == 0:

                                self.env['retired.employee.salary.line'].create({
                                    'retired_employee_salary_id': self.id,
                                    'employee_id': e.id,
                                    'end_date': e.end_date,
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
                                    'end_date': e.end_date,
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
                            'end_date': e.end_date,
                            'days_to_pay': days_to_pay,
                            'value': value,
                            'automatic': True,
                        })
                else:
                    raise ValidationError(u'Debe establecer la fecha de jubilación para el colaborador {}.'
                                          .format(e.name))

            return True

    @api.model
    def get_credit_account_retired_employee_id(self):
        return get_param_id(self, 'credit.account.retired.employee.id', 'account.account')

    @api.model
    def get_debit_account_retired_employee_id(self):
        return get_param_id(self, 'debit.account.retired.employee.id', 'account.account')

    @api.model
    def get_journal_retired_employee_id(self):
        return get_param_id(self, 'journal.retired.employee.id', 'account.journal')

    @api.model
    def get_account_analytic_account_retired_employee_id(self):
        return get_param_id(self, 'account.analytic.account.retired.employee.id', 'account.analytic.account')

    def mark_as_paid(self):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee salary can update the status.')
        else:
            self.state = 'paid'

            # Movimientos contables

            if self.get_credit_account_retired_employee_id() == '' \
                    or self.get_debit_account_retired_employee_id() == '' \
                    or self.get_journal_retired_employee_id() == '':
                raise UserError(
                    _("Debe ingresar las cuentas contables y el diario para poder marcar como pagado el salario jubilado."))

            timenow = time.strftime('%Y-%m-%d')
            amount = 0.0
            for re in self:
                for line in re.retired_employee_salary_line_ids:
                    amount += line.value

                retired_employee_name = re.period_start.strftime("%d/%m/%Y") + ' ' + re.period_end.strftime("%d/%m/%Y")
                reference = retired_employee_name

                journal_id = self.get_journal_retired_employee_id()
                analytic_account_id = self.get_account_analytic_account_retired_employee_id()
                debit_account_id = self.get_debit_account_retired_employee_id()
                credit_account_id = self.get_credit_account_retired_employee_id()

                name = "Salario jubilado: {}".format(retired_employee_name)
                credit_vals = {
                    'name': name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'retired_employee_id': re.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids = []
                line_ids.append((0, 0, credit_vals))

                debit_vals = {
                    'name': name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount,
                    'credit': 0,
                    'retired_employee_id': re.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids.append((0, 0, debit_vals))

                vals = {
                    'name': 'Salario jubilado: ' + retired_employee_name,
                    'narration': retired_employee_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': timenow,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()
        return self

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """
        for rec in self:
            messages = self._create_text_files(rec.retired_employee_salary_line_ids, rec.description,
                                               use_main_account=True)
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return self._compress_and_show(self.clean_filename(_("Retired payroll {} {}.zip").format(rec.period_start,
                                                                                                     rec.period_end)))

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

        template = self.env.ref('hr_dr_payroll.email_template_retired_employee_salary_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)


class RetiredEmployeeSalaryLine(models.Model):
    _name = 'retired.employee.salary.line'
    _description = 'Retired employee salary line'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('res_employee_id_uniq', 'UNIQUE (retired_employee_salary_id,employee_id)',
         'No se puede repetir el colaborador para un mismo pago de salario jubilado.')
    ]

    retired_employee_salary_id = fields.Many2one('retired.employee.salary', string="Retired employee salary",
                                                 required=True, readonly=True, ondelete='cascade')
    # _STATE = [
    #     ('draft', 'Draft'),
    #     ('pending', 'Pending'),
    #     ('cancelled', 'Cancelled'),
    #     ('approved', 'Approved'),
    #     ('rejected', 'Rejected'),
    # ]
    # state = fields.Selection(_STATE, string='State', default='draft', readonly=True, tracking=True)
    state = fields.Selection(related='retired_employee_salary_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True, ondelete='cascade')

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.end_date
            self.automatic = False

            days_to_pay, value = self.retired_employee_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value

    end_date = fields.Date('Retired date', tracking=True)
    date_of_death = fields.Date('Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)

    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class RetiredEmployeeThirteenthSalary(models.Model):
    _name = 'retired.employee.thirteenth.salary'
    _description = 'Retired employee thirteenth salary'
    #_inherit = ['hr.dr.export.file']
    _inherit = ['hr.generic.request']
    _order = "period_start desc"

    _hr_mail_templates = {'confirm': 'hr_dr_payroll.email_template_confirm_retired_employee_thirteenth_salary',
                          'approve': 'hr_dr_payroll.email_template_confirm_approve_retired_employee_thirteenth_salary',
                          'reject': 'hr_dr_payroll.email_template_confirm_reject_retired_employee_thirteenth_salary',
                          'cancel': 'hr_dr_payroll.email_template_confirm_cancelled_retired_employee_thirteenth_salary',
                          'paid': 'hr_dr_payroll.email_template_paid_retired_employee_thirteenth_salary'}
    _hr_notifications_mode_param = 'retired.employee.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.salary.second.administrator'

    retired_employee_thirteenth_salary_line_ids = fields.One2many(
        'retired.employee.thirteenth.salary.line', 'retired_employee_thirteenth_salary_id',
        string="Detail retired employee thirteenth salary",tracking=True)

    def _default_year(self):
        return datetime.utcnow().year

    year = fields.Integer('Year', required=True, default=_default_year, tracking=True)

    state = fields.Selection(selection_add=[('paid', 'Paid')])

    @api.onchange('year')
    def on_change_year(self):
        if self.year:
            period_start = datetime.utcnow().date() + relativedelta(day=1, month=12, year=self.year - 1)
            period_end = datetime.utcnow().date() + relativedelta(day=30, month=11, year=self.year)

            self.period_start = period_start
            self.period_end = period_end

    period_start = fields.Date('Period start', tracking=True)
    period_end = fields.Date('Period end', tracking=True)

    def unlink(self):
        for rets in self:
            if rets.state != 'draft':
                raise ValidationError(u'You can only delete retired employee thirteenth salary in draft status.')
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

    def _get_value_and_days_to_pay(self,e):

        days_to_pay = 0
        value = 0

        if e.end_date:
            date_start = self.period_start
            date_end = self.period_end
            if e.end_date < date_start:
                # difference = date_end - date_start
                # days_to_pay = difference.days + 1
                days_to_pay = 360
                value = e.pension
            elif e.end_date >= date_start and e.end_date < date_end:
                # difference = date_end - e.end_date
                # days_to_pay = difference.days

                days_to_pay = 0

                for i in range(0, 12):

                    date_start_i = date_start + relativedelta(months=i)
                    date_start_f = date_start + relativedelta(months=i)
                    days_of_month = monthrange(date_start_i.year, date_start_i.month)
                    date_start_f = date_start_f + relativedelta(day=days_of_month[1])

                    if e.end_date >= date_start_i and e.end_date <= date_start_f:

                        difference = date_start_f - e.end_date
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
                        if e.end_date < date_start_i:
                            days_to_pay = days_to_pay + 30

                # period_days = (date_end - date_start).days + 1
                period_days = 360
                value = days_to_pay * e.pension / period_days
            else:
                days_to_pay = 0
                value = 0

        return days_to_pay,value

    def action_create_update_lines(self,delete_actual_lines=True):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee thirteenth salary can create update lines.')
        else:
            if delete_actual_lines:
                line_ids = self.env['retired.employee.thirteenth.salary.line'].with_context(active_test=False)\
                    .search([('retired_employee_thirteenth_salary_id', '=', self.id),])
                if line_ids:
                    line_ids.unlink()

                # for retsl in self.retired_employee_thirteenth_salary_line_ids:
                #     retsl.unlink()

            limit_date = datetime.utcnow().date() + relativedelta(day=30, month=11, year=self.year)

            employees = self.env['hr.employee'].sudo().search([
                ('active', '=', False),
                ('state', 'in', ['retired']),
                ('end_date', '<', limit_date),
                ('single_payment_after_death', '=', False),
            ])

            for e in employees:
                if e.end_date:
                    if e.date_of_death:
                        if e.date_of_death >= self.period_start and e.date_of_death <= self.period_end:
                            self.env['retired.employee.thirteenth.salary.line'].create({
                                'retired_employee_thirteenth_salary_id': self.id,
                                'employee_id': e.id,
                                'end_date': e.end_date,
                                'date_of_death': e.date_of_death,
                                'days_to_pay': (self.period_end - self.period_start).days + 1,
                                'value': e.pension,
                                'automatic': True,
                            })
                    else:
                        days_to_pay,value = self._get_value_and_days_to_pay(e)

                        self.env['retired.employee.thirteenth.salary.line'].create({
                            'retired_employee_thirteenth_salary_id': self.id,
                            'employee_id': e.id,
                            'end_date': e.end_date,
                            'days_to_pay': days_to_pay,
                            'value': value,
                            'automatic': True,
                        })
                else:
                    raise ValidationError(
                        u'Debe establecer la fecha de jubilación para el colaborador {}.'.format(e.name))

            return True

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        # self.sudo().write({
        #     'state': 'reviewed',
        # })
        return self

    @api.model
    def get_credit_account_retired_employee_id(self):
        return get_param_id(self, 'credit.account.retired.employee.id', 'account.account')

    @api.model
    def get_debit_account_retired_employee_id(self):
        return get_param_id(self, 'debit.account.retired.employee.id', 'account.account')

    @api.model
    def get_journal_retired_employee_id(self):
        return get_param_id(self, 'journal.retired.employee.id', 'account.journal')

    @api.model
    def get_account_analytic_account_retired_employee_id(self):
        return get_param_id(self, 'account.analytic.account.retired.employee.id', 'account.analytic.account')

    def mark_as_paid(self):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee thirteenth salary can update the status.')
        else:
            self.state = 'paid'

            # Movimientos contables

            if self.get_credit_account_retired_employee_id() == '' \
                    or self.get_debit_account_retired_employee_id() == '' \
                    or self.get_journal_retired_employee_id() == '':
                raise UserError(
                    _("Debe ingresar las cuentas contables y el diario para poder marcar como pagado el decimotercer salario jubilado."))

            timenow = time.strftime('%Y-%m-%d')
            amount = 0.0
            for red13 in self:
                for line in red13.retired_employee_thirteenth_salary_line_ids:
                    amount += line.value

                retired_employee_name = red13.period_start.strftime("%d/%m/%Y") + ' ' \
                                        + red13.period_end.strftime("%d/%m/%Y")
                reference = retired_employee_name

                journal_id = self.get_journal_retired_employee_id()
                analytic_account_id = self.get_account_analytic_account_retired_employee_id()
                debit_account_id = self.get_debit_account_retired_employee_id()
                credit_account_id = self.get_credit_account_retired_employee_id()

                name = "Decimotercer salario jubilado: {}".format(retired_employee_name)
                credit_vals = {
                    'name': name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and - amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'retired_employee_d13_id': red13.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids = []
                line_ids.append((0, 0, credit_vals))

                debit_vals = {
                    'name': name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount,
                    'credit': 0,
                    'retired_employee_d13_id': red13.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids.append((0, 0, debit_vals))

                vals = {
                    'name': 'Decimotercer salario jubilado: ' + retired_employee_name,
                    'narration': retired_employee_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': timenow,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()


        return self

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """
        for rec in self:
            messages = self._create_text_files(rec.retired_employee_thirteenth_salary_line_ids, rec.description,
                                               use_main_account=True)
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))

            return self._compress_and_show(self.clean_filename(_("Retired 13th payroll {}.zip").format(str(rec.year))))

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

        template = self.env.ref(
            'hr_dr_payroll.email_template_retired_employee_thirteenth_salary_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)


class RetiredEmployeeThirteenthSalaryLine(models.Model):
    _name = 'retired.employee.thirteenth.salary.line'
    _description = 'Retired employee thirteenth salary line'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('rets_employee_id_uniq', 'UNIQUE (retired_employee_thirteenth_salary_id,employee_id)',
         'No se puede repetir el colaborador para un mismo pago de décimo tercer sueldo.')
    ]

    retired_employee_thirteenth_salary_id = fields.Many2one('retired.employee.thirteenth.salary',
                        string="Retired employee thirteenth salary", required=True, readonly=True, ondelete='cascade')
    state = fields.Selection(related='retired_employee_thirteenth_salary_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True, ondelete='cascade')

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.end_date
            self.automatic = False

            days_to_pay, value = self.retired_employee_thirteenth_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value

    end_date = fields.Date('Retired date', tracking=True)
    date_of_death = fields.Date('Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)

    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class RetiredEmployeeFourteenthSalary(models.Model):
    _name = 'retired.employee.fourteenth.salary'
    _description = 'Retired employee fourteenth salary'
    #_inherit = ['hr.dr.export.file']
    _inherit = ['hr.generic.request']
    _order = "period_start desc"

    _hr_mail_templates = {'confirm': 'hr_dr_payroll.email_template_confirm_retired_employee_fourteenth_salary',
                          'approve': 'hr_dr_payroll.email_template_confirm_approve_retired_employee_fourteenth_salary',
                          'reject': 'hr_dr_payroll.email_template_confirm_reject_retired_employee_fourteenth_salary',
                          'cancel': 'hr_dr_payroll.email_template_confirm_cancelled_retired_employee_fourteenth_salary',
                          'paid': 'hr_dr_payroll.email_template_paid_retired_employee_fourteenth_salary'}
    _hr_notifications_mode_param = 'retired.employee.salary.notifications.mode'
    _hr_administrator_param = 'retired.employee.salary.administrator'
    _hr_second_administrator_param = 'retired.employee.salary.second.administrator'

    retired_employee_fourteenth_salary_line_ids = fields.One2many(
        'retired.employee.fourteenth.salary.line', 'retired_employee_fourteenth_salary_id',
        string="Detail retired employee fourteenth salary", tracking=True)

    def _default_year(self):
        return datetime.utcnow().year
    year = fields.Integer('Year', required=True, default=_default_year, tracking=True)
    state = fields.Selection(selection_add=[('paid', 'Paid')])
    region = fields.Selection([
        ('sierra', 'Sierra'),
        ('coast', 'Coast'),
        ('eastern', 'East'),
        ('island', 'Island / Galapagos')
    ], string='Region', required=True, tracking=True)

    @api.onchange('region','year')
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

    period_start = fields.Date('Period start', tracking=True)
    period_end = fields.Date('Period end', tracking=True)

    def unlink(self):
        for rets in self:
            if rets.state != 'draft':
                raise ValidationError(u'You can only delete retired employee fourteenth salary in draft status.')
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

    def _get_value_and_days_to_pay(self,e):
        days_to_pay = 0
        value = 0

        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', self.year),
        ], limit = 1)

        if sbu:
            # if self.region == 'coast' or self.region == 'island':
            #     max_days_february = calendar.monthrange(self.year, 2)[1]
            #     date_start = datetime.utcnow().date() + relativedelta(day=1, month=3, year=self.year - 1)
            #     date_end = datetime.utcnow().date() + relativedelta(day=max_days_february, month=2, year=self.year)
            # elif self.region == 'sierra' or self.region == 'eastern':
            #     date_start = datetime.utcnow().date() + relativedelta(day=1, month=8, year=self.year - 1)
            #     date_end = datetime.utcnow().date() + relativedelta(day=31, month=7, year=self.year)

            if e.end_date < self.period_start:
                # difference = self.period_end - self.period_start
                # days_to_pay = difference.days + 1
                days_to_pay = 360
                value = sbu.value
            elif e.end_date >= self.period_start and e.end_date < self.period_end:
                # difference = self.period_end - e.end_date
                # days_to_pay = difference.days
                date_start = self.period_start

                days_to_pay = 0

                for i in range(0, 12):

                    date_start_i = date_start + relativedelta(months=i)
                    date_start_f = date_start + relativedelta(months=i)
                    days_of_month = monthrange(date_start_i.year, date_start_i.month)
                    date_start_f = date_start_f + relativedelta(day=days_of_month[1])

                    if e.end_date >= date_start_i and e.end_date <= date_start_f:

                        difference = date_start_f - e.end_date
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
                        if e.end_date < date_start_i:
                            days_to_pay = days_to_pay + 30

                # period_days = (self.period_end - self.period_start).days + 1
                period_days = 30
                value = days_to_pay * sbu.value / period_days
            else:
                days_to_pay = 0
                value = 0
        else:
            raise ValidationError(u'Debe establecer el salario básico unificado para el año {}.'.format(str(self.year)))

        return days_to_pay,value

    def action_create_update_lines(self,delete_actual_lines=True):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee fourteenth salary can create update lines.')
        else:
            if delete_actual_lines:
                line_ids = self.env['retired.employee.fourteenth.salary.line'].with_context(
                    active_test=False).search([
                    ('retired_employee_fourteenth_salary_id', '=', self.id),
                ])
                if line_ids:
                    line_ids.unlink()
                # for retsl in self.retired_employee_fourteenth_salary_line_ids:
                #     retsl.unlink()

            if self.region == 'coast' or self.region == 'island':
                max_days_february = calendar.monthrange(self.year, 2)[1]
                limit_date = datetime.utcnow().date() + relativedelta(day=max_days_february, month=2, year=self.year)
            elif self.region == 'sierra' or self.region == 'eastern':
                limit_date = datetime.utcnow().date() + relativedelta(day=31, month=7, year=self.year)

            employees = self.env['hr.employee'].sudo().search([
                ('active', '=', False),
                ('state', 'in', ['retired']),
                ('address_id.state_id.region', '=', self.region),
                ('end_date', '<', limit_date),
                ('single_payment_after_death', '=', False),
            ])
            for e in employees:
                if e.end_date:
                    if e.date_of_death:
                        if e.date_of_death >= self.period_start and e.date_of_death <= self.period_end:
                            sbu = self.env['hr.sbu'].sudo().search([
                                ('fiscal_year', '=', self.year),
                            ], limit=1)
                            if sbu:
                                self.env['retired.employee.fourteenth.salary.line'].create({
                                    'retired_employee_fourteenth_salary_id': self.id,
                                    'employee_id': e.id,
                                    'end_date': e.end_date,
                                    'date_of_death': e.date_of_death,
                                    'region': e.address_id.state_id.region,
                                    'days_to_pay': (self.period_end - self.period_start).days + 1,
                                    'value': sbu.value,
                                    'automatic': True,
                                })
                            else:
                                raise ValidationError(u'Debe establecer el salario básico unificado para el año {}.'
                                                      .format(str(self.year)))

                    else:
                        days_to_pay, value = self._get_value_and_days_to_pay(e)
                        self.env['retired.employee.fourteenth.salary.line'].create({
                            'retired_employee_fourteenth_salary_id': self.id,
                            'employee_id': e.id,
                            'end_date': e.end_date,
                            'region': e.address_id.state_id.region,
                            'days_to_pay': days_to_pay,
                            'value': value,
                            'automatic': True,
                        })
                else:
                    raise ValidationError(u'Debe establecer la fecha de jubilación para el colaborador {}.'
                                          .format(e.name))
            return True

    def mark_as_reviewed(self):
        self.state = 'reviewed'
        # self.sudo().write({
        #     'state': 'reviewed',
        # })
        return self

    @api.model
    def get_credit_account_retired_employee_id(self):
        return get_param_id(self, 'credit.account.retired.employee.id', 'account.account')

    @api.model
    def get_debit_account_retired_employee_id(self):
        return get_param_id(self, 'debit.account.retired.employee.id', 'account.account')

    @api.model
    def get_journal_retired_employee_id(self):
        return get_param_id(self, 'journal.retired.employee.id', 'account.journal')

    @api.model
    def get_account_analytic_account_retired_employee_id(self):
        return get_param_id(self, 'account.analytic.account.retired.employee.id', 'account.analytic.account')

    def mark_as_paid(self):
        if self.create_uid.id != self.env.uid:
            raise ValidationError(u'Only the creator of the retired employee fourteenth salary can update the status.')
        else:
            self.state = 'paid'

            # Movimientos contables

            if self.get_credit_account_retired_employee_id() == '' \
                    or self.get_debit_account_retired_employee_id() == '' \
                    or self.get_journal_retired_employee_id() == '':
                raise UserError(
                    _("Debe ingresar las cuentas contables y el diario para poder marcar como pagado el decimocuarto salario jubilado."))

            timenow = time.strftime('%Y-%m-%d')
            amount = 0.0
            for red14 in self:
                for line in red14.retired_employee_thirteenth_salary_line_ids:
                    amount += line.value

                retired_employee_name = red14.period_start.strftime("%d/%m/%Y") + ' ' + red14.period_end.strftime(
                    "%d/%m/%Y")
                reference = retired_employee_name

                journal_id = self.get_journal_retired_employee_id()
                analytic_account_id = self.get_account_analytic_account_retired_employee_id()
                debit_account_id = self.get_debit_account_retired_employee_id()
                credit_account_id = self.get_credit_account_retired_employee_id()

                name = "Decimocuarto salario jubilado: {}".format(retired_employee_name)
                credit_vals = {
                    'name': name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'retired_employee_d14_id': red14.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids = []
                line_ids.append((0, 0, credit_vals))

                debit_vals = {
                    'name': name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount,
                    'credit': 0,
                    'retired_employee_d14_id': red14.id,
                    # 'partner_id': .employee_id.address_home_id.id,
                    'analytic_account_id': analytic_account_id,
                }
                line_ids.append((0, 0, debit_vals))

                vals = {
                    'name': 'Decimocuarto salario jubilado: ' + retired_employee_name,
                    'narration': retired_employee_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': timenow,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()



        return self

    def generate_archive(self):
        """
        Genera un fichero comprimido con los documentos de pago para los bancos. Por cada banco se genera un fichero
        diferente.
        """
        for rec in self:
            messages = self._create_text_files(rec.retired_employee_fourteenth_salary_line_ids, rec.description,
                                               use_main_account=True)
            if len(messages) > 0:
                raise ValidationError(_("The documents couldn't be generated. Check errors below: \n-\t{}")
                                      .format("\n-\t".join(messages)))
            return self._compress_and_show(self.clean_filename(_("Retired 14th payroll {}.zip").format(str(rec.year))))

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

        template = self.env.ref('hr_dr_payroll.email_template_retired_employee_fourteenth_salary_notify_treasury',
                                False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        template.with_context(local_context).send_mail(self.id, force_send=True)


class RetiredEmployeeFourteenthSalaryLine(models.Model):
    _name = 'retired.employee.fourteenth.salary.line'
    _description = 'Retired employee fourteenth salary line'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('refs_employee_id_uniq', 'UNIQUE (retired_employee_fourteenth_salary_id,employee_id)',
         'No se puede repetir el colaborador para un mismo pago de décimo cuarto sueldo.')
    ]

    retired_employee_fourteenth_salary_id = fields.Many2one(
        'retired.employee.fourteenth.salary', string="Retired employee fourteenth salary", required=True,
        readonly=True, ondelete='cascade')
    state = fields.Selection(related='retired_employee_fourteenth_salary_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True, ondelete='cascade')
    region = fields.Selection([
        ('sierra', 'Sierra'),
        ('coast', 'Coast'),
        ('eastern', 'East'),
        ('island', 'Island / Galapagos')
    ], string='Region', required=True, tracking=True)
    end_date = fields.Date('Retired date', tracking=True)
    date_of_death = fields.Date('Death date', tracking=True)
    days_to_pay = fields.Integer(string="Days to pay", tracking=True)
    value = fields.Float(string="Value", digits='Payroll', tracking=True)
    automatic = fields.Boolean(string='Automatic', default=False, readonly=True, tracking=True)
    reason = fields.Text(string="Reason", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        if self.employee_id:
            self.end_date = self.employee_id.end_date
            self.region = self.employee_id.address_id.state_id.region
            self.automatic = False

            days_to_pay, value = self.retired_employee_fourteenth_salary_id._get_value_and_days_to_pay(self.employee_id)
            self.days_to_pay = days_to_pay
            self.value = value
