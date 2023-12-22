# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, time, timedelta
import pytz
from odoo.exceptions import UserError, ValidationError


def float_to_time(float_time):
    """
    Recibe un float representando una hora. La parte entera del número representa las horas y la fraccionaria los
    minutos. Devuelve dos números enteros: las horas y los minutos.

    :param float_time: Representación numérica de la hora
    :return: (int, int) Las horas y minutos representados
    """
    hours = int(float_time)
    minutes = round((float_time - hours) * 60)
    return hours, minutes


class Employee(models.Model):
    _inherit = 'hr.employee'
    permission_request_ids = fields.One2many('hr.permission.request', 'employee_requests_id',
                                             string="Permission request", readonly=True)


class PermissionType(models.Model):
    _name = "hr.permission.type"
    _description = 'Permission type'

    name = fields.Char(string="Name", required=True)
    acronym = fields.Char(string="Acronym", required=True)
    description = fields.Text(string="Description")
    normative_ids = fields.Many2many('hr.normative', string='Regulations')
    active = fields.Boolean(string='Active', default=True)
    _TYPE = [
        ('permission', 'Permission'),
        ('license_paid', 'Paid license'),
        ('license_unpaid', 'Non paid license'),
        ('sevice_commission_paid', 'Paid service commission'),
        ('sevice_commission_unpaid', 'Non paid service commission')
    ]
    type = fields.Selection(_TYPE, string='Type', help='')
    legal_detail_ids = fields.One2many('permission.type.legal.detail', 'permission_type_id', string="Legal details")

    def get_type_value(self, key):
        """
        Dada una clave de la lista de selección ´type´, devuelve el valor para esa clave.

        :param key: Clave del campo ´type´, por ejemplo: permission, license_paid, etc.
        :return: El valor asignado a la clave, por ejemplo: Permiso, Licencia con remuneración, etc.
        """
        for type_key, type_val in self._TYPE:
            if type_key == key:
                return type_val


class PermissionTypeLegalDetail(models.Model):
    _name = "permission.type.legal.detail"
    _description = 'Permission type legal detail'

    permission_type_id = fields.Many2one('hr.permission.type', string=_('Permission type'), required=True)
    normative_id = fields.Many2one('hr.normative', string=_('Regulation'), required=True)
    legal_detail = fields.Text(string="Legal detail", required=True)


class Normative(models.Model):
    _inherit = 'hr.normative'
    permission_type_ids = fields.Many2many('hr.permission.type', string="Permissions", required=False)


class PermissionShift(models.Model):
    """
    Clase que relaciona los permisos con los turnos de los colaboradores para recuperación de tiempo.
    """
    _name = "hr.permission.shift"
    _description = "Relation table between permissions and shifts."
    _rec_name = "shift_id"
    _order = "shift_id"

    permission_request_id = fields.Many2one('hr.permission.request', string=_('Permission request'))
    recovery_time = fields.Float(string=_("Time"), required=True)
    shift_id = fields.Many2one('hr.employee.shift', string=_("Shift"))


