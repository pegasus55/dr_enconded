# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class hr_dr_credit_accounting_community(models.Model):
#     _name = 'hr_dr_credit_accounting_community.hr_dr_credit_accounting_community'
#     _description = 'hr_dr_credit_accounting_community.hr_dr_credit_accounting_community'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
