# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].sudo().search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'

    @staticmethod
    def format_long_date_sp(datetime_instance):
        """
        Recibe una fecha y devuelve su representación en forma de texto de la forma '[día] de [mes] de [año]' para el
        idioma español.
        """
        months = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
                  7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}

        return datetime_instance.strftime('%d de {} de %Y').format(months[datetime_instance.month])

    def print_work_certificate(self):
        if self.get_hr_dr_management_responsible() is None:
            message = _("Please install the 'Human talent management' module and "
                        "define the responsible of human talent or change the actual settings.")
            raise ValidationError(message)

        self.env['hr.work.certificate.history'].create({
            'type': 'without_income',
            'employee_id': self.id,
        })
        return self.env.ref('hr_dr_employee_certificates.action_work_certificate_report').report_action(self)

    def print_work_certificate_with_income(self):
        if self.get_hr_dr_management_responsible() is None:
            message = _(
                "Please install the 'Human talent management' module and "
                "define the responsible of human talent or change the actual settings.")
            raise ValidationError(message)

        # Buscar el último contrato pese a que este inactivo y tomar ese salario
        if self.get_wage() != 0:
            self.env['hr.work.certificate.history'].create({
                'type': 'with_income',
                'employee_id': self.id,
            })
            return self.env.ref('hr_dr_employee_certificates.action_work_certificate_with_income_report').report_action(
                self)
        else:
            raise ValidationError(
                _('The employee is not associated with a valid employment contract.'))
            # El colaborador no está asociado a un contrato de trabajo válido.

    @api.model
    def get_signature_mode(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        signature_mode = config_parameter.get_param('employee.certificates.signature.mode', default='')
        return signature_mode

    @api.model
    def get_wage(self):
        certificate_with_income_based_on = self.get_certificate_with_income_based_on()

        if certificate_with_income_based_on == 'salary':
            contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', self.id),
            ], order="date_start desc", limit=1)
            if contract_id:
                return contract_id.wage
            else:
                return 0
        elif certificate_with_income_based_on == 'payroll':
            payroll_to_analyze = self.get_payroll_to_analyze()
            salary_rule_to_analyze = self.get_salary_rule_to_analyze()
            limit = -1
            if payroll_to_analyze == 'last_three_payrolls':
                limit = 3
            elif payroll_to_analyze == 'last_six_payrolls':
                limit = 6
            elif payroll_to_analyze == 'last_nine_payrolls':
                limit = 9
            elif payroll_to_analyze == 'last_twelve_payrolls':
                limit = 12
            elif payroll_to_analyze == 'all_payroll':
                limit = -1

            if limit != -1:
                payslip_ids = self.env['hr.payslip'].sudo().search([
                    ('employee_id', '=', self.id),
                    ('state', 'in', ['done', 'paid'])], limit=limit, order='date_to desc')
                total_salary = 0
                for payslip in payslip_ids:
                    for line in payslip.line_ids:
                        if line.code == salary_rule_to_analyze:
                            total_salary = total_salary + line.total
                count_salary = len(payslip_ids)
                if count_salary != 0:
                    average_salary = round(total_salary / count_salary, 2)
                    return average_salary
                else:
                    return 0
            else:
                payslip_ids = self.env['hr.payslip'].sudo().search([
                    ('employee_id', '=', self.id),
                    ('state', 'in', ['done', 'paid'])], order='date_to desc')
                total_salary = 0
                for payslip in payslip_ids:
                    for line in payslip.line_ids:
                        if line.code == salary_rule_to_analyze:
                            total_salary = total_salary + line.total
                count_salary = len(payslip_ids)
                if count_salary != 0:
                    average_salary = round(total_salary / count_salary, 2)
                    return average_salary
                else:
                    return 0
        else:
            return 0

    def get_certificate_with_income_based_on(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "certificate.with.income.based_on", default='')

    def get_payroll_to_analyze(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "certificate.payroll.to.analyze", default='')

    def get_salary_rule_to_analyze(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "certificate.salary.rule.code.to.analyze", default='')