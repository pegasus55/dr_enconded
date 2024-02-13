# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrPosition(models.Model):
    _name = "hr.position"
    _inherit = ['mail.thread']
    _description = 'Position'

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 tracking=True, default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    function_ids = fields.Many2many('hr.position.function', string="Functions")

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

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        return super(HrPosition, self).create(vals_list)

    def write(self, vals):
        self.validate_module()
        return super(HrPosition, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(HrPosition, self).unlink()