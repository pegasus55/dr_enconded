from odoo import api, fields, models, _


class VacationsSettings(models.TransientModel):
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
    planning_notifications = fields.Selection(_NOTIFICATIONS, string='Planning notifications mode',
                                              required=True, help='')
    planning_administrator_id = fields.Many2one(
        'hr.employee',
        'Planning administrator',
        help='')
    planning_second_administrator = fields.Many2one(
        'hr.employee',
        'Second planning administrator',
        help='')

    execution_notifications = fields.Selection(_NOTIFICATIONS, string='Execution notifications mode',
                                               required=True, help='')
    execution_administrator_id = fields.Many2one(
        'hr.employee',
        'Execution administrator',
        help='')
    execution_second_administrator = fields.Many2one(
        'hr.employee',
        'Second execution administrator',
        help='')

    vacation_lost_automatic_discount = fields.Boolean('Vacation lost automatic discount', default=False)

    _SM = [
        ('without_signature', 'Without signature'),
        ('uploaded_image', 'Uploaded image'),
        ('electronic_signature', 'Electronic signature'),
    ]
    vacations_signature_mode = fields.Selection(_SM, string='Signature mode for vacations', required=True)

    @api.model
    def get_values(self):
        res = super(VacationsSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(planning_notifications=config_parameter.get_param('planning.vacations.notifications.mode',
                                                                     default=''))

        if config_parameter.get_param('planning.vacations.notifications.administrator'):
            if config_parameter.get_param('planning.vacations.notifications.administrator') != '':
                res.update(planning_administrator_id=int(
                    config_parameter.get_param('planning.vacations.notifications.administrator')))

        if config_parameter.get_param('planning.vacations.notifications.second.administrator'):
            if config_parameter.get_param('planning.vacations.notifications.second.administrator') != '':
                res.update(planning_second_administrator=int(
                    config_parameter.get_param('planning.vacations.notifications.second.administrator')))

        res.update(execution_notifications=config_parameter.get_param('execution.vacations.notifications.mode',
                                                                      default=''))

        if config_parameter.get_param('execution.vacations.notifications.administrator'):
            if config_parameter.get_param('execution.vacations.notifications.administrator') != '':
                res.update(execution_administrator_id=int(
                    config_parameter.get_param('execution.vacations.notifications.administrator')))

        if config_parameter.get_param('execution.vacations.notifications.second.administrator'):
            if config_parameter.get_param('execution.vacations.notifications.second.administrator') != '':
                res.update(execution_second_administrator=int(
                    config_parameter.get_param('execution.vacations.notifications.second.administrator')))

        if config_parameter.get_param('vacation.lost.automatic.discount'):
            if config_parameter.get_param('vacation.lost.automatic.discount') != '':
                res.update(vacation_lost_automatic_discount=
                           bool(int(config_parameter.get_param('vacation.lost.automatic.discount', default=1))))

        res.update(vacations_signature_mode=config_parameter.get_param('vacations.signature.mode', default=''))
        return res
    
    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("planning.vacations.notifications.mode", self.planning_notifications)
        set_param("planning.vacations.notifications.administrator", self.planning_administrator_id.id)
        set_param("planning.vacations.notifications.second.administrator", self.planning_second_administrator.id)

        set_param("execution.vacations.notifications.mode", self.execution_notifications)
        set_param("execution.vacations.notifications.administrator", self.execution_administrator_id.id)
        set_param("execution.vacations.notifications.second.administrator", self.execution_second_administrator.id)

        set_param("vacation.lost.automatic.discount", int(self.vacation_lost_automatic_discount))

        set_param("vacations.signature.mode", self.vacations_signature_mode)

        super(VacationsSettings, self).set_values()

    @api.onchange('planning_notifications')
    def _onchange_planning_notifications(self):
        if self.planning_notifications == "Without_notifications" \
                or self.planning_notifications == "One_level_bd" \
                or self.planning_notifications == "One_level_br"\
                or self.planning_notifications == "One_level_bc" \
                or self.planning_notifications == "Two_levels_bd"\
                or self.planning_notifications == "All_levels_bd" \
                or self.planning_notifications == "Personalized":
            self.planning_administrator_id = ""
        if self.planning_notifications != "One_level_bd_and_two_administrator":
            self.planning_second_administrator = ""

    @api.onchange('execution_notifications')
    def _onchange_execution_notifications(self):
        if self.planning_notifications == "Without_notifications" \
                or self.planning_notifications == "One_level_bd" \
                or self.execution_notifications == "One_level_dr"\
                or self.execution_notifications == "One_level_dc" \
                or self.execution_notifications == "Two_levels_bd"\
                or self.execution_notifications == "All_levels_bd" \
                or self.execution_notifications == "Personalized":
            self.execution_administrator_id = ""
        if self.execution_notifications != "One_level_bd_and_two_administrator":
            self.execution_second_administrator = ""