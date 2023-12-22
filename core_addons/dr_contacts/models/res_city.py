# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCity(models.Model):
    _name = 'res.city'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Res City'

    def unlink(self):
        # Controla que no se pueda eliminar una ciudad asociada a un cliente o a una parroquia
        partner_ids = self.env['res.partner'].search([('city_id', '=', self.id)])
        parish_ids = self.env['res.parish'].search([('city_id', '=', self.id)])
        if partner_ids or parish_ids:
            raise ValidationError(_('You cannot delete this city. There are clients or parishes associated with it.'))
        return super(ResCity, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_('You cannot duplicate a city.'))
        return super(ResCity, self).copy(default)

    code = fields.Char(string='City code', size=3,
                       help='The city code. Maximum three characters.', tracking=True)
    name = fields.Char(string='City name', size=60,
                       help='Administrative divisions of the state.', tracking=True)
    state_id = fields.Many2one('res.country.state', string='State',
                               help='Select the state associated to the city.', tracking=True)
    country_id = fields.Many2one('res.country', string='Country', related='state_id.country_id', store=True)
    active = fields.Boolean(string='Active', default=True,
                            help='If the active field is set to False, it will allow you to hide the cities '
                                 'without removing it.', tracking=True)
    parish_ids = fields.One2many('res.parish', 'city_id', string="Parish")