# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PersonalAction(models.Model):
    _name = "hr.personal.action"
    _description = 'Personal action'
    _order = ""

    number = fields.Char(string='Number', required=True)
    date = fields.Date(string='Date', required=True)
    type = fields.Selection([
        ('decree', 'Decree'),
        ('agreement', 'Agreement'),
        ('resolution', 'Resolution')], string='Type', required=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True)
    identification_id = fields.Char(string='Identification', related='employee_id.identification_id', store=True)
    IESS_affiliation_number = fields.Char(string='IESS affiliation number', required=True)
    apply_since = fields.Date(string='Apply since', required=True)

    movement_id = fields.Many2one('hr.personal.action.movement', string="Movement", required=True)
    sub_movement_id = fields.Many2one('hr.personal.action.movement', string="Sub movement", required=True)

    budget_item = fields.Char(string='Budget item', required=True)

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    @api.model
    def create(self, vals):
        self.validate_module()
        return super(PersonalAction, self).create(vals)

    def write(self, vals):
        self.validate_module()
        return super(PersonalAction, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(PersonalAction, self).unlink()


class PersonalActionMovement(models.Model):
    _name = "hr.personal.action.movement"
    _description = 'Personal Action Movement'

    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('hr.personal.action.movement', string='Parent', tracking=True, ondelete='cascade')





