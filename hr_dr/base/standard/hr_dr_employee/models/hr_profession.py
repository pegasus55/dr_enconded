# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrProfession(models.Model):
    _name = "hr.profession"
    _description = 'Profession'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)