# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import time


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    retired_employee_salary_id = fields.Many2one('retired.employee.salary', 'Retired collaborator salary')
    retired_employee_d13_salary_id = fields.Many2one('retired.employee.thirteenth.salary',
                                                     'Retired collaborator thirteenth salary')
    retired_employee_d14_salary_id = fields.Many2one('retired.employee.fourteenth.salary',
                                                     'Retired collaborator fourteenth salary')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    retired_employee_salary_id = fields.Many2one('retired.employee.salary', string="Retired employee salary")
    retired_employee_thirteenth_salary_id = fields.Many2one('retired.employee.thirteenth.salary',
                                                            string="Retired employee thirteenth salary")
    retired_employee_fourteenth_salary_id = fields.Many2one('retired.employee.fourteenth.salary',
                                                            string="Retired employee fourteenth salary")


class RetiredEmployeeSalary(models.Model):
    _inherit = 'retired.employee.salary'

    def action_done(self):
        super(RetiredEmployeeSalary, self).action_done()
        mode = self.company_id.re_salary_accounting_entries_based

        for re in self:
            line_ids = []
            retired_employee_period = _("{} - {}").format(
                re.period_start.strftime("%d/%m/%Y"), re.period_end.strftime("%d/%m/%Y"))
            name = _("Retired collaborator salary: {}").format(retired_employee_period)

            for line in re.retired_employee_salary_line_ids:

                journal_id = self.get_journal()
                analytic_account_id = self.get_account_analytic_account(mode, line)
                debit_account_id = self.get_debit_account(mode, line)
                credit_account_id = self.get_credit_account(mode, line)

                if not journal_id or not debit_account_id or not credit_account_id:
                    raise UserError(_("You must enter the ledger accounts and the journal in order "
                                      "to mark the retired collaborator salary as done."))
                detail_name = _("Retired collaborator salary for {}. ({})").format(line.employee_id.name,
                                                                                   retired_employee_period)
                base_line = {
                    'credit': 0.00,
                    'debit': 0.00,
                    'date': self.date,
                    'name': detail_name,
                    'analytic_distribution': {analytic_account_id.id: 100}
                }
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': debit_account_id.id,
                    'debit': line.value,
                }))
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': credit_account_id.id,
                    'credit': line.value,
                    'partner_id': line.employee_id.address_home_id.id,
                }))

                vals = {
                    'name': name,
                    'ref': name,
                    'journal_id': journal_id,
                    'date': re.date,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()

    @api.model
    def get_credit_account(self, mode, detail):
        credit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.re_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_credit:
                        credit_account_id = salary_rule.account_credit
                    else:
                        raise ValidationError(
                            _("You must specify the credit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            credit_account_id = self.company_id.re_salary_credit_account
            if not credit_account_id:
                raise ValidationError(_("You must configure the credit account for retired collaborator salary "
                                        "in the company's configuration."))
        return credit_account_id

    @api.model
    def get_debit_account(self, mode, detail):
        debit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.re_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_debit:
                        debit_account_id = salary_rule.account_debit
                    else:
                        raise ValidationError(
                            _("You must specify the debit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            debit_account_id = self.company_id.re_salary_debit_account
            if not debit_account_id:
                raise ValidationError(_("You must configure the debit account for retired collaborator salary "
                                        "in the company's configuration."))
        return debit_account_id

    @api.model
    def get_journal(self):
        return self.company_id.re_salary_journal.id

    @api.model
    def get_account_analytic_account(self, mode, detail):
        analytic_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.re_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.analytic_account_id:
                        analytic_account_id = salary_rule.analytic_account_id
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            analytic_account_id = self.company_id.re_salary_account_analytic_account
        return analytic_account_id

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('retired_employee_salary_id', '=', self.id)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def action_cancel(self):
        pass

    def generate_payments(self, account_journal):
        for line in self.pay_living_wage_line_ids:
            if line.value_to_receive > 0:
                self.create_payment(line, account_journal)

    def create_payment(self, line, account_journal):
        mode = self.company_id.re_salary_accounting_entries_based
        debit_account_id = self.get_debit_account(mode, line)
        if not debit_account_id:
            raise ValidationError(_("You must set up the retired collaborator salary debit account in the company."))

        obj_payment = self.env['account.payment']
        obj_payment_method_line = self.env['account.payment.method.line']

        journal_id = False
        if account_journal:
            journal_id = account_journal
        else:
            if self.company_id.payroll_mode == "01":
                journal_id = self.company_id.main_account_journal
            else:
                for account_journal in self.company_id.account_journal_ids:
                    if account_journal.bank_account_id.bank_id == line.employee_id.bank_account_id.bank_id:
                        journal_id = account_journal
        if not journal_id:
            raise ValidationError(_("You must configure the accounting journal for payroll payments "
                                    "in the company configuration. Review the collaborator's bank account: %s.") %
                                  line.employee_id.name)

        method_line = obj_payment_method_line.search([
            ('code', '=', 'check'),
            ('payment_type', '=', 'outbound'),
            ('journal_id', '=', journal_id.id),
        ], limit=1)
        bank = line.employee_id.bank_account_id.id if line.employee_id.bank_account_id else None
        if bank:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'transfer'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)
        if not method_line:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'manual'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)

        retired_employee_period = _("{} - {}").format(self.period_start.strftime("%d/%m/%Y"),
                                                      self.period_end.strftime("%d/%m/%Y"))
        ref = _("Retired collaborator salary for {}. ({})").format(line.employee_id.name, retired_employee_period)

        account_payment = obj_payment.create({
            'partner_type': 'supplier',
            'is_internal_transfer': False,
            'partner_id': False,
            'employee_id': line.employee_id.address_home_id.id,
            'amount': line.value_to_receive,
            'date': self.date,
            'ref': ref,
            'payment_type': 'outbound',
            'payroll_payment': True,
            'journal_id': journal_id.id,
            'destination_account_id': debit_account_id.id,
            'payment_method_line_id': method_line.id,
            'partner_bank_id': bank,
            'company_id': self.env.company.id,
        })
        account_payment.partner_type = 'supplier'

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Retired collaborator salary request")
        local_context['request'] = _("you have made a retired collaborator salary request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id
        local_context['details'] = _("Retired collaborator salary request from {} to {}.").format(
            self.period_start, self.period_end)
        local_context['commentary'] = self.commentary
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref(
            'hr_dr_payroll_base.retired_employee_salary_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_work_entry_contract_enterprise.menu_hr_payroll_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        return local_context

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
        template = self.env.ref('hr_dr_payroll_base.email_template_retired_employee_salary_notify_treasury', False)
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


class RetiredEmployeeThirteenthSalary(models.Model):
    _inherit = 'retired.employee.thirteenth.salary'

    def action_done(self):
        super(RetiredEmployeeThirteenthSalary, self).action_done()
        mode = self.company_id.red13_salary_accounting_entries_based

        for re in self:
            line_ids = []
            retired_employee_period = _("{} - {}").format(
                re.period_start.strftime("%d/%m/%Y"), re.period_end.strftime("%d/%m/%Y"))
            name = _("Retired collaborator thirteenth salary: {}").format(retired_employee_period)

            for line in re.retired_employee_thirteenth_salary_line_ids:

                journal_id = self.get_journal()
                analytic_account_id = self.get_account_analytic_account(mode, line)
                debit_account_id = self.get_debit_account(mode, line)
                credit_account_id = self.get_credit_account(mode, line)

                if not journal_id or not debit_account_id or not credit_account_id:
                    raise UserError(_("You must enter the ledger accounts and the journal in order "
                                      "to mark the retired collaborator thirteenth salary as done."))
                detail_name = _("Retired collaborator thirteenth salary for {}. ({})").format(line.employee_id.name,
                                                                                              retired_employee_period)
                base_line = {
                    'credit': 0.00,
                    'debit': 0.00,
                    'date': self.date,
                    'name': detail_name,
                    'analytic_distribution': {analytic_account_id.id: 100}
                }
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': debit_account_id.id,
                    'debit': line.value,
                }))
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': credit_account_id.id,
                    'credit': line.value,
                    'partner_id': line.employee_id.address_home_id.id,
                }))

                vals = {
                    'name': name,
                    'ref': name,
                    'journal_id': journal_id,
                    'date': re.date,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()

    @api.model
    def get_credit_account(self, mode, detail):
        credit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red13_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_credit:
                        credit_account_id = salary_rule.account_credit
                    else:
                        raise ValidationError(
                            _("You must specify the credit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            credit_account_id = self.company_id.red13_salary_credit_account
            if not credit_account_id:
                raise ValidationError(_("You must configure the credit account for retired collaborator salary "
                                        "in the company's configuration."))
        return credit_account_id

    @api.model
    def get_debit_account(self, mode, detail):
        debit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red13_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_debit:
                        debit_account_id = salary_rule.account_debit
                    else:
                        raise ValidationError(
                            _("You must specify the debit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            debit_account_id = self.company_id.red13_salary_debit_account
            if not debit_account_id:
                raise ValidationError(_("You must configure the debit account for retired collaborator salary "
                                        "in the company's configuration."))
        return debit_account_id

    @api.model
    def get_journal(self):
        return self.company_id.red13_salary_journal.id

    @api.model
    def get_account_analytic_account(self, mode, detail):
        analytic_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red13_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.analytic_account_id:
                        analytic_account_id = salary_rule.analytic_account_id
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            analytic_account_id = self.company_id.red13_salary_account_analytic_account
        return analytic_account_id

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('retired_employee_thirteenth_salary_id', '=', self.id)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def action_cancel(self):
        pass

    def generate_payments(self, account_journal):
        for line in self.pay_living_wage_line_ids:
            if line.value_to_receive > 0:
                self.create_payment(line, account_journal)

    def create_payment(self, line, account_journal):
        mode = self.company_id.red13_salary_accounting_entries_based
        debit_account_id = self.get_debit_account(mode, line)
        if not debit_account_id:
            raise ValidationError(_("You must set up the retired collaborator thirteenth salary "
                                    "debit account in the company."))

        obj_payment = self.env['account.payment']
        obj_payment_method_line = self.env['account.payment.method.line']

        journal_id = False
        if account_journal:
            journal_id = account_journal
        else:
            if self.company_id.payroll_mode == "01":
                journal_id = self.company_id.main_account_journal
            else:
                for account_journal in self.company_id.account_journal_ids:
                    if account_journal.bank_account_id.bank_id == line.employee_id.bank_account_id.bank_id:
                        journal_id = account_journal
        if not journal_id:
            raise ValidationError(_("You must configure the accounting journal for payroll payments "
                                    "in the company configuration. Review the collaborator's bank account: %s.") %
                                  line.employee_id.name)

        method_line = obj_payment_method_line.search([
            ('code', '=', 'check'),
            ('payment_type', '=', 'outbound'),
            ('journal_id', '=', journal_id.id),
        ], limit=1)
        bank = line.employee_id.bank_account_id.id if line.employee_id.bank_account_id else None
        if bank:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'transfer'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)
        if not method_line:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'manual'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)

        retired_employee_period = _("{} - {}").format(self.period_start.strftime("%d/%m/%Y"),
                                                      self.period_end.strftime("%d/%m/%Y"))
        ref = _("Retired collaborator thirteenth salary for {}. ({})").format(line.employee_id.name,
                                                                              retired_employee_period)
        account_payment = obj_payment.create({
            'partner_type': 'supplier',
            'is_internal_transfer': False,
            'partner_id': False,
            'employee_id': line.employee_id.address_home_id.id,
            'amount': line.value_to_receive,
            'date': self.date,
            'ref': ref,
            'payment_type': 'outbound',
            'payroll_payment': True,
            'journal_id': journal_id.id,
            'destination_account_id': debit_account_id.id,
            'payment_method_line_id': method_line.id,
            'partner_bank_id': bank,
            'company_id': self.env.company.id,
        })
        account_payment.partner_type = 'supplier'

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Retired collaborator thirteenth salary request")
        local_context['request'] = _("you have made a retired collaborator thirteenth salary request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id
        local_context['details'] = _("Retired collaborator thirteenth salary request from {} to {}.").format(
            self.period_start, self.period_end)
        local_context['commentary'] = self.commentary
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref(
            'hr_dr_payroll_base.retired_employee_thirteenth_salary_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_work_entry_contract_enterprise.menu_hr_payroll_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        return local_context

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
        template = self.env.ref('hr_dr_payroll_base.email_template_retired_employee_thirteenth_salary_notify_treasury', False)
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


class RetiredEmployeeFourteenthSalary(models.Model):
    _inherit = 'retired.employee.fourteenth.salary'

    def action_done(self):
        super(RetiredEmployeeFourteenthSalary, self).action_done()
        mode = self.company_id.red14_salary_accounting_entries_based

        for re in self:
            line_ids = []
            retired_employee_period = _("{} - {}").format(
                re.period_start.strftime("%d/%m/%Y"), re.period_end.strftime("%d/%m/%Y"))
            name = _("Retired collaborator fourteenth salary: {}").format(retired_employee_period)

            for line in re.retired_employee_fourteenth_salary_line_ids:

                journal_id = self.get_journal()
                analytic_account_id = self.get_account_analytic_account(mode, line)
                debit_account_id = self.get_debit_account(mode, line)
                credit_account_id = self.get_credit_account(mode, line)

                if not journal_id or not debit_account_id or not credit_account_id:
                    raise UserError(_("You must enter the ledger accounts and the journal in order "
                                      "to mark the retired collaborator fourteenth salary as done."))
                detail_name = _("Retired collaborator fourteenth salary for {}. ({})").format(line.employee_id.name,
                                                                                              retired_employee_period)
                base_line = {
                    'credit': 0.00,
                    'debit': 0.00,
                    'date': self.date,
                    'name': detail_name,
                    'analytic_distribution': {analytic_account_id.id: 100}
                }
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': debit_account_id.id,
                    'debit': line.value,
                }))
                line_ids.append((0, 0, {
                    **base_line,
                    'account_id': credit_account_id.id,
                    'credit': line.value,
                    'partner_id': line.employee_id.address_home_id.id,
                }))

                vals = {
                    'name': name,
                    'ref': name,
                    'journal_id': journal_id,
                    'date': re.date,
                    'line_ids': line_ids
                }
                move = self.env['account.move'].create(vals)
                move.post()

    @api.model
    def get_credit_account(self, mode, detail):
        credit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red14_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_credit:
                        credit_account_id = salary_rule.account_credit
                    else:
                        raise ValidationError(
                            _("You must specify the credit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            credit_account_id = self.company_id.red14_salary_credit_account
            if not credit_account_id:
                raise ValidationError(_("You must configure the credit account for retired collaborator salary "
                                        "in the company's configuration."))
        return credit_account_id

    @api.model
    def get_debit_account(self, mode, detail):
        debit_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red14_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.account_debit:
                        debit_account_id = salary_rule.account_debit
                    else:
                        raise ValidationError(
                            _("You must specify the debit account for salary rule {} of salary structure {}.").format(
                                salary_rule.name, last_contract.struct_id.name))
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            debit_account_id = self.company_id.red14_salary_debit_account
            if not debit_account_id:
                raise ValidationError(_("You must configure the debit account for retired collaborator salary "
                                        "in the company's configuration."))
        return debit_account_id

    @api.model
    def get_journal(self):
        return self.company_id.red14_salary_journal.id

    @api.model
    def get_account_analytic_account(self, mode, detail):
        analytic_account_id = False
        if mode == '01':
            employee_id = detail.employee_id
            last_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('state', 'in', ['open', 'close']), ],
                order='date_start DESC', limit=1
            )
            if last_contract and last_contract.struct_id:
                code = self.company_id.red14_salary_salary_rule_code
                salary_rule = self.env['hr.salary.rule'].search([
                    ('struct_id', '=', last_contract.struct_id.id),
                    ('code', '=', code),
                ], limit=1)
                if salary_rule:
                    if salary_rule.analytic_account_id:
                        analytic_account_id = salary_rule.analytic_account_id
                else:
                    raise ValidationError(
                        _("No salary rule with code {} was found within the {} salary structure.").format(
                            code, last_contract.struct_id.name))
            else:
                raise ValidationError(
                    _("A contract was not found for the collaborator {} or "
                      "the contract found does not have a salary structure.").format(employee_id.name))
        else:
            analytic_account_id = self.company_id.red14_salary_account_analytic_account
        return analytic_account_id

    def action_view_payment(self):
        payments = self.env['account.payment'].search(
            [('payroll_payment', '=', True),
             ('retired_employee_fourteenth_salary_id', '=', self.id)])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def action_cancel(self):
        pass

    def generate_payments(self, account_journal):
        for line in self.pay_living_wage_line_ids:
            if line.value_to_receive > 0:
                self.create_payment(line, account_journal)

    def create_payment(self, line, account_journal):
        mode = self.company_id.red14_salary_accounting_entries_based
        debit_account_id = self.get_debit_account(mode, line)
        if not debit_account_id:
            raise ValidationError(_("You must set up the retired collaborator fourteenth salary "
                                    "debit account in the company."))

        obj_payment = self.env['account.payment']
        obj_payment_method_line = self.env['account.payment.method.line']

        journal_id = False
        if account_journal:
            journal_id = account_journal
        else:
            if self.company_id.payroll_mode == "01":
                journal_id = self.company_id.main_account_journal
            else:
                for account_journal in self.company_id.account_journal_ids:
                    if account_journal.bank_account_id.bank_id == line.employee_id.bank_account_id.bank_id:
                        journal_id = account_journal
        if not journal_id:
            raise ValidationError(_("You must configure the accounting journal for payroll payments "
                                    "in the company configuration. Review the collaborator's bank account: %s.") %
                                  line.employee_id.name)

        method_line = obj_payment_method_line.search([
            ('code', '=', 'check'),
            ('payment_type', '=', 'outbound'),
            ('journal_id', '=', journal_id.id),
        ], limit=1)
        bank = line.employee_id.bank_account_id.id if line.employee_id.bank_account_id else None
        if bank:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'transfer'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)
        if not method_line:
            method_line = obj_payment_method_line.search([
                ('code', '=', 'manual'),
                ('payment_type', '=', 'outbound'),
                ('journal_id', '=', journal_id.id),
            ], limit=1)

        retired_employee_period = _("{} - {}").format(self.period_start.strftime("%d/%m/%Y"),
                                                      self.period_end.strftime("%d/%m/%Y"))
        ref = _("Retired collaborator fourteenth salary for {}. ({})").format(line.employee_id.name,
                                                                              retired_employee_period)
        account_payment = obj_payment.create({
            'partner_type': 'supplier',
            'is_internal_transfer': False,
            'partner_id': False,
            'employee_id': line.employee_id.address_home_id.id,
            'amount': line.value_to_receive,
            'date': self.date,
            'ref': ref,
            'payment_type': 'outbound',
            'payroll_payment': True,
            'journal_id': journal_id.id,
            'destination_account_id': debit_account_id.id,
            'payment_method_line_id': method_line.id,
            'partner_bank_id': bank,
            'company_id': self.env.company.id,
        })
        account_payment.partner_type = 'supplier'

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Retired collaborator fourteenth salary request")
        local_context['request'] = _("you have made a retired collaborator fourteenth salary request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id
        local_context['details'] = _("Retired collaborator fourteenth salary request from {} to {}.").format(
            self.period_start, self.period_end)
        local_context['commentary'] = self.commentary
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref(
            'hr_dr_payroll_base.retired_employee_fourteenth_salary_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = self.env.ref('hr_work_entry_contract_enterprise.menu_hr_payroll_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url
        department = _('Human Talent Management')
        management_responsible = self.employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name
        local_context['department'] = department
        return local_context

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
        template = self.env.ref('hr_dr_payroll_base.email_template_retired_employee_fourteenth_salary_notify_treasury', False)
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