class PermissionRequest(models.Model):
    _name = "hr.permission.request"
    _description = 'Permission request'
    _order = "department_employee_requests_id,employee_requests_id,permission_type_id,state,date_from"
    _inherit = ['hr.generic.request']

    _hr_mail_templates = \
        {
            'confirm': 'hr_dr_permissions.email_template_confirm_permission_request',
            'confirm_direct': 'hr_dr_permissions.email_template_confirm_direct_permission_request',
            'approve': 'hr_dr_permissions.email_template_confirm_approve_permission_request',
            'reject': 'hr_dr_permissions.email_template_confirm_reject_permission_request',
            'cancel': 'hr_dr_permissions.email_template_confirm_cancel_permission_request'
        }

    _hr_notifications_mode_param = 'permission.notifications.mode'
    _hr_administrator_param = 'permission.notifications.administrator'
    _hr_second_administrator_param = 'permission.notifications.second.administrator'

    def _get_permission_types(self):
        """
        Obtiene los tipos de permiso a mostrar según el rol del usuario autenticado.
        Esta función valida el nomenclador 'Visible para Colaboradores'.
        :return: Array con los identificadores de los tipos de permisos a mostrar.
        """

        # Si el usuario es supervisor o administrador del módulo, muestra todos los permisos de su Normativa.
        if self.env.user.has_group('hr_dr_permissions.hr_dr_permissions_group_supervisor') \
                or self.env.user.has_group('hr_dr_permissions.hr_dr_permissions_group_manager'):
            return [x.id for x in self._default_employee().normative_id.permission_type_ids]
        # Solo muestra los permisos 'Visibles Para Colaboradores' a otros grupos de usuarios.
        else:
            return [x.res_id for x in self.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', self._default_employee().normative_id.id),
                ('nomenclature_id.module_id', '=', self.env.ref('base.module_' + self._module).id),
                ('nomenclature_id.acronym', '=', 'VPC'),
                ('boolean_value', '=', True),
                ('res_model_id', '=', self.env['ir.model'].sudo().search([('model', '=', PermissionType._name)]).id),
                ('current', '=', True)
            ])]

    def _compute_notifications(self):
        # Si la solicitud es hija de otra, mostrará el esquema de notificación de su padre.
        if self.parent_id.id:
            id = self.parent_id.id
        else:
            id = self.id

        notifications = self.env['hr.notifications'].search([
            ('res_id', '=', id),
            ('res_model', '=', self._name)
        ], order='level')
        self.notification_ids = notifications

    @api.depends('date_from', 'start')
    def _compute_datetime_from(self):
        for rec in self:
            if rec.date_from and rec.start:
                rec.datetime_from = rec._get_datetime(rec.date_from, rec.start, adjust_local_timezone=True)

    @api.depends('date_to', 'end')
    def _compute_datetime_to(self):
        for rec in self:
            if rec.date_to and rec.end:
                rec.datetime_to = rec._get_datetime(rec.date_to, rec.end, adjust_local_timezone=True)

    def _compute_allow_attach(self):
        """"
        Valida si el usuario puede o no adicionar una justificación adjunta en la solicitud.
        Esta función valida el tiempo máximo permitido después de la incorporación para presentar justificación.
        """

        for rec in self:
            # Solo para peticiones en estado aprobado.
            if rec.state == 'approved':
                configs = rec.env['hr.normative.nomenclature'].search([
                    ('normative_id', '=', rec._default_employee().normative_id.id),
                    ('nomenclature_id.module_id', '=', rec.env.ref('base.module_' + self._module).id),
                    ('nomenclature_id.acronym', '=', 'TMPDDLIPPJ'),
                    ('res_model_id', '=', rec.env['ir.model'].sudo().search([('model', '=', PermissionType._name)]).id),
                    ('res_id', '=', rec.permission_type_id.id),
                    ('current', '=', True)
                ])

                for config in configs:
                    allowed_hours = config.integer_value
                    return_datetime = self._get_datetime(rec.date_to, rec.end)
                    # Hallo la diferencia entre la fecha actual y la de fin del permiso.
                    time_difference = datetime.now() - return_datetime
                    # Calculo diferencia en horas
                    hours_beween = int(time_difference.total_seconds() / 3600)

                    # Si el tiempo permitido para la solicitud no es 0 y es mayor o igual al tiempo transcurrido
                    if allowed_hours != 0 and allowed_hours >= hours_beween:
                        rec.allow_attach = True
                        return
            elif rec.state == 'draft':
                rec.allow_attach = True
                return

            rec.allow_attach = False
            return

        # Por defecto, cuando se crea una nueva solicitud, permitir los adjuntos.
        self.allow_attach = True

    def is_day_by_day(self):
        """
        Revisa si el nomenclador DÍA A DÍA está activo para este tipo de notificaciones.

        :return: True si el nomenclador está activo, de lo contrario False
        """

        for rec in self:
            configs = rec.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', rec._default_employee().normative_id.id),
                ('nomenclature_id.module_id', '=', rec.env.ref('base.module_' + self._module).id),
                ('nomenclature_id.acronym', '=', 'DD'),
                ('boolean_value', '=', True),
                ('res_model_id', '=', rec.env['ir.model'].sudo().search([('model', '=', PermissionType._name)]).id),
                ('res_id', '=', rec.permission_type_id.id),
                ('current', '=', True)
            ])

            if len(configs) > 0:
                return True
        return False

    def _create_child_requests(self):
        """
        Crea los permisos diarios hijos de un permiso con el nomenclador Día a Día y más de un día de duración.
        """

        # Si tiene habilitado el nomenclador DÍA A DÍA:
        if self.is_day_by_day():
            # Hallo la cantidad de días de duración del permiso
            datetime_from = self._get_datetime(self.date_from, 0)
            datetime_to = self._get_datetime(self.date_to, 0)
            days_between = (datetime_to - datetime_from).days

            # Si el permiso es por más de un día creo un nuevo permiso para cada día
            # y le asigno como parent este permiso.
            if days_between > 0:
                for i in range(days_between + 1):
                    current_date = (datetime_from + timedelta(days=i)).date()
                    self.copy({
                        'date_from': current_date,
                        'date_to': current_date,
                        'parent_id': self.id,
                        'state': 'approved',
                    })

                self.is_head = True

    @api.constrains('state')
    def _constrain_state(self):
        if self.state == 'approved':
            self._create_child_requests()
            self._add_recovered_time()

    def is_recoverable_time(self):
        """
        Revisa si el nomenclador RECUPERAR TIEMPO OCUPADO EN EL PERMISO está activo para este tipo de notificaciones.
        :return: True si el nomenclador está activo, de lo contrario False
        """
        for rec in self:
            configs = rec.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', rec._default_employee().normative_id.id),
                ('nomenclature_id.module_id', '=', rec.env.ref('base.module_' + self._module).id),
                ('nomenclature_id.acronym', '=', 'RTOEEP'),
                ('boolean_value', '=', True),
                ('res_model_id', '=', rec.env['ir.model'].sudo().search([('model', '=', PermissionType._name)]).id),
                ('res_id', '=', rec.permission_type_id.id),
                ('current', '=', True)
            ])

            if len(configs) > 0:
                return True
        return False

    def _add_recovered_time(self):
        """
        Recorre todas las líneas de recuperación de tiempo y adiciona en cada turno de la línea el tiempo definido
        para ella.
        Para ello el usuario que ejecute la llamada a este método debe tener permisos para modificar el modelo
        "hr.employee.shift".
        """
        if self.is_recoverable_time():
            for line in self.permission_shift_ids:
                hours, minutes = float_to_time(line.recovery_time)
                line.shift_id.planned_end = line.shift_id.planned_end + timedelta(minutes=minutes, hours=hours)
        else:
            # Si no recupera tiempo, pero tiene asociados objetos hr.permission.shift, elimino dichos objetos
            for line in self.permission_shift_ids:
                line.unlink()

    @api.depends('datetime_from', 'datetime_to', 'permission_type_id')
    def _compute_total_time_to_recover(self):
        for rec in self:
            if rec.is_recoverable_time():
                if rec.datetime_from and rec.datetime_to:
                    if rec.is_day_by_day():
                        minutes_to_recover = 0
                        start = rec.datetime_from
                        end = datetime.combine(rec.datetime_from.date(), rec.datetime_to.time())

                        if rec.datetime_from < rec.datetime_to:  # No me interesa calcular cuando las fechas están mal
                            while end != rec.datetime_to:
                                minutes_to_recover += rec.get_permission_time(start, end)
                                start += timedelta(days=1)
                                end += timedelta(days=1)

                            # Ejecuto el cálculo 1 vez más para el último día.
                            if end == rec.datetime_to:
                                minutes_to_recover += rec.get_permission_time(start, end)
                    else:
                        minutes_to_recover = rec.get_permission_time()
                    hours = int(minutes_to_recover / 60)
                    minutes = round(minutes_to_recover % 60)
                    rec.time_to_recover = hours + (minutes / 60)
                else:
                    rec.time_to_recover = 0
            else:
                rec.time_to_recover = 0

    @api.depends('permission_shift_ids')
    def _compute_planned_time_to_recover(self):
        for rec in self:
            if rec.is_recoverable_time():
                rec.planned_time_to_recover = sum(line.recovery_time for line in rec.permission_shift_ids)
            else:
                rec.planned_time_to_recover = 0

    @api.depends('permission_type_id')
    def _compute_recovers_time(self):
        for rec in self:
            # Para el caso de un permiso día a día que sea también recuperable, el tiempo a recuperar solo se mostrará
            # en la notificación padre y no en las hijas.
            if rec.is_day_by_day():
                rec.recovers_time = rec.is_recoverable_time() and not rec.parent_id
            else:
                rec.recovers_time = rec.is_recoverable_time()

    def _validate_time_to_recover(self):
        """
        Valida que el tiempo a recuperar total sea igual a la suma de los intervalos planificados a recuperar.
        """
        for rec in self:
            if rec.is_recoverable_time():
                # if rec.time_to_recover and rec.planned_time_to_recover:
                if round(1000 * rec.time_to_recover) != round(1000 * rec.planned_time_to_recover):
                    raise ValidationError(_("Please, check time recovery field. \nThe sum of the planned time to "
                                            "recover must be exactly the total time spent in the permission."))

    def get_permission_time(self, datetime_start=None, datetime_end=None):
        """
        Calcula la intersección entre el tiempo del permiso solicitado y los turnos de trabajo del colaborador y devuelve
        la diferencia resultante.
        :return: Cantidad de minutos de los turnos de trabajo a emplear en el permiso.
        """
        if datetime_start is None:
            datetime_start = self.datetime_from
        if datetime_end is None:
            datetime_end = self.datetime_to

        employee_shifts = self.env['hr.employee.shift'].sudo().search([
            ('employee_id', '=', self.employee_requests_id.id),
            '|', '|', '&', ('planned_end', '<=', datetime_end), ('planned_end', '>', datetime_start),
            '&', ('planned_start', '>=', datetime_start), ('planned_start', '<', datetime_end),
            '&', ('planned_start', '<=', datetime_start), ('planned_end', '>=', datetime_end)

        ], order='planned_start asc')

        permission_time = 0
        for shift in employee_shifts:
            start = datetime_start if shift.planned_start < datetime_start else shift.planned_start
            end = datetime_end if shift.planned_end > datetime_end else shift.planned_end
            permission_time += (end - start).total_seconds() / 60
        return permission_time

    def approve(self):
        approved = super(PermissionRequest, self).approve()
        self._create_child_requests()
        self._add_recovered_time()
        return approved

    def name_get(self):
        result = []
        for permissionRequest in self:
            result.append(
                (
                    permissionRequest.id,
                    _("{} {} {}").format(permissionRequest.employee_requests_id.name,
                                         permissionRequest.permission_type_id.name,
                                         dict(self._fields['state'].selection).get(permissionRequest.state))
                )
            )
        return result

    def get_local_context(self, id=None):
        local_context = self.env.context.copy()

        type_string = PermissionType.get_type_value(PermissionType, self.permission_type_id.type).lower()
        local_context['subject'] = _("{} request".format(type_string))
        local_context['request'] = _("has made a {} request.".format(type_string))
        # if self.permission_type_id.type == 'permission':
        #     local_context['subject'] = _("Solicitud de permiso")
        #     local_context['request'] = _("ha realizado una solicitud de permiso.")
        # elif self.permission_type_id.type == 'license_paid':
        #     local_context['subject'] = _("Solicitud de licencia pagada")
        #     local_context['request'] = _("ha realizado una solicitud de licencia pagada.")
        # elif self.permission_type_id.type == 'license_unpaid':
        #     local_context['subject'] = _("Solicitud de licencia no pagada")
        #     local_context['request'] = _("ha realizado una solicitud de licencia no pagada.")
        # elif self.permission_type_id.type == 'sevice_commission_paid':
        #     local_context['subject'] = _("Solicitud de comisión de servicios pagada")
        #     local_context['request'] = _("ha realizado una solicitud de comisión de servicios pagada.")
        # elif self.permission_type_id.type == 'sevice_commission_unpaid':
        #     local_context['subject'] = _("Solicitud de comisión de servicios no pagada")
        #     local_context['request'] = _("ha realizado una solicitud de comisión de servicios no pagada.")
        local_context['db'] = self.sudo()._cr.dbname
        local_context['model'] = "hr.notifications"
        local_context['id'] = id
        local_context['action'] = self.env.ref('hr_dr_management.notifications_list_action').read()[0].get('id')
        local_context['menu_id'] = self.env.ref('hr_dr_management.menu_hr_management').id

        local_context['details'] = "Solicitud de {} de tipo {}, desde el {} hasta el {} en el horario comprendido " \
                                   "entre {} y {}.".format(
            PermissionType.get_type_value(PermissionType, self.permission_type_id.type).lower(),
            self.permission_type_id.name,
            self.date_from.strftime("%d/%m/%Y"),
            self.date_to.strftime("%d/%m/%Y"),
            '{0:02.0f}:{1:02.0f}'.format(*divmod(float(self.start) * 60, 60)),
            '{0:02.0f}:{1:02.0f}'.format(*divmod(float(self.end) * 60, 60))
        )

        local_context['dates'] = {
            'start': '{0:02.0f}:{1:02.0f}'.format(*divmod(float(self.start) * 60, 60)),
            'end': '{0:02.0f}:{1:02.0f}'.format(*divmod(float(self.end) * 60, 60))
        }

        local_context['commentary'] = self.commentary

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('hr_dr_permissions.permission_request_action_notifications_to_process').read()[0].get(
            'id')
        model = "hr.notifications"
        menu = self.env.ref('hr_dr_permissions.menu_hr_permission').id
        url = "{}/web#id={}&action={}&model={}&view_type=form&menu_id={}".format(base_url, id, action, model, menu)
        local_context['view_url'] = url

        return local_context

    def confirm_permission_request_direct(self):
        # Función solo para el administrador del módulo. No valida las configuraciones del módulo.
        # No sigue un esquema de aprobación, se considera aprobada directamente.
        self.mark_as_approved_direct()
        # TODO: Revisar la plantilla para confirmar la solicitud
        mail_id_confirm_request = 'hr_dr_permissions.email_template_confirm_direct_approve_permission_request'
        self.send_mail(mail_id_confirm_request)
        return self

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

            # Intervalo de tiempo del permiso solicitado.
            years, months, days, hours, minutes = self.get_years_months_days_hours_minutes(
                instance.date_from, instance.date_to)

            # Intervalo de tiempo entre la fecha en que iniciará el permiso y la fecha de ingreso a la empresa.
            years_a, months_a, days_a, hours_a, minutes_a = self.get_years_months_days_hours_minutes(
                instance.employee_requests_id.last_company_entry_date, instance.date_from)

            # Intervalo de tiempo entre la fecha en que iniciará el permiso y la fecha en que se realiza la solicitud.
            years_c_f, months_c_f, days_c_f, hours_c_f, minutes_c_f = self.get_years_months_days_hours_minutes(
                instance.create_date, instance.date_from)

            configurations = instance.env['hr.normative.nomenclature'].search([
                ('normative_id', '=', instance.employee_requests_id.normative_id.id),
                ('nomenclature_id.module_id', '=', instance.env.ref('base.module_' + instance._module).id),
                (
                'res_model_id', '=', instance.env['ir.model'].sudo().search([('model', '=', PermissionType._name)]).id),
                ('res_id', '=', instance.permission_type_id.id),
                ('current', '=', True)
            ])

            for conf in configurations:
                if conf.nomenclature_id.acronym == 'TMPEMI':
                    if (minutes > conf.integer_value2) or (
                            minutes <= conf.integer_value2 and (years > 0 or months > 0 or days > 0 or hours > 0)):
                        raise ValidationError(
                            _("El tiempo máximo permitido para el tipo de permiso: {} "
                              "y regulación: {} es: {} minuto(s).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name,
                                conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'TMPEH':
                    if (hours > conf.integer_value2) or (
                            hours <= conf.integer_value2 and (years > 0 or months > 0 or days > 0 or minutes > 0)):
                        raise ValidationError(
                            _("El tiempo máximo permitido para el tipo de permiso: {} "
                              "y regulación: {} es: {} hora(s).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name,
                                conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'TMPED':
                    if (days > conf.integer_value2) or (
                            days <= conf.integer_value2 and (years > 0 or months > 0 or hours > 0 or minutes > 0)):
                        raise ValidationError(
                            _("El tiempo máximo permitido para el tipo de permiso: {} "
                              "y regulación: {} es: {} día(s).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name,
                                conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'TMPEME':
                    if (months > conf.integer_value2) or (
                            months <= conf.integer_value2 and (years > 0 or days > 0 or hours > 0 or minutes > 0)):
                        raise ValidationError(
                            _("El tiempo máximo permitido para el tipo de permiso: {} "
                              "y regulación: {} es: {} mes(es).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name,
                                conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'TMPEA':
                    if (years > conf.integer_value2) or (
                            years <= conf.integer_value2 and (months > 0 or days > 0 or hours > 0 or minutes > 0)):
                        raise ValidationError(
                            _("El tiempo máximo permitido para el tipo de permiso: {} "
                              "y regulación: {} es: {} año(s).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name,
                                conf.integer_value2))
                if conf.nomenclature_id.acronym == 'RA':
                    if conf.boolean_value and not instance.justification_attachment_id.id:
                        raise ValidationError(
                            _(
                                "Requests for type: {} and normative: {} require mandatory attachment.").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name))
                elif conf.nomenclature_id.acronym == 'AEMPRUS':
                    if months_a < conf.integer_value2 and (years_a == 0):
                        raise ValidationError(
                            _("La antigüedad en la empresa del colaborador para poder solicitar el tipo de permiso: {} "
                              "y regulación: {} es: {} mes(es).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name, conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'AEAPRUS':
                    if years_a < conf.integer_value2:
                        raise ValidationError(
                            _("La antigüedad en la empresa del colaborador para poder solicitar el tipo de permiso: {} "
                              "y regulación: {} es: {} año(s).").format(
                                instance.permission_type_id.name,
                                instance.employee_requests_id.normative_id.name, conf.integer_value2))
                elif conf.nomenclature_id.acronym == 'EPRUSEEP':
                    if not conf.boolean_value:
                        if self._get_datetime(instance.date_from, instance.start) < instance.create_date:
                            raise ValidationError(
                                _("For type of permission: {} and regulation: {} it is not possible "
                                  "to create requests in the past.").format(
                                    instance.permission_type_id.name,
                                    instance.employee_requests_id.normative_id.name))
                elif conf.nomenclature_id.acronym == 'CDHDAPLS':
                    # Hallo la diferencia entre la fecha de inicio del permiso y la fecha de creación de la solicitud.
                    time_difference = self._get_datetime(instance.date_from, instance.start, True) - \
                                      instance.create_date
                    # Calculo diferencia en horas
                    hours_beween = round(time_difference.total_seconds() / 3600)

                    if hours_beween < conf.integer_value:
                        raise ValidationError(_("The anticipation time to make the type of permission: {} "
                                                "and regulation: {} is: {} hour{}.").format(
                            instance.permission_type_id.name,
                            instance.employee_requests_id.normative_id.name, conf.integer_value,
                            's' if conf.integer_value > 1 else ''))

            # Validación de recuperación de tiempo
            instance._validate_time_to_recover()

    def _get_datetime(self, s_date, s_time, adjust_local_timezone=False):
        """
        Crea un objeto datetime.datetime dados una fecha y una hora.

        :param s_date: Ojeto datetime.date con la fecha a combinar.
        :param s_time: Objeto float con la representación de la hora.
        :return: Objeto datetime compuesto por la fecha  a combinar.
        """

        # Convierto la hora de inicio en un objeto datetime.time
        hours, minutes = float_to_time(s_time)
        # hours = int(s_time)
        # minutes = round((s_time * 60) % 60)
        # seconds = int((s_time * 3600) % 60)
        start_time = time(hours, minutes, 0)

        if adjust_local_timezone:
            # Al utilizar datetime en lugar de date el ajustará la hora según la zona horaria local,
            # así que calcularé la diferencia en minutos entre la zona local y la UTC y la adicionaré
            # para que no desajuste las fechas y horas.

            # Determinando la cantidad de segundos de diferencia entre UTC y la zona horaria local.
            diff_to_utc = self._get_seconds_to_utc()

            return datetime.combine(s_date, start_time) + timedelta(seconds=diff_to_utc)
        else:
            return datetime.combine(s_date, start_time)

    def _get_seconds_to_utc(self):
        """
        Determina la cantidad de segundos de diferencia entre la zona horaria local y la UTC.

        :return: Segundos existentes entre las zonas horarias.
        """

        # Obtengo la zona local del usuario autenticado en Odoo
        zone = self.employee_requests_id.tz or self._context.get('tz') or self.env.user.tz
        user_tz = pytz.timezone(zone)
        d = datetime.now()
        user_dt = d.astimezone(user_tz).replace(tzinfo=None)
        utc_dt = d.astimezone(pytz.utc).replace(tzinfo=None)
        return (utc_dt - user_dt).total_seconds()

    permission_type_id = fields.Many2one('hr.permission.type', string="Permission type", required=True,
                                         domain=lambda self: [('id', 'in', self._get_permission_types())])
    date_from = fields.Date('From', required=True)
    date_to = fields.Date('To', required=True)
    start = fields.Float(string="Start", required=True)
    end = fields.Float(string="End", required=True)
    parent_id = fields.Many2one('hr.permission.request', string='Parent permission request', readonly=True)
    is_head = fields.Boolean(string='Is head', default=False, readonly=True)
    children_id = fields.One2many('hr.permission.request', 'parent_id', string="Child permission requests",
                                  readonly=True)
    justification_attachment_id = fields.Many2many('ir.attachment',
                                                   'justification_permission_request_attach_rel', 'doc_id',
                                                   'attach_id3',
                                                   string="Attach justification",
                                                   help='You can attach your attach justification.',
                                                   copy=False)
    datetime_from = fields.Datetime(compute='_compute_datetime_from', store=True, string='Datetime from')
    datetime_to = fields.Datetime(compute='_compute_datetime_to', store=True, string='Datetime to')
    allow_attach = fields.Boolean(compute='_compute_allow_attach', string=_('User can add attachments.'), default=True)
    permission_shift_ids = fields.One2many('hr.permission.shift', 'permission_request_id', string=_('Shifts'))
    time_to_recover = fields.Float(compute='_compute_total_time_to_recover', string=_('Total time to recover'))
    planned_time_to_recover = fields.Float(compute='_compute_planned_time_to_recover',
                                           string=_('Planned time to recover'))
    recovers_time = fields.Boolean(compute="_compute_recovers_time")

    @api.model
    def create(self, vals):
        record = super(PermissionRequest, self).create(vals)

        if record.date_from > record.date_to:
            raise UserError(_('The start of the request must be lesser or equal than the end of the request.'))

        permission_request = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', record.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', record.id)
        ])
        for pr in permission_request:
            if (record.date_from >= pr.date_from and record.date_from <= pr.date_to) \
                    or (record.date_to >= pr.date_from and record.date_to <= pr.date_from):
                # Solo permitir si un permiso es padre del otro
                if record.id != pr.parent_id.id and pr.id != record.parent_id.id:
                    raise UserError(_('There is already a request in status (Draft, Pending, or Approved) for the '
                                      'specified period.'))
        self._check_restrictions(record)
        return record

    def write(self, vals):
        record = super(PermissionRequest, self).write(vals)

        if self.date_from > self.date_to:
            raise UserError(_('The start of the request must be lesser or equal than the end of the request.'))

        permission_request = self.env['hr.permission.request'].search([
            ('employee_requests_id', '=', self.employee_requests_id.id),
            ('state', 'in', ['draft', 'pending', 'approved']),
            ('active', '=', True),
            ('id', '!=', self.id)
        ])
        for pr in permission_request:
            if (self.date_from >= pr.date_from and self.date_from <= pr.date_to) \
                    or (self.date_to >= pr.date_from and self.date_to <= pr.date_from):
                # Solo permitir si un permiso es padre del otro
                if self.id != pr.parent_id.id and pr.id != self.parent_id.id:
                    raise UserError(_('There is already a request in status (Draft, Pending, or Approved) for the '
                                      'specified period.'))

        self._check_restrictions()
        return record

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('You can only delete permission requests in draft status.'))
        return super(record, self).unlink()

    # # Caracteristicas especiales para una licencia por maternidad
    # # 10 dias mas por nacimiento multiple
    # # Caracteristicas especiales para una licencia por paternidad
    # # 5 dias mas
    # cesarea = fields.Boolean(string="Cesárea", default=False)
    # multiple_birth = fields.Boolean(string="Multiple Birth", default=False)
    # # 8 dias mas
    # premature_birth = fields.Boolean(string="Premature Birth", default=False)
    # special_care = fields.Boolean(string="Special Care", default=False)
    # # 25 dias mas
    # degenerative_terminal_irreversible_disease = fields.Boolean(string="Degenerative, terminal or irreversible disease", default=False)
    # degree_severe_disability = fields.Boolean(string="Degree of severe disability", default=False)
    #
    # # Caracteristicas especiales para una licencia por calamidad doméstica
    # # 3 dias proceso estandar
    # # 5 dias mas
    # first_level = fields.Boolean(string="Cónyuge o conviviente en unión de hecho legalmente reconocida, del padre, madre o hijos", default=False)
    # sinister = fields.Boolean(string="Siniestros que afecten gravemente la propiedad o los bienes", default=False)


class JustificationPermissionRequestAttachment(models.Model):
    _inherit = 'ir.attachment'

    justification_permission_request_attach_rel = fields.Many2many('hr.permission.request',
                                                                   'justification_attachment_id', 'attach_id3',
                                                                   'doc_id', string="Attached", invisible=1)



# class NormativeNomenclativePermissionType(models.Model):
#     _name = "hr.normative.nomenclature.permission.type"
#     _description = 'Nomenclature by Normative and Permission Type'
#     _order = 'normative_id,permission_type_id,nomenclature_id,valid_from asc'
#
#     def name_get(self):
#         result = []
#         for NNPT in self:
#             if NNPT.nomenclature_id.data_type == '1':
#                 result.append((NNPT.id, "{} - {} - {}".format(NNPT.nomenclature_id.name, NNPT.normative_id.acronym, NNPT.boolean_value1)))
#             elif NNPT.nomenclature_id.data_type == '2':
#                 result.append((NNPT.id, "{} - {} - {}".format(NNPT.nomenclature_id.name, NNPT.normative_id.acronym, NNPT.integer_value2)))
#             elif NNPT.nomenclature_id.data_type == '3':
#                 result.append((NNPT.id, "{} - {} - {}".format(NNPT.nomenclature_id.name, NNPT.normative_id.acronym, NNPT.float_value3)))
#             elif NNPT.nomenclature_id.data_type == '4':
#                 result.append((NNPT.id, "{} - {} - {}".format(NNPT.nomenclature_id.name, NNPT.normative_id.acronym, NNPT.char_value4)))
#             elif NNPT.nomenclature_id.data_type == '5':
#                 result.append((NNPT.id, "{} - {} - {}".format(NNPT.nomenclature_id.name, NNPT.normative_id.acronym, NNPT.date_value5)))
#         return result
#
#     normative_id = fields.Many2one('hr.normative', string="Normativa", required=True)
#     permission_type_id = fields.Many2one('hr.permission.type', string="Tipo de Permiso", required=True)
#     nomenclature_id = fields.Many2one('hr.nomenclature', string="Nomenclador", required=True)
#     nomenclature_id_data_type = fields.Selection(string="Nomenclature Data Type", related='nomenclature_id.data_type')
#     valid_from = fields.Date('Válido Desde', required=True, default=fields.Date.context_today)
#     valid_to = fields.Date('Válido Hasta')
#
#     @api.depends('valid_to')
#     def _compute_state(self):
#         for NNPT in self:
#             if NNPT.valid_to == False:
#                 NNPT.current = True
#             else:
#                 NNPT.current = False
#     current = fields.Boolean(string='current', store=True, compute=_compute_state)
#
#     boolean_value1 = fields.Boolean(string="Boolean Value")
#     integer_value2 = fields.Integer(string="Integer Value")
#     float_value3 = fields.Float(string="Float Value")
#     char_value4 = fields.Char(string="Char Value")
#     date_value5 = fields.Date(string="Date Value")
#
#     @api.model
#     def create(self, vals):
#         normativeNomenclativePT = super(NormativeNomenclativePermissionType, self).create(vals)
#
#         if normativeNomenclativePT.valid_to != False:
#             if normativeNomenclativePT.valid_from > normativeNomenclativePT.valid_to:
#                 raise UserError('La fecha de inicio debe ser menor o igual que la fecha de fin.')
#
#
#         normative_nomenclature_pts = self.env['hr.normative.nomenclature.permission.type'].search([('normative_id','=',normativeNomenclativePT.normative_id.id ),('nomenclature_id','=',normativeNomenclativePT.nomenclature_id.id ),('permission_type_id','=',normativeNomenclativePT.permission_type_id.id),('id','!=',normativeNomenclativePT.id)])
#         for nnpt in normative_nomenclature_pts:
#             if normativeNomenclativePT.valid_to == False and nnpt.valid_to == False:
#                 raise UserError(_("El nomenclador: {}, ya se encuentra activo para la normativa: {} y el tipo de permiso: {}.").format(
#                     nnpt.nomenclature_id.name,nnpt.normative_id.name,nnpt.permission_type_id.name))
#             elif normativeNomenclativePT.valid_to != False and nnpt.valid_to != False:
#                 if ((normativeNomenclativePT.valid_from >= nnpt.valid_from and normativeNomenclativePT.valid_from <= nnpt.valid_to) or (normativeNomenclativePT.valid_to >= nnpt.valid_from and normativeNomenclativePT.valid_to <= nnpt.valid_to)):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#             elif normativeNomenclativePT.valid_to == False and nnpt.valid_to != False:
#                 if (normativeNomenclativePT.valid_from >= nnpt.valid_from and normativeNomenclativePT.valid_from <= nnpt.valid_to):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#             elif normativeNomenclativePT.valid_to != False and nnpt.valid_to == False:
#                 if nnpt.valid_from <= normativeNomenclativePT.valid_to:
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#                 if (nnpt.valid_from >= normativeNomenclativePT.valid_from and nnpt.valid_from <= normativeNomenclativePT.valid_to):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#
#         return normativeNomenclativePT
#
#     
#     def write(self, vals):
#         normativeNomenclativePT = super(NormativeNomenclativePermissionType, self).write(vals)
#
#         if self.valid_to != False:
#             if self.valid_from > self.valid_to:
#                 raise UserError('La fecha de inicio debe ser menor o igual que la fecha de fin.')
#
#         normative_nomenclature_pts = self.env['hr.normative.nomenclature.permission.type'].search(
#             [('normative_id', '=', self.normative_id.id), ('nomenclature_id', '=', self.nomenclature_id.id),('permission_type_id', '=', self.permission_type_id.id),
#              ('id', '!=', self.id)])
#
#         for nnpt in normative_nomenclature_pts:
#             if self.valid_to == False and nnpt.valid_to == False:
#                 raise UserError(_("El nomenclador: {}, ya se encuentra activo para la normativa: {} y el tipo de permiso: {}.").format(
#                     nnpt.nomenclature_id.name, nnpt.normative_id.name, nnpt.permission_type_id.name))
#             elif self.valid_to != False and nnpt.valid_to != False:
#                 if ((self.valid_from >= nnpt.valid_from and self.valid_from <= nnpt.valid_to) or (
#                         self.valid_to >= nnpt.valid_from and self.valid_to <= nnpt.valid_to)):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#             elif self.valid_to == False and nnpt.valid_to != False:
#                 if (self.valid_from >= nnpt.valid_from and self.valid_from <= nnpt.valid_to):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#             elif self.valid_to != False and nnpt.valid_to == False:
#                 if nnpt.valid_from <= self.valid_to:
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#                 if (nnpt.valid_from >= self.valid_from and nnpt.valid_from <= self.valid_to):
#                     raise UserError('Ya existe un Nomenclador para esta Normativa y Tipo de Permiso en el lapso de tiempo espeficado.')
#
#         return normativeNomenclativePT
#
#     
#     def unlink(self):
#         for normativeNomenclativePermissionType in self:
#             if normativeNomenclativePermissionType.current == True:
#                 raise ValidationError(u'No se puede eliminar un nomenclador current.')
#         return super(NormativeNomenclativePermissionType, self).unlink()
#
# class NotificationsPermissionTypeEmployee(models.Model):
#     _name = "hr.n.permission.type.employee"
#     _description = 'Nomenclature by Normative and Permission Type'
#     _order = "permission_type_id,employee_requests_id,level"
#
#     employee_requests_id = fields.Many2one('hr.employee', string="Colaborador que Solicita", required=True)
#     permission_type_id = fields.Many2one('hr.permission.type', string="Tipo de Permiso", required=True)
#     employee_approve_id = fields.Many2one('hr.employee', string="Colaborador que Aprueba", required=True)
#     level = fields.Integer(string="Nivel", required=True, default=1)





# class PermissionNotificationByEmployee(models.Model):
#     _name = 'hr.permission.notification.employee'
#     _description = 'Notifications by Employee'
#     _order = "type,state,date_from_permission_request,level"
#
#     
#     def send_mail(self, mailTemplateId):
#         template = self.env.ref(mailTemplateId)
#         self.env['mail.template'].browse(template.id).send_mail(self.id)
#
#     permission_request_id = fields.Many2one('hr.permission.request', string='Permission Request')
#     employee_permission_request_id = fields.Many2one('hr.employee',
#                                                             string="Permission Request Employee",
#                                                             related='permission_request_id.employee_requests_id',
#                                                             store=True)
#     date_from_permission_request = fields.Datetime(string="Permission Request Date From",
#                                                       related='permission_request_id.date_from',
#                                                       store=True)
#     date_to_permission_request = fields.Datetime(string="Permission Request Date To",
#                                                     related='permission_request_id.date_to',
#                                                     store=True)
#
#     #
#     parent_id = fields.Many2one('hr.permission.notification.employee', string='Parent Notification Permission Request',
#                                 readonly=True)
#     notification_scheme_id = fields.Many2one('hr.n.permission.type.employee', 'Notification Scheme')
#     type = fields.Many2one('hr.permission.type', string='Tipo de Permiso')
#     level = fields.Integer('Level', store=True)
#     employee_approve_id = fields.Many2one('hr.employee', string="Approving Employee")
#     user_employee_approve_id = fields.Many2one('res.users', string="User Approving Employee",
#                                                related='employee_approve_id.user_id')
#     state = fields.Selection([
#         ('pending', 'Pending'),
#         ('reassigned', 'Reassigned'),
#         ('cancelled', 'Cancelled'),
#         ('approved', 'Approved'),
#         ('rejected', 'Rejected')
#     ], string='State', default='pending')
#     send = fields.Boolean(string="Send", default=False)
#     commentary = fields.Text(string="Commentary")
#
#     
#     def name_get(self):
#         result = []
#         for notificationByEmployee in self:
#             result.append(
#                 (
#                     notificationByEmployee.id,
#                     _("{} Tipo: {} Desde: {} Hasta: {} {}").format(
#                         notificationByEmployee.employee_permission_request_id.name,
#                         notificationByEmployee.type.name,
#                         notificationByEmployee.date_from_permission_request,
#                         notificationByEmployee.date_to_permission_request,
#                         dict(self._fields['state'].selection).get(notificationByEmployee.state)
#                         )
#                 )
#             )
#         return result
#
#     def approve_permission(self):
#         count_notifications = self.env['hr.permission.notification.employee'].search_count(
#             [('permission_request_id', '=', self.permission_request_id.id),('state', '!=', 'reassigned')])
#
#         if self.state == 'cancelled':
#             raise ValidationError(
#                 _("Esta notificación fue cancelada."))
#         elif self.state == 'reassigned':
#             raise ValidationError(
#                 _("Esta notificación fue reasignada."))
#         elif self.state != 'pending':
#             raise ValidationError(
#                 _("Esta notificación ya fue procesada."))
#         else:
#             if count_notifications == self.level:
#                 mail_id_aprove_final = 'hr_dr_permissions.email_template_confirm_aprove_permission'
#                 self.send_mail(mail_id_aprove_final)
#                 self.permission_request_id.state = 'approved'
#             else:
#                 notication = self.env['hr.permission.notification.employee'].search(
#                     [('permission_request_id', '=', self.permission_request_id.id),
#                      ('state', '=', 'pending'),
#                      ('level', '=', self.level + 1)])
#                 notication.send = True
#                 mail_id_aprove_reject = 'hr_dr_permissions.email_template_aprove_reject_permission'
#                 notication.send_mail(mail_id_aprove_reject)
#             self.state = 'approved'
#
#         return self
#
#     def reject_permission(self,commentary):
#
#         if self.state == 'cancelled':
#             raise ValidationError(
#                 _("Esta notificación fue cancelada."))
#         elif self.state == 'reassigned':
#             raise ValidationError(
#                 _("Esta notificación fue reasignada."))
#         elif self.state != 'pending':
#             raise ValidationError(
#                 _("Esta notificacion ya fue procesada."))
#         else:
#             # Actualizar la notificacion
#             self.state = 'rejected'
#             self.commentary = commentary
#
#             # Actualizar la solicitud
#             self.permission_request_id.state = 'rejected'
#
#             # Enviar el mail de rechazo
#             mail_id_reject_permission = 'hr_dr_permissions.email_template_confirm_reject_permission'
#             self.send_mail(mail_id_reject_permission)
#
#         return self
#
# class RejectNotificationPermissionRequest(models.TransientModel):
#     _name = 'hr.reject.notification.permission.request'
#     _description = 'Reject Notification Permission Request'
#
#     # Notificación Actual
#     actual_notification = fields.Many2one('hr.permission.notification.employee',
#                                                           string='Actual Notification', readonly=True,
#                                                           default=lambda self: self._context.get('active_id'))
#     commentary = fields.Text(string="Commentary", required=True)
#
#     
#     def action_reject(self):
#         self.actual_notification.reject_permission(self.commentary)
#
# class ReasignNotificationPermissionRequest(models.TransientModel):
#     _name = 'hr.reasign.notification.permission.request'
#     _description = 'Reasign Notification Permission Request'
#
#     # Notificación Actual
#     actual_notification = fields.Many2one('hr.permission.notification.employee',
#                                                           string='Actual Notification', readonly=True,
#                                                           default=lambda self: self._context.get('active_id'))
#     employee_approve_id = fields.Many2one('hr.employee', string="Current Approving Employee",
#                                           related='actual_notification.employee_approve_id', store=True)
#     # New
#     new_employee_approve_id = fields.Many2one('hr.employee', string="New Approving Employee",required=True)
#
#     
#     def action_reasign(self):
#
#         self.actual_notification.state = 'reassigned'
#         new_notification = self.env['hr.permission.notification.employee'].create({
#             'permission_request_id': self.actual_notification.permission_request_id.id,
#             'parent_id': self.actual_notification.id,
#             'type': self.actual_notification.type.id,
#             'level': self.actual_notification.level,
#             'employee_approve_id': self.new_employee_approve_id.id,
#             'state': 'pending',
#             'send': False,
#         })
#         if new_notification:
#             mail_id_aprove_reject = 'hr_dr_permissions.email_template_aprove_reject_permission'
#             new_notification.send_mail(mail_id_aprove_reject)