# -*- coding:utf-8 -*-
from typing import List

from odoo import api, Command, fields, models, _
from dateutil.relativedelta import relativedelta
import base64
import xlsxwriter
from io import BytesIO
import functools


def text_safe(text):
    """
    Si recibe una cadena de texto, la devuelve, si el valor recibido es el boolean False, devuelve una cadena de texto
    vacía.
    :param text: Valor de entrada
    :return: str
    """
    return '' if not text else text


def add2list(data_list: list, value: float, index: int):
    if len(data_list) <= index:
        data_list.append(value)
    else:
        data_list[index] += value


# def cell_notation(row, col):
#     # 65 90
#
#     return f'{}{row + 1}'

class Value:
    def __init__(self, employee_id, quantity, total):
        self.qty = quantity
        self.total = total
        self.employee_id = employee_id

    def __str__(self):
        return f'{self.total} | {self.qty}'


@functools.total_ordering
class Rule:
    category_order = ['INGRESOS', 'INGRESOS_NGBS', 'EGRESOS', 'EGRESOS_PASIVOS', 'C_COMPANY', 'PROVISIONES',
                      'SUBTOTALES', 'INFO', 'CRUCE_PROVISIONES']

    def __init__(self, code, name, category_code, sequence):
        self.code = code
        self.name = name
        self.category_code = category_code
        self.sequence = sequence
        self.values = []
        self.show_qty = False

    def __eq__(self, other):
        return self.code == other.code

    def __lt__(self, other):
        weight = self._get_category_weight() + self.sequence
        other_weight = other._get_category_weight() + other.sequence
        return weight < other_weight

    def __str__(self):
        return self.name

    def add_value(self, employee_id, total, qty=1):
        self.values.append(Value(employee_id, qty, total))

    def get_values(self, employee_id):
        for value in self.values:
            if value.employee_id == employee_id:
                return value
        return False

    def _get_category_weight(self):
        try:
            return Rule.category_order.index(self.category_code) * 1000
        except ValueError:
            return len(Rule.category_order) * 1000


