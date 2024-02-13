# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime

SCORES = [
        ('', _('None')),
        ('poor', _('Poor')),
        ('fair', _('Fair')),
        ('good', _('Good')),
        ('excellent', _('Excellent'))
    ]
_DEFAULT_SCORE = ''


class RecruitmentDegree(models.Model):
    _inherit = 'hr.recruitment.degree'
    _order = "sequence"

    active = fields.Boolean(string='Active', default=True)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_recruitment_stats(self):
        job_data = self.env['hr.job'].read_group(
            [('department_id', 'in', self.ids)],
            ['no_of_hired_employee', 'department_id'], ['department_id'])
        new_emp = dict((data['department_id'][0], data['no_of_hired_employee']) for data in job_data)

        for department in self:
            department.new_hired_employee = new_emp.get(department.id, 0)
            jobs = self.env['hr.job'].search([
                ('department_id', '=', department.id)
            ])
            expected_employee = 0
            for job in jobs:
                expected_employee += job.no_of_recruitment
            department.expected_employee = expected_employee


class Job(models.Model):
    _inherit = 'hr.job'

    @api.depends('total', 'no_of_employee')
    def _compute_no_of_recruitment(self):
        for job in self:
            job.no_of_recruitment = job.total - job.no_of_employee

    def set_recruit(self):
        for record in self:
            record.write({'state': 'recruit'})
        return True

    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_hired_employee': 0
        })

    no_of_recruitment = fields.Integer(string='Expected new collaborators', copy=False,
                                       help='Number of new collaborators you expect to recruit.',
                                       compute=_compute_no_of_recruitment)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    total = fields.Integer(string='Total expected collaborators', copy=False, help='')
    user_id = fields.Many2one('res.users', string="Recruitment responsible", tracking=True,
                              domain=lambda self: [('groups_id', 'in', self.env.ref(
                                  'hr_recruitment.group_hr_recruitment_user').id)])
    hr_responsible_id = fields.Many2one('res.users', string="HR Responsible", tracking=True,
                                        help="Person responsible of validating the collaborator's contracts.",
                                        domain=lambda self: [('groups_id', 'in', self.env.ref(
                                            'hr_recruitment.group_hr_recruitment_manager').id)])
    # current_process_staff_requirement_id = fields.Many2one('hr.process.staff.requirement',
    #                                                        string='Current process staff requirement')


