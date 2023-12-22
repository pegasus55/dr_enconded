# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    active = fields.Boolean(string='Active', default=True)
    region = fields.Selection([
        ('sierra', _('Sierra')),
        ('coast', _('Coast')),
        ('eastern', _('Eastern')),
        ('island', _('Island'))
    ], string='Region')
    city_ids = fields.One2many('res.city', 'state_id', string="Cities")