class Rules:

    rules: List[Rule]

    def __init__(self):
        self.rules = []

    def __str__(self):
        return '\n'.join(
            [' | '.join([r.code.ljust(30), r.category_code.ljust(20), str(r.sequence)]) for r in self.rules]
        )

    def __iter__(self):
        return self.rules.__iter__()

    def has_rule(self, code):
        for rule in self.rules:
            if rule.code == code:
                return rule
        return False

    def add_or_update(self, code, name, category_code, sequence, employee_id, total, qty, show_qty=False):
        rule = self.has_rule(code)
        if not rule:
            rule = Rule(code, name, category_code, sequence)
            rule.show_qty = show_qty
            self.rules.append(rule)
        rule.add_value(employee_id, total, qty)
        self.rules = sorted(self.rules)


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            next_month = relativedelta(months=+1, day=1, days=-1)
            self.date_end = self.date_start + next_month

    def action_print_xlsx(self):
        datafile = BytesIO()
        workbook = xlsxwriter.Workbook(datafile)
        name = self.name
        self.xlsx_body(workbook, name)
        workbook.close()
        datafile.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(datafile.getvalue()),
            'name': self.name,
            'store_fname': self.name + '.xlsx',
        })
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += "/web/content/%s?download=true" % (attachment.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def xlsx_body(self, workbook, name):
        bold_title = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#4F81BD', 'font_size': 10,
                                          'text_wrap': True, 'align': 'center', 'valign': 'top'})
        # bold_title.set_center_across()
        bold_subtitle = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#B8CCE4', 'font_size': 10,
                                             'align': 'right'})
        # bold_subtitle.set_center_across()
        number = workbook.add_format({'border': 1, 'font_size': 10})
        number_title = workbook.add_format({'border': 1, 'bg_color': '#4F81BD', 'bold': True, 'font_size': 10})
        number_subtitle = workbook.add_format({'border': 1, 'bg_color': '#B8CCE4', 'bold': True, 'font_size': 10})
        money = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'font_size': 10})
        money_title = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'bg_color': '#4F81BD', 'bold': True,
                                           'font_size': 10})
        money_subtitle = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'bg_color': '#B8CCE4',
                                              'bold': True, 'font_size': 10})
        border = workbook.add_format({'border': 1, 'font_size': 10})

        row = 1
        col = 0
        sheet = workbook.add_worksheet(name)
        sheet.write(0, 4, name.upper())
        # sheet.write(row, col, 'Mes')
        # sheet.write(row, col + 1, self.date_start.month)
        # sheet.write(row, col + 2, 'Periodo')
        # sheet.write(row, col + 3, self.date_start.year)
        sheet.write(row, col + 3, f'Mes: {self.date_start.month}')
        sheet.write(row, col + 4, f'Periodo: {self.date_start.year}')
        row += 1
        # sheet.write(row, col, 'No.', bold_title)
        # sheet.write(row, col + 1, 'Localidad', bold_title)
        # sheet.write(row, col + 2, 'Área', bold_title)
        # sheet.write(row, col + 3, 'Departamento', bold_title)
        # sheet.write(row, col + 4, 'Empleado', bold_title)
        # sheet.write(row, col + 5, 'Cédula', bold_title)
        # sheet.write(row, col + 6, 'Días Trabajados', bold_title)
        # sheet.write(row, col + 7, 'Sueldo', bold_title)

        sheet.merge_range(row, col, row + 1, col, 'No.', bold_title)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'Localidad', bold_title)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Área', bold_title)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Departamento', bold_title)
        sheet.merge_range(row, col + 4, row + 1, col + 4, 'Colaborador', bold_title)
        sheet.merge_range(row, col + 5, row + 1, col + 5, 'Cédula', bold_title)
        sheet.merge_range(row, col + 6, row + 1, col + 6, 'Días Trabajados', bold_title)
        # sheet.merge_range(row, col + 7, row + 1, col + 7, 'Sueldo', bold_title)

        rules = Rules()

        for slip_id in self.slip_ids:
            inputs = slip_id.input_line_ids
            for line_id in slip_id.line_ids:
                if line_id.salary_rule_id.appears_on_payroll_report:
                    qty = line_id.quantity
                    show_qty = False
                    if line_id.salary_rule_id.show_input_value:
                        show_qty = True
                        for input in inputs:
                            if line_id.code == input.code:
                                qty = input.amount
                                break
                    rules.add_or_update(code=line_id.code, name=line_id.name, sequence=line_id.sequence,
                                        category_code=line_id.category_id.code, employee_id=slip_id.employee_id.id,
                                        total=line_id.total, qty=qty, show_qty=show_qty)

        i = 0
        for rule in rules:
            # if rule.show_qty:
            #     sheet.write(row, col + 8 + i, rule.code, number_title)
            #     i += 1
            # sheet.write(row, col + 8 + i, rule.name, money_title)
            # i += 1
            if rule.show_qty:
                sheet.merge_range(row, col + 7 + i, row,  col + 8 + i, rule.name, bold_title)
                sheet.write(row + 1, col + 7 + i, 'Cant.', bold_title)
                sheet.write(row + 1, col + 8 + i, 'Imp.', bold_title)
                # sheet.write(row, col + 8 + i, rule.name, bold_title)
                i += 2
            else:
                sheet.merge_range(row, col + 7 + i, row + 1, col + 7 + i, rule.name, bold_title)
                # sheet.write(row, col + 8 + i, rule.name, bold_title)
                i += 1

        row += 1
        slip_number = 0
        area = ''
        current_total = []
        general_total = []
        for slip_id in sorted(self.slip_ids, key=lambda x: x.employee_id.department_id.id):
            if area == '':
                area = slip_id.employee_id.department_id.name
            elif area != slip_id.employee_id.department_id.name:
                row += 1
                i = 0
                for rule in rules:
                    if rule.show_qty:
                        sheet.write(row, col + 7 + i, '' if current_total[i] == 0 else current_total[i], number_subtitle)
                        add2list(general_total, current_total[i], i)
                        i += 1
                    # sheet.merge_range(row, 0, row, 7, f'Total {area}', bold)
                    for j in range(7):
                        sheet.write(row, j, '', bold_subtitle)
                    sheet.write(row, 4, f'Total {area}'.upper(), bold_subtitle)
                    sheet.write(row, col + 7 + i, '' if current_total[i] == 0 else current_total[i], money_subtitle)
                    add2list(general_total, current_total[i], i)
                    i += 1
                current_total = [0.0 for i in current_total]
                area = slip_id.employee_id.department_id.name

            row += 1
            slip_number += 1
            sheet.write(row, col, slip_number, border)
            sheet.write(row, col + 1, text_safe(False), border)
            sheet.write(row, col + 2, text_safe(slip_id.contract_id.department_id.name), border)
            sheet.write(row, col + 3, slip_id.employee_id.department_id.name, border)
            sheet.write(row, col + 4, slip_id.employee_id.name, border)
            sheet.write(row, col + 5, slip_id.employee_id.identification_id, border)
            sheet.write(row, col + 6, slip_id.worked_days, number)
            # sheet.write(row, col + 7, slip_id.basic_wage, money)
            i = 0
            for rule in rules:
                values = rule.get_values(slip_id.employee_id.id)
                if rule.show_qty:
                    sheet.write(row, col + 7 + i, values.qty if values else '', number)
                    add2list(current_total, values.qty if values else 0, i)
                    i += 1
                sheet.write(row, col + 7 + i, values.total if values else '', money)
                add2list(current_total, values.total if values else 0, i)
                i += 1

        if area != '':
            row += 1
            i = 0
            for rule in rules:
                if rule.show_qty:
                    sheet.write(row, col + 7 + i, '' if current_total[i] == 0 else current_total[i], number_subtitle)
                    add2list(general_total, current_total[i], i)
                    i += 1
                # sheet.merge_range(row, 0, row, 7, f'Total {area}', bold)
                for j in range(7):
                    sheet.write(row, j, '', bold_subtitle)
                sheet.write(row, 4, f'Total {area}'.upper(), bold_subtitle)
                sheet.write(row, col + 7 + i, '' if current_total[i] == 0 else current_total[i], money_subtitle)
                add2list(general_total, current_total[i], i)
                i += 1

        row += 1
        i = 0
        for rule in rules:
            if rule.show_qty:
                sheet.write(row, col + 7 + i, general_total[i], number_title)
                i += 1
            # sheet.merge_range(row, 0, row, 2, f'Total general', bold_title)
            for j in range(7):
                sheet.write(row, j, '', bold_title)
            sheet.write(row, 4, 'TOTAL GENERAL', bold_title)
            # sheet.merge_range(row, 0, row, 4, 'Total general', bold_title)
            sheet.write(row, col + 7 + i, general_total[i], money_title)
            i += 1

        sheet.freeze_panes(4, 5)
        sheet.set_column('B:C', None, None, {'hidden': True})
        sheet.set_column('A:A', 3)
        sheet.set_column('D:D', 17)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 11)
