# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
from xlrd.xldate import xldate_as_datetime


class ImportInput(models.TransientModel):
    _inherit = 'import.input'

    def action_import_input(self):
        if not self.data:
            raise ValidationError(_('To continue you must upload the input file.'))

        doc_import = xlrd.open_workbook(file_contents=base64.decodebytes(self.data))
        doc_import_sheet = doc_import.sheet_by_index(0)
        nrows_doc = doc_import_sheet.nrows
        for f in range(nrows_doc):
            if f >= 1:
                date = doc_import_sheet.cell_value(f, 0)
                payslip_input_type_code = doc_import_sheet.cell_value(f, 2)
                identification = doc_import_sheet.cell_value(f, 4)
                identification = str(identification).split('.')[0]
                amount = doc_import_sheet.cell_value(f, 5)

                employee_id = self.env['hr.employee'].search([('identification_id', '=', str(identification))])
                if employee_id:
                    payslip_input_type_id = self.env['hr.payslip.input.type'].search(
                        [('code', '=', str(payslip_input_type_code))])
                    if payslip_input_type_id:

                        date = xldate_as_datetime(date, doc_import.datemode)

                        self.env['hr.input'].create({
                            'date': date,
                            'payslip_input_type_id': payslip_input_type_id.id,
                            'employee_id': employee_id.id,
                            'amount': float(amount),
                        })
                    else:
                        raise ValidationError(
                            _('The code {} does not belong to any type of active input.').format(
                                str(payslip_input_type_code)))
                else:
                    raise ValidationError(
                        _('The identification number {} does not belong to any active collaborator.').format(
                            identification))
        return True