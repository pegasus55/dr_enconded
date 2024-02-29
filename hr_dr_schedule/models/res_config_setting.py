from odoo import api, fields, models, _


class ScheduleSettings(models.TransientModel):
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
    assistance_mode = fields.Selection(
        string="Algoritmo de asignación de marcaciones",
        required=True,
        selection=[
            ('1', 'Una tecla de función por tipo de evento'),
            ('2', 'Una tecla de función por actividad'),
            ('3', 'Sin tecla de función'),
        ],
        default="1"
    )
    attendance_state_ids = fields.Many2many('attendance.state', 'rcs_attendance_state_rel', 'res_config_settings_id',
                                            'attendance_state_id', string='Estados de asistencia')

    hour_extra_approval_request_notifications_mode = fields.Selection(
        _NOTIFICATIONS, required=True,
        string='Modo de notificaciones para solicitudes de aprobación de horas extras', help='')
    hour_extra_approval_request_administrator = fields.Many2one(
        'hr.employee',
        'Administrador para solicitudes de aprobación de horas extras',
        help='')
    hour_extra_approval_request_second_administrator = fields.Many2one(
        'hr.employee',
        'Segundo administrador para solicitudes de aprobación de horas extras',
        help='')

    max_time_in_past_to_request_for_attendance = fields.Integer(
        string="Tiempo máximo (en horas) para solicitar una marcación", required=True,
        help='Número de horas posteriores a la marcación solicitada donde es permitido realizar la solicitud.')

    user_attendance_approval_request_notifications_mode = fields.Selection(
        _NOTIFICATIONS, required=True,
        string='Modo de notificaciones para solicitudes de aprobación de marcación', help='')
    user_attendance_approval_request_administrator = fields.Many2one(
        'hr.employee',
        'Administrador para solicitudes de aprobación de marcación',
        help='')
    user_attendance_approval_request_second_administrator = fields.Many2one(
        'hr.employee',
        'Segundo administrador para solicitudes de aprobación de marcación',
        help='')

    amount_days_after_cdfr_to_HEAR = fields.Integer(
        string="Cantidad de días para reportar horas extras", required=True,
        help='Cantidad de días después de la fecha de corte donde es permitido reportar las horas extras.')
    include_holidays_amount_days_after_cdfr_to_HEAR = fields.Boolean(
        string="Incluir feriados y fines de semana en la cantidad de días para reportar horas extras", required=True,
        help='Incluir feriados y fines de semana en la cantidad de días después de la fecha de corte donde es '
             'permitido reportar las horas extras.')

    @api.onchange('assistance_mode')
    def on_change_assistance_mode(self):
        for rec in self:
            if rec.assistance_mode:
                rec.attendance_state_ids = [(6, 0, [])]

                att_state_ids = self.env['attendance.state']

                if rec.assistance_mode == '1':
                    attendance_device_state_code_0 = self.env.ref('hr_dr_schedule.attendance_device_state_code_0')
                    if attendance_device_state_code_0:
                        att_state_ids += attendance_device_state_code_0
                    attendance_device_state_code_1 = self.env.ref('hr_dr_schedule.attendance_device_state_code_1')
                    if attendance_device_state_code_1:
                        att_state_ids += attendance_device_state_code_1

                    attendance_device_state_code_2 = self.env.ref('hr_dr_schedule.attendance_device_state_code_2')
                    if attendance_device_state_code_2:
                        att_state_ids += attendance_device_state_code_2
                    attendance_device_state_code_3 = self.env.ref('hr_dr_schedule.attendance_device_state_code_3')
                    if attendance_device_state_code_3:
                        att_state_ids += attendance_device_state_code_3

                    attendance_device_state_code_4 = self.env.ref('hr_dr_schedule.attendance_device_state_code_4')
                    if attendance_device_state_code_4:
                        att_state_ids += attendance_device_state_code_4
                    attendance_device_state_code_5 = self.env.ref('hr_dr_schedule.attendance_device_state_code_5')
                    if attendance_device_state_code_5:
                        att_state_ids += attendance_device_state_code_5
                elif rec.assistance_mode == '2':
                    attendance_device_state_code_01 = self.env.ref('hr_dr_schedule.attendance_device_state_code_01')
                    if attendance_device_state_code_01:
                        att_state_ids += attendance_device_state_code_01
                    attendance_device_state_code_23 = self.env.ref('hr_dr_schedule.attendance_device_state_code_23')
                    if attendance_device_state_code_23:
                        att_state_ids += attendance_device_state_code_23
                    attendance_device_state_code_45 = self.env.ref('hr_dr_schedule.attendance_device_state_code_45')
                    if attendance_device_state_code_45:
                        att_state_ids += attendance_device_state_code_45
                elif rec.assistance_mode == '3':
                    attendance_device_state_code_i = self.env.ref('hr_dr_schedule.attendance_device_state_code_i')
                    if attendance_device_state_code_i:
                        att_state_ids += attendance_device_state_code_i

                rec.attendance_state_ids = att_state_ids

    @api.model
    def get_values(self):
        res = super(ScheduleSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        res.update(assistance_mode=config_parameter.get_param('attendance.mode', default=''))

        if config_parameter.get_param('attendance.state.ids'):
            if config_parameter.get_param('attendance.state.ids') != '':
                res.update(attendance_state_ids=self.env['attendance.state'].sudo().browse(
                    [int(id) for id in config_parameter.get_param('attendance.state.ids').split(',')]).exists())

        res.update(hour_extra_approval_request_notifications_mode=config_parameter.get_param(
            'hour.extra.approval.request.notifications.mode', default=''))

        if config_parameter.get_param('hour.extra.approval.request.administrator'):
            if config_parameter.get_param('hour.extra.approval.request.administrator') != '':
                res.update(hour_extra_approval_request_administrator=int(
                    config_parameter.get_param('hour.extra.approval.request.administrator')))

        if config_parameter.get_param('hour.extra.approval.request.second.administrator'):
            if config_parameter.get_param('hour.extra.approval.request.second.administrator') != '':
                res.update(hour_extra_approval_request_second_administrator=int(
                    config_parameter.get_param('hour.extra.approval.request.second.administrator')))

        res.update(
            max_time_in_past_to_request_for_attendance=int(config_parameter.get_param(
                'max.time.in.past.to.request.for.attendance', default=72)))

        res.update(user_attendance_approval_request_notifications_mode=config_parameter.get_param(
            'user.attendance.approval.request.notifications.mode', default=''))

        if config_parameter.get_param('user.attendance.approval.request.administrator'):
            if config_parameter.get_param('user.attendance.approval.request.administrator') != '':
                res.update(user_attendance_approval_request_administrator=int(
                    config_parameter.get_param('user.attendance.approval.request.administrator')))

        if config_parameter.get_param('user.attendance.approval.request.second.administrator'):
            if config_parameter.get_param('user.attendance.approval.request.second.administrator') != '':
                res.update(user_attendance_approval_request_second_administrator=int(
                    config_parameter.get_param('user.attendance.approval.request.second.administrator')))

        res.update(
            amount_days_after_cdfr_to_HEAR=int(config_parameter.get_param(
                'amount.days.after.cutoff.date.for.report.to.HEAR', default=2)))
        
        if config_parameter.get_param('include.holidays.amount.days.after.cutoff.date.for.report.to.HEAR'):
            if config_parameter.get_param('include.holidays.amount.days.after.cutoff.date.for.report.to.HEAR') != '':
                res.update(include_holidays_amount_days_after_cdfr_to_HEAR=bool(
                    int(config_parameter.get_param(
                        'include.holidays.amount.days.after.cutoff.date.for.report.to.HEAR', default=0))))

        return res
    
    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param("attendance.mode", self.assistance_mode)
        set_param('attendance.state.ids', ",".join([str(id) for id in self.attendance_state_ids.ids]))

        set_param("hour.extra.approval.request.notifications.mode", self.hour_extra_approval_request_notifications_mode)
        set_param("hour.extra.approval.request.administrator", self.hour_extra_approval_request_administrator.id)
        set_param("hour.extra.approval.request.second.administrator",
                  self.hour_extra_approval_request_second_administrator.id)

        set_param('max.time.in.past.to.request.for.attendance', self.max_time_in_past_to_request_for_attendance)

        set_param("user.attendance.approval.request.notifications.mode",
                  self.user_attendance_approval_request_notifications_mode)
        set_param("user.attendance.approval.request.administrator",
                  self.user_attendance_approval_request_administrator.id)
        set_param("user.attendance.approval.request.second.administrator",
                  self.user_attendance_approval_request_second_administrator.id)

        set_param('amount.days.after.cutoff.date.for.report.to.HEAR',
                  self.amount_days_after_cdfr_to_HEAR)

        set_param("include.holidays.amount.days.after.cutoff.date.for.report.to.HEAR", int(
            self.include_holidays_amount_days_after_cdfr_to_HEAR))

        super(ScheduleSettings, self).set_values()

    @api.onchange('hour_extra_approval_request_notifications_mode')
    def _onchange_hour_extra_approval_request_notifications_mode(self):
        if self.hour_extra_approval_request_notifications_mode == "Without_notifications" \
                or self.hour_extra_approval_request_notifications_mode == "One_level_bd" \
                or self.hour_extra_approval_request_notifications_mode == "One_level_br" \
                or self.hour_extra_approval_request_notifications_mode == "One_level_bc"\
                or self.hour_extra_approval_request_notifications_mode == "Two_levels_bd"\
                or self.hour_extra_approval_request_notifications_mode == "All_levels_bd"\
                or self.hour_extra_approval_request_notifications_mode == "Personalized":
            self.hour_extra_approval_request_administrator = ""
        if self.hour_extra_approval_request_notifications_mode != "One_level_bd_and_two_administrator":
            self.hour_extra_approval_request_second_administrator = ""

    @api.onchange('user_attendance_approval_request_notifications_mode')
    def _onchange_user_attendance_approval_request_notifications_mode(self):
        if self.user_attendance_approval_request_notifications_mode == "Without_notifications" \
                or self.user_attendance_approval_request_notifications_mode == "One_level_bd" \
                or self.user_attendance_approval_request_notifications_mode == "One_level_br" \
                or self.user_attendance_approval_request_notifications_mode == "One_level_bc" \
                or self.user_attendance_approval_request_notifications_mode == "Two_levels_bd" \
                or self.user_attendance_approval_request_notifications_mode == "All_levels_bd" \
                or self.user_attendance_approval_request_notifications_mode == "Personalized":
            self.user_attendance_approval_request_administrator = ""
        if self.user_attendance_approval_request_notifications_mode != "One_level_bd_and_two_administrator":
            self.user_attendance_approval_request_second_administrator = ""