# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.exceptions import UserError


class License(models.Model):
    _name = "dr.license"
    _description = 'License'
    _inherit = ['mail.thread']

    @api.depends('module_ids')
    def compute_applications(self):
        for record in self:
            record.update({
                'applications': len(record.module_ids)
            })

    @api.onchange('package', 'regulation', 'country_id', 'odoo')
    def _onchange_input_module_ids(self):
        domain = []
        regulation_ids = [id for id in self.regulation.ids]
        if self.package == 'Standard':
            domain = \
                [
                    '&',
                    '&',
                    '&', ('package', '=', 'Standard'), ('regulation', 'in', regulation_ids),
                    '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
                    '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
                ]


            # if self.regulation == 'generic':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&', ('package', '=', 'Standard'), ('regulation', '=', 'generic'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]
            # elif self.regulation == 'public':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&', ('package', '=', 'Standard'),
            #             '|', ('regulation', '=', 'public'), ('regulation', '=', 'generic'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]
            # elif self.regulation == 'private':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&', ('package', '=', 'Standard'),
            #             '|', ('regulation', '=', 'private'), ('regulation', '=', 'generic'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]
        elif self.package == 'Premium':
            domain = \
                [
                    '&',
                    '&',
                    '&', ('regulation', 'in', regulation_ids),
                    '|', ('package', '=', 'Standard'), ('package', '=', 'Premium'),
                    '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
                    '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
                ]


            # if self.regulation == 'generic':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&', ('regulation', '=', 'generic'),
            #             '|', ('package', '=', 'Standard'), ('package', '=', 'Premium'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]
            #
            # elif self.regulation == 'public':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&',
            #             '|', ('regulation', '=', 'public'), ('regulation', '=', 'generic'),
            #             '|', ('package', '=', 'Standard'), ('package', '=', 'Premium'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]
            #
            # elif self.regulation == 'private':
            #     domain = \
            #         [
            #             '&',
            #             '&',
            #             '&',
            #             '|', ('regulation', '=', 'private'), ('regulation', '=', 'generic'),
            #             '|', ('package', '=', 'Standard'), ('package', '=', 'Premium'),
            #             '|', ('country_id', '=', self.country_id.id), ('country_id', '=', False),
            #             '|', ('odoo', '=', self.odoo), ('odoo', '=', 'both')
            #         ]

        salable_module_ids = self.env['dr.salable.module'].sudo().search(domain)
        result = [sm.id for sm in salable_module_ids]
        self.module_ids = [(6, 0, result)]

    @api.onchange('plan')
    def _onchange_plan(self):
        if self.plan == '1':
            self.active_collaborators = 9
        elif self.plan == '2':
            self.active_collaborators = 49
        elif self.plan == '3':
            self.active_collaborators = 199
        elif self.plan == '4':
            self.active_collaborators = 699
        else:
            self.active_collaborators = 0

    @api.model_create_multi
    def create(self, vals_list):
        license = super(License, self).create(vals_list)

        for rec in license:
            if not rec.name or rec.name == '' or not rec.vat or rec.vat == '':
                # Debe especificar al menos el nombre y la identificación del cliente.
                raise UserError(_('You must specify at least the name and identification of the client.'))
        return license

    def write(self, vals):
        license = super(License, self).write(vals)

        if not self.name or self.name == '' or not self.vat or self.vat == '':
            # Debe especificar al menos el nombre y la identificación del cliente.
            raise UserError(_('You must specify at least the name and identification of the client.'))

        return license

    def unlink(self):
        for license in self:
            if license.state not in ('cancelled'):
                raise UserError(_('Licenses can only be removed in canceled status.'))
                # Solo se pueden eliminar licencias en estado cancelado.
        return super(License, self).unlink()

    def cancel_license(self):
        self.state = 'cancelled'

    def get_license_anticipation_days(self):
        license_anticipation_days = self.env['ir.config_parameter'].sudo().get_param('license.anticipation.days', '')
        if license_anticipation_days != '':
            return int(self.env['ir.config_parameter'].sudo().get_param('license.anticipation.days'))
        else:
            return 0

    def get_license_email_for_notification(self):
        return self.env['ir.config_parameter'].sudo().get_param('license.email.for.notification', '')

    def _cron_check_license(self):
        licenses = self.search([('active', '=', True), ('state', 'in', ['active'])])
        for l in licenses:
            today = datetime.utcnow().date()
            if l.expiration_date < today:
                l.state = 'expired'

            expiration_date = l.expiration_date + relativedelta(days=self.get_license_anticipation_days() * -(1))
            if expiration_date < today:
                # Notificar al cliente
                template = self.env.ref('dr_license.email_template_notify_approach_to_license_expiration_date_user',
                                        False)
                template = self.env['mail.template'].browse(template.id)
                local_context = self.env.context.copy()
                template.with_context(local_context).send_mail(l.id, force_send=True)

                # Notificar a la lista de correos
                emails_to = self.get_license_email_for_notification()
                if emails_to != '':
                    template_admin = self.env.ref(
                        'dr_license.email_template_notify_approach_to_license_expiration_date_admin', False)
                    template_admin = self.env['mail.template'].browse(template_admin.id)
                    template_admin.write({
                        'email_to': emails_to
                    })
                    local_context = self.env.context.copy()
                    template_admin.with_context(local_context).send_mail(l.id, force_send=True)

    customer_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    name = fields.Char('Name', related='customer_id.name', readonly=True, store=True, tracking=True)
    vat = fields.Char('Identification', related='customer_id.vat', readonly=True, store=True, tracking=True)
    expiration_date = fields.Date('Expiration date', required=True, tracking=True)
    active_collaborators = fields.Integer('Maximum number of active collaborators', required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    device_ids = fields.One2many('dr.device', 'license_id', string="Devices")
    renew_detail_ids = fields.One2many('dr.license.renew.detail', 'license_id', string="Renew details")
    module_ids = fields.Many2many('dr.salable.module', string="Apps")
    applications = fields.Integer('Applications', compute='compute_applications')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    _STATE = [
        ('active', 'Active license'),
        ('expired', 'Expired license'),
        ('cancelled', 'License canceled'),
    ]
    state = fields.Selection(_STATE, string='State', tracking=True, default="active")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 tracking=True, default=lambda self: self.env.company)
    os = fields.Char('Operating system', help='Operating system of the server where this license will be activated.',
                     tracking=True)
    path_ids = fields.One2many('dr.license.file.location', 'license_id', 'License file locations')
    confirmed = fields.Boolean('Confirmed', default=False, tracking=True,
                               help='This license has been delivered to the solicitor.')
    databases = fields.Text(string='Databases', help='Insert all database names allowed to this license separated '
                                                     'by comma. Remember database names are case sensitive. '
                                                     'If no database name is inserted, any will be accepted.',
                            tracking=True)
    _PACKAGE = [
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    ]
    package = fields.Selection(_PACKAGE, string='Nukleo version', required=True, tracking=True, default='Standard')
    _ODOO = [
        ('community', 'Community'),
        ('enterprise', 'Enterprise'),
    ]
    odoo = fields.Selection(_ODOO, string='Odoo', required=True, tracking=True)
    odoo_version = fields.Char(string='Version', required=True, tracking=True)
    python_version = fields.Char('Python version', required=True, help='', tracking=True)
    country_id = fields.Many2one('res.country', string='Country', help="", tracking=True, required=True,
                                 default=lambda x: x.env.company.country_id.id)
    # _REGULATION = [
    #     ('generic', 'Generic'),
    #     ('public', 'Public'),
    #     ('private', 'Private'),
    # ]
    # regulation = fields.Selection(_REGULATION, string='Regulation', required=True, tracking=True, default='generic')
    regulation = fields.Many2many('normative.license', string="Regulation")
    _PLAN = [
        ('1', 'Micro company (1-9 Collaborators)'),
        ('2', 'Small companies (10-49 Collaborators)'),
        ('3', 'Medium companies (50-199 Collaborators)'),
        ('4', 'Big companies (200-699 Collaborators)'),
    ]
    plan = fields.Selection(_PLAN, string='Plan', required=True, tracking=True, default='1')
    _ENVIRONMENT = [
        ('production', 'Production'),
        ('test', 'Test'),
    ]
    environment = fields.Selection(_ENVIRONMENT, string='Environment', required=True, tracking=True,
                                   default='production')


