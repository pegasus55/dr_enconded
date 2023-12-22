# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class hr_dr_vacations_ec_public(models.Model):
#     _name = 'hr_dr_vacations_ec_public.hr_dr_vacations_ec_public'
#     _description = 'hr_dr_vacations_ec_public.hr_dr_vacations_ec_public'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
