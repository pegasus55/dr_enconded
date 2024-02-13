# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ScheduleLegalObligations(models.Model):
    _name = 'schedule.legal.obligations'
    _description = 'Schedule of legal obligations'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, tracking=True)
    normative_id = fields.Many2one('hr.normative', string='Regulation', required=True, tracking=True)
    start_date_calculation_period = fields.Date(string='Start date of the calculation period', required=True,
                                                tracking=True)
    end_date_calculation_period = fields.Date(string='End date of the calculation period', required=True, tracking=True)
    max_payment_date = fields.Date(string='Maximum payment date', required=True, tracking=True)
    detail_ids = fields.One2many('schedule.legal.obligations.detail', 'schedule_legal_obligations_id', string="Details")


class ScheduleLegalObligationsDetail(models.Model):
    _name = 'schedule.legal.obligations.detail'
    _description = 'Schedule of legal obligations detail'
    _inherit = ['mail.thread']

    schedule_legal_obligations_id = fields.Many2one('schedule.legal.obligations', string='Schedule legal obligations',
                                                    required=True, tracking=True)
    ninth_digit_RUC = fields.Char(string='Ninth digit of the RUC', required=True, tracking=True)
    registration_period_start_date = fields.Date(string='Registration period start date', required=True, tracking=True)
    registration_period_end_date = fields.Date(string='Registration period end date', required=True, tracking=True)