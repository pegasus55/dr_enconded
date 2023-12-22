# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = 'hr.department'

    address_id = fields.Many2one('res.partner', string='Address',
                                 domain="[('type', '=', 'hr_department_address')]", tracking=True)

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
        return super(Department, self).create(vals)

    def write(self, vals):
        self.validate_module()
        return super(Department, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(Department, self).unlink()


class DepartmentSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_dr_department_additional_manager = fields.Boolean(string="Additional managers")
