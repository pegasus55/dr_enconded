# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Department(models.Model):
    _inherit = 'hr.department'

    additional_manager_ids = fields.One2many('hr.employee', 'additional_manager_in', string='Additional managers')


class Employee(models.Model):
    _inherit = 'hr.employee'

    additional_manager_in = fields.Many2one('hr.department', string="Additional manager in")