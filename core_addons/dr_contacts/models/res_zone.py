# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResZone(models.Model):
    _name = 'res.zone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Res Zone'

    def unlink(self):
        # Controla que no se pueda eliminar una zona asociada a un cliente
        partner_ids = self.env['res.partner'].search([('zone_id', '=', self.id)])
        if partner_ids:
            raise ValidationError(_('You cannot delete this zone. There are clients associated with it.'))
        return super(ResZone, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_('You cannot duplicate a zone.'))
        return super(ResZone, self).copy()

    code = fields.Char(string='Zone code', size=3, tracking=True)
    name = fields.Char(string='Zone name', size=60, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)