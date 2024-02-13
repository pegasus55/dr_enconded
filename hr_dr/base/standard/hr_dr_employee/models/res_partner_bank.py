# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    partner_id = fields.Many2one('res.partner', string='Account holder', ondelete='cascade', index=True,
                                 domain=[('vat', '!=', ''), '|', ('is_company', '=', True), ('parent_id', '=', False)],
                                 required=True)