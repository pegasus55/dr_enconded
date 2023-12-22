# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrCredit(models.Model):
    _name = 'hr.credit'
    _inherit = ['hr.generic.request']
    _description = "Credit request"
    _order = "employee_requests_id, date desc"

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_credit.email_template_confirm_employee_credit_request',
            'confirm_direct': 'hr_dr_credit.email_template_confirm_direct_approve_credit_request',
            'approve': 'hr_dr_credit.email_template_confirm_approve_employee_credit_request',
            'reject': 'hr_dr_credit.email_template_confirm_reject_employee_credit_request',
            'cancel': 'hr_dr_credit.email_template_confirm_cancel_employee_credit_request',
            'in_payroll': 'hr_dr_credit.email_template_confirm_in_payroll_employee_credit_request',
            'expired': 'hr_dr_credit.email_template_confirm_expired_employee_credit_request'
        }
    _hr_notifications_mode_param = 'employee.credit.request.notifications.mode'
    _hr_administrator_param = 'employee.credit.request.administrator'
    _hr_second_administrator_param = 'employee.credit.request.second.administrator'

    _INSTALLMENT = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),
        ('31', '31'),
        ('32', '32'),
        ('33', '33'),
        ('34', '34'),
        ('35', '35'),
        ('36', '36'),
    ]

    def _compute_credit_amount(self):
        total_paid = 0.0
        for credit in self:
            for line in credit.credit_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = credit.credit_amount - total_paid
            credit.total_amount = credit.credit_amount
            credit.balance_amount = balance_amount
            credit.total_paid_amount = total_paid

    def go_to_payroll(self):
        self.state = 'in_payroll'
        self.date_go_to_payroll = datetime.utcnow()
        self.user_go_to_payroll = self.env.uid
        # TODO Enviar mail cuando se pasa a nómina un crédito.

    def cancel_request_by_admin(self):
        self.cancel_request()

    def get_percentage(self, wage, amount):
        if wage != 0:
            precision = self.env['decimal.precision'].precision_get('Credit')
            return round(amount * 100 / wage, precision)
        return 0

    @api.onchange('contract_id', 'credit_amount')
    def on_change_contract_id_credit_amount(self):
        if self.sudo().contract_id:
            self.percentage_of_salary = self.get_percentage(self.sudo().contract_id.wage, self.credit_amount)
        else:
            self.percentage_of_salary = 0

    @api.onchange('employee_requests_id')
    def on_change_employee_id(self):
        if self.employee_requests_id and not self.employee_requests_id.employee_admin:
            self.department_employee_requests_id = self.sudo().employee_requests_id.department_id
            self.job_position = self.sudo().employee_requests_id.job_id
            precision = self.env['decimal.precision'].precision_get('Credit')

            total_amount_due = 0
            installments = dict()
            active_credits = self.env['hr.credit'].search([
                ('employee_requests_id', '=', self.employee_requests_id.id),
                ('state', 'in', ['approved', 'in_payroll']),
                ('balance_amount', '!=', 0)
            ])
            for ac in active_credits:
                total_amount_due = total_amount_due + ac.balance_amount
                for all in ac.credit_lines:
                    if not all.paid:
                        key = all.date.strftime("%m/%Y")
                        if key in installments:
                            installments[key] = round(float(installments.get(key, 0)) + all.amount, precision)
                        else:
                            installments[key] = all.amount

            installments_str = ""
            for key in installments:
                if installments_str == "":
                    installments_str = key + ": " + str(installments[key])
                else:
                    installments_str = installments_str + " " + key + ": " + str(installments[key])

            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', self.employee_requests_id.id),
                ('state', '=', 'open')])
            if not contract:
                message = _("You must define a contract for collaborator.")
                raise UserError(message)
            elif len(contract) > 1:
                raise UserError(_('There should only be one contract in execution.'))
            else:
                self.contract_id = contract[0].id

            wage = self.sudo().contract_id.wage
            maximum_credit_percentage = self.get_maximum_credit_percentage()
            maximun_credit_amount = round(wage * maximum_credit_percentage / 100, precision)

            self.consider = (_(
                "Número de créditos activos del colaborador: %s.\n"
                "El monto total adeudado es: %s.\n"
                "El detalle del monto total adeudado es:\n"
                "%s\n"
                "El salario del colaborador es: %s. "
                "El porcentaje máximo de endeudamiento en función del salario es: %s. "
                "El monto máximo de endeudamiento es: %s.\n"
                "El número máximo de créditos activos que puede tener el colaborador es: %s.\n"
                "El número máximo de cuotas que el colaborador puede elegir es: %s.\n") % (
                                 len(active_credits), total_amount_due, installments_str, wage,
                                 maximum_credit_percentage,
                                 maximun_credit_amount, self.get_maximum_number_of_credits(),
                                 self.get_maximum_number_of_installments()))

    @api.model
    def _get_last_approver(self):
        # Si no existe notificación, entonces el empleado que realizó la solicitud fue aprobado automáticamente.
        if len(self.notification_ids) == 0:
            return self.env['hr.employee'].sudo().search([('user_id', '=', self.create_uid.id)], limit=1)
        last_approver = self.notification_ids[len(self.notification_ids)-1].employee_approve_id
        return last_approver

    @api.model
    def _get_complete_address(self):
        address_home = self.employee_requests_id.sudo().address_home_id
        if address_home:
            if address_home.interception_type == 'na':
                address = _("%s %s, %s, %s, %s.") % (
                    address_home.street, address_home.number,
                    address_home.state_id.name, address_home.city_id.name, address_home.parish_id.name)
            elif address_home.interception_type == 'and':
                address = _("%s %s y %s, %s, %s, %s.") % (
                    address_home.street, address_home.number, address_home.street2,
                    address_home.state_id.name, address_home.city_id.name, address_home.parish_id.name)
            else:
                address = _("%s %s entre %s y %s, %s, %s, %s.") % (
                    address_home.street, address_home.number, address_home.street2, address_home.third_street,
                    address_home.state_id.name, address_home.city_id.name, address_home.parish_id.name)
            return address
        else:
            return ''

    @api.onchange('date')
    def on_change_date(self):
        if self.date:
            self.payment_date = self.date + relativedelta(months=1)

    @api.onchange('credit_amount', 'payment_date', 'installment')
    def on_change_input_installment(self):
        self.credit_lines = [(6, 0, [])]
        self.total_amount = 0
        self.balance_amount = 0

    def get_maximum_number_of_installments(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            "credit.maximum.number.of.installments", default=6))

    def get_maximum_number_of_credits(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            "maximum.number.of.credits", default=1))

    def get_credit_months_in_the_company(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            "credit.months.in.the.company", default=6))

    def get_maximum_credit_percentage(self):
        return float(self.env['ir.config_parameter'].sudo().get_param(
            "maximum.credit.percentage", default=30))

    def get_maximum_credit_percentage_based_on(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "maximum.credit.percentage.based_on", default='')

    def get_credit_payroll_to_analyze(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "credit.payroll.to.analyze", default='')

    def get_credit_salary_rule_code_to_analyze(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            "credit.salary.rule.code.to.analyze", default='')

    def get_average(self, instance):
        average = 0
        payslip_ids = []
        credit_payroll_to_analyze = instance.get_credit_payroll_to_analyze()
        limit = -1
        if credit_payroll_to_analyze == 'last_three_payrolls':
            limit = 3
        elif credit_payroll_to_analyze == 'last_six_payrolls':
            limit = 6
        elif credit_payroll_to_analyze == 'last_nine_payrolls':
            limit = 9
        elif credit_payroll_to_analyze == 'last_twelve_payrolls':
            limit = 12
        elif credit_payroll_to_analyze == 'all_payroll':
            limit = -1
        if limit != -1:
            payslip_ids = self.env['hr.payslip'].sudo().search([
                ('employee_id', '=', instance.employee_requests_id.id),
                ('state', 'in', ['done', 'paid'])], limit=limit, order='date_to desc')
        else:
            payslip_ids = self.env['hr.payslip'].sudo().search([
                ('employee_id', '=', instance.employee_requests_id.id),
                ('state', 'in', ['done', 'paid'])], order='date_to desc')

        salary_rule_code = self.get_credit_salary_rule_code_to_analyze()
        total_by_salary_rule_code = 0
        for payslip in payslip_ids:
            for line in payslip.line_ids:
                if line.code == salary_rule_code:
                    total_by_salary_rule_code += line.total
        if total_by_salary_rule_code == 0:
            raise UserError(
                _("Review the salary rule configured in the credit module settings [{}]. "
                  "For the payrolls analyzed, the value of said item is 0.").format(salary_rule_code)
            )

        count_payslip_ids = len(payslip_ids)
        if count_payslip_ids != 0:
            precision = self.env['decimal.precision'].precision_get('Credit')
            average = round(total_by_salary_rule_code / count_payslip_ids, precision)
        return average

    def _check_restrictions_create_edit(self, instance=None):
        # Si no recibe una instancia del modelo específica asume que es la actual.
        if instance is None:
            instance = self

        #
        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', instance.employee_requests_id.id),
            ('state', '=', 'open')])
        if not contract:
            raise UserError(_('You must define a contract for collaborator.'))
        elif len(contract) > 1:
            raise UserError(_('There should only be one contract in execution.'))

        # La fecha inicial de pago no puede ser menor que la fecha de creación.
        if instance.payment_date < instance.date:
            raise ValidationError(_("The initial payment date cannot be less than the creation date."))

        # El monto del crédito debe ser mayor que 0.
        if instance.credit_amount <= 0:
            raise ValidationError(
                _("The credit amount must be greater than 0."))

        # Debe configurar el administrador del departamento al que pertenece el colaborador solicitante.
        if not instance.user_manager_department_employee_requests_id:
            raise ValidationError(_("You must configure the administrator of the department to which the requesting "
                                    "collaborator belongs."))

        #
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            max_installments_for_employee = instance.get_maximum_number_of_installments()
            if int(instance.installment) > max_installments_for_employee:
                raise ValidationError(
                    _("The maximum number of installments that the collaborator can choose is: {}.").format(
                        max_installments_for_employee))

            maximum_number_of_credits = instance.get_maximum_number_of_credits()
            credit_count = self.env['hr.credit'].search_count([
                ('employee_requests_id', '=', instance.employee_requests_id.id),
                ('state', 'in', ['approved', 'in_payroll']),
                ('id', '!=', instance.id),
                ('balance_amount', '!=', 0)
            ])
            if credit_count >= maximum_number_of_credits:
                raise ValidationError(
                    _("The maximum number of active credits that the collaborator can have is: {}.").format(
                        maximum_number_of_credits))

            maximum_credit_percentage = instance.get_maximum_credit_percentage()
            maximum_credit_percentage_based_on = instance.get_maximum_credit_percentage_based_on()
            if maximum_credit_percentage_based_on == 'salary':
                if instance.percentage_of_salary > maximum_credit_percentage:
                    raise ValidationError(
                        _("The maximum percentage of indebtedness on the salary is: {}.").format(
                            maximum_credit_percentage))
            elif maximum_credit_percentage_based_on == 'payroll':
                average = self.get_average(instance)
                if instance.get_percentage(average, instance.credit_amount) > maximum_credit_percentage:
                    raise ValidationError(
                        _("The maximum percentage of indebtedness on the payroll is: {}. "
                          "The code of the analyzed salary rule is: {}.").format(
                            maximum_credit_percentage, self.get_credit_salary_rule_code_to_analyze()))

    def _check_restrictions(self, instance=None):
        """
        Valida las restricciones que pueda tener el modelo.

        @:param instance Instancia del modelo a validar.
        """

        # Si no recibe una instancia del modelo específica asume que es la actual.
        if instance is None:
            instance = self

        #
        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', instance.employee_requests_id.id),
            ('state', '=', 'open')])
        if not contract:
            raise ValidationError(_('You must define a contract for collaborator.'))
        elif len(contract) > 1:
            raise ValidationError(_('There should only be one contract in execution.'))

        #
        if not instance.credit_lines:
            raise ValidationError(_("Please compute installment."))

        # La fecha inicial de pago no puede ser menor que la fecha de creación.
        if instance.payment_date < instance.date:
            raise ValidationError(_("The initial payment date cannot be less than the creation date."))

        # El monto del crédito debe ser mayor que 0.
        if instance.credit_amount <= 0:
            raise ValidationError(
                _("The credit amount must be greater than 0."))  #

        # Debe configurar el administrador del departamento al que pertenece el colaborador solicitante.
        if not instance.user_manager_department_employee_requests_id:
            raise ValidationError(_("You must configure the administrator of the department to which "
                                    "the requesting collaborator belongs."))

        #
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            max_installments_for_employee = instance.get_maximum_number_of_installments()
            if int(instance.installment) > max_installments_for_employee:
                raise ValidationError(
                    _("The maximum number of installments that the collaborator can choose is: {}.").format(
                        max_installments_for_employee))

            maximum_number_of_credits = instance.get_maximum_number_of_credits()
            credit_count = self.env['hr.credit'].search_count([
                ('employee_requests_id', '=', instance.employee_requests_id.id),
                ('state', 'in', ['approved', 'in_payroll']),
                ('id', '!=', instance.id),
                ('balance_amount', '!=', 0)
            ])
            if credit_count >= maximum_number_of_credits:
                raise ValidationError(
                    _("The maximum number of active credits that the collaborator can have is: {}.").format(
                        maximum_number_of_credits))

            maximum_credit_percentage = instance.get_maximum_credit_percentage()
            maximum_credit_percentage_based_on = instance.get_maximum_credit_percentage_based_on()
            if maximum_credit_percentage_based_on == 'salary':
                if instance.percentage_of_salary > maximum_credit_percentage:
                    raise ValidationError(
                        _("The maximum percentage of indebtedness on the salary is: {}.").format(
                            maximum_credit_percentage))
            elif maximum_credit_percentage_based_on == 'payroll':
                average = self.get_average(instance)
                if instance.get_percentage(average, instance.credit_amount) > maximum_credit_percentage:
                    raise ValidationError(
                        _("The maximum percentage of indebtedness on the payroll is: {}. "
                          "The code of the analyzed salary rule is: {}.").format(
                            maximum_credit_percentage, self.get_credit_salary_rule_code_to_analyze()))

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()
        local_context['subject'] = _("Solicitud de crédito")
        local_context['request'] = _("ha realizado una solicitud de crédito.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.sudo().env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.sudo().env.ref('hr_dr_management.menu_hr_management').id

        local_context['details'] = "Solicitud de crédito por {}{}, en {} cuota(s) y fecha inicial de pago {}.".format(
            self.currency_id.symbol, self.credit_amount, self.installment, self.payment_date.strftime("%d/%m/%Y"))

        local_context['commentary'] = self.commentary

        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')
        action = self.sudo().env.ref('hr_dr_credit.employee_credit_request_action_notifications_to_process').read()[0].\
            get('id')
        model = "hr.notifications"
        menu = self.sudo().env.ref('hr_dr_credit.menu_hr_employee_credit_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        department = 'Dirección de Talento Humano'
        management_responsible = self.sudo().employee_requests_id.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        local_context['department'] = department

        return local_context

    def compute_installment(self):
        for credit in self:
            credit.credit_lines.unlink()
            date_start = credit.payment_date
            precision = self.env['decimal.precision'].precision_get('Credit')
            amount = round(credit.credit_amount / int(credit.installment), precision)
            total_amount_calculated = amount * int(credit.installment)
            for i in range(1, int(credit.installment) + 1):
                if i == int(credit.installment):
                    # Última cuota
                    if total_amount_calculated != credit.credit_amount:
                        value_last_due = amount + (credit.credit_amount - total_amount_calculated)
                        self.env['hr.credit.line'].create({
                            'date': date_start,
                            'installment': i,
                            'amount': value_last_due,
                            'employee_id': credit.employee_requests_id.id,
                            'department_id': credit.employee_requests_id.sudo().department_id.id,
                            'user_manager_department_employee_requests_id':
                                credit.employee_requests_id.sudo().department_id.manager_id.user_id.id,
                            'credit_id': credit.id})
                    else:
                        self.env['hr.credit.line'].create({
                            'date': date_start,
                            'installment': i,
                            'amount': amount,
                            'employee_id': credit.employee_requests_id.id,
                            'department_id': credit.employee_requests_id.sudo().department_id.id,
                            'user_manager_department_employee_requests_id':
                                credit.employee_requests_id.sudo().department_id.manager_id.user_id.id,
                            'credit_id': credit.id})
                else:
                    self.env['hr.credit.line'].create({
                        'date': date_start,
                        'installment': i,
                        'amount': amount,
                        'employee_id': credit.employee_requests_id.id,
                        'department_id': credit.employee_requests_id.sudo().department_id.id,
                        'user_manager_department_employee_requests_id':
                            credit.employee_requests_id.sudo().department_id.manager_id.user_id.id,
                        'credit_id': credit.id})
                date_start = date_start + relativedelta(months=1)
            credit._compute_credit_amount()
        return True

    def confirm_request_direct(self):
        self._check_restrictions()
        super(HrCredit, self).confirm_request_direct()

    @api.model
    def get_signature_mode(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        signature_mode = config_parameter.get_param('credits.signature.mode', default='')
        return signature_mode

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.credit.seq') or ' '
        res = super(HrCredit, self).create(values)
        return res

    def write(self, vals):
        res = super(HrCredit, self).write(vals)
        return res

    def unlink(self):
        for credit in self:
            if credit.state not in ['draft', 'cancelled']:
                raise UserError(_('You can only delete credits in draft and canceled status.'))
        return super(HrCredit, self).unlink()

    def print_employee_credit_request(self):
        return self.env.ref('hr_dr_credit.action_employee_credit_request_report').report_action(self)

    def print_discount_authorization(self):
        return self.env.ref('hr_dr_credit.action_discount_authorization_ec_report').report_action(self)

    def _default_employee(self):
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('employee_admin', '=', False),
            ('state', 'in', ['affiliate'])], limit=1)

    employee_requests_id = fields.Many2one(
        'hr.employee', string="Collaborator", required=True, default=_default_employee,
        tracking=True, ondelete='cascade')
    name = fields.Char(string="Name", default="/", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, tracking=True)
    state = fields.Selection(
        selection_add=[
            ('in_payroll', _('In payroll')),
            ('expired', _('Expired'))
        ])
    contract_id = fields.Many2one('hr.contract', string="Contract", readonly=True, store=True, tracking=True)
    date_go_to_payroll = fields.Datetime(string='Go to payroll date', readonly=True, tracking=True)
    user_go_to_payroll = fields.Many2one('res.users', string="Go to payroll user", readonly=True, tracking=True)
    credit_lines = fields.One2many('hr.credit.line', 'credit_id', string="Credit details", index=True)
    credit_amount = fields.Monetary(string="Credit amount", required=True, currency_field='currency_id', tracking=True)
    percentage_of_salary = fields.Float(string="Percentage of salary", readonly=True, store=True,
                                        digits='Credit', tracking=True)
    total_amount = fields.Monetary(string="Total amount", readonly=True, store=True, compute='_compute_credit_amount',
                                   currency_field='currency_id', tracking=True)
    balance_amount = fields.Monetary(string="Balance amount", store=True, compute='_compute_credit_amount',
                                     currency_field='currency_id', tracking=True)
    total_paid_amount = fields.Monetary(string="Total paid amount", store=True, compute='_compute_credit_amount',
                                        currency_field='currency_id', tracking=True)
    files = fields.Many2many('ir.attachment', 'employee_credit_file_ir_attachment_rel',
                             'files_employee_credit_id', 'attachment_id', string="Load files", tracking=True)
    evidences = fields.Many2many('ir.attachment', 'employee_credit_evidence_ir_attachment_rel',
                                 'evidences_employee_credit_id', 'attachment_id', string="Evidences", tracking=True)
    consider = fields.Text(string="Consider")
    installment = fields.Selection(_INSTALLMENT, string='No of installments', default='6', help='', required=True,
                                   tracking=True)
    payment_date = fields.Date(string="Payment start date", required=True, readonly=True, tracking=True)