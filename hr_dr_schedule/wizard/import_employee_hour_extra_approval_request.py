# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd


class ImportEmployeeHourExtraApprovalRequest(models.TransientModel):
    _name = 'import.employee.hour.extra.approval.request'
    _description = 'Import employee hour extra approval request'

    def action_import_employee_hour_extra_approval_request(self):
        if not self.data:
            raise ValidationError(_('Para continuar debe cargar el archivo de aprobación de horas extras.'))

        all = []
        found = []
        warning = []

        doc_import = xlrd.open_workbook(file_contents=base64.decodebytes(self.data))
        doc_import_sheet = doc_import.sheet_by_index(0)
        nrows_doc = doc_import_sheet.nrows
        for f in range(nrows_doc):
            if f >= 5:
                employee_hour_extra_approval_request_detail_id = int(doc_import_sheet.cell_value(f, 0))
                employee_identification = doc_import_sheet.cell_value(f, 2)
                aprobado = doc_import_sheet.cell_value(f, 9)
                aprobado_h = doc_import_sheet.cell_value(f, 10)
                aprobado_m = doc_import_sheet.cell_value(f, 11)
                aprobado_s = doc_import_sheet.cell_value(f, 12)

                all.append(employee_identification)
                employee = self.env['hr.employee'].search([('identification_id', '=', employee_identification)])
                if employee:
                    employee_hour_extra_approval_request_detail = \
                        self.env['employee.hour.extra.approval.request.detail'].\
                        browse(employee_hour_extra_approval_request_detail_id)
                    if employee_hour_extra_approval_request_detail:
                        if employee_hour_extra_approval_request_detail.approval_request_id.state in ['draft']:
                            if employee_hour_extra_approval_request_detail.employee_id != employee:
                                raise ValidationError(
                                    _("Inconsistencias en el archivo. La hora extra en el sistema está asociada "
                                      "al colaborador {} y en el archivo está haciendo referencia al colaborador {}."
                                      .format(employee_hour_extra_approval_request_detail.employee_id.display_name,
                                              employee.display_name)))

                            can_import = False
                            if self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_supervisor') \
                                    or self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_manager'):
                                can_import = True
                            elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_responsible'):
                                if self.env.user.employee_id.department_id == employee.department_id:
                                    can_import = True
                                else:
                                    raise ValidationError(
                                        _("Su usuario solo puede importar una solicitud de aprobación de horas "
                                          "extras de colaboradores de su propio departamento. "
                                          "El colaborador {} no pertenece al departamento "
                                          "del colaborador asociado al usuario en sesión.".
                                          format(employee.display_name)))
                            elif self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_employee'):
                                if self.env.user.employee_id == employee:
                                    can_import = True
                                else:
                                    raise ValidationError(
                                        _("Su usuario no cuenta con los permisos suficientes para importar "
                                          "una solicitud de aprobación horas extras de otros colaboradores."))
                            else:
                                raise ValidationError(
                                    _("Su usuario no cuenta con los permisos suficientes para importar "
                                      "una solicitud de aprobación de horas extras."))
                            if can_import:
                                pass
                                found.append(employee_identification)
                                if aprobado != 0:
                                    employee_hour_extra_approval_request_detail.amount_approved_hd = aprobado
                                    employee_hour_extra_approval_request_detail.change_amount_approved_hd()
                                else:
                                    employee_hour_extra_approval_request_detail.amount_approved_h = aprobado_h
                                    employee_hour_extra_approval_request_detail.amount_approved_m = aprobado_m
                                    employee_hour_extra_approval_request_detail.amount_approved_s = aprobado_s
                        else:
                            raise ValidationError(
                                _("Solo puede importar una solicitud de aprobación de horas extras "
                                  "en estado borrador."))

        warning = set(all) - set(found)
        warning = sorted(warning)
        if warning:
            list = '\n'.join('* ' + w for w in warning)
            raise UserError(_('Las horas extras asociadas a los colaboradores con los siguientes números de '
                              'identificación no pudieron ser importadas:\n%s' % list))

        return True

    # Columns
    data = fields.Binary(string='Archivo', help='Seleccione el archivo de aprobación de horas extras.')
