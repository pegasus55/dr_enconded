# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.addons.dr_license_customer.models.models import License


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def validate_employee_amount(self, create=False):
        lic = License(self.env['ir.config_parameter'].sudo().get_param)
        max_employees = lic.get_max_employees()
        active_employees = len(self.sudo().search([]))
        if create:
            if active_employees >= max_employees:
                raise ValidationError(_('You have {} active employees of {} allowed by your license. '
                                        'You cannot create more employees.').format(active_employees, max_employees))
        else:
            if active_employees > max_employees:
                raise ValidationError(_('You have {} active employees of {} allowed by your license.')
                                      .format(active_employees, max_employees))

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_employee_amount(True)
        res = super(HrEmployee, self).create(vals_list)
        return res

    def write(self, vals):
        self.validate_employee_amount()
        res = super(HrEmployee, self).write(vals)
        return res


class Module(models.Model):
    _inherit = "ir.module.module"

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    def button_install(self):
        self.validate_module()
        return super(Module, self).button_install()

    def button_immediate_install(self):
        self.validate_module()
        return super(Module, self).button_immediate_install()


class BaseLicense(models.AbstractModel):
    _name = 'dr.license.base'
    _description = 'License base model'

    def validate_license(self):
        self.validate_module()
        lic = License(self.env['ir.config_parameter'].sudo().get_param)
        self.validate_employee_amount(license=lic)
        valid_lic, lic_error = lic.validate_license(self.env.cr.dbname)
        if not valid_lic:
            raise ValidationError(lic_error)

    def validate_employee_amount(self, create=False, license=False):
        lic = License(self.env['ir.config_parameter'].sudo().get_param) if not license else license
        max_employees = lic.get_max_employees()
        active_employees = len(self.env['hr.employee'].sudo().search([]))
        if create:
            if active_employees >= max_employees:
                raise ValidationError(_('You have {} active employees of {} allowed by your license. '
                                        'You cannot create more employees.').format(active_employees, max_employees))
        else:
            if active_employees > max_employees:
                raise ValidationError(_('You have {} active employees of {} allowed by your license.')
                                      .format(active_employees, max_employees))

    def validate_module(self):
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))