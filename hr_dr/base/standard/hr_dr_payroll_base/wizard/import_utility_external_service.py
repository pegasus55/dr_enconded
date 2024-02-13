# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
import datetime


class ImportUtilityExternalService(models.TransientModel):
    _name = 'import.utility.external.service'
    _description = 'Import utility external service'
    _inherit = ['dr.base']

    def create_payment_utility_external_service(self,
                                                partner_id,
                                                worked_days,
                                                family_loads,
                                                judicial_withholding,
                                                permanent_part_time,
                                                hours_permanent_part_time,
                                                ruc_complementary_services_company,
                                                thirteenth_salary,
                                                fourteenth_salary,
                                                profits_previous_year,
                                                wage,
                                                reserve_funds,
                                                commissions,
                                                additional_cash_benefits,
                                                bonus_and_perks,
                                                utility_advance,
                                                payment_mode_living_wage):
        self.env['hr.payment.utility.external.service'].create({
            'payment_utility_id': self.payment_utility_id.id,
            'partner_id': partner_id.id,
            'worked_days': float(worked_days),
            'family_loads': int(family_loads),
            'judicial_withholding': int(judicial_withholding),
            'permanent_part_time': permanent_part_time,
            'hours_permanent_part_time': float(hours_permanent_part_time),
            'ruc_complementary_services_company': ruc_complementary_services_company,
            'thirteenth_salary': float(thirteenth_salary),
            'fourteenth_salary': float(fourteenth_salary),
            'profits_previous_year': float(profits_previous_year),
            'wage': float(wage),
            'reserve_funds': float(reserve_funds),
            'commissions': float(commissions),
            'additional_cash_benefits': float(additional_cash_benefits),
            'bonus_and_perks': float(bonus_and_perks),
            'utility_advance': float(utility_advance),
            'payment_mode_living_wage': payment_mode_living_wage,
        })

    def action_import_utility_external_service(self):
        if not self.data:
            raise ValidationError(_('To continue you must upload the external services personnel file.'))

        self.payment_utility_id.external_service_ids.unlink()

        doc_import = xlrd.open_workbook(file_contents=base64.decodebytes(self.data))
        sheets = doc_import.sheets()

        external_service_sheet = sheets[0]
        family_load_sheet = sheets[1]
        judicial_withholding_sheet = sheets[2]
        nrows_es = external_service_sheet.nrows
        for f in range(nrows_es):
            if f >= 1:
                partner_name = external_service_sheet.cell_value(f, 0)
                partner_surnames = external_service_sheet.cell_value(f, 1)
                partner_names = external_service_sheet.cell_value(f, 2)
                identification_type = external_service_sheet.cell_value(f, 3)
                partner_identification = external_service_sheet.cell_value(f, 4)
                partner_identification = str(partner_identification).split('.')[0]
                gender = external_service_sheet.cell_value(f, 5)
                occupation = external_service_sheet.cell_value(f, 6)
                occupation = str(occupation).split('.')[0]
                disability = external_service_sheet.cell_value(f, 7)
                payment_method = external_service_sheet.cell_value(f, 8)
                worked_days = external_service_sheet.cell_value(f, 9)
                family_loads = external_service_sheet.cell_value(f, 10)
                judicial_withholding = external_service_sheet.cell_value(f, 11)
                permanent_part_time = external_service_sheet.cell_value(f, 12)
                hours_permanent_part_time = external_service_sheet.cell_value(f, 13)
                if hours_permanent_part_time == '':
                    hours_permanent_part_time = 0
                ruc_complementary_services_company = external_service_sheet.cell_value(f, 14)
                ruc_complementary_services_company = str(ruc_complementary_services_company).split('.')[0]
                thirteenth_salary = external_service_sheet.cell_value(f, 15)
                fourteenth_salary = external_service_sheet.cell_value(f, 16)
                profits_previous_year = external_service_sheet.cell_value(f, 17)
                wage = external_service_sheet.cell_value(f, 18)
                reserve_funds = external_service_sheet.cell_value(f, 19)
                commissions = external_service_sheet.cell_value(f, 20)
                additional_cash_benefits = external_service_sheet.cell_value(f, 21)
                bonus_and_perks = external_service_sheet.cell_value(f, 22)
                utility_advance = external_service_sheet.cell_value(f, 23)
                payment_mode_living_wage = external_service_sheet.cell_value(f, 24)

                gender_result = ''
                if gender == "M":
                    gender_result = 'male'
                elif gender == "F":
                    gender_result = 'female'
                elif gender == "O":
                    gender_result = 'other'

                sector_table = self.env['hr.sector.table'].with_context(active_test=False).search([
                    ('IESS_code', '=', occupation)
                ], limit=1)
                if sector_table:
                    if not sector_table.active:
                        sector_table.active = True
                else:
                    raise ValidationError(_('There is no sector code {}.').format(occupation))

                disability_result = False
                if disability == "Si":
                    disability_result = True

                identification_type_id = False
                if identification_type == 'Cédula':
                    identification_type_id = self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False)
                elif identification_type == 'RUC':
                    identification_type_id = self.env.ref("l10n_ec.ec_ruc", raise_if_not_found=False)
                elif identification_type == 'Pasaporte':
                    identification_type_id = self.env.ref("l10n_ec.ec_passport", raise_if_not_found=False)
                elif identification_type == 'VAT':
                    identification_type_id = self.env.ref("l10n_latam_base.it_vat", raise_if_not_found=False)
                elif identification_type == 'Pasaporte extranjero':
                    identification_type_id = self.env.ref("l10n_latam_base.it_pass", raise_if_not_found=False)
                elif identification_type == 'Cédula Extranjera':
                    identification_type_id = self.env.ref("l10n_latam_base.it_fid", raise_if_not_found=False)
                elif identification_type == 'Desconocido':
                    identification_type_id = self.env.ref("l10n_ec.unknown", raise_if_not_found=False)

                permanent_part_time_result = False
                if permanent_part_time == "Si":
                    permanent_part_time_result = True

                partner = self.env['res.partner'].with_context(active_test=False).search([
                    ('vat', '=', partner_identification)
                ], limit=1)
                if partner:
                    partner.active = True
                    partner.is_external_service_personnel = True
                    partner.name = partner_name
                    partner.surnames = partner_surnames
                    partner.names = partner_names
                    partner.gender = gender_result
                    partner.occupation = sector_table.id
                    partner.disability = disability_result
                    if identification_type_id:
                        partner.l10n_latam_identification_type_id = identification_type_id.id
                    partner.payment_method = payment_method

                    partner.family_load_ids.unlink()
                    partner.judicial_withholding_ids.unlink()

                    self.create_payment_utility_external_service(
                        partner,
                        worked_days,
                        family_loads,
                        judicial_withholding,
                        permanent_part_time_result,
                        hours_permanent_part_time,
                        ruc_complementary_services_company,
                        thirteenth_salary,
                        fourteenth_salary,
                        profits_previous_year,
                        wage,
                        reserve_funds,
                        commissions,
                        additional_cash_benefits,
                        bonus_and_perks,
                        utility_advance,
                        payment_mode_living_wage
                    )
                else:
                    partner = self.env['res.partner'].create({
                        'name': partner_name,
                        'surnames': partner_surnames,
                        'names': partner_names,
                        'gender': gender_result,
                        'occupation': sector_table.id,
                        'disability': disability_result,
                        'l10n_latam_identification_type_id': identification_type_id.id if identification_type_id
                        else False,
                        'vat': partner_identification,
                        'is_external_service_personnel': True,
                        'payment_method': payment_method,
                    })
                    if partner:
                        self.create_payment_utility_external_service(
                            partner,
                            worked_days,
                            family_loads,
                            judicial_withholding,
                            permanent_part_time_result,
                            hours_permanent_part_time,
                            ruc_complementary_services_company,
                            thirteenth_salary,
                            fourteenth_salary,
                            profits_previous_year,
                            wage,
                            reserve_funds,
                            commissions,
                            additional_cash_benefits,
                            bonus_and_perks,
                            utility_advance,
                            payment_mode_living_wage
                        )
                    else:
                        raise ValidationError(_('An error occurred while creating the external service collaborator '
                                                'with identification number {}.').format(partner_identification))

        nrows_fl = family_load_sheet.nrows
        for f in range(nrows_fl):
            if f >= 1:
                partner_id_identification = family_load_sheet.cell_value(f, 0)
                partner_id_identification = str(partner_id_identification).split('.')[0]
                name = family_load_sheet.cell_value(f, 1)
                date_of_birth = family_load_sheet.cell_value(f, 2)
                date_of_birth_as_datetime = datetime.datetime(*xlrd.xldate_as_tuple(date_of_birth, doc_import.datemode))
                relationship = family_load_sheet.cell_value(f, 3)
                disability = family_load_sheet.cell_value(f, 4)
                disability_conadis = family_load_sheet.cell_value(f, 5)
                disability_conadis = str(disability_conadis).split('.')[0]
                disability_percentage = family_load_sheet.cell_value(f, 6)
                disability_description = family_load_sheet.cell_value(f, 7)
                id_type = family_load_sheet.cell_value(f, 8)
                identification = family_load_sheet.cell_value(f, 9)
                identification = str(identification).split('.')[0]
                insured = family_load_sheet.cell_value(f, 10)
                phone = family_load_sheet.cell_value(f, 11)
                phone = str(phone).split('.')[0]
                address = family_load_sheet.cell_value(f, 12)

                partner_associated = self.env['res.partner'].search([
                    ('vat', '=', partner_id_identification)
                ], limit=1)
                if not partner_associated:
                    raise ValidationError(
                        _('The partner with identification {} could not be located. The related family load is {}.').
                        format(partner_id_identification, name))

                id_type_id = False
                if id_type == 'Cédula':
                    id_type_id = self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False)
                elif id_type == 'RUC':
                    id_type_id = self.env.ref("l10n_ec.ec_ruc", raise_if_not_found=False)
                elif id_type == 'Pasaporte':
                    id_type_id = self.env.ref("l10n_ec.ec_passport", raise_if_not_found=False)
                elif id_type == 'VAT':
                    id_type_id = self.env.ref("l10n_latam_base.it_vat", raise_if_not_found=False)
                elif id_type == 'Pasaporte extranjero':
                    id_type_id = self.env.ref("l10n_latam_base.it_pass", raise_if_not_found=False)
                elif id_type == 'Cédula Extranjera':
                    id_type_id = self.env.ref("l10n_latam_base.it_fid", raise_if_not_found=False)
                elif id_type == 'Desconocido':
                    id_type_id = self.env.ref("l10n_ec.unknown", raise_if_not_found=False)

                insured_result = False
                if insured == "Si":
                    insured_result = True

                disability_result = False
                if disability == "Si":
                    disability_result = True

                self.env['res.partner.family.load'].create({
                    'name': name,
                    'date_of_birth': date_of_birth_as_datetime.date(),
                    'relationship': relationship,
                    'disability': disability_result,
                    'disability_conadis': disability_conadis,
                    'disability_percentage': disability_percentage,
                    'disability_description': disability_description,
                    'id_type': id_type_id.id if id_type_id else False,
                    'identification': identification,
                    'insured': insured_result,
                    'phone': phone,
                    'address': address,
                    'partner_id': partner_associated.id,
                })

        nrows_jw = judicial_withholding_sheet.nrows
        for f in range(nrows_jw):
            if f >= 1:
                partner_id_identification = judicial_withholding_sheet.cell_value(f, 0)
                partner_id_identification = str(partner_id_identification).split('.')[0]
                family_load_identification = judicial_withholding_sheet.cell_value(f, 1)
                family_load_identification = str(family_load_identification).split('.')[0]
                card_code = judicial_withholding_sheet.cell_value(f, 2)
                card_code = str(card_code).split('.')[0]
                judicial_process_number = judicial_withholding_sheet.cell_value(f, 3)
                judicial_process_number = str(judicial_process_number).split('.')[0]
                approval_identifier = judicial_withholding_sheet.cell_value(f, 4)
                approval_identifier = str(approval_identifier).split('.')[0]
                beneficiary_id_id_type = judicial_withholding_sheet.cell_value(f, 5)
                beneficiary_id_identification = judicial_withholding_sheet.cell_value(f, 6)
                beneficiary_id_identification = str(beneficiary_id_identification).split('.')[0]
                beneficiary_id_name = judicial_withholding_sheet.cell_value(f, 7)
                value = judicial_withholding_sheet.cell_value(f, 8)

                partner_associated = self.env['res.partner'].search([
                    ('vat', '=', partner_id_identification)
                ], limit=1)
                if not partner_associated:
                    raise ValidationError(
                        _('The partner with identification {} could not be located.').
                        format(partner_id_identification))

                family_load_associated = self.env['res.partner.family.load'].search([
                    ('identification', '=', family_load_identification)
                ], limit=1)
                if not family_load_associated:
                    raise ValidationError(
                        _('The family load with identification {} could not be located.').
                        format(family_load_identification))

                beneficiary_id_id_type_id = False
                if beneficiary_id_id_type == 'Cédula':
                    beneficiary_id_id_type_id = self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'RUC':
                    beneficiary_id_id_type_id = self.env.ref("l10n_ec.ec_ruc", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'Pasaporte':
                    beneficiary_id_id_type_id = self.env.ref("l10n_ec.ec_passport", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'VAT':
                    beneficiary_id_id_type_id = self.env.ref("l10n_latam_base.it_vat", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'Pasaporte extranjero':
                    beneficiary_id_id_type_id = self.env.ref("l10n_latam_base.it_pass", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'Cédula Extranjera':
                    beneficiary_id_id_type_id = self.env.ref("l10n_latam_base.it_fid", raise_if_not_found=False)
                elif beneficiary_id_id_type == 'Desconocido':
                    beneficiary_id_id_type_id = self.env.ref("l10n_ec.unknown", raise_if_not_found=False)

                beneficiary = self.env['res.partner'].with_context(active_test=False).search([
                    ('vat', '=', beneficiary_id_identification)
                ], limit=1)
                if beneficiary:
                    beneficiary.active = True
                    beneficiary.name = beneficiary_id_name
                    beneficiary.l10n_latam_identification_type_id = beneficiary_id_id_type_id.id if (
                        beneficiary_id_id_type_id) else False

                    self.env['res.partner.judicial.withholding'].create({
                        'partner_id': partner_associated.id,
                        'family_load_id': family_load_associated.id,
                        'card_code': card_code,
                        'judicial_process_number': judicial_process_number,
                        'approval_identifier': approval_identifier,
                        'beneficiary_id': beneficiary.id,
                        'representative_name': beneficiary.name,
                        'representative_id_type': beneficiary.l10n_latam_identification_type_id.id,
                        'representative_identification': beneficiary.vat,
                        'value': value,
                    })
                else:
                    beneficiary = self.env['res.partner'].create({
                        'name': beneficiary_id_name,
                        'l10n_latam_identification_type_id': beneficiary_id_id_type_id.id if beneficiary_id_id_type_id
                        else False,
                        'vat': beneficiary_id_identification,
                    })
                    if beneficiary:
                        self.env['res.partner.judicial.withholding'].create({
                            'partner_id': partner_associated.id,
                            'family_load_id': family_load_associated.id,
                            'card_code': card_code,
                            'judicial_process_number': judicial_process_number,
                            'approval_identifier': approval_identifier,
                            'beneficiary_id': beneficiary.id,
                            'representative_name': beneficiary.name,
                            'representative_id_type': beneficiary.l10n_latam_identification_type_id.id,
                            'representative_identification': beneficiary.vat,
                            'value': value,
                        })
        return True

    def _default_template(self):
        template_path = odoo.modules.module.get_resource_path(
            'hr_dr_payroll_base', 'import_template', 'Outside_service_staff_for_utilities.xlsx')
        with open(template_path, 'rb') as imp_sheet:
            file = imp_sheet.read()
        return file and base64.b64encode(file)

    def get_template(self):
        return {
            'name': 'Outside service staff for utilities',
            'type': 'ir.actions.act_url',
            'url': ("web/content/?model=" + self._name + "&id=" +
                    str(self.id) + "&filename_field=template_name&"
                                   "field=template&download=true&"
                                   "filename=Outside_service_staff_for_utilities.xlsx"),
            'target': 'self',
        }

    payment_utility_id = fields.Many2one('hr.payment.utility', string='Payment utility', ondelete='cascade',
                                         default=lambda self: self._context.get('active_id'))
    data = fields.Binary(string='Archivo', help='Select the external services staff file.')
    template = fields.Binary(string='Template', default=_default_template)
    template_name = fields.Char(default='Outside_service_staff_for_utilities.xlsx')