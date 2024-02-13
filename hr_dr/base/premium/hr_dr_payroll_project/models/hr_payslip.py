# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        analytic_distribution = self._get_project_analytic_lines(line)
        if line.salary_rule_id.id and line.salary_rule_id.analytic_account_id.id:
            analytic_distribution[line.salary_rule_id.analytic_account_id.id] = 100
        elif line.slip_id.contract_id.id and line.slip_id.contract_id.analytic_account_id.id:
            analytic_distribution[line.slip_id.contract_id.analytic_account_id.id] = 100
        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            # 'analytic_distribution': (line.salary_rule_id.analytic_account_id and {
            #     : 100}) or
            #                          (line.slip_id.contract_id.analytic_account_id.id and {
            #                              line.slip_id.contract_id.analytic_account_id.id: 100})
            'analytic_distribution': analytic_distribution
        }

    def _get_number_of_hours(self, date_from, date_to, contract_id):
        # Esta línea sería suficiente para el módulo de nóminas nativo de odoo.
        # return self.sum_worked_hours

        worked_days = self._get_worked_days(date_from, date_to, contract_id)
        hours_per_day = self.get_contract_hours_per_day()
        return worked_days * hours_per_day

    def _get_codes(self):
        """Busca en la configuración los códigos de reglas salariales definidos para realizar la desagregación por
        proyecto."""
        config_parameter = self.env['ir.config_parameter'].sudo()
        param = config_parameter.get_param('payroll.project.analytics.rules', default='')
        return [x.strip() for x in param.split(',')]

    def _get_project_analytic_lines(self, line):
        self.ensure_one()
        codes = self._get_codes()
        analytic_plan = 'Projects'
        employee_id = self.employee_id.id
        date_from = self.date_from
        date_to = self.date_to
        contract_id = self.contract_id

        analytic_distribution = {}
        if line.code in codes:
            number_of_hours = self._get_number_of_hours(date_from, date_to, contract_id)
            analytic_lines = self.env['account.analytic.line'].sudo().search([
                ('employee_id', '=', employee_id), ('date', '>=', date_from), ('date', '<=', date_to)])
                # ('plan_id.name', '=', analytic_plan)])

            for analytic_line in analytic_lines:
                if analytic_line.project_id.id and analytic_line.project_id.analytic_account_id.id:
                    analytic_account = analytic_line.project_id.analytic_account_id

                    if analytic_line.unit_amount > 0:
                        if analytic_account.id in analytic_distribution:
                            analytic_distribution[analytic_account.id] += analytic_line.unit_amount
                        else:
                            analytic_distribution[analytic_account.id] = analytic_line.unit_amount

            for key, val in analytic_distribution.items():
                if number_of_hours > 0:
                    analytic_distribution[key] = val * 100 / number_of_hours
            # analytic_distribution[analytic_account.id] = analytic_line.unit_amount * 100 / number_of_hours
        return analytic_distribution

    def get_contract_hours_per_day(self):
        self.ensure_one()
        hours_per_day = 0
        if self.contract_id.id:
            if self.contract_id.resource_calendar_id.id:
                hours_per_day = self.contract_id.resource_calendar_id.hours_per_day
        return hours_per_day


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_validate(self):
        payslip_done_result = self.mapped('slip_ids').filtered(lambda slip: slip.state not in ['draft', 'cancel']).action_payslip_done()
        self.action_close()
        return payslip_done_result