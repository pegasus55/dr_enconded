from odoo import api, fields, models, _


class PermissionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _NOTIFICATIONS = [
        ('Without_notifications', 'Without notifications'),

        ('Administrator', 'Administrator'),

        ('One_level_bd', 'One level based on department'),
        ('One_level_br', 'One level based on responsible'),
        ('One_level_bc', 'One level based on coach'),

        ('One_level_bd_and_administrator', 'One level based on department and administrator'),
        ('One_level_br_and_administrator', 'One level based on responsible and administrator'),
        ('One_level_bc_and_administrator', 'One level based on coach and administrator'),

        ('One_level_bd_and_two_administrator', 'One level based on department and two administrator'),

        ('Two_levels_bd', 'Two levels based on department'),
        ('Two_levels_bd_and_administrator', 'Two levels based on department and administrator'),

        ('All_levels_bd', 'All levels based on department'),
        ('All_levels_bd_and_administrator', 'All levels based on department and administrator'),

        ('Personalized', 'Personalized')
    ]
    permission_notifications = fields.Selection(_NOTIFICATIONS, string='Notifications mode', required=True, help='')
    
    permission_administrator_id = fields.Many2one(
        'hr.employee',
        'Administrator',
        help='')

    permission_second_administrator = fields.Many2one(
        'hr.employee',
        'Second administrator',
        help='')

    @api.model
    def get_values(self):
        res = super(PermissionSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(permission_notifications=config_parameter.get_param('permission.notifications.mode', default=''))

        if config_parameter.get_param('permission.notifications.administrator'):
            if config_parameter.get_param('permission.notifications.administrator') != '':
                res.update(permission_administrator_id=int(
                    config_parameter.get_param('permission.notifications.administrator')))

        if config_parameter.get_param('permission.notifications.second.administrator'):
            if config_parameter.get_param('permission.notifications.second.administrator') != '':
                res.update(permission_second_administrator=int(
                    config_parameter.get_param('permission.notifications.second.administrator')))

        return res
    
    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("permission.notifications.mode", self.permission_notifications)
        set_param("permission.notifications.administrator", self.permission_administrator_id.id)
        set_param("permission.notifications.second.administrator", self.permission_second_administrator.id)

        super(PermissionSettings, self).set_values()

    @api.onchange('permission_notifications')
    def _onchange_permission_notifications(self):
        if self.permission_notifications == "Without_notifications" \
                or self.permission_notifications == "One_level_bd" \
                or self.permission_notifications == "One_level_br"\
                or self.permission_notifications == "One_level_bc" \
                or self.permission_notifications == "Two_levels_bd"\
                or self.permission_notifications == "All_levels_bd" \
                or self.permission_notifications == "Personalized":
            self.permission_administrator_id = ""
        if self.permission_notifications != "One_level_bd_and_two_administrator":
            self.permission_second_administrator = ""