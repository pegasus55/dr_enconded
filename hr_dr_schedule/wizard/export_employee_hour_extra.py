# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError


class ExportEmployeeHourExtra(models.TransientModel):
    _name = 'export.employee.hour.extra'
    _description = 'Export employee hour extra'

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('end', '<=', datetime.utcnow().date()),
            ('state', 'in', ['open'])
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False

    attendance_period_id = fields.Many2one('hr.attendance.period', string='Período de asistencia', required=True,
                                           default=_default_period_id)

    def action_export_employee_hour_extra(self):
        data = {
            'attendance_period_id': self.attendance_period_id.id
        }
        return self.env.ref('hr_dr_schedule.action_export_employee_hour_extra_report').report_action(self, data=data)


class ExportEmployeeHourExtraXls(models.AbstractModel):
    _name = 'report.hr_dr_schedule.export_employee_hour_extra'
    _description = 'Report employee hour extra'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        attendance_period = self.env['hr.attendance.period'].search([('id', '=', data['attendance_period_id'])],
                                                                    limit=1)
        domain = []
        if self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_supervisor') \
                or self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_manager'):
            # Horas extras de toda la empresa
            domain = [('attendance_period_id', '=', attendance_period.id),
                      ('state', 'in', ['draft'])]
        elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_responsible'):
            # Horas extras de su departamento
            if self.env.user.employee_id.department_id.id:
                domain = [('attendance_period_id', '=', attendance_period.id),
                          ('state', 'in', ['draft']),
                          ('department_employee_id', '=', self.env.user.employee_id.department_id.id)]
            else:
                raise ValidationError(_("El colaborador asociado al usuario en sesión "
                                        "no pertenece a ningún departamento."))
        elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_employee'):
            # Horas extras propias
            domain = [('attendance_period_id', '=', attendance_period.id),
                      ('state', 'in', ['draft']),
                      ('user_employee_id', '=', self.env.uid)]
        else:
            raise ValidationError(_("Su usuario no cuenta con los permisos suficientes para generar el reporte."))

        employee_hour_extra = self.env['hr.employee.hour.extra'].search(
            domain,
            order='department_employee_id, employee_id')

        # Definiendo formatos de celdas
        text_props = {'font_size': 10, 'align': 'left', 'font_name': 'Calibri'}
        label_props = text_props.copy()
        label_props.update({'bold': True, 'align': 'right'})
        title_props = text_props.copy()
        title_props.update({'font_size': 18, 'font_name': 'Calibri Light', 'font_color': '#44546A'})
        h1_props = text_props.copy()
        h1_props.update({'font_size': 15, 'bold': True, 'font_color': '#44546A'})
        h2_props = h1_props.copy()
        h2_props.update({'font_size': 11})
        th_props = label_props.copy()
        th_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#44546A', 'font_color': '#FFFFFF',
                         'border': True, 'text_wrap': True})
        th_red_props = label_props.copy()
        th_red_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#FF0000', 'font_color': '#FFFFFF',
                             'border': True, 'text_wrap': True})
        th_green_props = label_props.copy()
        th_green_props.update({'align': 'center', 'valign': 'vcenter', 'bg_color': '#008000', 'font_color': '#FFFFFF',
                               'border': True, 'text_wrap': True})
        td_props = text_props.copy()
        td_props.update({'border': True})
        td_info_props = td_props.copy()
        td_info_props.update({'align': 'left', 'italic': True, 'font_color': '#7F7f7F'})
        date_props = text_props.copy()
        date_props.update({'num_format': 'dd/mm/yyyy'})
        number_props = text_props.copy()
        number_props.update({'num_format': '#,##0.00'})
        money_props = text_props.copy()
        money_props.update({'num_format': '#,##0.00'})
        td_date_props = date_props.copy()
        td_date_props.update({'border': True})
        td_number_props = number_props.copy()
        td_number_props.update({'align': 'right', 'border': True})
        td_money_props = money_props.copy()
        td_money_props.update({'align': 'right', 'border': True})

        reference_props = text_props.copy()
        reference_props.update({'font_size': 8})

        title = workbook.add_format(title_props)
        header1 = workbook.add_format(h1_props)
        header2 = workbook.add_format(h2_props)
        label = workbook.add_format(label_props)
        text = workbook.add_format(text_props)
        date_format = workbook.add_format(date_props)
        number_format = workbook.add_format(number_props)
        money_format = workbook.add_format(money_props)
        table_header = workbook.add_format(th_props)
        table_header_red = workbook.add_format(th_red_props)
        table_header_green = workbook.add_format(th_green_props)
        table_cell = workbook.add_format(td_props)
        table_info_cell = workbook.add_format(td_info_props)
        table_date_format = workbook.add_format(td_date_props)
        table_number_format = workbook.add_format(td_number_props)
        table_money_format = workbook.add_format(td_money_props)

        reference = workbook.add_format(reference_props)

        sheet = workbook.add_worksheet(_('Horas extras del período'))

        sheet.center_horizontally()

        col_end = 6
        # Estableciendo el ancho de las columnas
        sheet.set_column('A:A', 7.0)
        sheet.set_column('B:B', 30.0)
        sheet.set_column(2, col_end-1, 20.0)
        sheet.set_column(col_end, col_end, 50.0)

        # Escribiendo encabezado de informe
        sheet.merge_range(0, 0, 0, col_end, self.env.user.company_id.name, title)
        sheet.merge_range(1, 0, 1, col_end,
                          _('Horas extras del período: {}').format(attendance_period.display_name), header2)
        sheet.merge_range(2, 0, 2, col_end,
                          _('Lea los comentarios en cada columna. Las columnas de color rojo no se importan, '
                            'por ende no tiene sentido modificarlas. '
                            'Solo las columnas de color verde se importan.'), reference)

        # Escribiendo los encabezados de la tabla
        row = 3
        sheet.write(row, 0, _('Id'), table_header_red)
        sheet.write(row, 1, _('Colaborador'), table_header_red)
        sheet.write(row, 2, _('Identificación'), table_header_red)
        sheet.write(row, 3, _('Departamento'), table_header_red)
        sheet.write(row, 4, _('Cantidad (HH:MM:SS)'), table_header_red)
        sheet.write(row, 5, _('Cantidad (Valor decimal)'), table_header_red)
        sheet.write(row, 6, _('Motivo'), table_header_green)

        row += 1

        for line in employee_hour_extra:
            sheet.write(row, 0, line.id, table_cell)
            sheet.write(row, 1, line.employee_id.display_name, table_cell)
            if line.employee_id.identification_id:
                sheet.write(row, 2, line.employee_id.identification_id, table_cell)
            else:
                sheet.write(row, 2, '-', table_cell)
            if line.employee_id.department_id:
                sheet.write(row, 3, line.employee_id.department_id.name, table_cell)
            else:
                sheet.write(row, 3, '-', table_cell)

            sheet.write(row, 4, line.amount_hms, table_cell)
            sheet.write(row, 5, line.amount_hd, table_number_format)
            if line.employee_reason:
                sheet.write(row, 6, line.employee_reason, table_cell)
            else:
                sheet.write(row, 6, '', table_cell)

            row += 1

        sheet.fit_to_pages(1, 0)