# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    number = fields.Char(string="Number")
    interception_type = fields.Selection([
        ('na', _('N/A')),
        ('and', _('And')),
        ('between', _('Between')),
    ], string="Interception type", help="", default="na")
    third_street = fields.Char(string="Third street")
    condominium = fields.Char(string="Condominium")
    building_tower = fields.Char(string="Building / Tower")
    apartment_number = fields.Char(string="Apartment number")
    city_id = fields.Many2one('res.city', string="City", domain="[('state_id', '=?', state_id)]")
    parish_id = fields.Many2one('res.parish', string="Parish", domain="[('city_id', '=?', city_id)]")
    zone_id = fields.Many2one('res.zone', string="Zone")
    reference = fields.Text(string="Reference")
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        super(ResPartner, self)._onchange_country_id()
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False
            self.city_id = False
            self.parish_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        super(ResPartner, self)._onchange_state()
        if self.state_id and self.state_id != self.city_id.state_id:
            self.city_id = False
            self.parish_id = False

    @api.onchange('city_id')
    def _onchange_city_id(self):
        # Establecer los padres
        if self.city_id.state_id:
            self.state_id = self.city_id.state_id

            if self.city_id.state_id.country_id:
                self.country_id = self.city_id.state_id.country_id
                
        if self.city_id and self.city_id != self.parish_id.city_id:
            self.parish_id = False
    
    @api.onchange('parish_id')
    def _onchange_parish_id(self):
        # Establecer los padres
        if self.parish_id.city_id:
            self.city_id = self.parish_id.city_id
            
            if self.parish_id.city_id.state_id:
                self.state_id = self.parish_id.city_id.state_id
    
                if self.parish_id.city_id.state_id.country_id:
                    self.country_id = self.parish_id.city_id.state_id.country_id