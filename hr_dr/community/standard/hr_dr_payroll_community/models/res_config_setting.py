# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PayrollSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _NOTIFICATIONS = [
        ('Without_notifications', 'Without notifications'),

        ('Administrator', 'Administrator'),

        ('One_level_bd', 'One level based on department'),
        ('One_level_br', 'One level based on responsible'),
        ('One_level_bc', 'One level based on coach'),

        ('One_level_bd_and_administrator', 'One level based on department and administrator'),
        ('One_level_br_and_administrator', 'One level based on responsible and administrator'),
        ('One_level_bc_and_administrator', 'One level based on coach and administrator'),

        ('One_level_bd_and_two_administrator', 'One level based on department and two administrator'),

        ('Two_levels_bd', 'Two levels based on department'),
        ('Two_levels_bd_and_administrator', 'Two levels based on department and administrator'),

        ('All_levels_bd', 'All levels based on department'),
        ('All_levels_bd_and_administrator', 'All levels based on department and administrator'),

        ('Personalized', 'Personalized')
    ]

    retired_employee_salary_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Retired collaborator salary notifications mode', help='', required=True)
    retired_employee_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator salary administrator',
        help='')
    retired_employee_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator salary second administrator',
        help='')
    credit_account_retired_employee_salary = fields.Many2one(
        'account.account',
        _('Default credit account for retired collaborator salary'),
        help='')
    debit_account_retired_employee_salary = fields.Many2one(
        'account.account',
        _('Default debit account for retired collaborator salary'),
        help='')
    account_analytic_account_retired_employee_salary = fields.Many2one(
        'account.analytic.account',
        _('Default analytic account for retired collaborator salary'),
        help='')
    journal_retired_employee_salary = fields.Many2one(
        'account.journal',
        _('Default journal for retired collaborator salary'),
        help='')

    retired_employee_thirteenth_salary_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Retired collaborator thirteenth salary notifications mode', help='', required=True)
    retired_employee_thirteenth_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator thirteenth salary administrator',
        help='')
    retired_employee_thirteenth_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator thirteenth salary second administrator',
        help='')
    credit_account_retired_employee_thirteenth_salary = fields.Many2one(
        'account.account',
        _('Default credit account for retired collaborator thirteenth salary'),
        help='')
    debit_account_retired_employee_thirteenth_salary = fields.Many2one(
        'account.account',
        _('Default debit account for retired collaborator thirteenth salary'),
        help='')
    account_analytic_account_retired_employee_thirteenth_salary = fields.Many2one(
        'account.analytic.account',
        _('Default analytic account for retired collaborator thirteenth salary'),
        help='')
    journal_retired_employee_thirteenth_salary = fields.Many2one(
        'account.journal',
        _('Default journal for retired collaborator thirteenth salary'),
        help='')

    retired_employee_fourteenth_salary_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Retired collaborator fourteenth salary notifications mode', help='', required=True)
    retired_employee_fourteenth_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator fourteenth salary administrator',
        help='')
    retired_employee_fourteenth_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator fourteenth salary second administrator',
        help='')
    credit_account_retired_employee_fourteenth_salary = fields.Many2one(
        'account.account',
        _('Default credit account for retired collaborator fourteenth salary'),
        help='')
    debit_account_retired_employee_fourteenth_salary = fields.Many2one(
        'account.account',
        _('Default debit account for retired collaborator fourteenth salary'),
        help='')
    account_analytic_account_retired_employee_fourteenth_salary = fields.Many2one(
        'account.analytic.account',
        _('Default analytic account for retired collaborator fourteenth salary'),
        help='')
    journal_retired_employee_fourteenth_salary = fields.Many2one(
        'account.journal',
        _('Default journal for retired collaborator fourteenth salary'),
        help='')

    payment_utility_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Payment utility notifications mode', help='', required=True)
    payment_utility_administrator = fields.Many2one(
        'hr.employee',
        'Payment utility administrator',
        help='')
    payment_utility_second_administrator = fields.Many2one(
        'hr.employee',
        'Payment utility second administrator',
        help='')
    _PROFIT_CALCULATION = [
        ('contract', 'Duration of the contract'),
        ('payroll', 'The days worked on the payroll'),
    ]
    profit_calculation_based_on = fields.Selection(
        _PROFIT_CALCULATION, string='Profit calculation based on', help='', required=True, default="contract")
    credit_account_payment_utility_id = fields.Many2one(
        'account.account',
        _('Default credit account for payment utility'),
        help='')
    debit_account_payment_utility_id = fields.Many2one(
        'account.account',
        _('Default debit account for payment utility'),
        help='')
    account_analytic_account_payment_utility_id = fields.Many2one(
        'account.analytic.account',
        _('Default analytic account for payment utility'),
        help='')
    journal_payment_utility_id = fields.Many2one(
        'account.journal',
        _('Default journal for payment utility'),
        help='')

    pay_living_wage_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Pay living wage notifications mode', help='', required=True)
    pay_living_wage_administrator = fields.Many2one(
        'hr.employee',
        'Pay living wage administrator',
        help='')
    pay_living_wage_second_administrator = fields.Many2one(
        'hr.employee',
        'Pay living wage second administrator',
        help='')
    credit_account_pay_living_wage_id = fields.Many2one(
        'account.account',
        _('Default credit account for pay living wage'),
        help='')
    debit_account_pay_living_wage_id = fields.Many2one(
        'account.account',
        _('Default debit account for pay living wage'),
        help='')
    account_analytic_account_pay_living_wage_id = fields.Many2one(
        'account.analytic.account',
        _('Default analytic account for pay living wage'),
        help='')
    journal_pay_living_wage_id = fields.Many2one(
        'account.journal',
        _('Default journal for pay living wage'),
        help='')

    payment_tenth_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Pay tenth notifications mode', help='', required=True)
    payment_tenth_administrator = fields.Many2one(
        'hr.employee',
        'Pay tenth administrator',
        help='')
    payment_tenth_second_administrator = fields.Many2one(
        'hr.employee',
        'Pay tenth second administrator',
        help='')

    @api.model
    def get_values(self):
        res = super(PayrollSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        def has_value(key):
            """
            Valida que el parámetro recibido exista y no tenga valor de cadena vacía.
            :param key: Clave del parámetro a buscar
            :return: True | False
            """
            value = config_parameter.get_param(key)
            if value and value != '':
                return True
            return False

        res.update(retired_employee_salary_notifications_mode=config_parameter.get_param(
            'retired.employee.salary.notifications.mode', default=''))
        if has_value('retired.employee.salary.administrator'):
            res.update(retired_employee_salary_administrator=int(
                config_parameter.get_param('retired.employee.salary.administrator')))
        if has_value('retired.employee.salary.second.administrator'):
            res.update(retired_employee_salary_second_administrator=int(
                config_parameter.get_param('retired.employee.salary.second.administrator')))
        if has_value('credit.account.retired.employee.salary.id'):
            res.update(credit_account_retired_employee_salary=int(
                config_parameter.get_param('credit.account.retired.employee.salary.id')))
        if has_value('debit.account.retired.employee.salary.id'):
            res.update(debit_account_retired_employee_salary=int(
                config_parameter.get_param('debit.account.retired.employee.salary.id')))
        if has_value('account.analytic.account.retired.employee.salary.id'):
            res.update(account_analytic_account_retired_employee_salary=int(
                config_parameter.get_param('account.analytic.account.retired.employee.salary.id')))
        if has_value('journal.retired.employee.salary.id'):
            res.update(journal_retired_employee_salary=int(
                config_parameter.get_param('journal.retired.employee.salary.id')))

        res.update(retired_employee_thirteenth_salary_notifications_mode=config_parameter.get_param(
            'retired.employee.thirteenth.salary.notifications.mode', default=''))
        if has_value('retired.employee.thirteenth.salary.administrator'):
            res.update(retired_employee_thirteenth_salary_administrator=int(
                config_parameter.get_param('retired.employee.thirteenth.salary.administrator')))
        if has_value('retired.employee.thirteenth.salary.second.administrator'):
            res.update(retired_employee_thirteenth_salary_second_administrator=int(
                config_parameter.get_param('retired.employee.thirteenth.salary.second.administrator')))
        if has_value('credit.account.retired.employee.thirteenth.salary.id'):
            res.update(credit_account_retired_employee_thirteenth_salary=int(
                config_parameter.get_param('credit.account.retired.employee.thirteenth.salary.id')))
        if has_value('debit.account.retired.employee.thirteenth.salary.id'):
            res.update(debit_account_retired_employee_thirteenth_salary=int(
                config_parameter.get_param('debit.account.retired.employee.thirteenth.salary.id')))
        if has_value('account.analytic.account.retired.employee.thirteenth.salary.id'):
            res.update(account_analytic_account_retired_employee_thirteenth_salary=int(
                config_parameter.get_param('account.analytic.account.retired.employee.thirteenth.salary.id')))
        if has_value('journal.retired.employee.thirteenth.salary.id'):
            res.update(journal_retired_employee_thirteenth_salary=int(
                config_parameter.get_param('journal.retired.employee.thirteenth.salary.id')))

        res.update(retired_employee_fourteenth_salary_notifications_mode=config_parameter.get_param(
            'retired.employee.fourteenth.salary.notifications.mode', default=''))
        if has_value('retired.employee.fourteenth.salary.administrator'):
            res.update(retired_employee_fourteenth_salary_administrator=int(
                config_parameter.get_param('retired.employee.fourteenth.salary.administrator')))
        if has_value('retired.employee.fourteenth.salary.second.administrator'):
            res.update(retired_employee_fourteenth_salary_second_administrator=int(
                config_parameter.get_param('retired.employee.fourteenth.salary.second.administrator')))
        if has_value('credit.account.retired.employee.fourteenth.salary.id'):
            res.update(credit_account_retired_employee_fourteenth_salary=int(
                config_parameter.get_param('credit.account.retired.employee.fourteenth.salary.id')))
        if has_value('debit.account.retired.employee.fourteenth.salary.id'):
            res.update(debit_account_retired_employee_fourteenth_salary=int(
                config_parameter.get_param('debit.account.retired.employee.fourteenth.salary.id')))
        if has_value('account.analytic.account.retired.employee.fourteenth.salary.id'):
            res.update(account_analytic_account_retired_employee_fourteenth_salary=int(
                config_parameter.get_param('account.analytic.account.retired.employee.fourteenth.salary.id')))
        if has_value('journal.retired.employee.fourteenth.salary.id'):
            res.update(journal_retired_employee_fourteenth_salary=int(
                config_parameter.get_param('journal.retired.employee.fourteenth.salary.id')))

        res.update(payment_utility_notifications_mode=config_parameter.get_param(
            'payment.utility.notifications.mode', default=''))
        if has_value('payment.utility.administrator'):
            res.update(payment_utility_administrator=int(
                config_parameter.get_param('payment.utility.administrator')))
        if has_value('payment.utility.second.administrator'):
            res.update(payment_utility_second_administrator=int(
                config_parameter.get_param('payment.utility.second.administrator')))
        res.update(profit_calculation_based_on=config_parameter.get_param(
            'profit.calculation.based.on', default=''))
        if has_value('credit.account.payment.utility.id'):
            res.update(credit_account_payment_utility_id=int(
                config_parameter.get_param('credit.account.payment.utility.id')))
        if has_value('debit.account.payment.utility.id'):
            res.update(debit_account_payment_utility_id=int(
                config_parameter.get_param('debit.account.payment.utility.id')))
        if has_value('account.analytic.account.payment.utility.id'):
            res.update(account_analytic_account_payment_utility_id=int(
                config_parameter.get_param('account.analytic.account.payment.utility.id')))
        if has_value('journal.payment.utility.id'):
            res.update(journal_payment_utility_id=int(
                config_parameter.get_param('journal.payment.utility.id')))

        res.update(pay_living_wage_notifications_mode=config_parameter.get_param(
            'pay.living.wage.notifications.mode', default=''))
        if has_value('pay.living.wage.administrator'):
            res.update(pay_living_wage_administrator=int(
                config_parameter.get_param('pay.living.wage.administrator')))
        if has_value('pay.living.wage.second.administrator'):
            res.update(pay_living_wage_second_administrator=int(
                config_parameter.get_param('pay.living.wage.second.administrator')))
        if has_value('credit.account.pay.living.wage.id'):
            res.update(credit_account_pay_living_wage_id=int(
                config_parameter.get_param('credit.account.pay.living.wage.id')))
        if has_value('debit.account.pay.living.wage.id'):
            res.update(debit_account_pay_living_wage_id=int(
                config_parameter.get_param('debit.account.pay.living.wage.id')))
        if has_value('account.analytic.account.pay.living.wage.id'):
            res.update(account_analytic_account_pay_living_wage_id=int(
                config_parameter.get_param('account.analytic.account.pay.living.wage.id')))
        if has_value('journal.pay.living.wage.id'):
            res.update(journal_pay_living_wage_id=int(
                config_parameter.get_param('journal.pay.living.wage.id')))

        res.update(payment_tenth_notifications_mode=config_parameter.get_param(
            'payment.tenth.notifications.mode', default=''))
        if has_value('payment.tenth.administrator'):
            res.update(payment_tenth_administrator=int(
                config_parameter.get_param('payment.tenth.administrator')))
        if has_value('payment.tenth.second.administrator'):
            res.update(payment_tenth_second_administrator=int(
                config_parameter.get_param('payment.tenth.second.administrator')))

        return res
    
    def set_values(self):
        res = super(PayrollSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("retired.employee.salary.notifications.mode",
                  self.retired_employee_salary_notifications_mode)
        set_param("retired.employee.salary.administrator",
                  self.retired_employee_salary_administrator.id)
        set_param("retired.employee.salary.second.administrator",
                  self.retired_employee_salary_second_administrator.id)
        set_param('credit.account.retired.employee.salary.id',
                  self.credit_account_retired_employee_salary.id)
        set_param('debit.account.retired.employee.salary.id',
                  self.debit_account_retired_employee_salary.id)
        set_param('account.analytic.account.retired.employee.salary.id',
                  self.account_analytic_account_retired_employee_salary.id)
        set_param('journal.retired.employee.salary.id',
                  self.journal_retired_employee_salary.id)

        set_param("retired.employee.thirteenth.salary.notifications.mode",
                  self.retired_employee_thirteenth_salary_notifications_mode)
        set_param("retired.employee.thirteenth.salary.administrator",
                  self.retired_employee_thirteenth_salary_administrator.id)
        set_param("retired.employee.thirteenth.salary.second.administrator",
                  self.retired_employee_thirteenth_salary_second_administrator.id)
        set_param('credit.account.retired.employee.thirteenth.salary.id',
                  self.credit_account_retired_employee_thirteenth_salary.id)
        set_param('debit.account.retired.employee.thirteenth.salary.id',
                  self.debit_account_retired_employee_thirteenth_salary.id)
        set_param('account.analytic.account.retired.employee.thirteenth.salary.id',
                  self.account_analytic_account_retired_employee_thirteenth_salary.id)
        set_param('journal.retired.employee.thirteenth.salary.id',
                  self.journal_retired_employee_thirteenth_salary.id)

        set_param("retired.employee.fourteenth.salary.notifications.mode",
                  self.retired_employee_fourteenth_salary_notifications_mode)
        set_param("retired.employee.fourteenth.salary.administrator",
                  self.retired_employee_fourteenth_salary_administrator.id)
        set_param("retired.employee.fourteenth.salary.second.administrator",
                  self.retired_employee_fourteenth_salary_second_administrator.id)
        set_param('credit.account.retired.employee.fourteenth.salary.id',
                  self.credit_account_retired_employee_fourteenth_salary.id)
        set_param('debit.account.retired.employee.fourteenth.salary.id',
                  self.debit_account_retired_employee_fourteenth_salary.id)
        set_param('account.analytic.account.retired.employee.fourteenth.salary.id',
                  self.account_analytic_account_retired_employee_fourteenth_salary.id)
        set_param('journal.retired.employee.fourteenth.salary.id',
                  self.journal_retired_employee_fourteenth_salary.id)

        set_param("payment.utility.notifications.mode",
                  self.payment_utility_notifications_mode)
        set_param("payment.utility.administrator",
                  self.payment_utility_administrator.id)
        set_param("payment.utility.second.administrator",
                  self.payment_utility_second_administrator.id)
        set_param("profit.calculation.based.on",
                  self.profit_calculation_based_on)

        set_param("pay.living.wage.notifications.mode",
                  self.pay_living_wage_notifications_mode)
        set_param("pay.living.wage.administrator",
                  self.pay_living_wage_administrator.id)
        set_param("pay.living.wage.second.administrator",
                  self.pay_living_wage_second_administrator.id)

        set_param("payment.tenth.notifications.mode",
                  self.payment_tenth_notifications_mode)
        set_param("payment.tenth.administrator",
                  self.payment_tenth_administrator.id)
        set_param("payment.tenth.second.administrator",
                  self.payment_tenth_second_administrator.id)

        return res