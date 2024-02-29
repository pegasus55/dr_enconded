# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _inherit = ['hr.salary.rule', 'mail.thread']

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        Invocamos el name_search para buscar por codigo y/o nombre de la regla salarial
        """
        if args is None:
            args = []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        rule = self.search(domain + args, limit=limit)
        return rule.name_get()

    name = fields.Char(tracking=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(tracking=True)
    quantity = fields.Char(tracking=True)
    category_id = fields.Many2one('hr.salary.rule.category', tracking=True)
    active = fields.Boolean(tracking=True)
    appears_on_payslip = fields.Boolean(string='Appears on payslip', tracking=True)
    parent_rule_id = fields.Many2one('hr.salary.rule', string='Parent salary rule', tracking=True)
    company_id = fields.Many2one('res.company', tracking=True)
    condition_range = fields.Char(string='Range based on', tracking=True)
    condition_python = fields.Text(string='Python condition', tracking=True)
    condition_range_min = fields.Float(string='Minimum range', digits='Payroll', tracking=True)
    condition_range_max = fields.Float(string='Maximum range', digits='Payroll', tracking=True)
    amount_fix = fields.Float(string='Fixed amount', digits='Payroll', tracking=True)
    amount_percentage = fields.Float(digits='Payroll', tracking=True)
    amount_python_compute = fields.Text(string='Python code', tracking=True)
    amount_percentage_base = fields.Char(tracking=True)
    child_ids = fields.One2many('hr.salary.rule', 'parent_rule_id', string='Child salary rule', copy=True)
    register_id = fields.Many2one('hr.contribution.register', string='Contribution register', tracking=True)
    input_ids = fields.One2many('hr.rule.input', 'input_id', string='Inputs', copy=True)
    note = fields.Text(tracking=True)

    # Columns
    appears_on_additional_data = fields.Boolean(
        string='Appears on additional data',
        help='', tracking=True,
        )
    condition_acc = fields.Boolean(
        string='Accounting accounts by type of contract',
        help='', tracking=True
        )
    contract_type_account_account_ids = fields.One2many('hr.contract.type.account.account', 'salary_rule_id',
                                                        string='Accounting accounts by type of contract')
    amount_select = fields.Selection(
        selection_add=[('account_move', 'Accounting movements to be netted')], string='Amount type', tracking=True,
        ondelete={"account_move": "set default"})
    condition_select = fields.Selection(
        selection_add=[('has_account_move', 'Accounting movements to be netted exist')], string="Condition based on",
        tracking=True, ondelete={"has_account_move": "set default"})

    payment_term_days = fields.Integer(
        string="Días plazo de pago",
        help='EXLUSIVO PARA ASIENTOS EN EL DEBE\n'
             'Indica el número de días con el que se afectará el campo plazo de pago en el asiento contable'
             'generado por esta regla, util para pasar registros al siguiente mes indicando un plazo de 1 día.\n'
             'Por ejemplo, si la nomina se cierra el 31 de enero, y el plazo de es de 1 dia, el campo fecha'
             'de vencimiento del asiento contable será el 1ro de febrero.\n'
             'Util para traspasar saldos de nominas negativas al siguiente mes.', tracking=True
    ) 

    def _compute_rule(self, localdict):
        """
        1. Agregamos monto basado en account_move, que usa el saldo pendiente de conciliar del asiento contable
           asociado a la cuenta de la regla salarial
        2. Agregamos computo del impuesto a la renta, imposible de otra forma pues la tabla de RDEP
           se alimenta incluso de la nomina en curso aunque esta no exista aún (puede tener comisiones no proyectadas).
           #TODO: Hacerlo dry con satisfy_condition y mejorar performance
        """
        self.ensure_one()
        if self.amount_select == 'account_move':
            try:
                amount = localdict.get('force_amount')
                return amount, float(safe_eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Contacte a soporte. Error inesperado en la regla salarial %s (%s).')
                                % (self.name, self.code))
        elif self.code == 'RETENCION_IMPUESTO_RENTA':
            ctx = self.env.context.copy()

            # Al calcular el impuesto a la renta, resto a los ingresos el valor de los ingresos por impuesto a la renta
            # que estoy calculando para evitar discrepancias en los valores, pues de lo contrario varía el monto de los
            # ingresos cada vez que se le adiciona una regla salarial de impuestos.
            incomes = localdict['categories'].INGRESOS - \
                      (localdict.get('IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0) +
                       localdict.get('SEGUNDO_IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0))

            ctx.update({'INGRESOS': incomes})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            amount = payslip.employee_information.amount_this_employer_discount + \
                     payslip.employee_information.second_amount_this_employer_discount + \
                     payslip.employee_information.amount_detained_employee_discount
            return amount, float(safe_eval(self.quantity, localdict)), 100.0
        elif self.code == 'IMPUESTO_RENTA_ASUMIDO_EMPLEADOR':
            ctx = self.env.context.copy()

            # Al calcular el impuesto a la renta, resto a los ingresos el valor de los ingresos por impuesto a la renta
            # que estoy calculando para evitar discrepancias en los valores, pues de lo contrario varía el monto de los
            # ingresos cada vez que se le adiciona una regla salarial de impuestos.
            incomes = localdict['categories'].INGRESOS - \
                      (localdict.get('IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0) +
                       localdict.get('SEGUNDO_IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0))

            ctx.update({'INGRESOS': incomes})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            amount = payslip.employee_information.amount_this_employer_discount
            return amount, float(safe_eval(self.quantity, localdict)), 100.0
        elif self.code == 'SEGUNDO_IMPUESTO_RENTA_ASUMIDO_EMPLEADOR':
            ctx = self.env.context.copy()

            # Al calcular el impuesto a la renta, resto a los ingresos el valor de los ingresos por impuesto a la renta
            # que estoy calculando para evitar discrepancias en los valores, pues de lo contrario varía el monto de los
            # ingresos cada vez que se le adiciona una regla salarial de impuestos.
            incomes = localdict['categories'].INGRESOS - \
                      (localdict.get('IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0) +
                       localdict.get('SEGUNDO_IMPUESTO_RENTA_ASUMIDO_EMPLEADOR', 0.0))

            ctx.update({'INGRESOS': incomes})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            amount = payslip.employee_information.second_amount_this_employer_discount
            return amount, float(safe_eval(self.quantity, localdict)), 100.0
        return super(HrSalaryRule, self)._compute_rule(localdict)

    def _satisfy_condition(self, localdict):
        """
        1. Agregamos condicion basado en si existen account_move con saldo pendiente de conciliar del asiento contable
           asociado a la cuenta de la regla salarial
        2. Agregamos computo del impuesto a la renta, imposible de otra forma pues la tabla de RDEP
           se alimenta incluso de la nomina en curso aunque esta no exista aún (puede tener comisiones no proyectadas).
           #TODO: Hacerlo dry con compute_rule y mejorar performance
        """
        self.ensure_one()
        if self.condition_select == 'has_account_move':
            try:
                amount = localdict.get('force_amount')
                return amount
            except:
                raise UserError(_('Contacte a soporte. Error inesperado en la condicion de la regla salarial %s (%s).')
                                % (self.name, self.code))
        elif self.code == 'RETENCION_IMPUESTO_RENTA':
            ctx = self.env.context.copy()
            ctx.update({'INGRESOS': localdict['categories'].INGRESOS})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            
            if payslip.employee_information and \
               payslip.employee_information.amount_this_employer_discount + \
               payslip.employee_information.second_amount_this_employer_discount + \
               payslip.employee_information.amount_detained_employee_discount > 0: 
                return True
            return False
        elif self.code == 'IMPUESTO_RENTA_ASUMIDO_EMPLEADOR':
            ctx = self.env.context.copy()
            ctx.update({'INGRESOS': localdict['categories'].INGRESOS})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            if payslip.employee_information and \
               payslip.employee_information.amount_this_employer_discount > 0:
                return True
            return False
        elif self.code == 'SEGUNDO_IMPUESTO_RENTA_ASUMIDO_EMPLEADOR':
            ctx = self.env.context.copy()
            ctx.update({'INGRESOS': localdict['categories'].INGRESOS})
            payslip = localdict['payslip']
            payslip = self.env['hr.payslip'].with_context(ctx).search([('id','=',payslip.id)])
            if payslip.employee_information and \
               payslip.employee_information.second_amount_this_employer_discount > 0:
                return True
            return False
        return super(HrSalaryRule, self)._satisfy_condition(localdict)