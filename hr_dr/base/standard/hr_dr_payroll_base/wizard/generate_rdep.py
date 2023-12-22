# -*- coding: utf-8 -*-

import base64
import io
import os
import logging

from lxml import etree
from lxml.etree import DocumentInvalid
from jinja2 import Environment, FileSystemLoader

from odoo import fields, models, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class AccountRDEP(dict):
    """
    representacion del RDEP
    >>> rdep.campo = 'valor'
    >>> rdep['campo']
    'valor'
    """

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, item, value):
        if item in self.__dict__:
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)


class GenerateRDEP(models.TransientModel):
    _name = 'generate.rdep'
    _description = _('Generate RDEP')

    def find_employees(self):
        employee_ids = self.env['hr.employee'].with_context(active_test=False).search([
            ('employee_admin', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['affiliate', 'temporary', 'unemployed', 'retired'])
        ])
        return employee_ids

    def get_worked_days(self, employee, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')

        worked_days = 0

        for payslip in payslip_ids:
            days = payslip.worked_days * payslip.daily_hours / payslip.standard_daily_hours
            if payslip.reduction_of_working_hours:
                days = days * (100 - payslip.percentage_reduction_of_working_hours) / 100
            worked_days += days
        return worked_days

    def get_income(self, employee, code, date_from, date_to):
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from')
        value = 0
        mode = self.get_mode_by_code(code)
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if mode == 'by_rules':
                    if line.code in self.get_rule_by_process(code):
                        value += line.total
                elif mode == 'by_categories':
                    if line.category_id.code in self.get_category_by_process(code) and \
                            line.code not in self.get_rule_excluded_by_process(code):
                        value += line.total
        return value

    def get_mode_by_code(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.mode
        else:
            return ""

    def get_rule_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.salary_rule_code.split()
        else:
            return []

    def get_rule_excluded_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.salary_rule_code_excluded.split()
        else:
            return []

    def get_category_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.category_code.split()
        else:
            return []

    def _get_personal_expenses(self, employee_id):
        year = int(self.year)
        personal_expense = self.env['hr.personal.expense'].sudo().search([
            ('employee_id', '=', employee_id),
            ('rent_tax_table_id.fiscal_year', '=', year),
            ('state', '=', 'done')], limit=1)
        return personal_expense

    def is_beneficiary_of_galapagos(self, employee_id):
        if employee_id.address_home_id.state_id.region == 'island':
            return 'SI'
        else:
            return 'NO'

    def _get_code_identification_type(self, employee_id):
        return employee_id.identification_type.code

    def _get_residence(self, employee_id):
        return employee_id.residence

    def _get_code_country_of_residence(self, employee_id):
        return employee_id.country_of_residence.l10n_ec_code_ats

    def get_agreement_applies(self, employee_id):
        if employee_id.residence == '01':
            return 'NA'
        else:
            return employee_id.agreement_applies

    def get_disability_first_level(self, employee_id):
        result = {}
        for fl in employee_id.family_load_ids:
            if ((fl.relationship == 'spouses' or fl.relationship == 'wife' or fl.relationship == 'husband' or fl.relationship == 'cohabitant' or
                 fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter') and
                    fl.disability and fl.employee_dependent):
                result['type'] = '04'
                result['percent'] = fl.disability_percentage
                result['identification_type'] = fl.id_type.code
                result['identification'] = fl.identification
                return result
        return result

    def get_disability_any_level(self, employee_id):
        result = {}
        for fl in employee_id.family_load_ids:
            if fl.disability and fl.employee_dependent:
                result['type'] = '03'
                result['percent'] = fl.disability_percentage
                result['identification_type'] = fl.id_type.code
                result['identification'] = fl.identification
                return result
        return result

    def _get_disability(self, employee_id):
        result = {}
        if employee_id.disability:
            result['type'] = '02'
            result['percent'] = employee_id.disability_percentage
            result['identification_type'] = 'N'
            result['identification'] = '999'
        elif len(self.get_disability_any_level(employee_id)) > 0:
            result = self.get_disability_any_level(employee_id)
        elif len(self.get_disability_first_level(employee_id)) > 0:
            result = self.get_disability_first_level(employee_id)
        else:
            result['type'] = '01'
            result['percent'] = 0
            result['identification_type'] = 'N'
            result['identification'] = '999'
        return result

    def _get_wages_and_salaries_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-S", date_from, date_to)

    def _get_commissions_bonuses_and_other_taxable_income_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-SCB_OIG", date_from, date_to)

    def _get_utility_by_year_and_employee(self, employee_id):
        utility_line = self.env['hr.payment.utility.line'].sudo().search([
            ('fiscal_year', '=', int(self.year)),
            ('state_utility', 'in', ['done']),
            ('employee_id', '=', employee_id.id),
        ], limit=1)
        if utility_line:
            return utility_line.total_utility
        else:
            return 0

    def _get_d13_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-D13", date_from, date_to)

    def _get_d14_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-D14", date_from, date_to)

    def _get_reserve_funds_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-FR", date_from, date_to)

    def _get_living_wage_yearly(self, employee_id):
        living_wage = self.env['pay.living.wage.line'].search([
            ('fiscal_year', '=', int(self.year)),
            ('employee_id', '=', employee_id.id),
            ('state', 'in', ['paid'])], limit=1)
        if living_wage:
            return living_wage.value
        else:
            return 0

    def _get_oidr_not_constitute_taxed_income_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-OIRDNCRG", date_from, date_to)

    def _get_income_taxed_with_this_employer_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        pass

    def _get_type_net_salary_system(self, employee_id):
        return employee_id.type_net_salary_system

    def _get_personal_contribution_IESS_with_this_employer_yearly(self, employee_id):
        date_from = datetime.utcnow().date() + relativedelta(day=1, month=1, year=int(self.year))
        date_to = datetime.utcnow().date() + relativedelta(day=31, month=12, year=int(self.year))
        return self.get_income(employee_id, "RDEP-APIESSEE", date_from, date_to)

    def personal_expense_by_category_code(self, employee_id, codes):
        result = 0
        personal_expenses = self._get_personal_expenses(employee_id)
        for detail in personal_expenses.expenses_ids:
            if detail.personal_expenses_category_id.code in codes:
                result = detail.amount
        return result










    def check_tax(self, value):
        obj_income_id = self.env['hr.income.tax']
        income_id = obj_income_id.search([('amount','<=',value),('amount_to','>=',value)])
        amount = value - income_id.amount
        amount = (amount * (income_id.excess_tax_amount / 100)) + income_id.tax_amount
        return amount

    def _get_employee(self):
        # TODO Revisar
        employee_ids = self.find_employees()
        data = []
        for employee in employee_ids:
            personal_expenses = self._get_personal_expenses(employee.id)

            data.append({
                'benGalpg': self.is_beneficiary_of_galapagos(employee),
                'tipIdRet': self._get_code_identification_type(employee),
                'idRet': employee.identification_id,
                'apellidoTrab': employee.surnames,
                'nombreTrab':  employee.names,
                'estab': self.establishment_number,
                'residenciaTrab': self._get_residence(employee),
                'paisResidencia': self._get_code_country_of_residence(employee),
                'aplicaConvenio': self.get_agreement_applies(employee),
                'tipoTrabajDiscap': self._get_disability(employee)['type'],
                'porcentajeDiscap': self._get_disability(employee)['percent'],
                'tipIdDiscap': self._get_disability(employee)['identification_type'],
                'idDiscap': self._get_disability(employee)['identification'],
                'suelSal': '%.2f' % self._get_wages_and_salaries_yearly(employee),
                'sobSuelComRemu': '%.2f' % self._get_commissions_bonuses_and_other_taxable_income_yearly(employee),
                'partUtil': '%.2f' % self._get_utility_by_year_and_employee(employee),
                'intGrabGen': personal_expenses.income_other_employers if personal_expenses else 0,
                'impRentEmpl': '%.2f' % personal_expenses.amount_detained_employee if personal_expenses else 0, # TODO
                'decimTer': '%.2f' % self._get_d13_yearly(employee),
                'decimCuar': '%.2f' % self._get_d14_yearly(employee),
                'fondoReserva': '%.2f' % self._get_reserve_funds_yearly(employee),
                'salarioDigno': '%.2f' % self._get_living_wage_yearly(employee),
                'otrosIngRenGrav': '%.2f' % self._get_oidr_not_constitute_taxed_income_yearly(employee),
                'ingGravConEsteEmpl': '%.2f' % self._get_income_taxed_with_this_employer_yearly(employee), # TODO
                'sisSalNet': self._get_type_net_salary_system(employee),
                'apoPerIess': '%.2f' % self._get_personal_contribution_IESS_with_this_employer_yearly(employee),
                'aporPerIessConOtrosEmpls': '%.2f' % personal_expenses.IESS_other_employer if personal_expenses else 0,
                'deducVivienda': '%.2f' % self.personal_expense_by_category_code(['V']),
                'deducSalud': '%.2f' % self.personal_expense_by_category_code(['S']),
                'deducEducartcult': '%.2f' % self.personal_expense_by_category_code(['E']),
                'deducAliement': '%.2f' % self.personal_expense_by_category_code(['A']),
                'deducVestim': '%.2f' % self.personal_expense_by_category_code(['VE']),
                'deduccionTurismo': '%.2f' % self.personal_expense_by_category_code(['TL']),
                'exoDiscap': '%.2f' % personal_expenses.disability_deduction if personal_expenses else 0,
                'exoTerEd': '%.2f' % personal_expenses.third_age_deduction if personal_expenses else 0,

                'basImp': '%.2f' % personal_expenses.tax_base if personal_expenses else 0,
                'impRentCaus': '%.2f' % personal_expenses.profit_tax if personal_expenses else 0,
                'valRetAsuOtrosEmpls': '%.2f' % personal_expenses.amount_other_employer if personal_expenses else 0,
                'valImpAsuEsteEmpl': '%.2f' % (personal_expenses.amount_this_employer
                                        + personal_expenses.second_amount_this_employer) if personal_expenses else 0,
                'valRet': '%.2f' % (personal_expenses.amount_this_employer_posted
                                    + personal_expenses.second_amount_this_employer_posted
                                    + personal_expenses.amount_detained_employee_posted) if personal_expenses else 0,
            })
        return data

    def render_xml(self, rdep):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(template_path))
        template_rdep = env.get_template('RDEP.xml')
        return template_rdep.render(rdep)

    def validate_document(self, rdep, error_log=False):
        file_path = os.path.join(os.path.dirname(__file__), 'xsd/RDEP.xsd')
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        root = etree.fromstring(rdep.encode())
        ok = True
        if self.validate:
            try:
                xmlschema.assertValid(root)
            except DocumentInvalid:
                ok = False
        return ok, xmlschema

    def action_generate_rdep(self):
        rdep = AccountRDEP()
        year = self.year
        ruc = self.company_id.vat
        rdep.employees = self._get_employee()
        rdep.company = \
            {
                'ruc': self.company_id.vat,
                'year': self.year
            }
        rdep_rendered = self.render_xml(rdep)
        ok, schema = self.validate_document(rdep_rendered)
        buf = io.StringIO()
        buf.write(rdep_rendered)
        out = base64.encodebytes(buf.getvalue().encode('utf-8')).decode()
        logging.error(out)
        buf.close()
        buf_error = io.StringIO()
        for err in schema.error_log:
            buf_error.write(err.message+'\n')
        out_error = base64.encodebytes(buf_error.getvalue().encode())
        buf_error.close()
        name = "%s%s.xml" % (
            "RDEP",
            year
        )
        data2save = {
            'state': ok and 'ready' or 'error',
            'xml_file': out,
            'xml_file_name': name
        }
        if not ok:
            data2save.update({
                'error_file': out_error,
                'error_file_name': 'ERRORES.txt'
            })
        self.write(data2save)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'generate.rdep',
            'view_mode': ' form',
            'view_type': ' form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    year = fields.Char('Fiscal year', size=4, default=date.today().year)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    establishment_number = fields.Char('Establishment number', size=3, required=True, default='001')
    xml_file_name = fields.Char('XML file name', size=50, readonly=True)
    xml_file = fields.Binary('XML file')
    error_file_name = fields.Char('Error file name', size=50, readonly=True)
    error_file = fields.Binary('Error file')
    validate = fields.Boolean('Validate')
    status = fields.Selection(
        [
            ('draft', _('Draft')),
            ('ready', _('Ready')),
            ('error', _('Error'))
        ],
        string='Status', default='draft')