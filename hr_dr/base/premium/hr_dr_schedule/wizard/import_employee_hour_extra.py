# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd


class ImportEmployeeHourExtra(models.TransientModel):
    _name = 'import.employee.hour.extra'
    _description = 'Import employee hour extra'

    def action_import_employee_hour_extra(self):
        if not self.data:
            raise ValidationError(_('Para continuar debe cargar el archivo de horas extras.'))

        all = []
        found = []
        warning = []

        doc_import = xlrd.open_workbook(file_contents=base64.decodebytes(self.data))
        doc_import_sheet = doc_import.sheet_by_index(0)
        nrows_doc = doc_import_sheet.nrows
        for f in range(nrows_doc):
            if f >= 4:
                hr_employee_hour_extra_id = int(doc_import_sheet.cell_value(f, 0))
                employee_identification = doc_import_sheet.cell_value(f, 2)
                employee_reason = doc_import_sheet.cell_value(f, 6)
                all.append(employee_identification)
                employee = self.env['hr.employee'].search([('identification_id', '=', employee_identification)])
                if employee:
                    hr_employee_hour_extra = self.env['hr.employee.hour.extra'].browse(hr_employee_hour_extra_id)
                    if hr_employee_hour_extra:
                        if hr_employee_hour_extra.state in ['draft']:
                            if hr_employee_hour_extra.employee_id != employee:
                                raise ValidationError(
                                    _("Inconsistencias en el archivo. La hora extra en el sistema está asociada "
                                      "al colaborador {} y en el archivo está haciendo referencia al colaborador {}."
                                      .format(hr_employee_hour_extra.employee_id.display_name, employee.display_name)))

                            can_import = False
                            if self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_supervisor') \
                                    or self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_manager'):
                                can_import = True
                            elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_responsible'):
                                if self.env.user.employee_id.department_id == employee.department_id:
                                    can_import = True
                                else:
                                    raise ValidationError(
                                        _("Su usuario solo puede importar horas extras de colaboradores de "
                                          "su propio departamento. El colaborador {} no pertenece al departamento "
                                          "del colaborador asociado al usuario en sesión.".format(employee.display_name)))
                            elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_employee'):
                                if self.env.user.employee_id == employee:
                                    can_import = True
                                else:
                                    raise ValidationError(
                                        _("Su usuario no cuenta con los permisos suficientes para importar "
                                          "horas extras de otros colaboradores."))
                            else:
                                raise ValidationError(
                                    _("Su usuario no cuenta con los permisos suficientes "
                                      "para importar las horas extras."))
                            if can_import:
                                found.append(employee_identification)
                                hr_employee_hour_extra.employee_reason = employee_reason
                        else:
                            raise ValidationError(
                                _("Solo puede importar horas extras en estado borrador."))

        warning = set(all) - set(found)
        warning = sorted(warning)
        if warning:
            list = '\n'.join('* ' + w for w in warning)
            raise UserError(_('Las horas extras asociadas a los colaboradores con los siguientes números de '
                              'identificación no pudieron ser importadas:\n%s' % list))

        return True

    # Columns
    data = fields.Binary(string='Archivo', help='Seleccione el archivo de horas extras.')
