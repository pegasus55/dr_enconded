# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from datetime import datetime, timedelta
from dateutil import relativedelta
from odoo.exceptions import UserError, ValidationError
import math

APPROVED_STATES = ['open', 'pending', 'close']


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'dr.license.base']
    _order = 'date_from desc, employee_id'

    def _get_base_local_dict(self):
        """Adicionando self al objeto para llamar en las reglas salariales métodos de esta clase (
        como self._get_sick_subsidy_days(code) o self._get_last_overdraft())."""
        vals = super(HrPayslip, self)._get_base_local_dict()
        vals.update({'self': self})
        return vals

    def _get_inputs(self):
        inputs_ids = self.env['hr.input'].search([
            ('company_id', '=', self.env.company.id),
            ('date', '<=', self.date_to),
            ('date', '>=', self.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'available')
        ])
        return inputs_ids

    def _get_inputs_by_code(self, code):
        inputs_ids = self.env['hr.input'].search([
            ('company_id', '=', self.env.company.id),
            ('date', '<=', self.date_to),
            ('date', '>=', self.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'available'),
            ('code', '=', code),
        ])
        return inputs_ids

    def compute_sheet(self):
        self.validate_license()
        for rec in self:
            results = rec._get_inputs()
            rec.input_line_ids.unlink()

            for result in results:
                create = 1
                for line in rec.input_line_ids:
                    if line.code == result.code:
                        line.amount = line.amount + result.amount
                        line.input_ids = [(4, result.id)]
                        create = 0
                        break
                if create:
                    rec.input_line_ids.create({
                        'name': result.payslip_input_type_id.name,
                        'input_type_id': result.payslip_input_type_id.id,
                        'amount': result.amount,
                        'input_ids': [result.id],
                        'payslip_id': rec.id,
                        'judicial_withholding_id': result.judicial_withholding_id.id
                    })

            for result in rec.contract_id.input_ids:
                create = 1
                for line in rec.input_line_ids:
                    if line.code == result.code:
                        line.amount = line.amount + result.amount
                        line.input_ids = [(4, result.id)]
                        create = 0
                        break
                if create:
                    rec.input_line_ids.create({
                        'name': result.input_type_id.name,
                        'input_type_id': result.input_type_id.id,
                        'amount': result.amount,
                        'payslip_id': rec.id,
                        'judicial_withholding_id': result.judicial_withholding_id.id
                    })

        super(HrPayslip, self).compute_sheet()

    def _get_payslip_lines(self):
        """Heredado para adicionar a las líneas de nómina los beneficiarios, cuando estos existan en los inputs."""
        result = super(HrPayslip, self)._get_payslip_lines()
        for payslip in self:
            for line in filter(lambda x: x['slip_id'] == payslip.id, result):
                for input in payslip._get_inputs():
                    if line['code'] == input.code and input.judicial_withholding_id:
                        line.update({'judicial_withholding_id': input.judicial_withholding_id.id})
                    if (input.payslip_input_type_id.associated_rules and
                            line['code'] in input.payslip_input_type_id.associated_rules.split(',')
                            and input.judicial_withholding_id):
                        line.update({'judicial_withholding_id': input.judicial_withholding_id.id})
                for input in payslip.contract_id.input_ids:
                    if line['code'] == input.code and input.judicial_withholding_id:
                        line.update({'judicial_withholding_id': input.judicial_withholding_id.id})
                    if (input.input_type_id.associated_rules and
                            line['code'] in input.input_type_id.associated_rules.split(',')
                            and input.judicial_withholding_id):
                        line.update({'judicial_withholding_id': input.judicial_withholding_id.id})
        return result

    @api.model
    def get_sbu_by_year(self, year):
        sbu = self.env['hr.sbu'].sudo().search([
            ('fiscal_year', '=', year),
        ], limit=1)
        if sbu:
            return sbu.value
        else:
            return 0

    @api.depends('date_from')
    def _get_unified_basic_salary(self):
        """
        Este método devuelve el salario basico unificado con base a la fecha inicial de la nómina
        """
        for payslip in self:
            payslip.unified_basic_salary = self.get_sbu_by_year(payslip.date_from.year)
        return True

    @api.model
    def _get_worked_days(self, date_from, date_to, contract_id):
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
        else:
            date_from = datetime.strptime(date_from.isoformat(), '%Y-%m-%d')

        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
        else:
            date_to = datetime.strptime(date_to.isoformat(), '%Y-%m-%d')

        if contract_id:
            if not contract_id.date_start:
                raise UserError(_('Please enter the contract start date to continue.'))
            else:
                contract_date_start = contract_id.date_start
        else:
            contract_date_start = '%s-%s-01' % (date_from.year, date_from.month)

        date_start_contract = None
        if isinstance(contract_date_start, str):
            date_start_contract = datetime.strptime(contract_date_start, '%Y-%m-%d')
        else:
            date_start_contract = datetime.strptime(contract_date_start.isoformat(), '%Y-%m-%d')

        date_end_contract = False
        if contract_id and contract_id.date_end:
            date_end_contract = datetime.strptime(contract_id.date_end.isoformat(), '%Y-%m-%d')

        if date_start_contract > date_from:
            date_from = date_start_contract

        if date_end_contract:
            if date_end_contract < date_to:
                date_to = date_end_contract

        worked_days = date_to.day
        if date_to.month == 2 and not date_end_contract:
            if date_to.year % 4:
                worked_days += 2
            else:
                worked_days += 1
        elif date_to.day == 31:
            worked_days = 30
        worked_days -= date_from.day - 1

        return worked_days

    def get_calendar_days(self):
        """Calcula los días calendario como la cantidad de días entre el inicio y el fin del periodo de nómina
        (incluyendo ambos días) o los días del periodo que el empleado haya estado trabajando según su contrato."""
        self.ensure_one()
        slip_date_from = self.date_from
        slip_date_to = self.date_to
        if self.contract_id.id:
            contract_date_from = self.contract_id.date_start
            contract_date_to = self.contract_id.date_end
            date_from = slip_date_from if contract_date_from <= slip_date_from else contract_date_from
            if contract_date_to and contract_date_to < slip_date_to:
                date_to = contract_date_to
            else:
                date_to = slip_date_to
        else:
            date_from = slip_date_from
            date_to = slip_date_to

        self.calendar_days_in_month = (date_to - date_from).days + 1

    def have_overdraft_in_last_payslip(self):
        """Obtiene el valor del Sobregiro rol declarado en la nómina anterior."""
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from desc', limit=1)
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'SOBREGIRO' and line.total > 0:
                    return True
        return False

    def _get_last_overdraft(self):
        """Obtiene el valor del Sobregiro rol declarado en la nómina anterior."""
        payslip_ids = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid'])
        ], order='date_from desc', limit=1)
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == 'SOBREGIRO':
                    return line.total
        return 0

    def have_fortnight(self):
        obj_fortnight = self.env['hr.fortnight']
        fortnight = obj_fortnight.search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ])
        if fortnight:
            return True
        return False

    def _get_fortnight(self):
        obj_fortnight = self.env['hr.fortnight']
        fortnight = obj_fortnight.search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ])
        if fortnight:
            return sum(line.amount for line in fortnight)
        return 0

    def _get_sick_subsidy_days(self, salary_rule):
        """Obtiene la cantidad de días de subsidio."""
        value = 0
        input_ids = self.env['hr.input'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '<=', self.date_to),
            ('date', '>=', self.date_from),
            ('state', '=', 'available'),
            ('code', '=', 'SUBSIDIO_ENFERMEDAD')
        ])
        for input in input_ids:
            if salary_rule == 'SUBSIDIO_ENFERMEDAD':
                if input.amount - 3 > 0:
                    value = value + (input.amount - 3)
            elif salary_rule == 'SUBSIDIO_ENFERMEDAD_INFO_25':
                if input.amount - 3 > 0:
                    value = value + (input.amount - 3)
            elif salary_rule == 'SUBSIDIO_ENFERMEDAD_INFO_100':
                if input.amount - 3 > 0:
                    value = value + 3
                else:
                    value = value + input.amount
        return value

    def get_legal_years_months_days(self, date_start, date_end):
        """
        Método auxiliar para centralizar el cómputo de deltas de tiempo
        @date_start fecha inicio
        @date_end fecha final
        """
        if not date_start or not date_end:
            return 0, 0, 0

        if not isinstance(date_start, str):
            date_start = datetime.strptime(date_start.isoformat(), '%Y-%m-%d')
        else:
            date_start = datetime.strptime(date_start, '%Y-%m-%d')

        # A la fecha final se suma 1 día, de esta forma:
        # - Cuando el empleado trabajó del 1ene2017 al 1ene2017 le dará 1 día
        # - Cuando el empleado trabajó del 1ene2017 al 31ene2017 le dará 1 mes, 0 días

        if not isinstance(date_end, str):
            date_end = datetime.strptime(date_end.isoformat(), '%Y-%m-%d') + timedelta(days=1)
        else:
            date_end = datetime.strptime(date_end, '%Y-%m-%d') + timedelta(days=1)

        rd = relativedelta.relativedelta(date_end, date_start)
        return rd.years, rd.months, rd.days

    def normalize_years_months_days(self, years, months, legal_days):
        """
        Normalizamos el cómputo, por ejemplo 13 meses se convierten a 1 año y 1 mes
        """
        if legal_days > 30:
            months += int(legal_days / 30)
            legal_days = legal_days % 30  # El saldo de la division
        if months > 12:
            years += int(months / 12)
            months = months % 12  # El saldo de la division
        if months == 12:
            years += int(months / 12)
            months = months % 12  # El saldo de la division
        return years, months, legal_days

    @api.depends('employee_id', 'date_to')
    def _get_time_in_service(self):
        """
        Computa por los años, meses y días que un empleado ha trabajado para la empresa
        a la fecha de corte de la nómina.
        """
        for payslip in self:
            years = 0
            months = 0
            days = 0

            self.env['hr.historical.provision'].sudo().search([])

            # Se añade el tiempo de los contratos viejos
            # Se obtienen todos los contratos anteriores a la fecha seleccionada
            previous_contract_ids = self.env['hr.contract'].search([('employee_id', '=', payslip.employee_id.id),
                                                                    ('date_end', '<=', payslip.contract_id.date_start),
                                                                    ('state', 'in', APPROVED_STATES),
                                                                    ('id', '!=', payslip.contract_id.id),
                                                                    ],
                                                                   order='date_end')
            for previous in previous_contract_ids:
                years_previous, months_previous, days_previous = payslip.get_legal_years_months_days(
                    previous.date_start,
                    previous.date_end)
                years += years_previous
                months += months_previous
                days += days_previous
            # Se añade el tiempo del contrato vigente (el que está en la nómina)
            # en este caso no validamos que el contrato este aprobado pues es posible que el usuario haga
            # la nómina y luego anule el contrato para pruebas por ejemplo, en este caso es deseable que
            # si se lo considere para el tiempo
            years_current, months_current, days_current = payslip.get_legal_years_months_days(
                payslip.contract_id.date_start, payslip.date_to)
            years += years_current
            months += months_current
            days += days_current
            # Normalizamos el cómputo, por ejemplo 13 meses se convierten a 1 año y 1 mes
            years, months, days = payslip.normalize_years_months_days(years, months, days)
            payslip.years_in_service = years
            payslip.months_in_service = months
            payslip.days_in_service = days

    @api.depends('employee_id', 'date_to')
    def _get_number_service_months(self):
        """
        Util para el cálculo del fondo de reserva. Devuelve un entero con el número de meses que
        ha trabajado el empleado hasta el corte de la nómina, notas:
        - Una fracción de mes cuenta como mes
        - Si encuentra dos contratos distintos que se solapan en el mismo mes va a asumir
          que cuentan como dos meses.
        """
        for payslip in self:
            payslip.number_service_months = payslip.years_in_service * 12 + \
                                            payslip.months_in_service + \
                                            int(math.ceil(payslip.days_in_service / 30.0))
            # se usa 30.0 para convertir a flotante

    @api.depends('employee_id', 'date_to')
    def _get_days_to_pay_reserve_fund(self):
        """
        Campo auxiliar para el cómputo de fondos de reserva en el décimo tercer mes
        Para el décimo tercer mes retorna el número de días que se debe pagar por
        fondo de reserva, por ejemplo:

        Para la nómina del 28 de febrero 2018:
        - Para un empleado que ingreso un 01 de febr. 2017 retornará 30 días (pago completo)
        - Para un empleado que ingreso un 02 de febr. 2017 retornará 29 días
        - Para un empleado que ingreso un 03 de febr. 2017 retornará 28 días
        - Para un empleado que ingreso un 15 de febr. 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de febr. 2017 retornará 14 días
        - Para un empleado que ingreso un 27 de febr. 2017 retornará 04 días
        - Para un empleado que ingreso un 28 de febr. 2017 retornará 03 días

        Para la nómina del 30 de marzo 2018:
        - Para un empleado que ingreso un 01 de marzo 2017 retornará 30 días (pago completo)
        - Para un empleado que ingreso un 02 de marzo 2017 retornará 29 días
        - Para un empleado que ingreso un 15 de marzo 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de marzo 2017 retornará 14 días
        - Para un empleado que ingreso un 29 de marzo 2017 retornará 02 días
        - Para un empleado que ingreso un 30 de marzo 2017 retornará 01 días
        - Para un empleado que ingreso un 31 de marzo 2017 retornará 01 días

        Para la nómina del 30 de abril 2018:
        - Para un empleado que ingreso un 01 de abril 2017 retornará 30 días (pago completo)
        - Para un empleado que ingreso un 02 de abril 2017 retornará 29 días
        - Para un empleado que ingreso un 15 de abril 2017 retornará 16 días
        - Para un empleado que ingreso un 17 de abril 2017 retornará 14 días
        - Para un empleado que ingreso un 29 de abril 2017 retornará 02 días
        - Para un empleado que ingreso un 30 de abril 2017 retornará 01 días
        """
        if self.number_service_months < 13:
            days_to_pay_reserve_fund = 0
        elif self.number_service_months == 13:
            # Los días que me sobran del último mes, pero máximo 30 días ya que la formula en la regla salarial
            # de fondo de reserva la divide para 30 días.
            date_end = self.date_to
            days_in_service = self.days_in_service
            if self.days_in_service == 0:
                # En este caso si son 13 meses entonces es 1 año y 1 mes, osea 30 dÍas
                days_in_service = 30
            elif date_end.month == 2:  # febrero
                if date_end.year % 4:
                    # tiene 28 dias
                    days_in_service += 2
                else:  # Año bisiesto, tiene 29 días
                    days_in_service += 1
            elif date_end.day == 31:
                days_in_service = max(1, days_in_service - 1)
            days_to_pay_reserve_fund = min(30, days_in_service)
        else:  # Mayor que 13 meses
            days_to_pay_reserve_fund = 30

        self.days_to_pay_reserve_fund = days_to_pay_reserve_fund

    # @api.onchange('date_to')
    # def onchange_date_to(self):
    #     """
    #     Invocamos el método '_get_worked_days' en el onchange del campo 'date_to' para obtener los días trabajados.
    #     """
    #
    #     self.worked_days = self._get_worked_days(self.date_from, self.date_to, self.contract_id)
    #     self._get_days_to_pay_reserve_fund()

    @api.onchange('date_from', 'date_to', 'contract_id')
    def onchange_fields_affect_days_worked(self):
        if self.date_from and self.date_to and self.contract_id:
            self.worked_days = self._get_worked_days(self.date_from, self.date_to, self.contract_id)
        self._get_days_to_pay_reserve_fund()
        self.get_calendar_days()

    @api.onchange('employee_id')
    def onchange_employee(self):
        for rec in self:
            rec._compute_struct_id()
            rec.worked_days = rec._get_worked_days(rec.date_from, rec.date_to, rec.contract_id)
            rec._get_days_to_pay_reserve_fund()
            rec.get_calendar_days()
            rec.onchange_contract_id()

    @api.depends('contract_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.contract_id.struct_id

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id:
            self.daily_hours = self.contract_id.daily_hours
            self.standard_daily_hours = self.contract_id.standard_daily_hours
            self.reduction_of_working_hours = self.contract_id.reduction_of_working_hours
            self.percentage_reduction_of_working_hours = self.contract_id.percentage_reduction_of_working_hours

    @api.depends('line_ids.total')
    def _compute_basic_net(self):
        line_values = (self._origin)._get_line_values(['SALARIO_NOMINAL', 'SUBT_NETO'])
        for payslip in self:
            payslip.basic_wage = line_values['SALARIO_NOMINAL'][payslip._origin.id]['total']
            payslip.net_wage = line_values['SUBT_NETO'][payslip._origin.id]['total']

    @api.depends('employee_id', 'date_from')
    def _get_personal_expenses(self):
        for rec in self:
            rec.employee_information = False
            if rec.employee_id and rec.date_from:
                year = rec.date_from.year
                personal_expenses = self.env['hr.personal.expense'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id), ('rent_tax_table_id.fiscal_year', '=', year),
                    ('state', '=', 'done')], limit=1)
                rec.employee_information = personal_expenses

    def action_payslip_done(self):
        super(HrPayslip, self).action_payslip_done()
        # Recalculando el RDEP.
        if self.employee_information.id:
            self.employee_information._compute_amount()

    def action_print_payslip(self):
        report = super(HrPayslip, self).action_print_payslip()
        return {
            'name': _("Electronic signature"),
            'type': 'ir.actions.act_window',
            'res_model': 'dr_signature.check.passphrase.wizard',
            'context': {'fw_report': report},
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_assets_liquidation(self):
        assets_liquidation = self.env['hr.assets.liquidation'].sudo().search([('payslip_id', '=', self.id)], limit=1)
        if not assets_liquidation.id:
            raise ValidationError('No se puede hallar el modelo de liquidación de haberes.')

        return self.env.ref('hr_dr_payroll_enterprise.assets_liquidation_report').report_action(assets_liquidation)

    # def _compute_liquidation_form(self):
    #     for rec in self:
    #         rec.liquidation = False
    #         if rec.is_liquidation_payslip:
    #             assets_liquidation_form = self.env['hr.assets.liquidation'].sudo().search(
    #                 [('payslip_id', '=', rec.id)], limit=1)
    #             if assets_liquidation_form.id:
    #                 rec.liquidation = assets_liquidation_form.id
    #
    # @api.depends('liquidation')
    # def _compute_xiii_liquidation(self):
    #     for rec in self:
    #         rec.xiii_liquidation = 0
    #         if rec.is_liquidation_payslip and rec.liquidation.id:
    #             rec.xiii_liquidation = rec.liquidation.get_xiii_amount()

    def unlink(self):
        """Eliminando las inputs de tipo liquidación"""

        input_line_ids = []

        for rec in self:
            for line in rec.input_line_ids:
                for input in line.input_ids:
                    if input.code.startswith('INDE'):
                        input_line_ids.append(input.id)

        res = super(HrPayslip, self).unlink()

        self.env['hr.input'].browse(input_line_ids).unlink()

        return res

    years_in_service = fields.Integer(
        string="Years of service",
        compute="_get_time_in_service",
        store=False,
        help='Years of service since employee\'s first contract, up to the payroll cut-off date\n'
             'Used for computing benefits such as the reserve fund and vacations provision.',
    )
    months_in_service = fields.Integer(
        string="Months of service",
        compute="_get_time_in_service",
        store=False,
        help="Months of service since employee's first contract, up to the payroll cut-off date. "
             "Used for computing benefits such as the reserve fund and vacations provision.")
    days_in_service = fields.Integer(
        string="Days of service",
        compute="_get_time_in_service",
        store=False,
        help="Days of service since employee's first contract, up to the payroll cut-off date. "
             "Used for computing benefits such as the reserve fund and vacations provision.")
    number_service_months = fields.Integer(
        string="Number of service months",
        compute="_get_number_service_months",
        store=False,
        help="Number of different months that the employee has rendered services. "
             "Useful to pay reserve funds from the 13th month.")
    days_to_pay_reserve_fund = fields.Integer(string="Days to pay reserve fund",
                                              compute="_get_days_to_pay_reserve_fund",
                                              help="Number of days for which reserve funds must be paid at "
                                                   "employee's 13th month.")
    unified_basic_salary = fields.Float(string='SBU', store=True,
                                        compute='_get_unified_basic_salary',
                                        help='The unified basic salary used to calculate the provision of the '
                                             'fourteenth salary.')

    worked_days = fields.Float(string='Worked days', tracking=True, help='')
    calendar_days_in_month = fields.Integer(string="Month days", help='Calendar days in month.')

    daily_hours = fields.Float(string='Daily hours', tracking=True, help='')
    standard_daily_hours = fields.Float(string='Standard daily hours', tracking=True, help='')

    reduction_of_working_hours = fields.Boolean(string='Reduction of working hours', tracking=True)
    percentage_reduction_of_working_hours = fields.Float(string='Percentage reduction', tracking=True, help='')
    employee_information = fields.Many2one('hr.personal.expense', compute='_get_personal_expenses')

    is_liquidation_payslip = fields.Boolean('Is liquidation payslip', default=False)
    active = fields.Boolean(default=True)
    # liquidation = fields.Many2one('hr.assets.liquidation', compute='_compute_liquidation_form', store=True)
    xiii_liquidation = fields.Float()
    xiv_liquidation = fields.Float()
    vacations_liquidation = fields.Float()
