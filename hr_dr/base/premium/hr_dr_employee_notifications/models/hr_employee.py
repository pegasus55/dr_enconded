# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import pytz
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = 'hr.employee'

    def get_birthday_in_format_day_month(self):
        """
        Recibe una fecha y devuelve su representación en forma de texto de la forma '[día] de [mes] para el
        idioma español.
        """
        months = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
                  7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}

        return self.birthday.strftime('%d de {}').format(months[self.birthday.month])

    def get_date_format(self):
        """
        Obtiene el formato de fecha definido en el sistema o toma por defecto %d/%m/%Y si no hay uno.
        :return: Cadena de texto con el formato de fecha
        """
        lang = self.env.context.get("lang")
        langs = self.env['res.lang']
        if lang:
            langs = self.env['res.lang'].sudo().search([("code", "=", lang)])
        return langs.date_format or '%d/%m/%Y'

    def get_en_notify_administrators(self):
        en_notify_administrators = self.env['ir.config_parameter'].sudo().get_param('en.notify.administrators','')
        if en_notify_administrators != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('en.notify.administrators')))
        else:
            return False

    def get_administrators_emails(self):
        administrators_emails = ''
        config_parameter = self.env['ir.config_parameter'].sudo()
        if config_parameter.get_param('en.administrators.ids'):
            if config_parameter.get_param('en.administrators.ids') != '':
                for id in config_parameter.get_param('en.administrators.ids').split(','):
                    administrator = self.env['hr.employee'].sudo().search([('id', '=', int(id))], limit=1)
                    if len(administrator) > 0:
                        if administrator.work_email:
                            if administrators_emails == '':
                                administrators_emails = administrator.work_email
                            else:
                                administrators_emails += ',' + administrator.work_email

        return administrators_emails

    def get_hr_dr_management_responsible_email(self):
        email = ''
        config_parameter = self.env['ir.config_parameter'].sudo()
        id = int(config_parameter.get_param('hr_dr_management.responsible'))
        responsible = self.env['hr.employee'].sudo().search([('id', '=', int(id))], limit=1)
        if len(responsible) > 0:
            if responsible.work_email:
                email = responsible.work_email
        return email

    def get_en_email_for_mass_notifications(self):
        return self.env['ir.config_parameter'].sudo().get_param('en.email.for.mass.notifications', '')

    def get_en_anticipation_days(self):
        en_anticipation_days = self.env['ir.config_parameter'].sudo().get_param('en.anticipation.days', '')
        if en_anticipation_days != '':
            return int(self.env['ir.config_parameter'].sudo().get_param('en.anticipation.days'))
        else:
            return 0

    def get_en_apply_in_personal_income(self):
        apply_in_personal_income = self.env['ir.config_parameter'].sudo().get_param('en.apply.in.personal.income', '')
        if apply_in_personal_income != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('en.apply.in.personal.income')))
        else:
            return False

    def get_en_apply_in_personal_exit(self):
        apply_in_personal_exit = self.env['ir.config_parameter'].sudo().get_param('en.apply.in.personal.exit', '')
        if apply_in_personal_exit != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('en.apply.in.personal.exit')))
        else:
            return False

    def get_en_apply_in_birthday(self):
        apply_in_birthday = self.env['ir.config_parameter'].sudo().get_param('en.apply.in.birthday', '')
        if apply_in_birthday != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('en.apply.in.birthday')))
        else:
            return False

    def get_en_apply_in_anniversary(self):
        apply_in_anniversary = self.env['ir.config_parameter'].sudo().get_param('en.apply.in.anniversary','')
        if apply_in_anniversary != '':
            return bool(int(self.env['ir.config_parameter'].sudo().get_param('en.apply.in.anniversary')))
        else:
            return False

    def get_employees_emails(self):
        """
        Obtiene un listado de los emails de los colaboradores y lo retorna.

        :return: Lista de cadenas con los correos electrónicos de los colaboradores activos.
        """
        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', True)]).mapped('work_email')
        # Eliminando el valor False de la lista de emails
        while False in employees:
            employees.remove(False)
        # Eliminando cualquier email duplicado
        return list(set(employees))

    def report_bug(self, technical_message):
        template = self.env.ref('hr_dr_employee_notifications.email_template_report_bug', False)
        template = self.env['mail.template'].browse(template.id)
        local_context = self.env.context.copy()
        local_context['technical_message'] = technical_message
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def throw_error(self, call_from_cron, function, message, report_bug=False):
        if call_from_cron:
            message_log = _("ERROR: Function: {}. Message: {}").format(function, message)
            _logger.error(message_log)
        else:
            message_log = _("ERROR: Function: {}. Message: {}").format(function, message)
            _logger.error(message_log)
            raise UserError(_(message))

        if report_bug:
            user = False
            db = False
            datetime = False
            technical_message = _("User: {}. Database: {}. Datetime: {}. Function: {}. Message: {}").\
                format(user, db, datetime, function, message)
            self.report_bug(technical_message)

    def get_personal_not_notify_income(self):
        """
        Obtiene un listado con los colaboradores que aún no se notifica su ingreso.
        :return: listado de hr.employee
        """
        employees = self.search([
            ('active', '=', True),
            ('employee_admin', '=', False),
            ('notified_income', '=', False)])
        return employees

    def cron_mark_all_personal_as_notified_income(self):
        employees = self.get_personal_not_notify_income()
        for e in employees:
            e.notified_income = True

    def cron_notify_personal_income(self):
        employees = self.get_personal_not_notify_income()
        for e in employees:
            e.action_notify_personal_income(call_from_cron=True)

    def notify_personal_income(self, emails_to):
        template = self.env.ref('hr_dr_employee_notifications.email_template_notify_personal_income', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })

        department = 'Dirección de Talento Humano'
        management_responsible = self.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        local_context = self.env.context.copy()
        local_context['department'] = department
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def action_notify_personal_income(self, call_from_cron=False):
        for record in self:
            if not record.notified_income:
                if self.get_en_apply_in_personal_income():
                    # Notificar según la configuración
                    if self.get_en_notify_administrators():
                        # Notificar a la lista de administradores
                        emails_to = self.get_administrators_emails()
                        if emails_to != '':
                            try:
                                record.notify_personal_income(emails_to)
                                record.notified_income = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_income", e, report_bug=True)
                        else:
                            # Por favor defina los administradores en la configuración de notificaciones.
                            message = _("Please define administrators in the notification settings.")
                            self.throw_error(call_from_cron, "action_notify_personal_income", message, report_bug=True)
                    else:
                        # Notificar al correo para notificaciones masivas si existe.
                        # Caso contrario notificar a todos los colaboradores
                        emails_to = self.get_en_email_for_mass_notifications()
                        if emails_to == '':
                            emails_to = ','.join(self.get_employees_emails())

                        if emails_to != '':
                            try:
                                record.notify_personal_income(emails_to)
                                record.notified_income = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_income", e, report_bug=True)
                        else:
                            # Por favor defina el correo para notificaciones masivas o el correo de trabajo
                            # para al menos un colaborador para que esta funcionalidad tenga sentido."
                            message = _("Please define the email for mass notifications or the work email "
                                        "for at least one collaborator for this functionality to make sense.")
                            self.throw_error(call_from_cron, "action_notify_personal_income", message, report_bug=True)
                else:
                    # Notificar al administrador de talento humano
                    if 'hr_dr_management' in self.env.registry._init_modules:
                        emails_to = record.get_hr_dr_management_responsible_email()
                        if emails_to != '':
                            try:
                                record.notify_personal_income(emails_to)
                                record.notified_income = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_income", e, report_bug=True)
                        else:
                            # Por favor defina el responsable de talento humano en la
                            # configuración del módulo 'Administración de Talento Humano'.
                            message = _("Please define the responsible of human talent in the "
                                        "configuration of module 'Human talent management'.")
                            self.throw_error(call_from_cron, "action_notify_personal_income", message, report_bug=True)
                    else:
                        message = _("Please install the 'Human talent management' module and define the responsible "
                                    "of human talent or change the notification settings.")
                        # Por favor instale el módulo 'Administración de Talento Humano' y defina el responsable
                        # de talento humano o cambie la configuración de notificaciones.
                        self.throw_error(call_from_cron, "action_notify_personal_income", message, report_bug=True)
        return True

    def action_notify_personal_exit(self, call_from_cron=False):
        for record in self:
            if not record.notified_exit:
                if self.get_en_apply_in_personal_exit():
                    # Notificar según la configuración
                    if self.get_en_notify_administrators():
                        # Notificar a la lista de administradores
                        emails_to = self.get_administrators_emails()
                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, False)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_exit", e, report_bug=True)
                        else:
                            # Por favor defina los administradores en la configuración de notificaciones.
                            message = _("Please define administrators in the notification settings.")
                            self.throw_error(call_from_cron, "action_notify_personal_exit", message, report_bug=True)
                    else:
                        # Notificar al correo para notificaciones masivas si existe.
                        # Caso contrario notificar a todos los colaboradores
                        emails_to = self.get_en_email_for_mass_notifications()
                        if emails_to == '':
                            emails_to = ','.join(self.get_employees_emails())

                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, False)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_exit", e, report_bug=True)
                        else:
                            # Por favor defina el correo para notificaciones masivas o el correo de trabajo para
                            # al menos un colaborador para que esta funcionalidad tenga sentido.
                            message = _("Please define the email for mass notifications or the work email for "
                                        "at least one collaborator for this functionality to make sense.")
                            self.throw_error(call_from_cron, "action_notify_personal_exit", message, report_bug=True)
                else:
                    # Notificar al administrador de talento humano
                    if 'hr_dr_management' in self.env.registry._init_modules:
                        emails_to = record.get_hr_dr_management_responsible_email()
                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, False)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_exit", e, report_bug=True)
                        else:
                            # Por favor defina el responsable de talento humano en
                            # la configuración del módulo 'Administración de Talento Humano'."
                            message = _("Please define the responsible of human talent in "
                                        "the configuration of module 'Human talent management'.")
                            self.throw_error(call_from_cron, "action_notify_personal_exit", message, report_bug=True)
                    else:
                        message = _("Please install the 'Human talent management' module and define "
                                    "the responsible of human talent or change the notification settings.")
                        # Por favor instale el módulo 'Administración de Talento Humano' y defina
                        # el responsable de talento humano o cambie la configuración de notificaciones."
                        self.throw_error(call_from_cron, "action_notify_personal_exit", message, report_bug=True)
        return True

    def action_notify_personal_retired(self, call_from_cron=False):
        for record in self:
            if not record.notified_exit:
                if self.get_en_apply_in_personal_exit():
                    # Notificar según la configuración
                    if self.get_en_notify_administrators():
                        # Notificar a la lista de administradores
                        emails_to = self.get_administrators_emails()
                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, True)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_retired", e, report_bug=True)
                        else:
                            # Por favor defina los administradores en la configuración de notificaciones.
                            message = _("Please define administrators in the notification settings.")
                            self.throw_error(call_from_cron, "action_notify_personal_retired", message, report_bug=True)
                    else:
                        # Notificar al correo para notificaciones masivas si existe.
                        # Caso contrario notificar a todos los colaboradores
                        emails_to = self.get_en_email_for_mass_notifications()
                        if emails_to == '':
                            emails_to = ','.join(self.get_employees_emails())

                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, True)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_retired", e, report_bug=True)
                        else:
                            # Por favor defina el correo para notificaciones masivas o el correo de trabajo para
                            # al menos un colaborador para que esta funcionalidad tenga sentido.
                            message = _("Please define the email for mass notifications or the work email for "
                                        "at least one collaborator for this functionality to make sense.")
                            self.throw_error(call_from_cron, "action_notify_personal_retired", message, report_bug=True)
                else:
                    # Notificar al administrador de talento humano
                    if 'hr_dr_management' in self.env.registry._init_modules:
                        emails_to = record.get_hr_dr_management_responsible_email()
                        if emails_to != '':
                            try:
                                record.notify_personal_exit(emails_to, True)
                                record.notified_exit = True
                            except Exception as e:
                                self.throw_error(call_from_cron, "action_notify_personal_retired", e, report_bug=True)
                        else:
                            # Por favor defina el responsable de talento humano en
                            # la configuración del módulo 'Administración de Talento Humano'.
                            message = _("Please define the responsible of human talent in "
                                        "the configuration of module 'Human talent management'.")
                            self.throw_error(call_from_cron, "action_notify_personal_retired", message, report_bug=True)
                    else:
                        message = _("Please install the 'Human talent management' module and define "
                                    "the responsible of human talent or change the notification settings.")
                        # Por favor instale el módulo 'Administración de Talento Humano' y defina
                        # el responsable de talento humano o cambie la configuración de notificaciones.
                        self.throw_error(call_from_cron, "action_notify_personal_retired", message, report_bug=True)
        return True

    def notify_personal_exit(self, emails_to, retired):
        template = False
        if retired:
            template = self.env.ref('hr_dr_employee_notifications.email_template_notify_personal_retired', False)
            template = self.env['mail.template'].browse(template.id)
        else:
            template = self.env.ref('hr_dr_employee_notifications.email_template_notify_personal_exit', False)
            template = self.env['mail.template'].browse(template.id)

        if template:
            template.write({
                'email_to': emails_to
            })
            department = 'Dirección de Talento Humano'
            management_responsible = self.get_hr_dr_management_responsible()
            if management_responsible and management_responsible.department_id:
                department = management_responsible.department_id.name

            local_context = self.env.context.copy()
            local_context['department'] = department
            template.with_context(local_context).send_mail(self.id, force_send=True)

    def get_today_birthdays(self):
        """
        Obtiene un listado con los colaboradores que cumplen años en el día de hoy, o en el futuro teniendo en cuenta los días de anticipación para las notificaciones.
        :return: listado de hr.employee
        """
        employees = self.search([('active', '=', True)])
        birthdays = []
        for employee in employees:
            if employee.birthday:
                current_date = datetime.utcnow()

                tz_name = employee.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    message = _("Local time zone is not defined. Collaborator: {}".format(employee.name))
                    self.throw_error(True, "get_today_birthdays", message, report_bug=True)
                    continue
                tz = pytz.timezone(tz_name)
                current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                current_date = current_date.date()
                birthday = employee.birthday + relativedelta(days=self.get_en_anticipation_days() * -(1), year=current_date.year)
                if birthday == current_date:
                    birthdays.append(employee)
        return birthdays

    def cron_notify_birthdays(self):
        birthdays = self.get_today_birthdays()
        call_from_cron = True
        if len(birthdays) > 0:
            if self.get_en_apply_in_birthday():
                # Notificar según la configuración
                if self.get_en_notify_administrators():
                    # Notificar a la lista de administradores
                    emails_to = self.get_administrators_emails()
                    if emails_to != '':
                        try:
                            self.notify_birthdays(emails_to, birthdays)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_birthdays", e, report_bug=True)
                    else:
                        # "Por favor defina los administradores en la configuración de notificaciones."
                        message = _("Please define administrators in the notification settings.")
                        self.throw_error(call_from_cron, "cron_notify_birthdays", message, report_bug=True)

                else:
                    # Notificar al correo para notificaciones masivas si existe.
                    # Caso contrario notificar a todos los colaboradores
                    emails_to = self.get_en_email_for_mass_notifications()
                    if emails_to == '':
                        emails_to = ','.join(self.get_employees_emails())

                    if emails_to != '':
                        try:
                            self.notify_birthdays(emails_to, birthdays)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_birthdays", e, report_bug=True)
                    else:
                        # Por favor defina el correo para notificaciones masivas o el correo de trabajo para
                        # al menos un colaborador para que esta funcionalidad tenga sentido.
                        message = _("Please define the email for mass notifications or the work email for "
                                    "at least one collaborator for this functionality to make sense.")
                        self.throw_error(call_from_cron, "cron_notify_birthdays", message, report_bug=True)
            else:
                # Notificar al administrador de talento humano
                if 'hr_dr_management' in self.env.registry._init_modules:
                    emails_to = self.get_hr_dr_management_responsible_email()
                    if emails_to != '':
                        try:
                            self.notify_birthdays(emails_to, birthdays)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_birthdays", e, report_bug=True)
                    else:
                        # Por favor defina el responsable de talento humano en
                        # la configuración del módulo 'Administración de Talento Humano'.
                        message = _("Please define the responsible of human talent in "
                                    "the configuration of module 'Human talent management'.")
                        self.throw_error(call_from_cron, "cron_notify_birthdays", message, report_bug=True)
                else:
                    message = _("Please install the 'Human talent management' module and define the responsible "
                                "of human talent or change the notification settings.")
                    # Por favor instale el módulo 'Administración de Talento Humano' y defina el responsable
                    # de talento humano o cambie la configuración de notificaciones.
                    self.throw_error(call_from_cron, "cron_notify_birthdays", message, report_bug=True)

    def notify_birthdays(self, emails_to, birthdays):

        template = self.env.ref('hr_dr_employee_notifications.email_template_notify_birthdays', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })

        department = 'Dirección de Talento Humano'
        management_responsible = self.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        local_context = self.env.context.copy()
        local_context['birthdays'] = birthdays
        local_context['department'] = department

        template.with_context(local_context).send_mail(birthdays[0].id, force_send=True)

    def get_today_anniversary(self):
        """
        Obtiene un listado con los colaboradores que cumplen año de trabajo en el día de hoy, o en el futuro teniendo en cuenta los días de anticipación para las notificaciones.
        :return: listado de hr.employee
        """
        employees = self.search([('active', '=', True)])
        anniversary = []
        for employee in employees:
            if employee.last_company_entry_date:
                current_date = datetime.utcnow()

                tz_name = employee.tz or self._context.get('tz') or self.env.user.tz
                if not tz_name:
                    message = _("Local time zone is not defined. Collaborator: {}".format(employee.name))
                    self.throw_error(True, "get_today_anniversary", message, report_bug=True)
                    continue
                tz = pytz.timezone(tz_name)
                current_date = pytz.utc.localize(current_date, is_dst=None).astimezone(tz)
                current_date = current_date.date()
                last_company_entry_date = employee.last_company_entry_date + relativedelta(days=self.get_en_anticipation_days() * -(1),year=current_date.year)
                if last_company_entry_date == current_date:
                    anniversary.append(employee)
        return anniversary

    def cron_notify_anniversary(self):
        anniversary = self.get_today_anniversary()
        call_from_cron = True
        if len(anniversary) > 0:
            if self.get_en_apply_in_birthday():
                # Notificar según la configuración
                if self.get_en_notify_administrators():
                    # Notificar a la lista de administradores
                    emails_to = self.get_administrators_emails()
                    if emails_to != '':
                        try:
                            self.notify_anniversary(emails_to, anniversary)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_anniversary", e, report_bug=True)
                    else:
                        # Por favor defina los administradores en la configuración de notificaciones.
                        message = _("Please define administrators in the notification settings.")
                        self.throw_error(call_from_cron, "cron_notify_anniversary", message, report_bug=True)
                else:
                    # Notificar al correo para notificaciones masivas si existe.
                    # Caso contrario notificar a todos los colaboradores
                    emails_to = self.get_en_email_for_mass_notifications()
                    if emails_to == '':
                        emails_to = ','.join(self.get_employees_emails())

                    if emails_to != '':
                        try:
                            self.notify_anniversary(emails_to, anniversary)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_anniversary", e, report_bug=True)
                    else:
                        # Por favor defina el correo para notificaciones masivas o el correo de trabajo para al menos
                        # un colaborador para que esta funcionalidad tenga sentido.
                        message = _("Please define the email for mass notifications or the work email for at least "
                                    "one collaborator for this functionality to make sense.")
                        self.throw_error(call_from_cron, "cron_notify_anniversary", message, report_bug=True)
            else:
                # Notificar al administrador de talento humano
                if 'hr_dr_management' in self.env.registry._init_modules:
                    emails_to = self.get_hr_dr_management_responsible_email()
                    if emails_to != '':
                        try:
                            self.notify_anniversary(emails_to, anniversary)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_anniversary", e, report_bug=True)
                    else:
                        # Por favor defina el responsable de talento humano en
                        # la configuración del módulo 'Administración de Talento Humano'.
                        message = _("Please define the responsible of human talent in "
                                    "the configuration of module 'Human talent management'.")
                        self.throw_error(call_from_cron, "cron_notify_anniversary", message, report_bug=True)
                else:
                    message = _("Please install the 'Human talent management' module and define "
                                "the responsible of human talent or change the notification settings.")
                    # Por favor instale el módulo 'Administración de Talento Humano' y defina el responsable
                    # de talento humano o cambie la configuración de notificaciones.
                    self.throw_error(call_from_cron, "cron_notify_anniversary", message, report_bug=True)

    def notify_anniversary(self, emails_to, anniversary):
        template = self.env.ref('hr_dr_employee_notifications.email_template_notify_anniversary', False)
        template = self.env['mail.template'].browse(template.id)
        template.write({
            'email_to': emails_to
        })
        department = 'Dirección de Talento Humano'
        management_responsible = self.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        local_context = self.env.context.copy()
        local_context['department'] = department
        local_context['anniversary'] = anniversary
        template.with_context(local_context).send_mail(anniversary[0].id, force_send=True)

    # Si está marcada esta opción significa que el ingreso de este colaborador ya fue notificado.
    notified_income = fields.Boolean(string='Notified income', default=False,
                                     help="If this option is checked, it means that the entry of this collaborator "
                                          "has already been notified.")
    # Si está marcada esta opción significa que la salida de este colaborador ya fue notificada.
    notified_exit = fields.Boolean(string='Notified exit', default=True,
                                   help="If this option is checked, it means that the exit of this collaborator "
                                        "has already been notified.")
