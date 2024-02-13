# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time, timedelta
from .common import days2ymd
from odoo.exceptions import UserError, ValidationError
from random import choice
from string import digits


class Employee(models.Model):
    _inherit = 'hr.employee'
    _sql_constraints = [
        ('identification_id_uniq', 'unique(identification_id)', 'The identification number must be unique.'),
    ]

    def validate_module(self):
        """
        Valida que estén instalados los módulos de dr_start_system
        y dr_license_customer o lanza un error de lo contrario.
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    def get_password(self, employee):
        password = "{}.{}{}@Nukle0".format(employee.identification_id,
                                           employee.names.strip()[0].upper(),
                                           employee.surnames.strip()[0].lower())
        return password

    # @api.onchange('work_email')
    # def onchange_work_email(self):
    #     if self.work_email and self.user_id:
    #         self.user_id.work_email = self.work_email

    # @api.onchange('private_email')
    # def onchange_private_email(self):
    #     if self.private_email and self.address_home_id:
    #         self.address_home_id.email = self.private_email
    #
    #     if self.private_email and self.user_id:
    #         self.user_id.email = self.private_email

    @api.onchange('identification_id')
    def onchange_identification_id(self):
        if self.identification_id:
            if not self.barcode:
                try:
                    barcode = str(int(self.identification_id))
                except:
                    barcode = "".join(choice(digits) for i in range(8))
                    if len(str(int(barcode))) < 8:
                        barcode = barcode + "".join(choice(digits) for i in range(8 - len(barcode)))

                if len(barcode) > 8:
                    barcode = barcode[:8]
                elif len(barcode) < 8:
                    barcode = barcode + "".join(choice(digits) for i in range(8 - len(barcode)))
                self.barcode = barcode

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        employees = super(Employee, self).create(vals_list)
        for employee in employees:
            if not employee.identification_id and not employee.employee_admin:
                raise UserError(_('You must specify the identification number.'))

            if employee.last_company_entry_date and employee.department_id:
                self.env['hr.employee.department.history'].create({
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'date_from': employee.last_company_entry_date,
                })

            if employee.last_company_entry_date:
                self.env['hr.employee.company.history'].create({
                    'employee_id': employee.id,
                    'date_from': employee.last_company_entry_date,
                })

            # if employee.state in ["affiliate", 'temporary']:
            #     if not employee.work_email and not employee.private_email:
            #         raise UserError(_('You must specify work email or personal email.'))

            if not employee.address_home_id:
                default_country_id = self.get_default_country_id()
                partner_with_same_vat = self.env['res.partner'].with_context(active_test=False).search([
                    ('vat', '=', employee.identification_id),
                    ('l10n_latam_identification_type_id', '=', employee.identification_type.id)
                ])
                if partner_with_same_vat:
                    employee_with_same_address_home_id = self.with_context(active_test=False).search([
                        ('address_home_id', '=', partner_with_same_vat.id)])
                    if len(employee_with_same_address_home_id) == 0:
                        employee.address_home_id = partner_with_same_vat
                        if not partner_with_same_vat.active:
                            partner_with_same_vat.active = True

                        partner_with_same_vat.name = employee.name
                        partner_with_same_vat.image_1920 = employee.image_1920
                        partner_with_same_vat.mobile = employee.personal_mobile_phone
                        partner_with_same_vat.phone = employee.phone
                        partner_with_same_vat.country_id = default_country_id
                        partner_with_same_vat.company_id = employee.company_id.id
                    else:
                        # No se definió la dirección privada del colaborador,
                        # además existe una dirección privada con identificación
                        # %s asociada a un colaborador existente con nombre %s.
                        # Tenga en cuenta que algunos datos pueden estar inactivos.
                        raise UserError(_("The collaborator's private address was not defined. "
                                          "In addition, there is a private address with identification %s associated "
                                          "with an existing collaborator with name %s. "
                                          "Please note that some data may be inactive.") %
                                        (partner_with_same_vat.vat, employee_with_same_address_home_id.name))
                else:
                    partner = self.env['res.partner'].create({
                        'name': employee.name,
                        'image_1920': employee.image_1920,
                        'mobile': employee.personal_mobile_phone,
                        'phone': employee.phone,
                        'country_id': default_country_id,
                        'vat': employee.identification_id,
                        'l10n_latam_identification_type_id': employee.identification_type.id,
                        'type': 'private',
                        'company_id': employee.company_id.id
                    })
                    employee.address_home_id = partner

            if self.get_validate_identification():
                if employee.identification_id:
                    if not self.check_id(employee.identification_id,
                                         employee.identification_type,
                                         employee.address_home_id.country_id.code):
                        # Formato de %s incorrecto para %s
                        raise UserError(_('Wrong %s format for %s.') % (employee.identification_type.name,
                                                                        employee.address_home_id.country_id.name))

            if self.get_create_user_when_creating_employee():
                if employee.state in ["affiliate", 'temporary']:
                    if not employee.user_id:
                        user_with_same_login = self.env['res.users'].with_context(active_test=False).search([
                            '|',
                            ('login', '=', employee.work_email),
                            ('login', '=', employee.identification_id)
                        ])
                        if user_with_same_login:
                            employee_with_same_user_id = self.with_context(active_test=False).search(
                                [('user_id', '=', user_with_same_login.id)])
                            if len(employee_with_same_user_id) == 0:
                                employee.user_id = user_with_same_login
                                if not user_with_same_login.active:
                                    user_with_same_login.active = True

                                user_with_same_login.name = employee.name
                                user_with_same_login.email = employee.private_email
                                user_with_same_login.work_email = employee.work_email
                                user_with_same_login.password = self.get_password(employee)
                            else:
                                # El usuario del colaborador no fue definido.
                                # Además, existe un usuario con nombre %s y login %s
                                # asociado a un colaborador con nombre %s.
                                # Tenga en cuenta que algunos datos pueden estar inactivos.
                                raise UserError(_("The collaborator's user was not defined. "
                                                  "There is also a user with name %s and login %s "
                                                  "associated with a collaborator with name %s."
                                                  "Please note that some data may be inactive.") %
                                                (user_with_same_login.name, user_with_same_login.login,
                                                 employee_with_same_user_id.name))
                        else:
                            user = self.env['res.users'].create({
                                'name': employee.name,
                                'login': employee.work_email or employee.identification_id,
                                'password': self.get_password(employee),
                            })
                            employee.user_id = user
                            user.email = employee.private_email
                            user.work_email = employee.work_email
        return employees

    def write(self, vals):
        if self.id:
            self.validate_module()
            edh = False
            ech = False
            if vals.get('last_company_entry_date'):
                edh = self.env['hr.employee.department.history'].search(
                    [('employee_id', '=', self.id), ('date_from', '=', self.last_company_entry_date)])
                ech = self.env['hr.employee.company.history'].search(
                    [('employee_id', '=', self.id), ('date_from', '=', self.last_company_entry_date)])

            employee = super(Employee, self).write(vals)

            if not self.identification_id and not self.employee_admin:
                raise UserError(_('You must specify the identification number.'))

            # if self.state in ["affiliate", 'temporary']:
            #     if not self.work_email and not self.private_email:
            #         raise UserError(_('You must specify work email or personal email.'))

            if self.get_validate_identification():
                if self.identification_id:
                    if not self.check_id(self.identification_id,
                                         self.identification_type,
                                         self.address_home_id.country_id.code):
                        # Formato de %s incorrecto para %s
                        raise UserError(_('Wrong %s format for %s.') % (self.identification_type.name,
                                                                        self.address_home_id.country_id.name))

            if employee and edh:
                if not self.env.context.get('reenter') == '1':
                    edh.date_from = self.last_company_entry_date

            if employee and ech:
                if not self.env.context.get('reenter') == '1':
                    ech.date_from = self.last_company_entry_date
                    self.compute_total_time_in_company()

            if not self.address_home_id:
                default_country_id = self.get_default_country_id()
                partner_with_same_vat = self.env['res.partner'].with_context(active_test=False).search([
                    ('vat', '=', self.identification_id),
                    ('l10n_latam_identification_type_id', '=', self.identification_type.id)
                ])
                if partner_with_same_vat:
                    employee_with_same_address_home_id = self.with_context(active_test=False).search([
                        ('address_home_id', '=', partner_with_same_vat.id)])
                    if len(employee_with_same_address_home_id) == 0:
                        self.address_home_id = partner_with_same_vat
                        if not partner_with_same_vat.active:
                            partner_with_same_vat.active = True

                        partner_with_same_vat.name = self.name
                        partner_with_same_vat.image_1920 = self.image_1920
                        partner_with_same_vat.mobile = self.personal_mobile_phone
                        partner_with_same_vat.phone = self.phone
                        partner_with_same_vat.country_id = default_country_id
                        partner_with_same_vat.company_id = self.company_id.id
                    else:
                        # No se definió la dirección privada del colaborador,
                        # además existe una dirección privada con identificación
                        # %s asociada a un colaborador existente con nombre %s.
                        # Tenga en cuenta que algunos datos pueden estar inactivos.
                        raise UserError(_("The collaborator's private address was not defined. "
                                          "In addition, there is a private address with identification %s associated "
                                          "with an existing collaborator with name %s. "
                                          "Please note that some data may be inactive.") %
                                        (partner_with_same_vat.vat, employee_with_same_address_home_id.name))
                else:
                    partner = self.env['res.partner'].create({
                        'name': self.name,
                        'image_1920': self.image_1920,
                        'mobile': self.personal_mobile_phone,
                        'phone': self.phone,
                        'country_id': default_country_id,
                        'vat': self.identification_id,
                        'l10n_latam_identification_type_id': self.identification_type.id,
                        'type': 'private',
                        'company_id': self.company_id.id
                    })
                    self.address_home_id = partner

            if self.get_create_user_when_creating_employee():
                if self.state in ["affiliate", 'temporary']:
                    if not self.user_id:
                        user_with_same_login = self.env['res.users'].with_context(active_test=False).search([
                            '|',
                            ('login', '=', self.work_email),
                            ('login', '=', self.identification_id)
                        ])
                        if user_with_same_login:
                            employee_with_same_user_id = self.with_context(active_test=False).search(
                                [('user_id', '=', user_with_same_login.id)])
                            if len(employee_with_same_user_id) == 0:
                                self.user_id = user_with_same_login
                                if not user_with_same_login.active:
                                    user_with_same_login.active = True

                                user_with_same_login.name = self.name
                                user_with_same_login.email = self.private_email
                                user_with_same_login.work_email = self.work_email
                                user_with_same_login.password = self.get_password(employee)
                            else:
                                # El usuario del colaborador no fue definido.
                                # Además, existe un usuario con nombre %s y login %s
                                # asociado a un colaborador con nombre %s.
                                # Tenga en cuenta que algunos datos pueden estar inactivos.
                                raise UserError(_("The collaborator's user was not defined. "
                                                  "There is also a user with name %s and login %s "
                                                  "associated with a collaborator with name %s."
                                                  "Please note that some data may be inactive.") %
                                                (user_with_same_login.name, user_with_same_login.login,
                                                 employee_with_same_user_id.name))
                        else:
                            user = self.env['res.users'].create({
                                'name': self.name,
                                'login': self.work_email or self.identification_id,
                                'password': self.get_password(self),
                            })
                            self.user_id = user
                            user.email = self.private_email
                            user.work_email = self.work_email
            return employee

    def unlink(self):
        self.validate_module()
        self.user_id.unlink()
        self.address_home_id.unlink()
        return super(Employee, self).unlink()

    @api.depends('job_id')
    def _compute_job_title(self):
        for employee in self.filtered('job_id'):
            employee.job_title = employee.job_id.position_id.name

    @api.depends('company_history_ids', 'company_history_ids.employee_id', 'company_history_ids.date_from',
                 'company_history_ids.date_to')
    def compute_total_time_in_company(self):
        for employee in self:
            time_worked_total_day = 0
            total_time_in_company = ""
            for ch in employee.company_history_ids:
                time_worked_total_day += ch.time_worked_total_day

            result = days2ymd(time_worked_total_day)
            years = int(result['y'])
            months = int(result['m'])
            days = int(result['d'])

            total_time_in_company = _("{} year(s) {} month(S) {} day(S)").format(years, months, days)

            employee.update({
                'total_time_in_company_years': years,
                'total_time_in_company_months': months,
                'total_time_in_company_days': days,
                'total_time_in_company_total_days': time_worked_total_day,
                'total_time_in_company': total_time_in_company,
            })

    @api.depends('family_load_ids', 'family_load_ids.employee_id', 'family_load_ids.relationship')
    def compute_number_of_children(self):
        for employee in self:
            count = 0
            for fl in employee.family_load_ids:
                if fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter':
                    count += 1
            employee.update({
                'children': count,
            })

    def compute_number_of_dependencies(self):
        for employee in self:
            count = 0
            for fl in employee.family_load_ids:
                if self.is_family_load_dependent(fl):
                    count += 1
            employee.update({
                'dependencies': count,
            })

    def _any_sons_disability(self):
        for fl in self.family_load_ids:
            if ((fl.relationship == 'children' or fl.relationship == 'son' or fl.relationship == 'daughter') and
                    fl.disability):
                return True
        return False

    def _any_family_load_presents_catastrophic_diseases(self):
        for fl in self.family_load_ids:
            if fl.presents_catastrophic_diseases:
                return True
        return False

    def is_family_load_dependent(self, fl):
        def calculate_children_age(children, td):
            if children.date_of_birth:
                birthdate_in_period = children.date_of_birth + relativedelta(year=td.year)
                rd = relativedelta(birthdate_in_period, children.date_of_birth)
                return rd.years
            else:
                return 100

        today = datetime.today().date()
        if ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son')
            and calculate_children_age(fl, today) < 18) or \
                ((fl.relationship == 'children' or fl.relationship == 'daughter' or fl.relationship == 'son') and
                 fl.disability) or \
                (fl.relationship == 'spouse' or fl.relationship == 'wife' or fl.relationship == 'husband' or
                 fl.relationship == 'cohabitant'):
            return True
        return False

    def get_create_user_when_creating_employee(self):
        create_user_when_creating_employee = self.env['ir.config_parameter'].sudo().get_param(
            'create.user.when.creating.employee', '')
        if create_user_when_creating_employee != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('create.user.when.creating.employee')))
        else:
            return False

    def get_validate_identification(self):
        validate_identification = self.env['ir.config_parameter'].sudo().get_param(
            'hr_dr.employee.validate.identification', '')
        if validate_identification != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('hr_dr.employee.validate.identification')))
        else:
            return False

    def check_id(self, vat, identification_type, code):
        if code == 'EC':
            if identification_type.name == "Cédula":
                valid = False
                if len(vat) != 10:
                    return valid
                try:
                    int(vat)
                except:
                    return valid

                # Multiplicamos por 2 si es impar o por 1 si es par los dígitos de la cédula
                values = [int(vat[x]) * (2 - x % 2) for x in range(9)]
                # Sumamos los dígitos y si el valor es mayor que 9 le restamos nueve y nos quedamos con el nuevo valor
                sum_values = sum(map(lambda x: x > 9 and x - 9 or x, values))
                # Le restamos a 10 el último dígito del resultado y este sería el dígito verificador y para que sea
                # una cédula válida debe coincidir con el dígito 10 de la cédula
                if int(vat[9]) == 10 - int(str(sum_values)[-1:]):
                    valid = True
                # Las cédulas que terminan en 0, no cumplen con el algoritmo descrito en el if, por tal
                # motivo agregamos la siguiente línea para estos casos
                elif int(vat[9]) == int(str(sum_values)[-1:]) == 0:
                    valid = True
                # elif int(vat[9]) == 0:
                #     valid = True
                return valid
            elif identification_type.name == "RUC":
                return True
            elif identification_type.name == "Pasaporte":
                return True
            elif identification_type.name == "Unknown":
                return True
            else:
                return True
        else:
            return True

    def get_default_country_id(self):
        country_id = int(self.env['ir.config_parameter'].sudo().get_param('hr_dr.employee.country'))
        return country_id

    @api.depends("birthday")
    def _compute_third_age(self):
        for rec in self:
            age = relativedelta(datetime.today().date(), rec.birthday).years
            if age >= 65:
                rec.third_age = True
            else:
                rec.third_age = False

    def default_country_of_residence(self):
        return self.env.ref("base.ec")

    identification_id = fields.Char(string='Nº Identification', groups="hr.group_hr_user", required=True, tracking=True)
    marital = fields.Selection([
        ('single', _('Single(a)')),
        ('married', _('Married(a)')),
        ('cohabitant', _('Legal Cohabitant')),
        ('widower', _('Widower(a)')),
        ('divorced', _('Divorced(a)'))
    ], string='Marital status', groups="hr.group_hr_user", default='', tracking=True)
    certificate = fields.Selection([
        ('graduate', _('Graduate')),
        ('bachelor', _('Bachelor')),
        ('master', _('Master')),
        ('doctor', _('Doctor')),
        ('other', _('Other')),
    ], 'Certificate level', default='', groups="hr.group_hr_user", tracking=True)

    personal_mobile_phone = fields.Char(related='address_home_id.mobile', related_sudo=False,
                                        readonly=False, string="Mobile", groups="hr.group_hr_user")
    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    signature_mode = fields.Selection(_SM, string='Signature mode', required=True, default='without_signature')
    signature = fields.Binary(string="Signature", attachment=True, tracking=True)
    state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
        ('unemployed', _('Unemployed')),
        ('retired', _('Retired'))
    ], string='State', default='affiliate', tracking=True, required=True)
    last_company_entry_date = fields.Date('Entry date', tracking=True,
                                          help='Last date of entry to the company.')
    normative_id = fields.Many2one('hr.normative', string="Regulation", tracking=True,
                                   default=lambda self: self.env.user.company_id.normative_default_id)
    profession_id = fields.Many2one('hr.profession', string='Profession', tracking=True)
    third_age = fields.Boolean(string='Third age', tracking=True, help='', compute='_compute_third_age')
    allow_attendance_web = fields.Boolean(string='Allow attendance web', default=False, tracking=True)
    department_history_ids = fields.One2many('hr.employee.department.history', 'employee_id',
                                             string="Department history")
    company_history_ids = fields.One2many('hr.employee.company.history', 'employee_id', string="Company history")
    total_time_in_company = fields.Char(string='Total time in company', store=True, readonly=True,
                                        compute='compute_total_time_in_company', tracking=True)
    total_time_in_company_years = fields.Integer(string='Total time in company (years)', store=True, readonly=True,
                                                 compute='compute_total_time_in_company', tracking=True)
    total_time_in_company_months = fields.Integer(string='Total time in company (months)', store=True, readonly=True,
                                                  compute='compute_total_time_in_company', tracking=True)
    total_time_in_company_days = fields.Integer(string='Total time in company (days)', store=True, readonly=True,
                                                compute='compute_total_time_in_company', tracking=True)
    total_time_in_company_total_days = fields.Integer(string='Total time in company (total days)', store=True,
                                                      readonly=True, compute='compute_total_time_in_company',
                                                      tracking=True)
    backups_ids = fields.One2many('hr.employee.backup', 'employee_id', string="Backups")
    family_load_ids = fields.One2many('hr.employee.family.load', 'employee_id', string='Family loads', help='')
    judicial_withholding_ids = fields.One2many('hr.judicial.withholding', 'employee_id',
                                               string='Judicial withholdings', help='')
    food_preferences_ids = fields.Many2many('hr.employee.food.preferences', string="Food preferences")
    allergies_ids = fields.Many2many('hr.employee.allergies', string="Allergies")

    children = fields.Integer(string='Number of children', groups="hr.group_hr_user", tracking=True,
                              compute='compute_number_of_children')
    dependencies = fields.Integer(string='Number of dependencies', groups="hr.group_hr_user", tracking=True,
                                  compute='compute_number_of_dependencies')
    identification_type = fields.Many2one('l10n_latam.identification.type', required=True, tracking=True,
                                          string="Identification type",
                                          # domain="[('country_id', '=?', address_home_id_country_id)]",
                                          default=lambda self: self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False),
                                          help="The type of identification.")

    # Health
    blood_type = fields.Selection(
        string="Blood type",
        selection=[
            ('O', _('O NEGATIVO')),
            ('O+', _('O POSITIVO')),
            ('A-', _('A NEGATIVO')),
            ('A+', _('A POSITIVO')),
            ('B-', _('B NEGATIVO')),
            ('B+', _('B POSITIVO')),
            ('AB-', _('AB NEGATIVO')),
            ('AB+', _('AB POSITIVO')),
        ],
        default="",
        tracking=True
    )
    donor = fields.Boolean(string='Donor', default=False, tracking=True)
    presents_catastrophic_disease = fields.Boolean(string='Presents catastrophic disease', default=False, tracking=True)
    catastrophic_disease_ids = fields.Many2many('hr.catastrophic.disease', string="Catastrophic diseases")
    disability = fields.Boolean(string='Disability', tracking=True, help='')
    _DISABILITY_TYPE = [
        ('own', _('Own')),
        ('surrogate', _('Surrogate')),
    ]
    disability_type = fields.Selection(_DISABILITY_TYPE, string='Disability type', tracking=True,
                                       help='')
    disability_conadis = fields.Char(string='Disability conadis', tracking=True, help='')
    disability_description = fields.Text(string='Disability description', tracking=True, help='')
    disability_percentage = fields.Float(string='Disability percentage', tracking=True, help='')
    medical_exam_ids = fields.One2many('hr.medical.exam', 'employee_id', string="Medical exams")
    work_region = fields.Selection(string='Work region', related='address_id.state_id.region', readonly=True)
    record_attendance_from_system = fields.Boolean(string='Record attendance from the system', default=False)

    employee_admin = fields.Boolean(string='Employee admin', default=False)
    unemployed_type = fields.Selection([
        ('fired', _('Fired')),
        ('resigned', _('Resigned')),
    ], string='Unemployed type', tracking=True)
    retirement_certificate = fields.Binary("Retirement certificate", attachment=True, help="", tracking=True)
    pension = fields.Float(string='Pension', digits='Employee', tracking=True)
    date_of_death = fields.Date('Date of death', help="", tracking=True)
    beneficiary_id = fields.Many2one('res.partner', string="Beneficiary", tracking=True)
    beneficiary_document = fields.Binary("Document to justify the beneficiary", attachment=True, help="",
                                         tracking=True)
    death_certificate = fields.Binary("Death certificate", attachment=True, help="", tracking=True)
    single_payment_after_death = fields.Boolean(string='Single payment after death', default=False, tracking=True)
    single_payment_after_death_document = fields.Binary("Document to justify the single payment after death",
                                                        attachment=True, help="", tracking=True)

    PAYMENT_METHOD = [
        ('CTA', _('Wire transfer')),
        ('CHQ', _('Check')),
        ('EFE', _('Cash')),
        ('undefined', _('Undefined')),
    ]
    payment_method = fields.Selection(selection=PAYMENT_METHOD, required=True, tracking=True,
                                      string=_('Payment method'), help=_('Method to receive payments.'))
    address_home_id_country_id = fields.Many2one('res.country', related='address_home_id.country_id',
                                                 readonly=True, string="Country")
    address_home_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user", tracking=True,
        # domain="["
        #        "('l10n_latam_identification_type_id', '=', identification_type), "
        #        "('vat', '=', identification_id), "
        #        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )

    RESIDENCE = [
        ('01', _('Local resident')),
        ('02', _('Foreign resident')),
    ]
    residence = fields.Selection(selection=RESIDENCE, required=True, string='Residence', tracking=True, default='01')
    country_of_residence = fields.Many2one('res.country', required=True, string="Country of residence",
                                           tracking=True, default=default_country_of_residence)
    AGREEMENT_APPLIES = [
        ('SI', _('With agreement')),
        ('NO', _('Without agreement')),
    ]
    agreement_applies = fields.Selection(selection=AGREEMENT_APPLIES, required=True, string='Agreement applies',
                                         tracking=True, default='SI')
    type_net_salary_system = fields.Selection([
        ('1', _('Without net salary system')),
        ('2', _('With net salary system')),
    ], required=True, string='Type of net salary system',  tracking=True, default='1')

    # @api.depends('work_experience_ids.time_worked_integer')
    # def _total_time_worked(self):
    #     avgyear = 365.2425
    #     avgmonth = 365.2425 / 12.0
    #     for employee in self:
    #         total_time_worked = 0
    #         total_time_worked_amd = ""
    #         total_employer = 0
    #         for work_experience in employee.work_experience_ids:
    #             total_time_worked += work_experience.time_worked_integer
    #             total_employer += 1
    #
    #         years, remainder = divmod(total_time_worked, avgyear)
    #         years = int(years)
    #         months, remainder = divmod(remainder, avgmonth)
    #         months = int(months)
    #         days = int(remainder)
    #         total_time_worked_amd = "{} Año(S) {} Mes(S) {} Día(S)".format(years, months, days)
    #
    #         if total_employer != 0:
    #             years_average, remainder_average = divmod(total_time_worked / total_employer, avgyear)
    #             years_average = int(years_average)
    #             months_average, remainder_average = divmod(remainder_average, avgmonth)
    #             months_average = int(months_average)
    #             days_average = int(remainder_average)
    #             average_time_work_experience_by_employer_amd = "{} Año(S) {} Mes(S) {} Día(S)".format(years_average,
    #                                                                                                   months_average,
    #                                                                                                   days_average)
    #         else:
    #             average_time_work_experience_by_employer_amd = "{} Año(S) {} Mes(S) {} Día(S)".format(0, 0, 0)
    #
    #         employee.update({
    #             'total_time_work_experience_amd': total_time_worked_amd,
    #             'total_time_work_experience_integer': total_time_worked,
    #             'average_time_work_experience_by_employer_amd': average_time_work_experience_by_employer_amd,
    #         })
    # total_time_work_experience_amd = fields.Char(string='Total time worked', store=True, readonly=True,
    #                                             compute='_total_time_worked',
    #                                             tracking=True, track_sequence=5)
    # total_time_work_experience_integer = fields.Integer(string='Total time worked', store=True, readonly=True,
    #                                              compute='_total_time_worked',
    #                                              tracking=True, track_sequence=5)
    # average_time_work_experience_by_employer_amd = fields.Char(string='Average time per employer', store=True, readonly=True,
    #                                              compute='_total_time_worked',
    #                                              tracking=True, track_sequence=5)