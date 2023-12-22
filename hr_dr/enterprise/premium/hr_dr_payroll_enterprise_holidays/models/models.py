# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class hr_dr_payroll_enterprise_holidays(models.Model):
#     _name = 'hr_dr_payroll_enterprise_holidays.hr_dr_payroll_enterprise_holidays'
#     _description = 'hr_dr_payroll_enterprise_holidays.hr_dr_payroll_enterprise_holidays'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
