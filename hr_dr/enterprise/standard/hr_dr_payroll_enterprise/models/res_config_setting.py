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
        _NOTIFICATIONS, string='Retired collaborator salary notifications mode')
    retired_employee_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator salary administrator',
        help='')
    retired_employee_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator salary second administrator',
        help='')

    retired_employee_thirteenth_salary_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Retired collaborator thirteenth salary notifications mode')
    retired_employee_thirteenth_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator thirteenth salary administrator',
        help='')
    retired_employee_thirteenth_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator thirteenth salary second administrator',
        help='')

    retired_employee_fourteenth_salary_notifications_mode = fields.Selection(
        _NOTIFICATIONS, string='Retired collaborator fourteenth salary notifications mode')
    retired_employee_fourteenth_salary_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator fourteenth salary administrator',
        help='')
    retired_employee_fourteenth_salary_second_administrator = fields.Many2one(
        'hr.employee',
        'Retired collaborator fourteenth salary second administrator',
        help='')

    payment_utility_notifications_mode = fields.Selection(_NOTIFICATIONS, string='Payment utility notifications mode')
    payment_utility_administrator = fields.Many2one(
        'hr.employee',
        'Payment utility administrator',
        help='')
    payment_utility_second_administrator = fields.Many2one(
        'hr.employee',
        'Payment utility second administrator',
        help='')
    _PROFIT_CALCULATION = [
        ('payroll', 'The days worked on the payroll'),
        ('history', 'The days worked in the history'),
        ('contract', 'Duration of the contract'),
    ]
    profit_calculation_based_on = fields.Selection(
        _PROFIT_CALCULATION, string='Profit calculation based on', help='', required=True, default="contract")
    include_external_services_in_csv_file = fields.Boolean(
        string='Include external services personnel in the utility legalization file')

    pay_living_wage_notifications_mode = fields.Selection(_NOTIFICATIONS, string='Pay living wage notifications mode')
    pay_living_wage_administrator = fields.Many2one(
        'hr.employee',
        'Pay living wage administrator',
        help='')
    pay_living_wage_second_administrator = fields.Many2one(
        'hr.employee',
        'Pay living wage second administrator',
        help='')

    payment_tenth_notifications_mode = fields.Selection(_NOTIFICATIONS, string='Pay tenth notifications mode')
    payment_tenth_administrator = fields.Many2one(
        'hr.employee',
        'Pay tenth administrator',
        help='')
    payment_tenth_second_administrator = fields.Many2one(
        'hr.employee',
        'Pay tenth second administrator',
        help='')

    percentage_for_personal_expenses = fields.Float(string="Discount percentage for personal expenses",
                                                    digits='Payroll')

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

        res.update(retired_employee_thirteenth_salary_notifications_mode=config_parameter.get_param(
            'retired.employee.thirteenth.salary.notifications.mode', default=''))
        if has_value('retired.employee.thirteenth.salary.administrator'):
            res.update(retired_employee_thirteenth_salary_administrator=int(
                config_parameter.get_param('retired.employee.thirteenth.salary.administrator')))
        if has_value('retired.employee.thirteenth.salary.second.administrator'):
            res.update(retired_employee_thirteenth_salary_second_administrator=int(
                config_parameter.get_param('retired.employee.thirteenth.salary.second.administrator')))

        res.update(retired_employee_fourteenth_salary_notifications_mode=config_parameter.get_param(
            'retired.employee.fourteenth.salary.notifications.mode', default=''))
        if has_value('retired.employee.fourteenth.salary.administrator'):
            res.update(retired_employee_fourteenth_salary_administrator=int(
                config_parameter.get_param('retired.employee.fourteenth.salary.administrator')))
        if has_value('retired.employee.fourteenth.salary.second.administrator'):
            res.update(retired_employee_fourteenth_salary_second_administrator=int(
                config_parameter.get_param('retired.employee.fourteenth.salary.second.administrator')))

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
        if config_parameter.get_param('include.external.services.in.csv.file'):
            if config_parameter.get_param('include.external.services.in.csv.file') != '':
                res.update(include_external_services_in_csv_file=
                           bool(int(config_parameter.get_param('include.external.services.in.csv.file', default=1))))

        res.update(pay_living_wage_notifications_mode=config_parameter.get_param(
            'pay.living.wage.notifications.mode', default=''))
        if has_value('pay.living.wage.administrator'):
            res.update(pay_living_wage_administrator=int(
                config_parameter.get_param('pay.living.wage.administrator')))
        if has_value('pay.living.wage.second.administrator'):
            res.update(pay_living_wage_second_administrator=int(
                config_parameter.get_param('pay.living.wage.second.administrator')))

        res.update(payment_tenth_notifications_mode=config_parameter.get_param(
            'payment.tenth.notifications.mode', default=''))
        if has_value('payment.tenth.administrator'):
            res.update(payment_tenth_administrator=int(
                config_parameter.get_param('payment.tenth.administrator')))
        if has_value('payment.tenth.second.administrator'):
            res.update(payment_tenth_second_administrator=int(
                config_parameter.get_param('payment.tenth.second.administrator')))

        if has_value('percentage.for.personal.expenses'):
            res.update(percentage_for_personal_expenses=float(
                config_parameter.get_param('percentage.for.personal.expenses')))

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

        set_param("retired.employee.thirteenth.salary.notifications.mode",
                  self.retired_employee_thirteenth_salary_notifications_mode)
        set_param("retired.employee.thirteenth.salary.administrator",
                  self.retired_employee_thirteenth_salary_administrator.id)
        set_param("retired.employee.thirteenth.salary.second.administrator",
                  self.retired_employee_thirteenth_salary_second_administrator.id)

        set_param("retired.employee.fourteenth.salary.notifications.mode",
                  self.retired_employee_fourteenth_salary_notifications_mode)
        set_param("retired.employee.fourteenth.salary.administrator",
                  self.retired_employee_fourteenth_salary_administrator.id)
        set_param("retired.employee.fourteenth.salary.second.administrator",
                  self.retired_employee_fourteenth_salary_second_administrator.id)

        set_param("payment.utility.notifications.mode",
                  self.payment_utility_notifications_mode)
        set_param("payment.utility.administrator",
                  self.payment_utility_administrator.id)
        set_param("payment.utility.second.administrator",
                  self.payment_utility_second_administrator.id)
        set_param("profit.calculation.based.on",
                  self.profit_calculation_based_on)
        set_param("include.external.services.in.csv.file", int(self.include_external_services_in_csv_file))

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

        set_param("percentage.for.personal.expenses",
                  self.percentage_for_personal_expenses)

        return res