# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api, _
from ..models.models import License

class LicenseWizard(models.TransientModel):
    _name = 'dr.license.customer.wizard'
    _description = 'License Request Wizard'

    id_number = fields.Char('Id. number', required=True,
                            help="Insert your identification number to fetch your license from our servers.")

    def get_license(self):
        lic = License(self.env['ir.config_parameter'].sudo().get_param)
        lic.request_license(self.id_number)

        lic.update_res_config_params(self.env['ir.config_parameter'].sudo().set_param)

        # # Actualizo el parámetro del sistema con la nueva fecha. (Solo para mostrar el valor en la configuración.)
        # self.env['ir.config_parameter'].sudo().set_param("license.expiring.date", lic.get_expiration_date(as_str=True))
        # self.env['ir.config_parameter'].sudo().set_param("license.max.active.employees", lic.get_max_employees())
        # self.env['ir.config_parameter'].sudo().set_param("license.nukleo.version", lic.get_nukleo_version())
        # self.env['ir.config_parameter'].sudo().set_param("license.devices", json.dumps(lic.get_devices()))
        # self.env['ir.config_parameter'].sudo().set_param("license.apps", json.dumps(lic.get_apps_tradename()))
