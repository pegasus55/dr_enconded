# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    PAYMENT_METHOD = [
        ('CTA', _('Wire transfer')),
        ('CHQ', _('Check')),
        ('EFE', _('Cash')),
        ('undefined', _('Undefined')),
    ]
    payment_method = fields.Selection(selection=PAYMENT_METHOD, required=True,
                                      string=_('Payment method'), help=_('Method to receive payments.'))