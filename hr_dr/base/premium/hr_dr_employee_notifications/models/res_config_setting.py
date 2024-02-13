from odoo import api, fields, models, _


class EmployeeSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    apply_in_personal_income = fields.Boolean(string='Apply in personal income')
    apply_in_personal_exit = fields.Boolean(string='Apply in personal exit')
    apply_in_birthday = fields.Boolean(string='Apply in birthday')
    apply_in_anniversary = fields.Boolean(string='Apply in anniversary')
    apply_in_profession_celebration_date = fields.Boolean(string='Apply in profession celebration date')
    notify_administrators = fields.Boolean(string='Notify administrators')
    administrators_ids = fields.Many2many(
        'hr.employee',
        'rcs_he_employee_notifications_rel',
        'res_config_settings_id',
        'employee_id',
        string=_('Administrators'), required=True)
    # Cantidad de días de anticipación para el envío de notificaciones.
    anticipation_days = fields.Integer(string='Anticipation days',
                                       help='Number of days in advance for sending notifications.', default=5)
    email_for_mass_notifications = fields.Char(string='Email for mass notifications')

    @api.model
    def get_values(self):
        res = super(EmployeeSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        if config_parameter.get_param('en.apply.in.personal.income'):
            if config_parameter.get_param('en.apply.in.personal.income') != '':
                res.update(apply_in_personal_income=bool(int(config_parameter.get_param('en.apply.in.personal.income',
                                                                                        default=1))))

        if config_parameter.get_param('en.apply.in.personal.exit'):
            if config_parameter.get_param('en.apply.in.personal.exit') != '':
                res.update(apply_in_personal_exit=bool(int(config_parameter.get_param('en.apply.in.personal.exit',
                                                                                      default=1))))

        if config_parameter.get_param('en.apply.in.birthday'):
            if config_parameter.get_param('en.apply.in.birthday') != '':
                res.update(apply_in_birthday=bool(int(config_parameter.get_param('en.apply.in.birthday', default=1))))

        if config_parameter.get_param('en.apply.in.anniversary'):
            if config_parameter.get_param('en.apply.in.anniversary') != '':
                res.update(apply_in_anniversary=bool(int(config_parameter.get_param('en.apply.in.anniversary',
                                                                                    default=1))))

        if config_parameter.get_param('en.apply.in.profession.celebration.date'):
            if config_parameter.get_param('en.apply.in.profession.celebration.date') != '':
                res.update(apply_in_profession_celebration_date=bool(int(config_parameter.get_param(
                    'en.apply.in.profession.celebration.date', default=1))))

        if config_parameter.get_param('en.notify.administrators'):
            if config_parameter.get_param('en.notify.administrators') != '':
                res.update(notify_administrators=bool(int(config_parameter.get_param('en.notify.administrators',
                                                                                     default=1))))

        if config_parameter.get_param('en.administrators.ids'):
            if config_parameter.get_param('en.administrators.ids') != '':
                res.update(administrators_ids=self.env['hr.employee'].sudo().browse(
                    [int(id) for id in config_parameter.get_param('en.administrators.ids').split(',')]).exists())

        if config_parameter.get_param('en.anticipation.days'):
            if config_parameter.get_param('en.anticipation.days') != '':
                res.update(anticipation_days=int(config_parameter.get_param('en.anticipation.days', default=5)))

        if config_parameter.get_param('en.email.for.mass.notifications'):
            if config_parameter.get_param('en.email.for.mass.notifications') != '':
                res.update(email_for_mass_notifications=config_parameter.get_param('en.email.for.mass.notifications',
                                                                                   default=''))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param("en.apply.in.personal.income", int(self.apply_in_personal_income))
        set_param("en.apply.in.personal.exit", int(self.apply_in_personal_exit))
        set_param("en.apply.in.birthday", int(self.apply_in_birthday))
        set_param("en.apply.in.anniversary", int(self.apply_in_anniversary))
        set_param("en.apply.in.profession.celebration.date", int(self.apply_in_profession_celebration_date))
        set_param("en.notify.administrators", int(self.notify_administrators))
        set_param('en.administrators.ids', ",".join([str(id) for id in self.administrators_ids.ids]))
        set_param("en.anticipation.days", self.anticipation_days)
        set_param("en.email.for.mass.notifications", self.email_for_mass_notifications)
        super(EmployeeSettings, self).set_values()