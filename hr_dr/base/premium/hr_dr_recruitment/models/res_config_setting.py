from odoo import api, fields, models, _


class RecruitmentSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _NOTIFICATIONS = [
        ('Without_notifications', _('Without notifications')),

        ('Administrator', _('Administrator')),

        ('One_level_bd', _('One level based on department')),
        ('One_level_br', _('One level based on responsible')),
        ('One_level_bc', _('One level based on coach')),

        ('One_level_bd_and_administrator', _('One level based on department and administrator')),
        ('One_level_br_and_administrator', _('One level based on responsible and administrator')),
        ('One_level_bc_and_administrator', _('One level based on coach and administrator')),

        ('One_level_bd_and_two_administrator', _('One level based on department and two administrator')),

        ('Two_levels_bd', _('Two levels based on department')),
        ('Two_levels_bd_and_administrator', _('Two levels based on department and administrator')),

        ('All_levels_bd', _('All levels based on department')),
        ('All_levels_bd_and_administrator', _('All levels based on department and administrator')),

        ('Personalized', _('Personalized'))
    ]
    staff_requirement_request_notifications = fields.Selection(_NOTIFICATIONS, required=True,
                                                               string='Staff requirement request notifications mode',
                                                               help='')
    staff_requirement_request_administrator_id = fields.Many2one(
        'hr.employee',
        string='Staff requirement request administrator',
        help='')
    staff_requirement_request_second_administrator_id = fields.Many2one(
        'hr.employee',
        string='Staff requirement request second administrator',
        help='')
    start_schedule_approval_day_of_staff_requirement_request = fields.Boolean(string='Start schedule approval day '
                                                                                     'of staff requirement request')
    include_holidays_in_working_days_of_scheme_schedule = fields.Boolean(string='Include holidays in working days '
                                                                                'of scheme schedule')
    validate_anticipation_dynamically = fields.Boolean(string='Validate anticipation dynamically')
    _MODE = [
        ('by_position', _('By position')),
        ('by_job', _('By job')),
    ]
    mode = fields.Selection(_MODE, string='Validation mode', help='', required=True)

    @api.model
    def get_values(self):
        res = super(RecruitmentSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(staff_requirement_request_notifications=config_parameter.get_param(
            'staff.requirement.request.notifications.mode', default=''))

        if config_parameter.get_param('staff.requirement.request.notifications.administrator'):
            if config_parameter.get_param('staff.requirement.request.notifications.administrator') != '':
                res.update(staff_requirement_request_administrator_id=int(config_parameter.get_param(
                    'staff.requirement.request.notifications.administrator')))

        if config_parameter.get_param('staff.requirement.request.notifications.second.administrator'):
            if config_parameter.get_param('staff.requirement.request.notifications.second.administrator') != '':
                res.update(staff_requirement_request_second_administrator_id=int(config_parameter.get_param(
                    'staff.requirement.request.notifications.second.administrator')))

        include_holidays = False
        if config_parameter.get_param('include.holidays.in.working.days.of.scheme.schedule'):
            if config_parameter.get_param('include.holidays.in.working.days.of.scheme.schedule') == 'True':
                include_holidays = True
            else:
                include_holidays = False
        res.update(include_holidays_in_working_days_of_scheme_schedule=include_holidays)

        start_schedule = False
        if config_parameter.get_param('start.schedule.approval.day.of.staff.requirement.request'):
            if config_parameter.get_param('start.schedule.approval.day.of.staff.requirement.request') == 'True':
                start_schedule = True
            else:
                start_schedule = False
        res.update(start_schedule_approval_day_of_staff_requirement_request=start_schedule)

        validate_anticipation = False
        if config_parameter.get_param('validate.anticipation.dynamically.in.staff.requirement.request'):
            if config_parameter.get_param('validate.anticipation.dynamically.in.staff.requirement.request') == 'True':
                validate_anticipation = True
            else:
                validate_anticipation = False
        res.update(validate_anticipation_dynamically=validate_anticipation)

        res.update(mode=config_parameter.get_param(
            'validate.anticipation.dynamically.in.staff.requirement.request.mode', default=''))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        
        set_param("staff.requirement.request.notifications.mode", self.staff_requirement_request_notifications)
        set_param("staff.requirement.request.notifications.administrator",
                  self.staff_requirement_request_administrator_id.id)
        set_param("staff.requirement.request.notifications.second.administrator",
                  self.staff_requirement_request_second_administrator_id.id)
        set_param("start.schedule.approval.day.of.staff.requirement.request",
                  self.start_schedule_approval_day_of_staff_requirement_request)
        set_param("include.holidays.in.working.days.of.scheme.schedule",
                  self.include_holidays_in_working_days_of_scheme_schedule)
        set_param("validate.anticipation.dynamically.in.staff.requirement.request",
                  self.validate_anticipation_dynamically)
        set_param("validate.anticipation.dynamically.in.staff.requirement.request.mode",
                  self.mode)

        super(RecruitmentSettings, self).set_values()

    @api.onchange('staff_requirement_request_notifications')
    def _onchange_staff_requirement_request_notifications(self):
        if self.staff_requirement_request_notifications == "Without_notifications" \
                or self.staff_requirement_request_notifications == "One_level_bd" \
                or self.staff_requirement_request_notifications == "One_level_br"\
                or self.staff_requirement_request_notifications == "One_level_bc" \
                or self.staff_requirement_request_notifications == "Two_levels_bd"\
                or self.staff_requirement_request_notifications == "All_levels_bd" \
                or self.staff_requirement_request_notifications == "Personalized":
            self.staff_requirement_request_administrator_id = ""
        if self.staff_requirement_request_notifications != "One_level_bd_and_two_administrator":
            self.staff_requirement_request_second_administrator_id = ""