class StaffRequirementRequest(models.Model):
    _name = "hr.staff.requirement.request"
    _description = 'Staff requirement request'
    _order = "date_incorporation"
    _inherit = ['hr.generic.request']

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_recruitment.email_template_confirm_staff_requirement_request',
            'confirm_direct': 'hr_dr_recruitment.email_template_confirm_direct_staff_requirement_request',
            'approve': 'hr_dr_recruitment.email_template_confirm_approve_staff_requirement_request',
            'reject': 'hr_dr_recruitment.email_template_confirm_reject_staff_requirement_request',
            'cancel': 'hr_dr_recruitment.email_template_confirm_cancel_staff_requirement_request'
        }
    _hr_notifications_mode_param = 'staff.requirement.request.notifications.mode'
    _hr_administrator_param = 'staff.requirement.request.notifications.administrator'
    _hr_second_administrator_param = 'staff.requirement.request.notifications.second.administrator'

    def get_name_type(self):
        return dict(self._fields['type'].selection).get(self.type)

    def get_process_duration(self, job_id):
        config_parameter = self.env['ir.config_parameter'].sudo()
        mode = config_parameter.get_param('validate.anticipation.dynamically.in.staff.requirement.request.mode',
                                          default='')
        scheme = []
        if mode == 'by_job':
            scheme = self.env['hr.scheme.schedule.process.staff.requirement'].search([
                ('job_id', '=', job_id.id),
                ('mode', '=', 'by_job'),
                ('active', '=', True)
            ])
        else:
            position_id = False
            try:
                position_id = job_id.position_id.id
            except ValueError as error:
                position_id = job_id.position_id.ids[0]

            scheme = self.env['hr.scheme.schedule.process.staff.requirement'].search([
                ('position_id', '=', position_id),
                ('mode', '=', 'by_position'),
                ('active', '=', True)
            ], limit=1)

        process_duration = 0
        anticipation_days = 0
        reason_anticipation_days = ""
        for e in scheme:
            process_duration += e.working_days

        if self.env['ir.config_parameter'].sudo().get_param(
                'validate.anticipation.dynamically.in.staff.requirement.request'):
            if self.env['ir.config_parameter'].sudo().get_param(
                    'validate.anticipation.dynamically.in.staff.requirement.request') == 'True':
                # Validación dinámica
                anticipation_days = process_duration

                # El proceso de selección de personal se extiende por {} días.
                reason_anticipation_days += _("The process staff requirement lasts {} days.").format(process_duration)

                if self.env['ir.config_parameter'].sudo().get_param(
                        'start.schedule.approval.day.of.staff.requirement.request'):
                    if self.env['ir.config_parameter'].sudo().get_param(
                            'start.schedule.approval.day.of.staff.requirement.request') == 'False':
                        anticipation_days += 1
                        # Se incrementa 1 día debido a que en la configuración se especifica que el cronograma
                        # del proceso de selección comienza el día siguiente a la aprobación de la solicitud
                        # de requerimiento de personal.
                        reason_anticipation_days += \
                            _(" It is increased by 1 day because in the configuration it is specified that "
                              "the schedule of the selection process begins the day after the approval of the staff "
                              "requirement request.")
                else:
                    anticipation_days += 1
                    reason_anticipation_days += \
                        _(" It is increased by 1 day because in the configuration it is specified that "
                          "the schedule of the selection process begins the day after the approval of the staff "
                          "requirement request.")

                configurations = self.env['hr.normative.nomenclature'].search([
                    ('normative_id', '=', self.employee_requests_id.normative_id.id),
                    ('nomenclature_id.module_id', '=', self.env.ref('base.module_' + self._module).id),
                    ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
                    ('current', '=', True)
                ])
                for configuration in configurations:
                    if configuration.nomenclature_id.acronym == 'CADDPASRP':
                        anticipation_days += configuration.integer_value
                        # Se incrementan {} día(s) dedicados al proceso de aprobación de la solicitud de
                        # requerimiento de personal.
                        reason_anticipation_days += _(
                            " {} day(s) dedicated to the approval process of the staff requirement request "
                            "are increased.").format(configuration.integer_value)
                    if configuration.nomenclature_id.acronym == 'CADDPC':
                        anticipation_days += configuration.integer_value
                        # Se incrementan {} día(s) dedicados al proceso de contratación.
                        reason_anticipation_days += _(" {} day(s) dedicated to the hiring process are increased.").\
                            format(configuration.integer_value)

                return process_duration, anticipation_days, reason_anticipation_days
            else:
                # Validación estática por configuración
                configuration = self.env['hr.normative.nomenclature'].search([
                    ('normative_id', '=', self.employee_requests_id.normative_id.id),
                    ('nomenclature_id.module_id', '=', self.env.ref('base.module_' + self._module).id),
                    ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
                    ('nomenclature_id.acronym', '=', 'CMDARSRP'),
                    ('current', '=', True)
                ], limit=1)

                anticipation_days = configuration.integer_value
                # Las solicitudes de requerimiento de personal se deben realizar con {} días de anticipación a
                # la fecha de incorporación. Dicho valor fue definido por el administrador en la configuración.
                reason_anticipation_days += _("The staff requirement request must be made {} days prior to "
                                              "the date of incorporation. This value was defined by the administrator in "
                                              "the configuration.").format(configuration.integer_value)
        else:
            # Validación estática por configuración
            configuration = self.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', self.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=', self.env.ref('base.module_' + self._module).id),
                ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', self._name)]).id),
                ('nomenclature_id.acronym', '=', 'CMDARSRP'),
                ('current', '=', True)
            ], limit=1)

            anticipation_days = configuration.integer_value
            # Las solicitudes de requerimiento de personal se deben realizar con {} días de anticipación a
            # la fecha de incorporación. Dicho valor fue definido por el administrador en la configuración.
            reason_anticipation_days += _("The staff requirement request must be made {} days prior to "
                                          "the date of incorporation. This value was defined by the administrator in "
                                          "the configuration.").format(configuration.integer_value)

            return process_duration, anticipation_days, reason_anticipation_days

    @api.depends('job_id')
    def _compute_process_duration(self):
        process_duration, anticipation_days, reason_anticipation_days = self.get_process_duration(self.job_id)
        self.process_duration = process_duration
        self.anticipation_days = anticipation_days
        self.reason_anticipation_days = reason_anticipation_days

    def mark_as_approved(self):
        super(StaffRequirementRequest, self).mark_as_approved()

        # Crear el proceso de selección de personal
        psr = self.env['hr.process.staff.requirement'].create({
            'staff_requirement_request': self.id,
            'employee_requests_id': self.employee_requests_id.id,
            'department_employee_requests_id': self.department_employee_requests_id.id,
            'type': self.type,
            'quantity': self.quantity,
            'job_id': self.job_id.id,
            'employee_to_replace_id': self.employee_to_replace_id.id,
            'date_incorporation': self.date_incorporation
        })

        config_parameter = self.env['ir.config_parameter'].sudo()
        mode = config_parameter.get_param('validate.anticipation.dynamically.in.staff.requirement.request.mode',
                                          default='')
        scheme_schedule = []
        if mode == 'by_job':
            scheme_schedule = self.env['hr.scheme.schedule.process.staff.requirement'].search([
                ('job_id', '=', self.job_id.id),
                ('mode', '=', 'by_job'),
                ('active', '=', True)
            ])
        else:
            scheme_schedule = self.env['hr.scheme.schedule.process.staff.requirement'].search([
                ('position_id', '=', self.job_id.position_id.id),
                ('mode', '=', 'by_position'),
                ('active', '=', True)
            ])

        holidays = self.env['hr.holiday'].search([])

        # Buscar en la configuración
        include_holidays_in_working_days = False
        if config_parameter.get_param('include.holidays.in.working.days.of.scheme.schedule'):
            if config_parameter.get_param('include.holidays.in.working.days.of.scheme.schedule') == 'True':
                include_holidays_in_working_days = True
            else:
                include_holidays_in_working_days = False

        start_approval_day = False
        if config_parameter.get_param('start.schedule.approval.day.of.staff.requirement.request'):
            if config_parameter.get_param('start.schedule.approval.day.of.staff.requirement.request') == 'True':
                start_approval_day = True
            else:
                start_approval_day = False

        today_date = datetime.utcnow().date()
        if not start_approval_day:
            today_date = today_date + relativedelta(days=1)

        for ss in scheme_schedule:
            date_from = today_date
            date_to = today_date + relativedelta(days=ss.working_days-1)

            if not include_holidays_in_working_days:
                date_from_copy = date_from

                while date_from_copy <= date_to:
                    if date_from_copy.weekday() > 4:
                        # Es sábado o domingo
                        date_to = date_to + relativedelta(days=1)
                    if date_from_copy in [holiday.date for holiday in holidays]:
                        # Es feriado
                        date_to = date_to + relativedelta(days=1)

                    date_from_copy = date_from_copy + relativedelta(days=1)

            psr.write({'schedule_process_staff_requirement_ids': [(0, 0, {
                'sequence': ss.sequence,
                'stage_id': ss.stage_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'employee_ids': [(6, 0, [e.id for e in ss.employee_ids])]
            })]})

            today_date = date_to + relativedelta(days=1)

        view_id = self.env.ref('hr_dr_recruitment.hr_process_staff_requirement_view_form').id
        return {'type': 'ir.actions.act_window',
                'name': 'hr.process.staff.requirement.view.form',
                'res_model': 'hr.process.staff.requirement',
                'res_id': psr.id,
                'target': 'current',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    def name_get(self):
        result = []
        for staffRequirement in self:
            result.append(
                (
                    staffRequirement.id, _("{} {} {} {} {}").format(
                        staffRequirement.employee_requests_id.name,
                        dict(self._fields['type'].selection).get(staffRequirement.type),
                        staffRequirement.job_id.name,
                        staffRequirement.department_id.name,
                        staffRequirement.date_incorporation)
                )
            )
        return result

    def get_local_context(self, id=None):
        env = self.sudo().env
        local_context = env.context.copy()
        local_context['subject'] = _("Staff requirement request")
        local_context['request'] = _("has made a staff requirement request.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = env.ref('hr_dr_management.menu_hr_management').id

        if self.quantity > 1:
            local_context['details'] = "Type staff requirement request {}. {} collaborators are required for the {} " \
                                       "job. Workplace: {} and incorporation date: {}.".format(
                self.get_name_type()[0], self.quantity, self.job_id.name, self.address_id.name,
                self.date_incorporation.strftime("%d/%m/%Y"))
        else:
            local_context['details'] = "Type staff requirement request {}. {} collaborator is required for the {} " \
                                       "job. Workplace: {} and incorporation date: {}.".format(
                self.get_name_type()[0], self.quantity, self.job_id.name, self.address_id.name,
                self.date_incorporation.strftime("%d/%m/%Y"))

        local_context['commentary'] = self.commentary
        base_url = env['ir.config_parameter'].get_param('web.base.url')
        action = env.ref('hr_dr_recruitment.'
                              'staff_requirement_request_action_notifications_to_process').read()[0].get('id')
        model = "hr.notifications"
        menu = env.ref('hr_recruitment.menu_hr_recruitment_root').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(
            base_url, id, action, model, menu)
        local_context['view_url'] = url
        return local_context

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    def _check_restrictions(self, instance=None):
        """
        Valida las restricciones que pueda tener el modelo.

        @:param instance Instancia del modelo a validar.
        """

        # Si no recibe una instancia del modelo específica asume que es la actual.
        if instance is None:
            instance = self

        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:

            years, months, days, hours, minutes = self.get_years_months_days_hours_minutes(
                instance.create_date, instance.date_incorporation)

            configurations = instance.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', instance.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=', instance.env.ref('base.module_' + instance._module).id),
                ('res_model_id', '=', instance.env['ir.model'].sudo().search([('model', '=', instance._name)]).id),
                ('current', '=', True)
            ])
            for configuration in configurations:
                if configuration.nomenclature_id.acronym == 'CMDARSRP':
                    if instance.env['ir.config_parameter'].sudo().get_param(
                            'validate.anticipation.dynamically.in.staff.requirement.request'):
                        if instance.env['ir.config_parameter'].sudo().get_param(
                                'validate.anticipation.dynamically.in.staff.requirement.request') == 'True':
                            # Validación dinámica
                            process_duration, anticipation_days, reason_anticipation_days = instance.\
                                get_process_duration(instance.job_id)
                            if days < anticipation_days and (years == 0 and months == 0):
                                raise ValidationError(_("Staff requirement request must be made at least with {} "
                                                        "anticipation days.").format(anticipation_days))
                        else:
                            # Validación fija
                            if days < configuration.integer_value and (years == 0 and months == 0):
                                raise ValidationError(
                                    _("Staff requirement request must be made at least with {} "
                                      "anticipation days.").format(configuration.integer_value))
                    else:
                        # Validación fija, se toman los dias entre la fecha de creación y la fecha de incorporación
                        # sin contar el dia que se solicita ni el que se incorpora
                        if days < configuration.integer_value and (years == 0 and months == 0):
                            raise ValidationError(
                                _("Staff requirement request must be made at least with {} "
                                  "anticipation days.").format(configuration.integer_value))

    @api.model
    def create(self, vals):
        self.validate_module()
        srr = super(StaffRequirementRequest, self).create(vals)
        self._check_restrictions(srr)
        return srr

    def write(self, vals):
        self.validate_module()
        srr = super(StaffRequirementRequest, self).write(vals)
        self._check_restrictions()
        return srr

    def unlink(self):
        self.validate_module()
        for srr in self:
            if srr.state != 'draft':
                raise ValidationError(_('You can only delete staff requirement requests in draft status.'))
        return super(StaffRequirementRequest, self).unlink()

    _TYPE = [
        ('01', _('Fixed Personnel')),
        ('02', _('Seasonal Staff')),
        ('03', _('Eventual Staff')),
        ('04', _('Intern'))
    ]
    type = fields.Selection(_TYPE, string='Type', default='01', required=True, help='')
    quantity = fields.Integer(string='Quantity', default=1, required=True)
    job_id = fields.Many2one('hr.job', string="Job", required=True)
    position_id = fields.Many2one('hr.position', string="Position", related='job_id.position_id', store=True,
                                  readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", related='job_id.department_id', store=True,
                                    readonly=True)
    address_id = fields.Many2one('res.partner', string="Job location", related='job_id.address_id', store=True,
                                 help="Address where collaborators are working", readonly=True)
    process_duration = fields.Integer(string="Duration process", compute=_compute_process_duration)
    anticipation_days = fields.Integer(string="Anticipation days to comply with the process",
                                       compute=_compute_process_duration)
    reason_anticipation_days = fields.Text(string="Reason of anticipation days", compute=_compute_process_duration)
    employee_to_replace_id = fields.Many2one('hr.employee', string="Collaborator to replace")
    date_incorporation = fields.Date(string='Incorporation date', required=True)


