# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class PayLivingWage(models.Model):
    _name = 'pay.living.wage'
    _description = 'Pay living wage'
    _inherit = ['hr.generic.request']
    _order = "fiscal_year desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_payroll_base.email_template_confirm_pay_living_wage',
            'confirm_direct': 'hr_dr_payroll_base.email_template_confirm_direct_approve_pay_living_wage',
            'approve': 'hr_dr_payroll_base.email_template_confirm_approve_pay_living_wage',
            'reject': 'hr_dr_payroll_base.email_template_confirm_reject_pay_living_wage',
            'cancel': 'hr_dr_payroll_base.email_template_confirm_cancel_pay_living_wage',
            'paid': 'hr_dr_payroll_base.email_template_pay_living_wage_notify_treasury'
        }
    _hr_notifications_mode_param = 'pay.living.wage.notifications.mode'
    _hr_administrator_param = 'pay.living.wage.administrator'
    _hr_second_administrator_param = 'pay.living.wage.second.administrator'

    def _default_start_date(self):
        start_date = datetime.utcnow().date() + relativedelta(day=1, month=1, years=-1)
        return start_date

    @api.onchange('period_start')
    def onchange_period_start(self):
        if self.period_start:
            self.period_end = self.period_start + relativedelta(day=31, month=12)
            self.fiscal_year = self.period_start.year

    def unlink(self):
        for res in self:
            if res.state != 'draft':
                raise ValidationError(_('You can only delete the living wage payment in draft status.'))
        return super(PayLivingWage, self).unlink()

    def name_get(self):
        result = []
        for res in self:
            result.append(
                (
                    res.id,
                    _("Pay living wage {} - {}").format(res.period_start, res.period_end)
                )
            )
        return result

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
        template = self.env.ref('hr_dr_payroll_base.email_template_pay_living_wage_notify_treasury', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        local_context = self.env.context.copy()
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def generate_payments(self):
        pass

    @api.model
    def get_living_wage_by_year(self, year):
        living_wage = self.env['hr.living.wage'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if living_wage:
            return living_wage.value
        else:
            raise ValidationError(_('You must set the living wage for the year {}.').format(str(year)))

    def get_total_living_wage(self, year):
        living_wage = self.get_living_wage_by_year(year)
        return living_wage * 12.0

    def get_proportional_living_wage(self, year, worked_days):
        total_living_wage = self.get_total_living_wage(year)
        return round(worked_days * total_living_wage / 360.0, 2)

    def get_utility_by_year_and_employee(self, year, employee):
        utility_line = self.env['hr.payment.utility.line'].sudo().search([
            ('fiscal_year', '=', year - 1),
            ('state_utility', 'in', ['done']),
            ('employee_id', '=', employee.id),
        ], limit=1)
        if utility_line:
            return utility_line.total_utility
        else:
            return 0

    def action_create_update_lines(self, delete_actual_lines=True):
        pass

    def mark_as_reviewed(self):
        self.state = 'reviewed'

    def mark_as_done(self):
        self.state = 'done'

    def mark_as_draft(self):
        super(PayLivingWage, self).mark_as_draft()
        line_ids = self.env['pay.living.wage.line'].with_context(
            active_test=False).search([('pay_living_wage_id', '=', self.id)])
        if line_ids:
            line_ids.unlink()

    def get_local_context(self, id=None):
        pass

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
            if len(configurations) > 0:
                for configuration in configurations:
                    pass

    def action_view_payment(self):
        pass

    pay_living_wage_line_ids = fields.One2many('pay.living.wage.line', 'pay_living_wage_id',
                                               string="Living wage payment detail")
    period_start = fields.Date(string='Start of period', required=True, default=_default_start_date, tracking=True)
    period_end = fields.Date(string='End of period', required=True, tracking=True)
    date = fields.Date(string='Posting date', default=fields.Date.today(), help='', tracking=True)
    fiscal_year = fields.Integer(string='Fiscal year', tracking=True, help='')
    utility = fields.Monetary(string="Utility", tracking=True, currency_field='currency_id',
                              help="Utility of the company.")
    state = fields.Selection(selection_add=[
        ('calculated', _('Calculated')),
        ('recalculate', _('Recalculate')),
        ('reviewed', _('Reviewed')),
        ('done', _('Done')),
        ('paid', _('Paid')),
    ])


class PayLivingWageLine(models.Model):
    _name = 'pay.living.wage.line'
    _description = 'Pay living wage detail'
    _rec_name = 'employee_id'
    _order = "pay_living_wage_id, employee_id"
    _inherit = ['mail.thread']

    pay_living_wage_id = fields.Many2one('pay.living.wage', string="Pay living wage", tracking=True, required=True,
                                         readonly=True, ondelete='cascade')
    company_id = fields.Many2one(related='pay_living_wage_id.company_id', string='Company')
    currency_id = fields.Many2one(related='pay_living_wage_id.currency_id', string='Currency')

    fiscal_year = fields.Integer(related='pay_living_wage_id.fiscal_year', store="True", string='Fiscal year', help='')
    state = fields.Selection(string='Status', tracking=True, related='pay_living_wage_id.state', store="True")
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, tracking=True,
                                  ondelete='cascade')
    employee_state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
        ('unemployed', _('Unemployed')),
        ('retired', _('Retired'))
    ], string='Collaborator status', default='affiliate', tracking=True)

    wage = fields.Monetary(string="Wage", tracking=True, currency_field='currency_id',
                           help="The monthly salary or salary of the previous fiscal year.")
    thirteenth_salary = fields.Monetary(string="Thirteenth salary", tracking=True,
                                        currency_field='currency_id',
                                        help="The thirteenth remuneration corresponding to the proportional value "
                                             "of the time worked in the previous fiscal year.")
    fourteenth_salary = fields.Monetary(string="Fourteenth salary", tracking=True,
                                        currency_field='currency_id',
                                        help="The fourteenth remuneration corresponding to the proportional value "
                                             "of the time worked in the previous fiscal year.")
    commissions = fields.Monetary(string="Commissions", tracking=True, currency_field='currency_id',
                                  help="The variable commissions that the employer would have paid to the worker or "
                                       "ex-worker that obey legitimate and usual commercial practices in "
                                       "the previous fiscal year.")
    utility = fields.Monetary(string="Utility", tracking=True, currency_field='currency_id',
                              help="The participation of profits to workers or former workers of the "
                                   "previous fiscal year.")
    other_income = fields.Monetary(string="Additional benefits", tracking=True,
                                   currency_field='currency_id',
                                   help="The additional benefits received in cash by the worker through "
                                        "collective contracts, which do not constitute legal obligations, "
                                        "and the periodic voluntary contributions in cash by the employer "
                                        "to its workers in the previous fiscal year.")
    reserve_fund = fields.Monetary(string="Reserve funds", tracking=True,
                                   currency_field='currency_id',
                                   help="The reserve funds corresponding to the previous fiscal year.")
    historical = fields.Monetary(string="historical", tracking=True, currency_field='currency_id',
                                 help="Used when the system starts after the first of January.")
    worked_days = fields.Float(string="Worked days", tracking=True)
    total_living_wage = fields.Monetary(string="Total living wage for the period", tracking=True,
                                        currency_field='currency_id')
    proportional_living_wage = fields.Monetary(string="Proportional living wage for the period",
                                               currency_field='currency_id', tracking=True)
    all_income = fields.Monetary(string="Total revenue", tracking=True, currency_field='currency_id')
    value = fields.Monetary(string="Calculated compensation", tracking=True,
                            currency_field='currency_id')
    value_to_receive = fields.Monetary(string="Compensation to receive", tracking=True,
                                       currency_field='currency_id')