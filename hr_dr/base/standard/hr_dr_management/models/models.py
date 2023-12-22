# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import pytz
from datetime import datetime
import calendar
import logging
_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = ['res.company']

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

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        return super(Company, self).create(vals_list)

    def write(self, vals):
        self.validate_module()
        return super(Company, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(Company, self).unlink()

    normative_default_id = fields.Many2one('hr.normative', string="Default regulation")


class Normative(models.Model):
    _name = "hr.normative"
    _description = 'Regulations'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    acronym = fields.Char(string="Acronym", required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='Country', help="", required=True,
                                 default=lambda x: x.env.company.country_id.id)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    link_ids = fields.One2many('hr.link', 'normative_id', string="Links")
    hour_night_ids = fields.Many2many('hr.hour.night', string="Hours night", required=False)
    hour_extra_ids = fields.Many2many('hr.hour.extra', string="Hours extra", required=False)


class Link(models.Model):
    _name = "hr.link"
    _description = 'Links'
    _inherit = ['mail.thread']

    name = fields.Char(string="Link", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    normative_id = fields.Many2one('hr.normative', string="Regulation", tracking=True)


class HourNight(models.Model):
    _name = "hr.hour.night"
    _description = 'Night hours'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    start = fields.Float(string="Start", required=True, tracking=True)
    end = fields.Float(string="End", required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    normative_ids = fields.Many2many('hr.normative', string='Regulations', required=True)


class HourExtra(models.Model):
    _name = "hr.hour.extra"
    _description = 'Extra hours'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    start = fields.Float(string="Start", required=True, tracking=True)
    end = fields.Float(string="End", required=True, tracking=True)
    assigned_schedule = fields.Boolean(string='Apply with assigned schedule', default=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    normative_ids = fields.Many2many('hr.normative', string='Regulations', required=True)


class Nomenclature(models.Model):
    _name = "hr.nomenclature"
    _description = 'Nomenclature'
    _inherit = ['mail.thread']
    _order = "module_id, name"
    _sql_constraints = [
        ('acronym_module_id_unique', 'UNIQUE (acronym, module_id)',
         _('Acronyms must be unique per module.'))
    ]

    @api.model
    def get_field_types(self):
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        return field_list

    @api.depends('module_id')
    def _compute_module_name(self):
        for record in self:
            if record.module_id:
                record.module_name = record.module_id.name
            else:
                record.module_name = ""

    _LEVEL = [
        ('for_module', _('For module')),
        ('for_model', _('For model')),
    ]
    level = fields.Selection(_LEVEL, string='Level', required=True, default='for_module', tracking=True)
    module_id = fields.Many2one('ir.module.module', string="Module", required=True, ondelete='cascade', tracking=True)
    module_name = fields.Char(string="Module name", store=True, compute=_compute_module_name)
    name = fields.Char(string="Name", required=True, tracking=True)
    acronym = fields.Char(string="Acronym", required=True, tracking=True)
    description = fields.Text(string="Description", required=True, tracking=True)
    data_type = fields.Selection(selection='get_field_types', string='Data type', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, required=True, tracking=True)


class NormativeNomenclature(models.Model):
    _name = "hr.normative.nomenclature"
    _description = 'Nomenclatures by regulations'
    _inherit = ['mail.thread']
    _order = 'normative_id, nomenclature_id, valid_from asc'

    @api.depends('valid_to')
    def _compute_current(self):
        for NN in self:
            if not NN.valid_to:
                NN.current = True
            else:
                NN.current = False

    def name_get(self):
        result = []
        for record in self:
            result.append(
                (
                    record.id, _("{} {}").format(
                        record.normative_id.acronym,
                        record.nomenclature_id.acronym)
                )
            )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        nn = super(NormativeNomenclature, self).create(vals_list)

        if nn.valid_to and nn.valid_from > nn.valid_to:
            raise UserError(_('The start date must be less than or equal to the end date.'))
        #
        # nn_ids = self.env['hr.normative.nomenclature'].search([
        #     ('normative_id', '=', nn.normative_id.id),
        #     ('nomenclature_id','=',nn.nomenclature_id.id ),
        #     ('res_model_id', '=', nn.res_model_id.id),
        #     ('res_id', '=', nn.res_id),
        #     ('id','!=',nn.id)
        # ])
        #
        # for nr in nomenclature_recruitment_ids:
        #     if nomenclatureRecruitment.valid_to == False and nr.valid_to == False:
        #         raise UserError(_("The Nomenclature: {}, already active.").format(
        #             nr.nomenclature_id.name))
        #     elif nomenclatureRecruitment.valid_to != False and nr.valid_to != False:
        #         if ((nomenclatureRecruitment.valid_from >= nr.valid_from and nomenclatureRecruitment.valid_from <= nr.valid_to) or (nomenclatureRecruitment.valid_to >= nr.valid_from and nomenclatureRecruitment.valid_to <= nr.valid_to)):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #     elif nomenclatureRecruitment.valid_to == False and nr.valid_to != False:
        #         if (nomenclatureRecruitment.valid_from >= nr.valid_from and nomenclatureRecruitment.valid_from <= nr.valid_to):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #     elif nomenclatureRecruitment.valid_to != False and nr.valid_to == False:
        #         if nr.valid_from <= nomenclatureRecruitment.valid_to:
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #         if (nr.valid_from >= nomenclatureRecruitment.valid_from and nr.valid_from <= nomenclatureRecruitment.valid_to):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))

        return nn

    def unlink(self):
        for NN in self:
            if not NN.current:
                raise ValidationError(_('Cannot delete current value of normative nomenclature.'))
        return super(NormativeNomenclature, self).unlink()

    def write(self, vals):
        record = super(NormativeNomenclature, self).write(vals)

        if self.valid_to and self.valid_from > self.valid_to:
            raise UserError(_('The start date must be less than or equal to the end date.'))
        #
        # nomenclature_ecruitment_ids = self.env['hr.normative.nomenclature.recruitment'].search([('nomenclature_id','=',self.nomenclature_id.id ),( 'id','!=',self.id )])
        #
        # for nr in nomenclature_ecruitment_ids:
        #     if self.valid_to == False and nr.valid_to == False:
        #         raise UserError(_("The Nomenclature: {}, already active.").format(
        #             nr.nomenclature_id.name))
        #     elif self.valid_to != False and nr.valid_to != False:
        #         if ((self.valid_from >= nr.valid_from and self.valid_from <= nr.valid_to) or (self.valid_to >= nr.valid_from and self.valid_to <= nr.valid_to)):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #     elif self.valid_to == False and nr.valid_to != False:
        #         if (self.valid_from >= nr.valid_from and self.valid_from <= nr.valid_to):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #     elif self.valid_to != False and nr.valid_to == False:
        #         if nr.valid_from <= self.valid_to:
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))
        #         if (nr.valid_from >= self.valid_from and nr.valid_from <= self.valid_to):
        #             raise UserError(_('A Nomenclature already exists within the specified time span.'))

        return record

    normative_id = fields.Many2one('hr.normative', string="Regulation", required=True, tracking=True)
    nomenclature_id = fields.Many2one('hr.nomenclature', string="Nomenclature", required=True, tracking=True)
    level = fields.Selection(
        string='Level', related='nomenclature_id.level', store=True)
    nomenclature_id_data_type = fields.Selection(string="Nomenclature data type", related='nomenclature_id.data_type')
    module_id = fields.Many2one('ir.module.module', string="Module", related='nomenclature_id.module_id', store=True)
    valid_from = fields.Date(string='Valid from', required=True, default=fields.Date.context_today, tracking=True)
    valid_to = fields.Date(string='Valid to', tracking=True)
    current = fields.Boolean(string='Current', store=True, compute=_compute_current)
    boolean_value = fields.Boolean(string="Boolean value", tracking=True)
    integer_value = fields.Integer(string="Integer value", tracking=True)
    float_value = fields.Float(string="Float value", tracking=True)
    char_value = fields.Char(string="Char value", tracking=True)
    date_value = fields.Date(string="Date value", tracking=True)
    res_id = fields.Integer(string='Record identifier', tracking=True)
    res_model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', tracking=True)
    res_model = fields.Char(string='Model name', related='res_model_id.model', readonly=True, store=True)


class SchemeNotifications(models.Model):
    _name = "hr.scheme.notifications"
    _description = 'Scheme notifications'
    _inherit = ['mail.thread']
    _order = "model_id,sub_model_id,employee_requests_id,level"

    @api.constrains('res_id')
    def _check_res_id(self):
        """
        - Si el campo sub_model_id tiene valor, res_id es requerido.
        - El valor de res_id tiene que ser un identificador válido para el modelo sub_model.
        """
        for rec in self:
            submodel_id = rec.sub_model_id.id
            if submodel_id:
                if not rec.res_id:
                    raise ValidationError(_("Record identifier field is required."))

                submodel_rows = self.env[rec.sub_model_id.model].sudo().search(
                    [('id', '=', rec.res_id), ('active', '=', True)]
                )
                if len(submodel_rows) == 0:
                    # Selecciono todas las filas para mostrar del objeto
                    all_submodel_rows = self.env[rec.sub_model_id.model].sudo().search(
                        [('active', '=', True)], order='id'
                    )
                    raise ValidationError(
                        _("{0} is not a valid Id for {1} submodel. \n\nValid ids for {1} are:\n {2}").format(
                            rec.res_id, rec.sub_model_id.name,
                            "\n".join(str(x.id) + ' - ' + x.name for x in all_submodel_rows)
                        )
                    )

    model_id = fields.Many2one('ir.model', string="Model", required=True, ondelete='cascade', tracking=True)
    sub_model_id = fields.Many2one('ir.model', string='Sub model', ondelete='cascade', tracking=True)
    sub_model = fields.Char(string='Sub model name', related='sub_model_id.model', readonly=True, store=True)
    res_id = fields.Integer(string='Record identifier', tracking=True)
    employee_requests_id = fields.Many2one('hr.employee', string="Collaborator requesting", required=True,
                                           tracking=True)
    employee_approve_id = fields.Many2one('hr.employee', string="Approving collaborator", required=True, tracking=True)
    level = fields.Integer(string="Level", required=True, default=1, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)


class Notifications(models.Model):
    _name = 'hr.notifications'
    _description = 'Notifications'
    _inherit = ['mail.thread']

    def _compute_notifications(self):
        if self.res_id and self.res_model and self.id:
            notifications = self.env['hr.notifications'].search([
                ('res_id', '=', self.res_id),
                ('res_model', '=', self.res_model),
                ('id', '!=', self.id),
            ], order='level')
            self.notifications_ids = notifications

    @api.depends('user_employee_approve_id', 'processed', 'state')
    def _compute_user_manageable(self):
        """
        Valida si la notificación puede ser gestionada por el usuario activo.
        """
        # Si la notificación fue procesada o no está pendiente no es gestionable
        if self.processed or self.state != 'pending':
            self.is_user_manageable = False
        else:
            self.is_user_manageable = True
            # Si el usuario no es quien debe aprobarla ni es administrador del módulo tampoco es gestionable
            # print(self._is_current_model_admin())
            if self.env.user != self.user_employee_approve_id and not self._is_current_model_admin():
                self.is_user_manageable = False

    def _is_current_model_admin(self):
        """
        Valida si el usuario actual es administrador del módulo del que se emite la notificación.
        :return: True/False
        """
        if self.res_model == 'hr.staff.requirement.request':
            return self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager')
        elif self.res_model == 'hr.vacation.planning.request' \
                or self.res_model == 'hr.vacation.execution.request':
            return self.env.user.has_group('hr_dr_vacations.hr_dr_vacations_group_supervisor') \
                    or self.env.user.has_group('hr_dr_vacations.hr_dr_vacations_group_manager')
        elif self.res_model == 'hr.permission.request':
            return self.env.user.has_group('hr_dr_permissions.hr_dr_permissions_group_supervisor') \
                   or self.env.user.has_group('hr_dr_permissions.hr_dr_permissions_group_manager')
        elif self.res_model == 'user.attendance.request' \
                or self.res_model == 'employee.hour.extra.approval.request':
            return self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_supervisor') \
                   or self.env.user.has_group('hr_dr_schedule.hr_dr_schedule_group_manager')
        elif self.res_model == 'hr.loan':
            return self.env.user.has_group('hr_dr_loan.hr_dr_loan_group_supervisor') \
                   or self.env.user.has_group('hr_dr_loan.hr_dr_loan_group_manager')
        elif self.res_model == 'hr.credit':
            return self.env.user.has_group('hr_dr_credit.hr_dr_credit_group_supervisor') \
                   or self.env.user.has_group('hr_dr_credit.hr_dr_credit_group_manager')
        return False

    def action_open(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id).get_formview_action()
        return False

    def send_mail(self, local_context):
        template = self.env.ref('hr_dr_management.email_template_aprove_reject_notification', False)
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def name_get(self):
        result = []
        for notification in self:
            result.append((
                notification.id, _("Collaborator requesting: {} Approving collaborator: {} Level: {} Status: {}").
                format(
                    notification.employee_requests_id.name, notification.employee_approve_id.name,
                    notification.level, dict(self._fields['state'].selection).get(notification.state))))
        return result

    def approve(self):
        if self.state == 'cancelled':
            raise Exception(
                _("This notification was canceled."))
        elif self.state == 'reassigned':
            raise Exception(
                _("This notification was reassigned."))
        elif self.state == 'approved':
            raise Exception(
                _("This notification was approved."))
        elif self.state == 'rejected':
            raise Exception(
                _("This notification was rejected."))
        else:
            same_level_processed = self.env['hr.notifications'].search_count([
                ('res_model', '=', self.res_model),
                ('res_id', '=', self.res_id),
                ('level', '=', self.level),
                ('state', 'in', ['approved', 'rejected']),
                ('processed', '=', True),
                ('id', '!=', self.id)
            ])
            if same_level_processed > 0:
                raise Exception(
                    _("Another responsible at the same level has already processed this request."))
            else:
                # Actualizar la notificación
                self.state = 'approved'
                self.processed = True

                same_level = self.env['hr.notifications'].search([
                    ('res_model', '=', self.res_model),
                    ('res_id', '=', self.res_id),
                    ('level', '=', self.level),
                    ('state', 'in', ['pending']),
                    ('send', '=', True),
                    ('id', '!=', self.id)
                ])
                for sl in same_level:
                    sl.processed = True

                level_up = self.env['hr.notifications'].search([
                    ('res_model', '=', self.res_model),
                    ('res_id', '=', self.res_id),
                    ('level', '=', self.level+1),
                    ('state', 'in', ['pending'])
                ])

                if len(level_up) == 0:
                    # La notificación actual era la de mayor nivel
                    # Buscar y actualizar la solicitud
                    request = self.env[self.res_model].browse(self.res_id)
                    view = request.mark_as_approved()
                    return view
                else:
                    for lup in level_up:
                        # Enviar mail a las notificaciones del nivel actual
                        if lup.res_model and lup.res_id:
                            context = lup.env[lup.res_model].browse(lup.res_id).get_local_context(lup.id)
                            lup.send_mail(context)

                        # Marcar como enviada la notificación
                        lup.send = True
        return self

    def reject(self, commentary):
        if self.state == 'cancelled':
            raise Exception(
                _("This notification was canceled."))
        elif self.state == 'reassigned':
            raise Exception(
                _("This notification was reassigned."))
        elif self.state == 'approved':
            raise Exception(
                _("This notification was approved."))
        elif self.state == 'rejected':
            raise Exception(
                _("This notification was rejected."))
        else:
            # Actualizar la notificación
            self.state = 'rejected'
            self.processed = True
            self.commentary = commentary

            same_level = self.env['hr.notifications'].search([
                ('res_model', '=', self.res_model),
                ('res_id', '=', self.res_id),
                ('level', '=', self.level),
                ('state', 'in', ['pending']),
                ('send', '=', True),
                ('id', '!=', self.id)
            ])
            for sl in same_level:
                sl.processed = True

            # Buscar y actualizar la solicitud
            request = self.env[self.res_model].browse(self.res_id)
            request.mark_as_rejected(commentary)
        return self

    scheme_notification_id = fields.Many2one('hr.scheme.notifications', string='Scheme notifications')
    level = fields.Integer(string='Level', default=1, tracking=True)
    employee_requests_id = fields.Many2one('hr.employee', string="Collaborator requesting", tracking=True)
    user_employee_requests_id = fields.Many2one('res.users', string="User collaborator requesting",
                                                related='employee_requests_id.user_id', store=True)
    employee_approve_id = fields.Many2one('hr.employee', string="Approving collaborator", tracking=True)
    user_employee_approve_id = fields.Many2one('res.users', string="User approving collaborator",
                                               related='employee_approve_id.user_id', store=True)
    parent_id = fields.Many2one('hr.notifications', string='Parent notification', readonly=True, tracking=True)
    state = fields.Selection([
        ('pending', _('Pending')),
        ('reassigned', _('Reassigned')),
        ('cancelled', _('Cancelled')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected'))
    ], string='Status', default='pending', tracking=True)
    commentary = fields.Text(string="Commentary", tracking=True)
    send = fields.Boolean(string="Send", default=False, tracking=True)
    processed = fields.Boolean(string="Processed", default=False, tracking=True)
    res_id = fields.Integer(string='Record identifier', tracking=True)
    res_model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', tracking=True)
    res_model = fields.Char(string='Model name', related='res_model_id.model', readonly=True, store=True, tracking=True)
    notifications_ids = fields.One2many('hr.notifications', compute='_compute_notifications', string='Notifications')
    is_user_manageable = fields.Boolean(compute='_compute_user_manageable')


class RejectHrNotification(models.TransientModel):
    _name = 'reject.hr.notification'
    _description = 'Reject notification'

    def action_reject(self):
        self.actual_notification.reject(self.commentary)

    actual_notification = fields.Many2one('hr.notifications',
                                          string='Actual notification', readonly=True,
                                          default=lambda self: self._context.get('active_id'))
    commentary = fields.Text(string="Commentary", required=True)


class ReassignNotification(models.TransientModel):
    _name = 'hr.reassign.notification'
    _description = 'Reassign notification'

    def action_reassign_notification(self):
        new_notification = self.env['hr.notifications'].create({
            'level': self.actual_notification.level,
            'employee_requests_id': self.actual_notification.employee_requests_id.id,
            'employee_approve_id': self.new_approver_id.id,
            'parent_id': self.actual_notification.id,
            'state': self.actual_notification.state,
            'commentary': self.actual_notification.commentary,
            'send': self.actual_notification.send,
            'processed': self.actual_notification.processed,
            'res_id': self.actual_notification.res_id,
            'res_model_id': self.actual_notification.res_model_id.id
        })
        self.actual_notification.state = 'reassigned'

        if new_notification and new_notification.send and new_notification.state == 'pending' \
                and not new_notification.processed:
            # TODO: Enviar correo relacionado a la nueva notificacion
            pass

    actual_notification = fields.Many2one('hr.notifications',
                                          string='Actual notification', readonly=True,
                                          default=lambda self: self._context.get('active_id'))
    current_approver_id = fields.Many2one('hr.employee', string="Current approver",
                                          related='actual_notification.employee_approve_id', store=True)
    new_approver_id = fields.Many2one('hr.employee', string="New approver", required=True)


class HrRequest(models.AbstractModel):
    _name = "hr.request"
    _description = 'Request'
    _inherit = ['mail.thread']

    def mark_as_draft(self):
        self.state = 'draft'
        self.date_confirmation = False
        self.user_confirmation = False
        self.reason_reject = False
        self.date_cancellation = False
        self.user_cancellation = False
        self.approval_date = False

    def cancel_request(self):
        self.state = 'cancelled'
        self.date_cancellation = datetime.utcnow()
        self.user_cancellation = self.env.uid

    def confirm_request(self):
        self.date_confirmation = datetime.utcnow()
        self.user_confirmation = self.env.uid

    def mark_as_approved(self):
        self.state = 'approved'

    def mark_as_approved_direct(self):
        self.date_confirmation = datetime.utcnow()
        self.user_confirmation = self.env.uid
        self.state = 'approved'

    def mark_as_rejected(self, reason):
        self.state = 'rejected'
        self.reason_reject = reason

    def get_years_months_days_hours_minutes(self, date_start, date_end):
        if not date_start or not date_end:
            return 0, 0, 0, 0, 0
        rd = relativedelta(date_end, date_start)
        return rd.years, rd.months, rd.days, rd.hours, rd.minutes

    def is_department_manager(self, employee):
        if employee.department_id.manager_id == employee:
            return True
        if 'hr_department_additional_manager' in self.env.registry._init_modules:
            if employee.department_id.additional_manager_ids:
                for am in employee.department_id.additional_manager_ids:
                    if employee == am:
                        return True
        return False

    def convert_time_to_utc(self, dt, tz_name=None, ui=True):
        """
        @param dt: datetime obj to convert to UTC
        @param tz_name: the name of the timezone to convert.
        In case of no tz_name passed, this method will try to find the timezone in context or the login user record.
        @param ui: Identifies if the call was made from the user interface or from a cron.

        @return: an instance of datetime object
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            if ui:
                raise ValidationError(
                    _("Local time zone is not defined. "
                      "You may need to set a time zone in collaborator or user's preferences."))
            else:
                module = self.env.ref('base.module_' + self._module)
                model = self.env['ir.model'].sudo().search([('model', 'w=', HrRequest._name)]).model
                message = _("ERROR==> Module: {}, Model: {}, Function: convert_time_to_utc(). "
                            "Local time zone is not defined. "
                            "You may need to set a time zone in collaborator or user's preferences.").format(
                    module, model)
                _logger.error(message)
                tz_name = 'America/Guayaquil'

        local = pytz.timezone(tz_name)
        local_dt = local.localize(dt, is_dst=None)
        return local_dt.astimezone(pytz.utc)

    def convert_utc_time_to_tz(self, utc_dt, tz_name=None, ui=True):
        """
        Method to convert UTC time to local time
        :param utc_dt: datetime in UTC
        :param tz_name: the name of the timezone to convert. In case of no tz_name passed,
        this method will try to find the timezone in context or the login user record
        :param ui: Identifies if the call was made from the user interface or from a cron.

        :return: datetime object presents local time
        """
        tz_name = tz_name or self._context.get('tz') or self.env.user.tz
        if not tz_name:
            if ui:
                raise ValidationError(_("Local time zone is not defined. You may need to set a time zone "
                                        "in collaborator or your user's preferences."))
            else:
                module = self.env.ref('base.module_' + self._module)
                model = self.env['ir.model'].sudo().search([('model', '=', HrRequest._name)]).model
                message = _("ERROR==> Module: {}, Model: {}, Function: convert_utc_time_to_tz(). "
                            "Local time zone is not defined. You may need to set a time zone in collaborator "
                            "or user's preferences.").format(module, model)
                _logger.error(message)
                tz_name = 'America/Guayaquil'
        tz = pytz.timezone(tz_name)
        return pytz.utc.localize(utc_dt, is_dst=None).astimezone(tz)

    _STATE = [
        ('draft', _('Draft')),
        ('pending', _('Pending')),
        ('cancelled', _('Cancelled')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    ]
    state = fields.Selection(_STATE, string='Status', default='draft', readonly=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    commentary = fields.Text(string="Commentary", tracking=True)
    date_confirmation = fields.Datetime(string='Confirmation date', readonly=True, tracking=True)
    user_confirmation = fields.Many2one('res.users', string="Confirmation user", readonly=True, tracking=True)
    reason_reject = fields.Text(string="Reason reject", readonly=True, tracking=True)
    date_cancellation = fields.Datetime(string='Cancellation date', readonly=True, tracking=True)
    user_cancellation = fields.Many2one('res.users', string="Cancellation user", readonly=True, tracking=True)
    approval_date = fields.Datetime(string='Approval date', readonly=True, tracking=True)


class HrGenericRequest(models.AbstractModel):
    _name = 'hr.generic.request'
    _description = 'Generic request'
    _inherit = ['hr.request']

    # En este dict se almacenarán los identificadores de las plantillas de correo a emplear
    # en cada clase que herede de esta.
    _hr_mail_templates = {'confirm': '', 'confirm_direct': '', 'approve': '', 'reject': '', 'cancel': '', 'paid': ''}
    # Nombre del parámetro con el modo de notificación para el módulo heredando de este.
    _hr_notifications_mode_param = ''
    # Nombre del parámetro con el administrador para el módulo heredando de este.
    _hr_administrator_param = ''
    # Nombre del parámetro con el segundo administrador para el módulo heredando de este.
    _hr_second_administrator_param = ''

    @api.depends('state', 'notification_ids')
    def compute_readonly_values(self):
        for item in self:
            if item.state == 'draft':
                item.readonly_values = False
            elif item.state == 'cancelled' or item.state == 'approved' or item.state == 'rejected':
                item.readonly_values = True
            else:
                user_id = self.env.uid
                n = self.env['hr.notifications'].search([
                    ('state', '=', 'pending'),
                    ('send', '=', True),
                    ('processed', '=', False),
                    ('res_id', '=', item.id),
                    ('res_model', '=', 'hr.loan'),
                    ('user_employee_approve_id', '=', user_id)
                ], limit=1)
                if n:
                    item.readonly_values = False
                else:
                    item.readonly_values = True

    def _compute_notifications(self):
        notifications = self.env['hr.notifications'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', self._name)
        ], order='level')
        self.notification_ids = notifications

    def get_local_context(self, id=None):
        local_context = self.sudo().env.context.copy()
        return local_context

    def mark_as_approved(self):
        result = super(HrGenericRequest, self).mark_as_approved()
        # Enviar mail de aprobación de solicitud
        self.send_mail_approve_request()
        return result

    def mark_as_rejected(self, reason):
        result = super(HrGenericRequest, self).mark_as_rejected(reason)
        # Enviar el mail de rechazo al solicitante
        self.send_mail_reject_request()
        return result

    def send_mail(self, mail_template_id):
        """
        Envía un email basado en la plantilla que recibe como parámetro.
        :param mail_template_id: El identificador de la plantilla de correo a utilizar.
        :return:
        """
        template = self.env.ref(mail_template_id, False)
        local_context = self.get_local_context()
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def send_mail_confirm_request(self):
        self.send_mail(self._hr_mail_templates['confirm'])

    def send_mail_confirm_direct_request(self):
        self.send_mail(self._hr_mail_templates['confirm_direct'])

    def send_mail_approve_request(self):
        self.send_mail(self._hr_mail_templates['approve'])

    def send_mail_cancel_request(self):
        self.send_mail(self._hr_mail_templates['cancel'])

    def send_mail_reject_request(self):
        self.send_mail(self._hr_mail_templates['reject'])

    def confirm_request(self):
        self._check_restrictions()

        notifications_mode = self.env['ir.config_parameter'].sudo().\
            get_param(self._hr_notifications_mode_param)
        administrator = int(self.env['ir.config_parameter'].sudo().
                            get_param(self._hr_administrator_param))
        second_administrator = int(self.env['ir.config_parameter'].sudo().
                                   get_param(self._hr_second_administrator_param))

        if notifications_mode == 'Without_notifications':
            super(HrGenericRequest, self).confirm_request()
            # Enviando correo de confirmación de solicitud
            self.send_mail_confirm_request()
            # Se aprueba automáticamente la solicitud y se envía el mail de aprobación
            self.mark_as_approved()
        elif notifications_mode == 'Administrator':
            super(HrGenericRequest, self).confirm_request()
            self._admin_confirm_request(administrator)
        elif notifications_mode == 'One_level_bd':
            super(HrGenericRequest, self).confirm_request()
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department)
            if level > 0:
                self.state = 'pending'
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
            else:
                # Enviando correo de aprobación automática porque no hay esquema de aprobación
                self.mark_as_approved()
        elif notifications_mode == 'One_level_br':
            super(HrGenericRequest, self).confirm_request()
            if self.employee_requests_id.parent_id:
                # Tiene un responsable
                self.state = 'pending'
                self._send_notification_to(self.employee_requests_id.parent_id.id)
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
            else:
                self.mark_as_approved()
        elif notifications_mode == 'One_level_bc':
            super(HrGenericRequest, self).confirm_request()
            if self.employee_requests_id.coach_id:
                # Tiene un monitor
                self.state = 'pending'
                self._send_notification_to(self.employee_requests_id.coach_id.id)
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
            else:
                self.mark_as_approved()
        elif notifications_mode == 'One_level_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department)
            super(HrGenericRequest, self).confirm_request()
            self._admin_confirm_request(administrator, level)
        elif notifications_mode == 'One_level_br_and_administrator':
            super(HrGenericRequest, self).confirm_request()
            manager = self.employee_requests_id.parent_id  # El responsable de quien realiza la solicitud
            if manager:
                # Tiene un responsable
                self._send_notification_to(manager.id)
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
                self._admin_confirm_request(administrator, 1)
            else:
                self._admin_confirm_request(administrator)
        elif notifications_mode == 'One_level_bc_and_administrator':
            super(HrGenericRequest, self).confirm_request()
            coach = self.employee_requests_id.coach_id  # El monitor de quien realiza la solicitud
            if coach:
                # Tiene un monitor
                self._send_notification_to(coach.id)
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
                self._admin_confirm_request(administrator, 1)
            else:
                self._admin_confirm_request(administrator)
        elif notifications_mode == 'One_level_bd_and_two_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department)
            super(HrGenericRequest, self).confirm_request()
            self._second_admin_confirm_request(administrator, second_administrator, level)
        elif notifications_mode == 'Two_levels_bd':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=1)
            super(HrGenericRequest, self).confirm_request()
            if level > 0:
                self.state = 'pending'
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
            else:
                self.mark_as_approved()
        elif notifications_mode == 'Two_levels_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=1)
            super(HrGenericRequest, self).confirm_request()
            self._admin_confirm_request(administrator, level)
        elif notifications_mode == 'All_levels_bd':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=-1)
            super(HrGenericRequest, self).confirm_request()
            if level > 0:
                self.state = 'pending'
                # Enviando correo de confirmación de solicitud
                self.send_mail_confirm_request()
            else:
                self.mark_as_approved()
        elif notifications_mode == 'All_levels_bd_and_administrator':
            department = self.employee_requests_id.department_id
            level = self._send_notifications_bd(department, propagate=-1)
            super(HrGenericRequest, self).confirm_request()
            self._admin_confirm_request(administrator, level)
        elif notifications_mode == 'Personalized':
            super(HrGenericRequest, self).confirm_request()
            self._do_personalized_notifications_mode()
        return self

    def confirm_request_direct(self):
        self.mark_as_approved_direct()
        self.send_mail_confirm_direct_request()

    def mark_as_draft(self):
        super(HrGenericRequest, self).mark_as_draft()

        notifications = self.env['hr.notifications'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', self._name)
        ], order='level')

        if notifications:
            notifications.unlink()

    def cancel_request(self):
        super(HrGenericRequest, self).cancel_request()

        # Iterar por las notificaciones asociadas y cancelarlas
        notification_ids = self.env['hr.notifications'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('state', '=', 'pending'),
            ('processed', '=', False)
        ])
        for notification in notification_ids:
            notification.state = 'cancelled'

        # Enviar mail de cancelación de solicitud
        self.send_mail_cancel_request()

        return self

    def _do_personalized_notifications_mode(self):
        esqueme_notifications = self.env['hr.scheme.notifications'].sudo().search([
            ('active', '=', True),
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('model_id', '=', self.env['ir.model'].sudo().search([('model', '=', self._name)]).id)
        ], order='level asc')
        if len(esqueme_notifications) == 0:
            self.mark_as_approved()
        else:
            self.state = 'pending'
            # Enviando correo de confirmación de solicitud
            self.send_mail_confirm_request()
            for en in esqueme_notifications:
                self._send_notification_to(en.employee_approve_id.id, en.level - 1)

    def _send_notification_to(self, employee_id, level=0):
        """
        Crea la notificación al usuario recibido como parámetro.
        Si la notificación es de primer nivel, envía un email al usuario.

        :param employee_id: Identificador del colaborador que aprueba la notificación.
        :param level: Nivel de aprobación que ya tiene la petición (un nivel menos que el que tendrá esta notificación).
        """

        notification = self.env['hr.notifications'].create({
            'level': level + 1,
            'employee_requests_id': self.employee_requests_id.id,
            'employee_approve_id': employee_id,
            'state': 'pending',
            'send': True if not level else False,
            'res_id': self.id,
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
        })

        if not level:
            # Enviar email de aprobación / denegación solo si el colaborador tiene el primer nivel de notificación.
            notification.send_mail(self.get_local_context(notification.id))

    def _send_notifications_bd(self, department, propagate=0, level=0):
        """
        Crea las notificaciones basadas en departamentos para cada administrador de departamento y administradores
        adicionales según los niveles de propagación que se hayan definido.

        Por defecto se enviará una notificación al o a los administradores de departamento de jerarquía inmediata
        superior a quien realiza la solicitud.

        :param department: Departamento a notificar.
        :param propagate: Número de niveles a propagar la notificación. Si el campo 'propagate' tiene un valor positivo,
            esta notificación se extenderá a tantos niveles por encima del departamento ya enviado como se indique en el
            valor (siempre que estos existan). Si el valor de 'propagate' es negativo, entonces la notificación se
            extenderá a todos los niveles superiores al departamento.
        :param level: Nivel de la útlima notificación realizada.

        :return: Retorna un número indicando los niveles de notificación completados.
        """

        scheme_exists = False
        superior_department = department.parent_id

        if self.employee_requests_id.department_id == department and self.is_department_manager(
                self.employee_requests_id):
            # El usuario pertenece a este departamento y es el administrador o uno de los administradores adicionales
            # del mismo.

            if superior_department:
                # La notificación se realiza en el dpto. superior
                level = self._send_notifications_bd(superior_department, propagate)
        else:
            superior_manager = department.manager_id  # Responsable del departamento
            if superior_manager:
                # Existe responsable superior
                scheme_exists = True
                self._send_notification_to(superior_manager.id, level)

            # Verificamos que este instaldo el modulo 'hr_dr_department_additional_manager' y por ende exista el campo
            # 'additional_manager_ids'
            if 'hr_dr_department_additional_manager' in self.env.registry._init_modules:
                additional_managers = department.additional_manager_ids
                if additional_managers:
                    for additional_manager in additional_managers:
                        scheme_exists = True
                        self._send_notification_to(additional_manager.id, level)

            if scheme_exists:
                level += 1
                if propagate != 0:
                    # Existe una estructura superior y las notificaciones aún deben propagarse hacia el nivel superior.
                    level = self._send_notifications_bd(superior_department, propagate - 1, level)

        return level

    def _admin_confirm_request(self, administrator, level=0):
        """
        Gestiona el cambio de estado de la notificación y el envío de correos electrónicos cuando el modo de
        notificación incluye al administrador.

        :param administrator: Identificador del administrador.
        :param level: Nivel de la última notificación realizada.
        """

        admin_made_request = self.employee_requests_id.id.__str__() == administrator

        if not level and admin_made_request:
            # El único nivel de aprobación es del administrador y este es quien realizó la solicitud.
            self.mark_as_approved()
        else:
            self.state = 'pending'

            # Enviando correo de confirmación de solicitud
            self.send_mail_confirm_request()

            # Si el administrador realizó la petición no lo incluyo en los niveles de aprobación
            if not admin_made_request:
                self._send_notification_to(administrator, level)

    def _second_admin_confirm_request(self, administrator, second_administrator, level=0):

        first_admin_made_request = self.employee_requests_id.id.__str__() == administrator

        self.state = 'pending'
        # Enviando correo de confirmación de solicitud
        self.send_mail_confirm_request()
        # Si el administrador realizó la petición no lo incluyo en los niveles de aprobación
        if not first_admin_made_request:
            self._send_notification_to(administrator, level)
            level += 1

        second_admin_made_request = self.employee_requests_id.id.__str__() == second_administrator
        # Si el administrador realizó la petición no lo incluyo en los niveles de aprobación
        if not second_admin_made_request:
            self._send_notification_to(second_administrator, level)

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
            pass

    def _check_restrictions_create_edit(self, instance=None):
        if instance is None:
            instance = self
        create_edit_without_restrictions = self._context.get('create_edit_without_restrictions')
        if not create_edit_without_restrictions:
            pass

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

    @api.model_create_multi
    def create(self, vals_list):
        self.validate_module()
        res = super(HrGenericRequest, self).create(vals_list)
        self._check_restrictions_create_edit(res)
        return res

    def write(self, vals):
        self.validate_module()
        res = super(HrGenericRequest, self).write(vals)
        self._check_restrictions_create_edit()
        return res

    def unlink(self):
        self.validate_module()
        return super(HrGenericRequest, self).unlink()

    def get_mode_by_code(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            return rule_process.mode
        else:
            return ""

    def get_rule_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            if rule_process.salary_rule_code:
                return rule_process.salary_rule_code.split(',')
            else:
                raise ValidationError(_('You must specify the comma-separated salary rule codes that are used '
                                        'in the process whose code is {}.').format(code))
        else:
            return []

    def get_rule_excluded_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            if rule_process.salary_rule_code_excluded:
                return rule_process.salary_rule_code_excluded.split(',')
            else:
                return []
        else:
            return []

    def get_category_by_process(self, code):
        rule_process = self.env['hr.salary.rule.process'].sudo().search([
            ('code', '=', code)
        ], limit=1)
        if rule_process:
            if rule_process.category_code:
                return rule_process.category_code.split(',')
            else:
                raise ValidationError(_('You must specify the comma-separated category codes that are used '
                                        'in the process whose code is {}.').format(code))
        else:
            return []

    def get_income(self, employee, date_from, date_to):
        pass

    def get_historical(self, year, provision_type, payment_type, employee):
        pass

    employee_requests_id = fields.Many2one(
        'hr.employee', string="Collaborator", required=True,
        tracking=True, ondelete='cascade')
    user_employee_requests_id = fields.Many2one(
        'res.users', string="User", related='employee_requests_id.user_id', store=True, tracking=True)
    # Departamento al que pertenecía el colaborador al momento de realizar la solicitud.
    department_employee_requests_id = fields.Many2one(
        'hr.department', string="Department",
        readonly=True, store=True, tracking=True,
        help="Department to which the collaborator belonged at the time of making the request.")
    # Puesto de trabajo asignado al colaborador al momento de realizar la solicitud.
    job_position = fields.Many2one(
        'hr.job', string="Job position",
        readonly=True, store=True, tracking=True,
        help="Job position assigned to the collaborator at the time of making the request.")  # Puesto de trabajo
    user_manager_department_employee_requests_id = fields.Many2one(
        'res.users', string="Manager", help="User manager department collaborator requesting",
        related='employee_requests_id.department_id.manager_id.user_id', store=True, tracking=True)
    notification_ids = fields.One2many('hr.notifications', compute='_compute_notifications', string='Notifications')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id')
    readonly_values = fields.Boolean(string='Readonly values', compute=compute_readonly_values)


class Holiday(models.Model):
    _name = "hr.holiday"
    _description = 'Holidays'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    date = fields.Date(string='Date', required=True, tracking=True)


class AttendancePeriod(models.Model):
    _name = "hr.attendance.period"
    _description = 'Attendance period'
    _inherit = ['mail.thread']
    _order = "start desc"

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'

    def name_get(self):
        result = []
        for ap in self:
            start = ap.start.strftime(self.get_date_format())
            end = ap.end.strftime(self.get_date_format())
            result.append(
                (
                    ap.id,
                    _("{} - {}").format(start, end)
                )
            )
        return result

    def action_close_period(self):
        self.state = 'closed'
        return self

    def _cron_create_attendance_period(self):
        attendance_period = self.search([], limit=1, order="start desc")
        cutoff_day_reports = int(self.env['ir.config_parameter'].sudo().get_param('cutoff.day.reports', '-1'))
        if attendance_period:
            current_date = datetime.utcnow()
            tz_name = self._context.get('tz') or self.env.user.tz
            if not tz_name:
                module = self.env.ref('base.module_' + self._module)
                model = self.env['ir.model'].sudo().search([('model', '=', AttendancePeriod._name)]).model
                message = _(
                    "ERROR==> Module: {}, Model: {}, Function: _cron_create_attendance_period(). "
                    "Local time zone is not defined.").format(
                    module, model)
                _logger.error(message)
                tz_name = 'America/Guayaquil'
                tz = pytz.timezone(tz_name)
                current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                current_date = current_date.date()
            else:
                tz = pytz.timezone(tz_name)
                current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                current_date = current_date.date()
            if current_date >= attendance_period.end:
                if cutoff_day_reports == -1:
                    date_start = attendance_period.end + relativedelta(days=1)
                    max_days_month = calendar.monthrange(date_start.year, date_start.month)[1]
                    date_end = date_start + relativedelta(day=max_days_month)
                    self.create({
                        'start': date_start,
                        'end': date_end,
                        'state': 'open',
                    })
                else:
                    date_start = attendance_period.end + relativedelta(days=1)
                    date_end = date_start + relativedelta(month=date_start.month + 1, day=attendance_period.end.day)
                    self.create({
                        'start': date_start,
                        'end': date_end,
                        'state': 'open',
                    })
        else:
            # Crear el primer período
            if cutoff_day_reports == -1:
                current_date = datetime.utcnow()
                tz_name = self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    module = self.env.ref('base.module_' + self._module)
                    model = self.env['ir.model'].sudo().search([('model', '=', AttendancePeriod._name)]).model
                    message = _(
                        "ERROR==> Module: {}, Model: {}, Function: _cron_create_attendance_period(). "
                        "Local time zone is not defined.").format(
                        module, model)
                    _logger.error(message)
                    tz_name = 'America/Guayaquil'
                    tz = pytz.timezone(tz_name)
                    current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                    current_date = current_date.date()
                else:
                    tz = pytz.timezone(tz_name)
                    current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                    current_date = current_date.date()
                date_start = current_date + relativedelta(day=1)
                max_days_month = calendar.monthrange(current_date.year, current_date.month)[1]
                date_end = current_date + relativedelta(day=max_days_month)
                self.create({
                    'start': date_start,
                    'end': date_end,
                    'state': 'open',
                })
            else:
                current_date = datetime.utcnow()
                tz_name = self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    module = self.env.ref('base.module_' + self._module)
                    model = self.env['ir.model'].sudo().search([('model', '=', AttendancePeriod._name)]).model
                    message = _(
                        "ERROR==> Module: {}, Model: {}, Function: _cron_create_attendance_period(). "
                        "Local time zone is not defined.").format(
                        module, model)
                    _logger.error(message)
                    tz_name = 'America/Guayaquil'
                    tz = pytz.timezone(tz_name)
                    current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                    current_date = current_date.date()
                else:
                    tz = pytz.timezone(tz_name)
                    current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                    current_date = current_date.date()
                if current_date.day > int(cutoff_day_reports):
                    date_start = current_date + relativedelta(day=int(cutoff_day_reports)+1)
                    date_end = current_date + relativedelta(month=current_date.month+1, day=int(cutoff_day_reports))
                    self.create({
                        'start': date_start,
                        'end': date_end,
                        'state': 'open',
                    })
                else:
                    date_start = current_date - relativedelta(months=1)
                    date_start = date_start + relativedelta(day=int(cutoff_day_reports)+1)
                    date_end = current_date + relativedelta(day=int(cutoff_day_reports))
                    self.create({
                        'start': date_start,
                        'end': date_end,
                        'state': 'open',
                    })

    start = fields.Date(string="Start", required=True, tracking=True)
    end = fields.Date(string="End", required=True, tracking=True)
    state = fields.Selection([
        ('open', _('Open')),
        ('closed', _('Closed')),
    ], string='Status', default='open', tracking=True)