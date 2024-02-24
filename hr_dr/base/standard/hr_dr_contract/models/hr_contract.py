# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class Contract(models.Model):
    _inherit = 'hr.contract'

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

    @api.constrains('wage')
    def _constrain_wage(self):
        if self.wage <= 0:
            raise ValidationError('The wage must be greater than zero.')

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        contract = super(Contract, self).create(vals_list)
        return contract

    def write(self, vals):
        self.validate_module()
        res = super(Contract, self).write(vals)
        return res

    def unlink(self):
        self.validate_module()
        for contract in self:
            if contract.state != 'draft':
                raise ValidationError('You can only delete contracts in draft status.')
        return super(Contract, self).unlink()

    # def action_draft_to_open(self):
    #     for record in self:
    #         record.state = 'open'
    #     return True
    #
    # def action_open_to_close(self):
    #     for record in self:
    #         if not record.date_end or not record.iess_output_documents_id:
    #             raise ValidationError('To finalize a contract, '
    #                                   'you must set the end date and upload the IESS exit documents.')
    #         else:
    #             record.state = 'close'
    #     return True
    #
    # def action_to_draft(self):
    #     for record in self:
    #         record.state = 'draft'
    #     return True

    @api.onchange('date_start')
    def on_change_date_start(self):
        if self.date_start:
            self.trial_date_end = self.date_start + relativedelta(months=3)

    def _cron_notify_trial_period_end(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        emails = set()
        if config_parameter.get_param('contract.administrators.ids'):
            if config_parameter.get_param('contract.administrators.ids') != '':
                for id in config_parameter.get_param('contract.administrators.ids').split(','):
                    employee_id = int(id)
                    employee = self.env['hr.employee'].sudo().search([('id', '=', employee_id)], limit=1)
                    if len(employee) > 0:
                        if employee.work_email != '':
                            emails.add(employee.work_email)
                        else:
                            emails.add(employee.private_email)
        emails_to = ','.join(emails)

        amount_days_before_trial_date_end = int(config_parameter.get_param('trial.period.end.anticipation.days',
                                                                           default=30))
        date_now = datetime.utcnow().date()
        date_now = date_now + relativedelta(days=amount_days_before_trial_date_end)
        contracts = self.search([
            ('active', '=', True),
            ('notification_send_trial_date_end', '=', False),
            ('state', 'in', ['open']),
            ('trial_date_end', '<=', date_now)
        ])

        for c in contracts:
            template = self.env.ref('hr_dr_contract.email_template_notify_trial_date_end', False)
            template = self.env['mail.template'].browse(template.id)
            template.write({
                'email_to': emails_to
            })
            local_context = c.env.context.copy()
            department = _('Human Talent Management')
            management_responsible = self.sudo().employee_id.get_hr_dr_management_responsible()
            if management_responsible and management_responsible.department_id:
                department = management_responsible.department_id.name
            local_context['department'] = department

            template.with_context(local_context).send_mail(c.id, force_send=True)
            c.notification_send_trial_date_end = True

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.name = self.employee_id.name
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id
            self.normative_id = self.employee_id.normative_id
            self.date_start = self.employee_id.last_company_entry_date

            if self.employee_id.address_id:
                if self.employee_id.address_id.state_id.region == 'sierra' \
                        or self.employee_id.address_id.state_id.region == 'eastern':
                    self.payment_period_fourteenth = 'sierra_oriente_fourteenth_salary'
                elif self.employee_id.address_id.state_id.region == 'coast' \
                        or self.employee_id.address_id.state_id.region == 'island':
                    self.payment_period_fourteenth = 'costa_fourteenth_salary'

    @api.onchange('resource_calendar_id')
    def onchange_resource_calendar_id(self):
        if self.resource_calendar_id:
            self.daily_hours = self.resource_calendar_id.hours_per_day
            self.weekly_hours = self.resource_calendar_id.hours_per_day * 5
            self.monthly_hours = self.resource_calendar_id.hours_per_day * 30

    def get_all_contract(self, employee, date_from, date_to):
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', 'in', ['open', 'close']), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.search(clause_final).ids

    @api.onchange('fortnight_percentage', 'wage')
    def on_change_fortnight_percentage(self):
        if self.fortnight_percentage:
            precision = self.env['decimal.precision'].precision_get('Payroll')
            value = round((self.wage * self.fortnight_percentage / 100), precision)
            self.fortnight = value

    @api.onchange('fortnight')
    def on_change_fortnight(self):
        if self.fortnight:
            precision = self.env['decimal.precision'].precision_get('Payroll')
            if self.wage != 0:
                value = round((self.fortnight * 100 / self.wage), precision)
            else:
                value = 0
            self.fortnight_percentage = value

    def get_years_months_days(self, date_start, date_end):
        if not date_start or not date_end:
            return 0, 0, 0

        date_end = date_end + timedelta(days=1)
        rd = relativedelta(date_end, date_start)
        return rd.years, rd.months, rd.days

    @api.depends('date_start', 'date_end')
    def compute_time_in_service(self):
        years, months, days = self.get_years_months_days(
            self.date_start,
            self.date_end or fields.Date.context_today(self))

        self.years_in_service = years
        self.months_in_service = months
        self.days_in_service = days

    @api.onchange('payment_period_fourteenth')
    def _onchange_payment_period_fourteenth(self):
        if self.payment_period_fourteenth:
            if self.payment_period_fourteenth == 'sierra_oriente_fourteenth_salary':
                self.calculation_period_fourteenth = _("From August 1 of the previous year to July 31 "
                                                       "of the year of payment.")
                self.max_date_payment_period_fourteenth = _("Until August 15 of each year.")
            elif self.payment_period_fourteenth == 'costa_fourteenth_salary':
                self.calculation_period_fourteenth = _("From March 1 of the previous year to February 28 "
                                                       "of the year of payment.")
                self.max_date_payment_period_fourteenth = _("Until March 15 of each year.")
            else:
                self.calculation_period_fourteenth = ""
                self.max_date_payment_period_fourteenth = ""

    name = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', tracking=True)
    department_id = fields.Many2one('hr.department', tracking=True)
    job_id = fields.Many2one('hr.job', tracking=True)
    trial_date_end = fields.Date(tracking=True)
    resource_calendar_id = fields.Many2one('resource.calendar', tracking=True)
    notes = fields.Text(tracking=True)
    company_id = fields.Many2one('res.company', tracking=True)
    date_start = fields.Date(tracking=True)
    date_end = fields.Date(tracking=True)

    normative_id = fields.Many2one('hr.normative', string="Regulation", tracking=True)
    normative_acronym = fields.Char(string="Acronym", related='normative_id.acronym')
    receive_fortnight = fields.Boolean(string='Receive fortnight', default=True, tracking=True)
    fortnight_percentage = fields.Float(string='Fortnight percentage', digits='Contract', tracking=True, help='')
    fortnight = fields.Float(string='Fortnight', digits='Contract', tracking=True, help='')

    receives_night_hours = fields.Boolean(string='Receives night hours (25%)', default=True, tracking=True)
    receives_hours_supplementary = fields.Boolean(string='Receives extra hours supplementary (50%)', default=True,
                                                  tracking=True)
    receives_hours_extraordinary = fields.Boolean(string='Receives extra hours extraordinary (100%)', default=True,
                                                  tracking=True)
    receives_profits = fields.Boolean(string='Receive profits', default=True, tracking=True, help='')
    reduction_of_working_hours = fields.Boolean(string='Reduction of working hours', default=False, tracking=True)
    percentage_reduction_of_working_hours = fields.Float(string='Percentage reduction', default=0, tracking=True, help='')
    notification_send_trial_date_end = fields.Boolean(string='Notification send trial date end', default=False,
                                                      tracking=True)
    mrl_code = fields.Char(string='MRL code', size=64, tracking=True, help='Code assigned to the contract '
                                                                           'at the ministry of labor relations.')
    IESS_affiliation_number = fields.Char(string='IESS affiliation number', tracking=True)

    daily_hours = fields.Float(string='Daily hours', default=8, tracking=True, help='')
    weekly_hours = fields.Float(string='Weekly hours', default=40, tracking=True, help='')
    monthly_hours = fields.Float(string='Monthly hours', default=240, tracking=True, help='')

    standard_daily_hours = fields.Float(string='Standard daily hours', default=8, tracking=True, help='')

    years_in_service = fields.Integer(string="Years in service", compute="compute_time_in_service", store=False,)
    months_in_service = fields.Integer(string="Months in service", compute="compute_time_in_service", store=False,)
    days_in_service = fields.Integer(string="Days in service", compute="compute_time_in_service", store=False,)
    APPLICATION_RESERVE_FUND = [
        ('automatic', _('Automatic (After 1 year)')),
        ('always_force', _('Always force'))
    ]
    application_reserve_fund = fields.Selection(APPLICATION_RESERVE_FUND, string='Application of reserve fund',
                                                default='automatic', tracking=True, help='')
    PAYMENT_RESERVE_FUND = [
        ('monthly', _('Monthly')),
        ('accumulated', _('Accumulated'))
    ]
    payment_reserve_fund = fields.Selection(PAYMENT_RESERVE_FUND, string='Payment of reserve funds', default='monthly',
                                            tracking=True, help='')
    PAYMENT_TENTH = [
        ('monthly', _('Monthly')),
        ('accumulated', _('Accumulated'))
    ]
    payment_thirteenth_salary = fields.Selection(PAYMENT_TENTH, string='Payment thirteenth salary', default='monthly',
                                                 tracking=True,
                                                 help='The calculation is made from December 1 of the previous year to '
                                                      'November 30 of the payment year. It must be paid until '
                                                      'December 24 of each year.')
    payment_fourteenth_salary = fields.Selection(PAYMENT_TENTH, string='Payment fourteenth salary', default='monthly',
                                                 tracking=True, help='')
    PAYMENT_PERIOD_FOURTEENTH = [
        ('sierra_oriente_fourteenth_salary', _('Sierra - Eastern (Fourteenth salary)')),
        ('costa_fourteenth_salary', _('Coast - Island (Fourteenth salary)'))
    ]
    payment_period_fourteenth = fields.Selection(PAYMENT_PERIOD_FOURTEENTH, string='Region',
                                                 default='sierra_oriente_fourteenth_salary', tracking=True, help='')
    calculation_period_fourteenth = fields.Char(string='Calculation period', tracking=True, help='')
    max_date_payment_period_fourteenth = fields.Char(string='Maximum date of payment', tracking=True,
                                                     help='The date before which the fourteenth salary '
                                                          'is due by region.')
    IESS_input_document = fields.Binary(string="Attach IESS input document", tracking=True, attachment=True,
                                        help='You can attach your IESS input documents.', copy=False)
    IESS_output_document = fields.Binary(string="Attach IESS output document", tracking=True, attachment=True,
                                         help='You can attach your IESS output documents.', copy=False)

    IESS_extra_spouse = fields.Boolean(string="IESS extra spouse", tracking=True)
    IESS_refund_contribution = fields.Boolean(string="Refund of contribution to the IESS", tracking=True)
    settlement = fields.Boolean(string="Settlement", tracking=True, default=False)