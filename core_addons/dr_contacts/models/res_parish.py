# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResParish(models.Model):
    _name = 'res.parish'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Res Parish'

    def unlink(self):
        # Controla que no se pueda eliminar una parroquia asociada a un cliente
        partner_ids = self.env['res.partner'].search([('parish_id', '=', self.id)])
        if partner_ids:
            raise ValidationError(_('You cannot delete this parish. There are clients associated with it.'))
        return super(ResParish, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_('You cannot duplicate a parish.'))
        return super(ResParish, self).copy()

    code = fields.Char(string='Parish code', size=3,
                       help='The parish code. Maximum three characters.', tracking=True)
    name = fields.Char(string='Parish name', size=60,
                       help='Administrative divisions of the city.', tracking=True)
    city_id = fields.Many2one('res.city', string='City',
                              help='Select the city associated to the parish.', tracking=True)
    state_id = fields.Many2one('res.country.state', string='State', related='city_id.state_id', store=True)
    country_id = fields.Many2one('res.country', string='Country', related='city_id.country_id', store=True)
    active = fields.Boolean(string='Active', default=True, tracking=True,
                            help='If the active field is set to False, it will allow you to hide the parish '
                                 'without removing it.')