class ProcessStaffRequirement(models.Model):
    _name = "hr.process.staff.requirement"
    _description = 'Process staff requirement'

    def start(self):
        count = self.env['hr.process.staff.requirement'].search_count([
            ('job_id', '=', self.job_id.id),
            ('state', '=', 'in_progress'),
            ('id', '!=', self.id)
        ])
        if count > 0:
            raise ValidationError(
                _("There can only be one active process staff requirement per job."))
        else:
            self.state = 'in_progress'
            self.job_id.website_published = True
            self.job_id.set_recruit()
            return self

    def mark_as_draft(self):
        self.state = 'draft'
        self.job_id.website_published = False
        self.job_id.set_open()
        return self

    def mark_as_cancelled(self):
        self.state = 'cancelled'
        self.job_id.website_published = False
        self.job_id.set_open()
        return self

    def finalize(self):
        self.state = 'finalized'
        self.job_id.website_published = False
        self.job_id.set_open()
        return self

    def create_schedule_details(self):
        holidays = self.env['hr.holiday'].search([])
        day_global = 1
        for schedule in self.schedule_process_staff_requirement_ids:
            for detail in schedule.detail_ids:
                detail.unlink()

            date_from = schedule.date_from
            date_to = schedule.date_to
            day_stage = 1

            while date_from <= date_to:
                is_holiday = False
                if date_from.weekday() > 4:
                    # Es sábado o domingo
                    is_holiday = True
                if date_from in [holiday.date for holiday in holidays]:
                    # Es feriado
                    is_holiday = True

                self.env['hr.schedule.process.staff.requirement.detail'].create({
                    'schedule_id': schedule.id,
                    'day_stage': day_stage,
                    'day_global': day_global,
                    'calendar_day': date_from.day,
                    'is_holiday': is_holiday
                })
                day_stage += 1
                day_global += 1
                date_from = date_from + relativedelta(days=1)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'process.staff.requirement') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('process.staff.requirement') or _('New')
        result = super(ProcessStaffRequirement, self).create(vals)
        return result

    def _compute_schedule_detail(self):
        details = self.env['hr.schedule.process.staff.requirement.detail'].search([
            ('schedule_id', 'in', [schedule.id for schedule in self.schedule_process_staff_requirement_ids] ),
        ])
        self.schedule_detail_ids = details

    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: _('New'))
    staff_requirement_request = fields.Many2one('hr.staff.requirement.request', string="Staff requirement request")
    employee_requests_id = fields.Many2one('hr.employee', string="Collaborator requesting", required=True)
    user_employee_requests_id = fields.Many2one('res.users', string="User requesting",
                                                related='employee_requests_id.user_id', store=True, readonly=True)
    department_employee_requests_id = fields.Many2one('hr.department', string="Department employee requesting",
                                                      related='employee_requests_id.department_id', store=True,
                                                      readonly=True)
    user_manager_department_employee_requests_id = fields.Many2one(
        'res.users', string="User manager department employee requesting",
        related='employee_requests_id.department_id.manager_id.user_id', store=True, readonly=True)
    _TYPE = [
        ('01', _('Fixed Personnel')),
        ('02', _('Seasonal Staff')),
        ('03', _('Eventual Staff')),
        ('04', _('Intern'))
    ]
    type = fields.Selection(_TYPE, string='Type', required=True, help='')
    quantity = fields.Integer(string='Quantity', required=True)
    job_id = fields.Many2one('hr.job', string="Job", required=True)
    position_id = fields.Many2one('hr.position', string="Position", related='job_id.position_id', store=True,
                                  readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", related='job_id.department_id', store=True,
                                    readonly=True)
    address_id = fields.Many2one('res.partner', string="Job location", related='job_id.address_id', store=True,
                                 help="Address where employees are working", readonly=True)
    employee_to_replace_id = fields.Many2one('hr.employee', string="Collaborator to replace")
    date_incorporation = fields.Date(string='Incorporation date', required=True)
    schedule_process_staff_requirement_ids = fields.One2many('hr.schedule.process.staff.requirement',
                                                             'process_staff_requirement_id', string="Schedule")
    state = fields.Selection([
        ('draft', _('Draft')),
        ('in_progress', _('In Progress')),
        ('cancelled', _('Cancelled')),
        ('finalized', _('Finalized'))
    ], string='State', default='draft')
    applicant_ids = fields.One2many('hr.applicant', 'process_staff_requirement_id', string="Applicants")
    schedule_detail_ids = fields.One2many(
        'hr.schedule.process.staff.requirement.detail',
        compute='_compute_schedule_detail',
        string='Schedule detail'
    )


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    @api.model
    def create(self, vals):
        self.validate_module()
        applicant = super(Applicant, self).create(vals)

        process_staff_requirement_id = self.env['hr.process.staff.requirement'].search([
            ('job_id', '=', applicant.job_id.id),
            ('state', '=', 'in_progress')
        ], limit=1)

        if process_staff_requirement_id:
            applicant.process_staff_requirement_id = process_staff_requirement_id.id

        return applicant

    def write(self, vals):
        self.validate_module()
        return super(Applicant, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(Applicant, self).unlink()

    # @
    # def write(self, vals):
    #     res = super(Applicant, self).write(vals)
    #
    #     # Eliminando puntuaciones de etapas posteriores al retroceder la etapa.
    #     stage_id = vals.get('stage_id')
    #     if stage_id is not None:
    #         self._delete_futher_stage_score()
    #
    #     return res

    def _default_process_staff_requirement_id(self):
        process_staff_requirement_id = self.env['hr.process.staff.requirement'].search([
            ('job_id', '=', self.job_id.id),
            ('state', '=', 'in_progress')
        ], limit=1)

        if process_staff_requirement_id:
            return process_staff_requirement_id.id
        else:
            return False

    @api.onchange('job_id')
    def on_change_job_id(self):
        self.process_staff_requirement_id = self._default_process_staff_requirement_id()

    @api.depends('stage_id', 'applicant_stage_score_ids')
    def _compute_score(self):
        for rec in self:
            rec.score = rec.applicant_stage_score_ids.search([
                ('applicant_id', '=', self.id), ('stage_id', '=', rec.stage_id.id)], limit=1).score

    @api.depends('stage_id', 'applicant_stage_score_ids')
    def _inverse_score(self):
        for rec in self:
            if not rec.score: continue
            current_stage_score = rec.applicant_stage_score_ids.search([
                ('applicant_id', '=', self.id), ('stage_id', '=', rec.stage_id.id)], limit=1)
            if current_stage_score.id:
                current_stage_score.score = rec.score
            else:
                current_stage_score.sudo().create({
                    'applicant_id': rec.id,
                    'stage_id': rec.stage_id.id,
                    'score': rec.score,
                })

    # current_stage_score = self.env['hr.applicant.stage.score'].sudo().search([('applicant_id', '=', self.id), ('stage_id', '=', self.stage_id.id)], limit=1)

    # def _delete_futher_stage_score(self):
    #     """"
    #     Elimina todas las puntuaciones existentes para esta postulación en etapas superiores a la actual.
    #     """
    #
    #     if self.stage_id:
    #         sequence = self.stage_id.sequence
    #         further_scores = self.env['hr.applicant.stage.score'].sudo().search(
    #             [('applicant_id', '=', self.id),('stage_id.sequence','>',sequence)]).unlink()

    process_staff_requirement_id = fields.Many2one('hr.process.staff.requirement', string='Process staff requirement')
    applicant_stage_score_ids = fields.One2many('hr.applicant.stage.score', 'applicant_id', readonly=True,
                                                string=_('Score by stage'))
    score = fields.Selection(SCORES, string=_('Current score'), default=_DEFAULT_SCORE,
                             help=_('This is the score for the current stage of the application'),
                             compute='_compute_score', inverse="_inverse_score")


class ApplicantStageScore(models.Model):
    _name = 'hr.applicant.stage.score'
    _description = _("Applicant score by stage")
    _order = 'stage_id desc'

    @api.depends('stage_id', 'applicant_id')
    def _compute_is_applicant_current_stage_score(self):
        for rec in self:
            rec.is_applicant_current_stage_score = rec.stage_id == rec.applicant_id.stage_id

    applicant_id = fields.Many2one('hr.applicant', string=_("Applicant"), required=True, ondelete='cascade')
    stage_id = fields.Many2one('hr.recruitment.stage', string=_("Stage"), required=True, readonly=True,
                               ondelete='cascade')
    score = fields.Selection(SCORES, string=_('Score'), default=_DEFAULT_SCORE, readonly=True,
                             help=_('This is the score for the current stage of the application'))
    is_applicant_current_stage_score = fields.Boolean(compute='_compute_is_applicant_current_stage_score',
                                                      string=_('Current stage'),
                                                      help=_('This is the current state of the applicant'))


class SchemeScheduleProcessStaffRequirement(models.Model):
    _name = "hr.scheme.schedule.process.staff.requirement"
    _inherit = ['mail.thread']
    _description = 'Scheme schedule process staff requirement'
    _order = "position_id,job_id,sequence"

    def name_get(self):
        result = []
        for record in self:
            position_or_job = ""
            if record.mode == 'by_position':
                position_or_job = record.position_id.name
            else:
                position_or_job = record.job_id.name

            result.append(
                (
                    record.id, _("{} {} {} {} {}").format(
                        dict(self._fields['mode'].selection).get(record.mode),
                        position_or_job,
                        record.sequence,
                        record.stage_id.name,
                        record.working_days)
                )
            )
        return result

    _MODE = [
        ('by_position', 'By position'),
        ('by_job', 'By job'),
    ]
    mode = fields.Selection(_MODE, string='Mode', default='by_position', required=True, help='', tracking=True)
    position_id = fields.Many2one('hr.position', string='Position', tracking=True)
    job_id = fields.Many2one('hr.job', string='Job', tracking=True)
    sequence = fields.Integer(string='Sequence', required=True, tracking=True)
    stage_id = fields.Many2one('hr.recruitment.stage', string='Stage', required=True, tracking=True)
    working_days = fields.Integer(string='Number of working days', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    employee_ids = fields.Many2many('hr.employee', string="Involved")


class ScheduleProcessStaffRequirement(models.Model):
    _name = "hr.schedule.process.staff.requirement"
    _description = 'Schedule process staff requirement'
    _order = "process_staff_requirement_id,sequence"

    process_staff_requirement_id = fields.Many2one('hr.process.staff.requirement', string='Process staff requirement')
    sequence = fields.Integer(string='Sequence', required=True)
    stage_id = fields.Many2one('hr.recruitment.stage', string='Stage', required=True)
    date_from = fields.Date(string='Date from', required=True)
    date_to = fields.Date(string='Date to', required=True)
    employee_ids = fields.Many2many('hr.employee', string="Involved")
    detail_ids = fields.One2many('hr.schedule.process.staff.requirement.detail', 'schedule_id', string="Details")

    #
    # def _create_details(self):
    #
    #     self.detail_ids = [(6, 0, [])]
    #
    #     previous = self.env['hr.schedule.process.staff.requirement'].search([
    #         ('process_staff_requirement_id', '=', self.process_staff_requirement_id.id),
    #         ('sequence', '<', self.sequence),
    #         ('id', '!=', self.id),
    #     ], order='sequence')
    #
    #     holidays = self.env['hr.holiday'].search([])
    #
    #     day_global = 1
    #     if len(previous) > 0:
    #         for previou in previous:
    #             rd = relativedelta(previou.date_to, previou.date_from)
    #             day_global += rd.days
    #
    #
    #     date_from = self.date_from
    #     date_to = self.date_to
    #     day_stage = 1
    #
    #     while date_from <= date_to:
    #
    #         is_holiday = False
    #         if date_from.weekday() > 4:
    #             # Es sabado o domingo
    #             is_holiday = True
    #         if date_from in [holiday.date for holiday in holidays]:
    #             # Es feriado
    #             is_holiday = True
    #
    #         self.env['hr.schedule.process.staff.requirement.detail'].create({
    #             'schedule_id': self.id,
    #             'day_stage': day_stage,
    #             'day_global': day_global,
    #             'calendar_day': date_from.day,
    #             'is_holiday': is_holiday
    #         })
    #
    #         day_stage += 1
    #         day_global += 1
    #         date_from = date_from + relativedelta(days=1)


class ScheduleProcessStaffRequirementDetail(models.Model):
    _name = "hr.schedule.process.staff.requirement.detail"
    _description = 'Schedule process staff requirement detail'

    schedule_id = fields.Many2one('hr.schedule.process.staff.requirement', string='Schedule')
    day_stage = fields.Integer(string='Day stage')
    day_global = fields.Integer(string='Day global')
    calendar_day = fields.Integer(string='Calendar day')
    is_holiday = fields.Boolean(string='Is holiday')