# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ExportPeriodSummary(models.TransientModel):
    _name = "hr.export.period.summary"
    _description = 'Export period summary'

    def _default_period_id(self):
        last_period = self.env['hr.attendance.period'].search([
            ('end', '<=', datetime.utcnow().date())
        ], order='end desc', limit=1)
        if last_period:
            return last_period
        return False

    attendance_period_id = fields.Many2one('hr.attendance.period', string='Período de asistencia', required=True,
                                           default=_default_period_id)

    def action_export_period_summary(self):
        data = {
            'attendance_period_id': self.attendance_period_id.id
        }
        return self.env.ref('hr_dr_schedule.action_export_period_summary_request').report_action(self, data=data)


class ExportPeriodSummaryXls(models.AbstractModel):
    _name = 'report.hr_dr_schedule.report_period_summary'
    _description = 'Report period summary'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, lines):
        attendance_period = self.env['hr.attendance.period'].search([('id', '=', data['attendance_period_id'])], limit=1)
        period_summary = self.env['hr.employee.period.summary'].search(
            [('attendance_period_id', '=', attendance_period.id)], order='department_employee_id')

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
        td_props = text_props.copy()
        td_props.update({'border': True})
        td_info_props = td_props.copy()
        td_info_props.update({'align': 'left', 'italic': True, 'font_color': '#7F7f7F'})
        date_props = text_props.copy()
        date_props.update({'num_format': 'dd/mm/yyyy'})
        number_props = text_props.copy()
        number_props.update({'num_format': '#,##0'})
        money_props = text_props.copy()
        money_props.update({'num_format': '#,##0.00'})
        td_date_props = date_props.copy()
        td_date_props.update({'border': True})
        td_number_props = number_props.copy()
        td_number_props.update({'align': 'right', 'border': True})
        td_money_props = money_props.copy()
        td_money_props.update({'align': 'right', 'border': True})

        title = workbook.add_format(title_props)
        header1 = workbook.add_format(h1_props)
        header2 = workbook.add_format(h2_props)
        label = workbook.add_format(label_props)
        text = workbook.add_format(text_props)
        date_format = workbook.add_format(date_props)
        number_format = workbook.add_format(number_props)
        money_format = workbook.add_format(money_props)
        table_header = workbook.add_format(th_props)
        table_cell = workbook.add_format(td_props)
        table_info_cell = workbook.add_format(td_info_props)
        table_date_format = workbook.add_format(td_date_props)
        table_number_format = workbook.add_format(td_number_props)
        table_money_format = workbook.add_format(td_money_props)

        sheet = workbook.add_worksheet(_('Resumen del período'))

        # Dando formato a la hoja
        # sheet.set_landscape()
        # sheet.set_paper(9)  # A4 paper format (change to 0 for printer default)
        sheet.center_horizontally()
        # sheet.set_margins(left=0.7, right=0.7, top=0.75, bottom=0.75)

        # Calculando las columnas necesarias para las horas extras y las horas nocturnas

        extra_hours = []
        night_hours = []

        for line in period_summary:
            for extra_line in line.hour_extra_sumary_ids:
                if extra_line.hour_extra_id not in extra_hours:
                    extra_hours.append(extra_line.hour_extra_id)

            for night_line in line.hour_night_sumary_ids:
                if night_line.hour_extra_id not in extra_hours:
                    night_hours.append(night_line.hour_night_id)

        extra_hours_col_start = 2
        extra_hours_col_end = extra_hours_col_start + (len(extra_hours) if len(extra_hours) == 0 else len(extra_hours) -1)
        night_hours_col_start = extra_hours_col_end + 1
        night_hours_col_end = night_hours_col_start + (len(night_hours) if len(night_hours) == 0 else len(night_hours) -1)

        # Estableciendo el ancho de las columnas
        sheet.set_column('A:A', 20.0)
        sheet.set_column('B:B', 14.0)
        sheet.set_column(2,night_hours_col_end, 15.0)

        # Escribiendo encabezado de informe
        sheet.merge_range(0, 0, 0, night_hours_col_end, self.env.user.company_id.name, title)
        sheet.merge_range(1, 0, 1, night_hours_col_end, _('Resumen del período: {}').format(attendance_period.display_name), header2)

        # Escribiendo los encabezados de la tabla
        row = 3

        # Estableciendo formato base del encabezado
        for col in range(night_hours_col_end + 1):
            sheet.write_blank(row, col, None, table_header)
            sheet.write_blank(row + 1, col, None, table_header)

        sheet.merge_range(row, 0, row + 1, 0, _('Colaborador'), table_header)
        sheet.merge_range(row, 1, row + 1, 1, _('Cédula'), table_header)
        if extra_hours_col_start == extra_hours_col_end:
            sheet.write(row, extra_hours_col_start, _('Horas Extras'), table_header)
        else:
            sheet.merge_range(row, extra_hours_col_start, row, extra_hours_col_end, _('Horas Extras'), table_header)
        if night_hours_col_start == night_hours_col_end:
            sheet.write(row, night_hours_col_start,  _('Horas Nocturnas'), table_header)
        else:
            sheet.merge_range(row, night_hours_col_start, row, night_hours_col_end, _('Horas Nocturnas'), table_header)
        row += 1
        for idx, extra in enumerate(extra_hours):
            sheet.write(row, extra_hours_col_start + idx, extra.display_name, table_header)
        for idx, night in enumerate(night_hours):
            sheet.write(row, night_hours_col_start + idx, night.display_name, table_header)
        row += 1

        department = None

        for line in period_summary:
            if department != line.employee_id.department_id.display_name:
                department = line.employee_id.department_id.display_name
                if department is not None:
                    sheet.merge_range(row, 0, row, night_hours_col_end, department, table_info_cell)
                    row += 1

            for col in range(night_hours_col_end + 1):
                sheet.write_blank(row, col, None, table_cell)

            sheet.write(row, 0, line.employee_id.display_name, table_cell)
            if line.employee_id.identification_id:
                sheet.write(row, 1, line.employee_id.identification_id, table_cell)
            else:
                sheet.write(row, 1, '-', table_cell)

            for extra_line in line.hour_extra_sumary_ids:
                sheet.write(row, extra_hours_col_start + extra_hours.index(extra_line.hour_extra_id),
                            extra_line.amount_hd, table_number_format)

            for night_line in line.hour_night_sumary_ids:
                sheet.write(row, night_hours_col_start + night_hours.index(night_line.hour_night_id),
                            night_line.amount_hd, table_number_format)
            row += 1

        sheet.fit_to_pages(1, 0)