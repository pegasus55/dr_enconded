# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time, timedelta
from .common import convert_utc_time_to_tz
from odoo.exceptions import UserError, ValidationError


class EmployeeFamilyLoad(models.Model):
    _name = 'hr.employee.family.load'
    _description = 'Employee family load'
    _inherit = ['mail.thread']
    _order = "employee_id"

    def compute_age(self):
        for efl in self:
            if efl.date_of_birth:
                today = datetime.utcnow()
                tz_name = efl.employee_id.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    raise ValidationError(_(
                        "Local time zone is not defined. You may need to set a time zone "
                        "in your employee or user's preferences."))
                today = convert_utc_time_to_tz(today, tz_name)
                today = today.date()
                age = today.year - efl.date_of_birth.year
                birthday = efl.date_of_birth + relativedelta(years=age)
                if birthday > today:
                    age = age - 1
                efl.age = age
            else:
                efl.age = 0

    age = fields.Integer(string='Age', compute='compute_age', store=False, help='')
    name = fields.Char(string='Name', help='', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of birth', help='', tracking=True)
    _RELATIONSHIP = [
        ('parent', _('Parent')),
        ('mother', _('Mother')),
        ('father', _('Father')),
        ('siblings', _('Siblings')),
        ('sister', _('Sister')),
        ('brother', _('Brother')),
        ('spouses', _('Spouses')),
        ('wife', _('Wife')),
        ('husband', _('Husband')),
        ('cohabitant', _('Cohabitant')),
        ('children', _('Children')),
        ('daughter', _('Daughter')),
        ('son', _('Son')),
        ('other', _('Other'))
    ]
    relationship = fields.Selection(_RELATIONSHIP, string='Relationship', help='', required=True, tracking=True)
    disability = fields.Boolean(string='Disability', help='', tracking=True)
    disability_conadis = fields.Char(string='Disability conadis', help='', tracking=True)
    disability_percentage = fields.Float(string='Percentage of disability', digits='Employee', tracking=True)
    disability_description = fields.Text(string='Disability description', tracking=True)
    id_type = fields.Many2one('l10n_latam.identification.type', required=True, tracking=True,
                              string="Identification type",
                              domain="[('country_id', '=?', address_home_id_country_id)]",
                              default=lambda self: self.env.ref("l10n_ec.ec_dni", raise_if_not_found=False),
                              help="The type of identification.")
    identification = fields.Char(string='Identification', tracking=True, help='', required=True)
    insured = fields.Boolean(string='Insured', help='')
    phone = fields.Char(string='Phone', help='')
    address = fields.Char(string='Address', help='')
    employee_id = fields.Many2one('hr.employee', string='Collaborator', required=True, ondelete='cascade', help='',
                                  tracking=True)
    address_home_id_country_id = fields.Many2one('res.country', related='employee_id.address_home_id_country_id',
                                                 readonly=True, string="Country")
    active = fields.Boolean(string='Active', default=True, tracking=True)
    backup_document = fields.Many2many('ir.attachment', 'family_load_ir_attachment_rel', 'family_load_id',
                                       'attachment_id', string="Backup documents", tracking=True)
    receive_taxed_income = fields.Boolean(string='Receive taxed income', default=False)
    employee_dependent = fields.Boolean(string='Employee dependent', default=True)
    presents_catastrophic_diseases = fields.Boolean(string='Presents catastrophic, rare, or orphan diseases',
                                                    default=False)