# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
from xlrd.xldate import xldate_as_datetime


class ImportUserAttendance(models.TransientModel):
    _name = 'import.user.attendance'
    _description = 'Import user attendance'
    _inherit = ['dr.base']

    def get_attendance_state_ids(self, device):
        attendance_states = {}
        if len(device.attendance_device_state_line_ids) > 0:
            for attendance_state in device.attendance_device_state_line_ids:
                attendance_states[attendance_state.attendance_state_id.code] = attendance_state.attendance_state_id.id
        else:
            config_parameter = self.env['ir.config_parameter'].sudo()
            if config_parameter.get_param('attendance.state.ids'):
                if config_parameter.get_param('attendance.state.ids') != '':
                    for id in config_parameter.get_param('attendance.state.ids').split(','):
                        attendance_state_id = int(id)
                        attendance_state = self.env['attendance.state'].sudo().search([
                            ('id', '=', attendance_state_id)], limit=1)
                        if len(attendance_state) > 0:
                            attendance_states[attendance_state.code] = attendance_state.id
        return attendance_states

    def create_attendance_device_user(self):
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate', 'temporary', 'intern'])])
        attendance_device_web_id = self.env.ref('hr_dr_schedule.attendance_device_web').id
        for e in employees:
            attendance_device_user = self.env['attendance.device.user'].with_context(active_test=False).search([
                ('user_id', '=', e.barcode),
                ('device_id', '=', attendance_device_web_id)])
            if not attendance_device_user:
                self.env['attendance.device.user'].create({
                    'name': e.name,
                    'device_id': attendance_device_web_id,
                    'user_id': e.barcode,
                    'employee_id': e.id,
                })

    def action_import_user_attendance(self):
        if not self.data:
            raise ValidationError(_('Para continuar debe cargar el archivo de marcaciones.'))
        device = self.env.ref('hr_dr_schedule.attendance_device_web')
        self.create_attendance_device_user()
        all = []
        found = []
        warning = []
        attendance_states = self.get_attendance_state_ids(device)
        doc_import = xlrd.open_workbook(file_contents=base64.decodebytes(self.data))
        doc_import_sheet = doc_import.sheet_by_index(0)
        nrows_doc = doc_import_sheet.nrows
        for f in range(nrows_doc):
            if f >= 1:
                employee_identification = doc_import_sheet.cell_value(f, 1)
                all.append(employee_identification)
                employee = self.env['hr.employee'].search([('identification_id', '=', int(employee_identification))])
                if employee:
                    found.append(employee_identification)
                    date_time = xldate_as_datetime(doc_import_sheet.cell_value(f, 2), doc_import.datemode)
                    date_time = self.convert_time_to_utc(date_time, employee.tz)

                    user_attendance = self.env['user.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('timestamp', '=', date_time)])

                    if not user_attendance:
                        attendance_device_user = self.env['attendance.device.user'].with_context(active_test=False).\
                            search([('user_id', '=', employee.barcode),
                                    ('device_id', '=', self.env.ref('hr_dr_schedule.attendance_device_web').id)])

                        if int(doc_import_sheet.cell_value(f, 3)) not in attendance_states.keys():
                            attendance_states_codes = ','.join([str(i) for i in attendance_states.keys()])
                            raise UserError(_('El código %s es inválido para la configuración actual de horarios. '
                                              'Los códigos válidos son: %s.')
                                            % (int(doc_import_sheet.cell_value(f, 3)), attendance_states_codes))

                        self.env['user.attendance'].create({
                            'user_id': attendance_device_user.id,
                            'timestamp': date_time,
                            'status': int(doc_import_sheet.cell_value(f, 3)),
                            'attendance_state_id': attendance_states[int(doc_import_sheet.cell_value(f, 3))],
                            'device_id': device.id,
                            'mode': 'web',
                        })

        warning = set(all) - set(found)
        warning = sorted(warning)
        if warning:
            list = '\n'.join('* ' + w for w in warning)
            raise UserError(_('Las marcaciones asociadas a los colaboradores con los siguientes números de '
                              'identificación no pudieron ser importadas:\n%s' % list))

        tree_view_id = self.env.ref('hr_dr_schedule.view_attendance_data_tree').id
        form_view_id = self.env.ref('hr_dr_schedule.view_attendance_data_form').id
        search_view_id = self.env.ref('hr_dr_schedule.user_attendance_data_search_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Todas las marcaciones',
            'res_model': 'user.attendance',
            'target': 'current',
            'view_mode': 'tree',
            'context': {'search_default_group_by_employee': True, 'search_default_filter_last_period': 1,
                        'search_default_group_by_day': True},
            'search_view_id': [search_view_id, 'search'],
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
        }

    def _default_template(self):
        template_path = odoo.modules.module.get_resource_path(
            'hr_dr_schedule', 'import_template', 'Importar marcaciones.xlsx')
        with open(template_path, 'rb') as imp_sheet:
            file = imp_sheet.read()
        return file and base64.b64encode(file)

    def get_template(self):
        return {
            'name': 'Importar marcaciones',
            'type': 'ir.actions.act_url',
            'url': ("web/content/?model=" + self._name + "&id=" +
                    str(self.id) + "&filename_field=template_name&"
                                   "field=template&download=true&"
                                   "filename=Importar marcaciones.xlsx"),
            'target': 'self',
        }

    # Columns
    data = fields.Binary(string='Archivo', help='Seleccione el archivo de marcaciones.')
    template = fields.Binary(string='Plantilla', default=_default_template)
    template_name = fields.Char(default='Importar marcaciones.xlsx')