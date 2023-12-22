# -*- coding: utf-8 -*-

from odoo import models


class Employee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'dr_signature.base']
    _description = 'Employee extension table'
