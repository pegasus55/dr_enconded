# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PermissionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rules_to_analyze = fields.Char(string='Salary rule codes',
                                   help='Add a salary rule code to detail in project timesheets. More than one rule '
                                        'can be set, separated by comma')

    @api.model
    def get_values(self):
        res = super(PermissionSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()
        res.update(rules_to_analyze=config_parameter.get_param('payroll.project.analytics.rules', default=''))
        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('payroll.project.analytics.rules', self.rules_to_analyze)
        super(PermissionSettings, self).set_values()
