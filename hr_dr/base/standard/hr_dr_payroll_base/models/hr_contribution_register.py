# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrContributionRegister(models.Model):
    _name = 'hr.contribution.register'
    _description = 'Contribution register'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True)
    note = fields.Text(string='Description')
    active = fields.Boolean(default=True, string="Active")