# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CloneSalaryRule(models.TransientModel):
    _name = 'clone.salary.rule'
    _description = 'Clone salary rule'
    _inherit = ['dr.base']

    def action_clone_salary_rule(self):
        pass