class RenewLicense(models.TransientModel):
    _name = 'dr.renew.license'
    _description = 'Renew license'

    license_id = fields.Many2one('dr.license', string="License", default=lambda self: self._context.get('active_id'),
                                 required=True)
    _PERIOD = [
        ('1', '1 Month'),
        ('3', '3 Months'),
        ('6', '6 Months'),
        ('9', '9 Months'),
        ('12', '12 Months'),
        ('15', '15 Months'),
        ('18', '18 Months'),
        ('24', '24 Months'),
    ]
    period = fields.Selection(_PERIOD, string='Period', required=True)
    description = fields.Text(string="Description", required=True)

    def action_accept(self):
        actual_expiration_date = self.license_id.expiration_date
        today = datetime.utcnow().date()
        if actual_expiration_date < today:
            next_expiration_date = today + relativedelta(months=int(self.period))
        else:
            next_expiration_date = actual_expiration_date + relativedelta(months=int(self.period))
        self.license_id.expiration_date = next_expiration_date
        self.license_id.state = 'active'
        self.license_id.confirmed = False

        self.env['dr.license.renew.detail'].create({
            'license_id': self.license_id.id,
            'actual_expiration_date': actual_expiration_date,
            'next_expiration_date': next_expiration_date,
            'description': self.description
        })


