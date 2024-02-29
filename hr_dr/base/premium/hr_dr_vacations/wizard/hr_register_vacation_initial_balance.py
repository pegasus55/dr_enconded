# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class RegisterVacationInitialBalance(models.TransientModel):
    _name = 'hr.register.vacation.initial.balance'
    _description = 'Register vacation initial balance'

    # @api.onchange('vacations_cutoff_date', 'hours_per_day')
    # def onchange_vacations_cutoff_date_hours_per_day(self):
    #     if self.vacations_cutoff_date and self.hours_per_day:
    #         self.vacations_cutoff_date_days = int(self.vacations_cutoff_date)
    #
    #         hours = self.vacations_cutoff_date - int(self.vacations_cutoff_date)
    #         hours = hours * self.hours_per_day
    #         self.vacations_cutoff_date_hours = int(hours)
    #
    #         minutes = hours - int(hours)
    #         self.vacations_cutoff_date_minutes = int(minutes * 60)

    @api.onchange('vacations_cutoff_date_days',
                  'vacations_cutoff_date_hours',
                  'vacations_cutoff_date_minutes',
                  'hours_per_day')
    def onchange_vacations_cutoff_dhm_date_hours_per_day(self):
        if self.hours_per_day and \
                (self.vacations_cutoff_date_days or
                 self.vacations_cutoff_date_hours or self.vacations_cutoff_date_minutes):
            precision = self.env['decimal.precision'].sudo().precision_get('Vacations')
            self.vacations_cutoff_date = round(self.vacations_cutoff_date_days +
                                               self.vacations_cutoff_date_hours / self.hours_per_day +
                                               self.vacations_cutoff_date_minutes / (self.hours_per_day * 60),
                                               precision)

    employee_id = fields.Many2one('hr.employee', string="Collaborator", default=lambda self: self._context.get('active_id'),
                                  required=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working hours', readonly=True,
                                           related='employee_id.resource_calendar_id')
    hours_per_day = fields.Float(string='Average working hours per day', readonly=True,
                                 related='employee_id.resource_calendar_id.hours_per_day')
    cutoff_date = fields.Date('Cutoff date', required=True)
    vacations_cutoff_date = fields.Float(string='Vacations available at the cutoff date', required=True,
                                         digits='Vacations')
    detailed_income = fields.Boolean(string='Detailed income', default=False)
    vacations_cutoff_date_days = fields.Integer(string='Vacations available at the cutoff date (Days)')
    vacations_cutoff_date_hours = fields.Integer(string='Vacations available at the cutoff date (Hours)')
    vacations_cutoff_date_minutes = fields.Integer(string='Vacations available at the cutoff date (Minutes)')
    register_provisioned_vacations = fields.Boolean(string='Register provisioned vacations', default=False)
    provisioned_value = fields.Float(string='Provisioned value', digits='Vacations')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related='company_id.currency_id')
    
    def action_accept(self):
        # TODO Realizar asiento contable de provision de vacaciones
        self.employee_id.cutoff_date = self.cutoff_date
        self.employee_id.vacations_cutoff_date = self.vacations_cutoff_date
        self.employee_id.register_vacation_initial_balance()