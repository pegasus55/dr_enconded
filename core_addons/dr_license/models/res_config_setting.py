from odoo import api, fields, models, _

class LicenseSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    license_anticipation_days = fields.Integer(string='Anticipation days', help='Number of days in advance to send the license expiration notification.', default=30) # Número de días de antelación para enviar la notificación de expiración de licencia.
    license_emails_for_notification = fields.Text(string='Comma separated mailing list') # Lista de correos separados por comas

    @api.model
    def get_values(self):
        res = super(LicenseSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        if ICPSudo.get_param('license.anticipation.days'):
            if ICPSudo.get_param('license.anticipation.days') != '':
                res.update(license_anticipation_days=int(ICPSudo.get_param('license.anticipation.days', default=30)))

        if ICPSudo.get_param('license.email.for.notification'):
            if ICPSudo.get_param('license.email.for.notification') != '':
                res.update(license_emails_for_notification=ICPSudo.get_param('license.email.for.notification', default=''))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("license.anticipation.days", self.license_anticipation_days)
        set_param("license.email.for.notification", self.license_emails_for_notification)
        super(LicenseSettings, self).set_values()
