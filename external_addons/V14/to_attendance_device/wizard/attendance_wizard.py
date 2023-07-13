import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Attendance Wizard'

    @api.model
    def _default_get_all_device_ids(self):
        all_devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        if all_devices:
            return all_devices.ids
        else:
            return []

    device_ids = fields.Many2many('attendance.device', string='Devices', default=_default_get_all_device_ids, domain=[('state', '=', 'confirmed')])

    def _download_device_attendance(self, devices):
        for device in devices:
            try:
                 with self.pool.cursor() as cr:
                    device.with_env(self.env(cr=cr)).action_attendance_download()
            except Exception as e:
                _logger.error(e)

    def action_download_attendance(self):
        if not self.device_ids:
            raise UserError(_('You must confirm at least one device to continue!'))
        self._download_device_attendance(self.device_ids)

    def cron_download_device_attendance(self):
        devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        self._download_device_attendance(devices)

    def cron_sync_attendance(self):
        self.env['user.attendance']._cron_synch_hr_attendance()

    def sync_attendance(self):
        # TODO: rename me into `action_sync_attendance` in master/14+
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        self.env['user.attendance']._cron_synch_hr_attendance()

    def clear_attendance(self):
        # TODO: rename me into `action_clear_attendance` in master/14+
        if not self.device_ids:
            raise UserError(_('You must confirm at least one device to continue!'))
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise UserError(_('Only HR Attendance Managers can manually clear device attendance data'))

        for device in self.device_ids:
            device.clearAttendance()
