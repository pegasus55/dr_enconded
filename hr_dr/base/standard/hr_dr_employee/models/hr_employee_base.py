# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    name = fields.Char(string='Surnames and names', tracking=True)
    surnames = fields.Char(string='Surnames', tracking=True)
    names = fields.Char(string='Names', tracking=True)
    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    signature_mode = fields.Selection(_SM, string='Signature mode', required=True, default='without_signature')
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
    allow_attendance_web = fields.Boolean(string='Allow attendance web', default=False, tracking=True)
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
    identification_type = fields.Many2one('l10n_latam.identification.type', required=True, tracking=True,
                                          string="Identification type",
                                          default=lambda self: self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False),
                                          help="The type of identification.")
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
    record_attendance_from_system = fields.Boolean(string='Record attendance from the system', default=False)
    PAYMENT_METHOD = [
        ('CTA', _('Wire transfer')),
        ('CHQ', _('Check')),
        ('EFE', _('Cash')),
        ('undefined', _('Undefined')),
    ]
    payment_method = fields.Selection(selection=PAYMENT_METHOD,
                                      string=_('Payment method'), help=_('Method to receive payments.'))
    employee_admin = fields.Boolean(string='Employee admin', default=False)
    currency_id = fields.Many2one('res.currency', string="Currency", related='company_id.currency_id', readonly=True)
    work_phone = fields.Char('Work phone', compute="_compute_work_contact_details", store=True,
                             inverse='_inverse_work_contact_details')

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.name = self.name.strip()
            parts = self.name.split(' ')
            surnames = ''
            names = ''
            if parts and len(parts) != 0:
                if len(parts) == 1:
                    surnames = parts[0]
                elif len(parts) == 2:
                    surnames = parts[0]
                    names = parts[1]
                elif len(parts) == 3:
                    surnames = ' '.join(parts[:-1])
                    names = parts[2]
                elif len(parts) > 3:
                    surnames = ' '.join(parts[:-2])
                    names = ' '.join(parts[-2:])

            self.surnames = surnames.upper()
            self.names = names.upper()
            self.name = self.name.upper()

    @api.depends('department_id')
    def _compute_parent_id(self):
        for employee in self.filtered('department_id.manager_id'):
            if employee == employee.department_id.manager_id:
                if employee.department_id.parent_id and employee.department_id.parent_id.manager_id:
                    employee.parent_id = employee.department_id.parent_id.manager_id
            else:
                employee.parent_id = employee.department_id.manager_id

    @api.model
    def get_hr_dr_management_responsible(self):
        """
        Busca en la configuración del sistema el responsable de RR.HH. y lo devuelve o lanza un error de no encontrarlo.
        :return: ('hr.employee') El colaborador responsable de RR.HH.
        """
        hr_responsible = self.env['hr.employee'].sudo().search([
            ('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('hr_dr_management.responsible')))], limit=1)

        if len(hr_responsible) == 1:
            return hr_responsible[0]
        else:
            return False

    @api.depends('work_contact_id', 'work_contact_id.mobile', 'work_contact_id.email', 'work_contact_id.phone')
    def _compute_work_contact_details(self):
        for employee in self:
            if employee.work_contact_id:
                employee.mobile_phone = employee.work_contact_id.mobile
                employee.work_email = employee.work_contact_id.email
                employee.work_phone = employee.work_contact_id.phone

    def _inverse_work_contact_details(self):
        for employee in self:
            if not employee.work_contact_id:
                employee.work_contact_id = self.env['res.partner'].sudo().create({
                    'email': employee.work_email,
                    'mobile': employee.mobile_phone,
                    'phone': employee.work_phone,
                    'name': employee.name,
                    'image_1920': employee.image_1920,
                    'company_id': employee.company_id.id
                })
            else:
                employee.work_contact_id.sudo().write({
                    'email': employee.work_email,
                    'mobile': employee.mobile_phone,
                    'phone': employee.work_phone,
                })