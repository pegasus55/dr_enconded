import json
import datetime as dt
from odoo import fields, models, api, _


class Device(models.AbstractModel):
    _name = 'dr.license.customer.device'
    _description = 'License customer device'

    brand = fields.Char('Mark')
    model = fields.Char('Model')
    sn = fields.Char('SN')


class LicenseSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    license_expiring_date = fields.Datetime(string='Expiring date', help='License expiration date')
    max_active_employees = fields.Integer(string="Active collaborators")
    license_package = fields.Char(string='Version')
    licensed_devices = fields.Char('Devices')
    licensed_apps = fields.Char('Apps')

    @api.model
    def get_values(self):
        res = super(LicenseSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        if ICPSudo.get_param('license.expiring.date'):
            if ICPSudo.get_param('license.expiring.date') != '':
                res.update(license_expiring_date=dt.datetime.strptime(
                    ICPSudo.get_param('license.expiring.date', default='1970-01-01')[:10], '%Y-%m-%d'))

        res.update(
            max_active_employees=int(ICPSudo.get_param(
                'license.max.active.employees', default=0)))

        res.update(license_package=ICPSudo.get_param(
            'license.nukleo.version', default=''))

        res.update(licensed_devices=ICPSudo.get_param('license.devices', default='[]'))
        res.update(licensed_apps=ICPSudo.get_param('license.apps', default='[]'))

        return res

    @api.model
    def get_devices(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        devices_str = ICPSudo.get_param('license.devices', False)
        if devices_str and devices_str != '':
            return json.loads(devices_str)
        return []