class StartLicense(models.TransientModel):
    _name = 'dr.start.license'
    _description = 'Start license'

    license_id = fields.Many2one('dr.license', string="License", default=lambda self: self._context.get('active_id'),
                                 required=True)
    expiration_date = fields.Date('Expiration date', required=True)

    def action_accept(self):
        self.license_id.expiration_date = self.expiration_date
        # self.license_id.renew_detail_ids.unlink()
        self.license_id.state = 'active'
        # self.license_id.confirmed = False


class LicenseRenewDetail(models.Model):
    _name = "dr.license.renew.detail"
    _description = 'License renew detail'
    _inherit = ['mail.thread']

    license_id = fields.Many2one('dr.license', string="License", required=True, tracking=True, ondelete='cascade')
    actual_expiration_date = fields.Date('Expiration date before renovation', required=True, tracking=True)
    next_expiration_date = fields.Date('Expiration date after renovation', required=True, tracking=True)
    evidences = fields.Many2many('ir.attachment', 'license_renew_detail_ir_attachment_rel', 'license_renew_detail_id',
                                 'attachment_id', string="Evidences", tracking=True)
    description = fields.Text(string="Description", tracking=True)


class Device(models.Model):
    _name = "dr.device"
    _description = 'Device'
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True, tracking=True)
    license_id = fields.Many2one('dr.license', string="License", required=True, tracking=True, ondelete='cascade')
    brand_id = fields.Many2one('dr.device.brand', string="Brand", required=True, tracking=True)
    model_id = fields.Many2one('dr.device.brand.model', string="Model", required=True, tracking=True,
                               domain="[('brand_id', '=', brand_id)]")
    serial_number = fields.Char('Serial number', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class DeviceBrand(models.Model):
    _name = "dr.device.brand"
    _description = 'Device brand'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    model_ids = fields.One2many('dr.device.brand.model', 'brand_id', string="Models")


class DeviceBrandModel(models.Model):
    _name = "dr.device.brand.model"
    _description = 'Device brand model'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    brand_id = fields.Many2one('dr.device.brand', string="Brand", required=True, tracking=True, ondelete='cascade')


class SalableModule(models.Model):
    _name = 'dr.salable.module'
    _description = 'List of salable modules'
    _inherit = ['mail.thread']

    name = fields.Char('Name', tracking=True)
    tradename = fields.Char('Tradename', tracking=True)
    shortdesc = fields.Text("Short description", tracking=True)
    summary = fields.Text("Summary", tracking=True)
    _PACKAGE = [
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    ]
    package = fields.Selection(_PACKAGE, string='Nukleo version', required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='Country', help="", tracking=True)
    # _REGULATION = [
    #     ('generic', 'Generic'),
    #     ('public', 'Public'),
    #     ('private', 'Private'),
    # ]
    # regulation = fields.Selection(_REGULATION, string='Regulation', required=True, tracking=True)
    regulation = fields.Many2one("normative.license", string='Regulation', required=True, tracking=True)
    _ODOO = [
        ('community', 'Community'),
        ('enterprise', 'Enterprise'),
        ('both', 'Both')
    ]
    odoo = fields.Selection(_ODOO, string='Odoo', required=True, tracking=True)
    _TYPE = [
        ('internal', 'Internal'),
        ('commercial', 'Commercial'),
    ]
    type = fields.Selection(_TYPE, string='Type', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    _sql_constraints = [('name_uniq', 'unique(name)', 'You can only add a module to the list once.')]


class LicFileLocation(models.Model):
    _name = 'dr.license.file.location'
    _description = 'License files location'
    _inherit = ['mail.thread']

    LICENSE_FILES = [('APPS_FILE', 'Applications file'),
                     ('DEV_FILE', 'Devices file'),
                     ('LIC_FILE', 'License file'),
                     ('EXE_FILE', 'Executions file'),
                     ('DAT_FILE', 'Execution dates file')]

    license_id = fields.Many2one('dr.license', tracking=True)
    file = fields.Selection(LICENSE_FILES, 'File', required=True, tracking=True)
    path = fields.Char('File path', required=True, tracking=True)

    _sql_constraints = [
        ('license_file_uniq', 'unique(license_id, file)', 'This file type has already been defined for this license!'),
        ('license_path_uniq', 'unique(license_id, path)',
         'This path has already been defined for another file type in this license!'),
    ]


class NormativeLicense(models.Model):
    _name = "normative.license"
    _description = 'Regulations license'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    acronym = fields.Char(string="Acronym", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
