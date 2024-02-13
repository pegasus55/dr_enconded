# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    surnames = fields.Char(readonly=True)
    names = fields.Char(readonly=True)
    _SM = [
        ('without_signature', _('Without signature')),
        ('uploaded_image', _('Uploaded image')),
        ('electronic_signature', _('Electronic signature')),
    ]
    signature_mode = fields.Selection(_SM, string='Signature mode', required=True, default='without_signature',
                                      readonly=True)
    state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
        ('unemployed', _('Unemployed')),
        ('retired', _('Retired'))
    ], string='State', default='affiliate', tracking=True, required=True, readonly=True)
    last_company_entry_date = fields.Date('Entry date', tracking=True,
                                          help='Last date of entry to the company.', readonly=True)
    normative_id = fields.Many2one('hr.normative', string="Regulation", tracking=True,
                                   default=lambda self: self.env.user.company_id.normative_default_id, readonly=True)
    profession_id = fields.Many2one('hr.profession', string='Profession', tracking=True, readonly=True)
    allow_attendance_web = fields.Boolean(string='Allow attendance web', default=False, tracking=True, readonly=True)
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
        default="", readonly=True,
        tracking=True
    )
    donor = fields.Boolean(string='Donor', default=False, tracking=True, readonly=True)
    presents_catastrophic_disease = fields.Boolean(string='Presents catastrophic disease', default=False,
                                                   tracking=True, readonly=True)
    disability = fields.Boolean(string='Disability', tracking=True, help='', readonly=True)
    _DISABILITY_TYPE = [
        ('own', _('Own')),
        ('surrogate', _('Surrogate')),
    ]
    disability_type = fields.Selection(_DISABILITY_TYPE, string='Disability type', tracking=True,
                                       help='', readonly=True)
    disability_conadis = fields.Char(string='Disability conadis', tracking=True, help='', readonly=True)
    disability_description = fields.Text(string='Disability description', tracking=True, help='', readonly=True)
    disability_percentage = fields.Float(string='Disability percentage', tracking=True, help='', readonly=True)
    record_attendance_from_system = fields.Boolean(string='Record attendance from the system', default=False,
                                                   readonly=True)
    PAYMENT_METHOD = [
        ('CTA', _('Wire transfer')),
        ('CHQ', _('Check')),
        ('EFE', _('Cash')),
        ('undefined', _('Undefined')),
    ]
    payment_method = fields.Selection(selection=PAYMENT_METHOD,
                                      string=_('Payment method'), help=_('Method to receive payments.'), readonly=True)
    employee_admin = fields.Boolean(string='Employee admin', default=False, readonly=True)
    unemployed_type = fields.Selection([
        ('fired', _('Fired')),
        ('resigned', _('Resigned')),
    ], string='Unemployed type', tracking=True, readonly=True)
    pension = fields.Float(string='Pension', digits='Employee', tracking=True, readonly=True)
    date_of_death = fields.Date('Date of death', help="", tracking=True, readonly=True)
    beneficiary_id = fields.Many2one('res.partner', string="Beneficiary", tracking=True, readonly=True)
    single_payment_after_death = fields.Boolean(string='Single payment after death', default=False, tracking=True,
                                                readonly=True)