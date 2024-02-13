# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrProfession(models.Model):
    _inherit = "hr.profession"

    celebration_date = fields.Date(string="Celebration date", tracking=True)
    email_template_id = fields.Many2one('mail.template', string='Celebration date email template', tracking=True)

    def get_celebration_date_in_format_day_month(self):
        months = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
                  7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}
        return self.celebration_date.strftime('%d de {}').format(months[self.celebration_date.month])

    @api.model
    def get_hr_dr_management_responsible(self):
        hr_responsible = self.env['hr.employee'].sudo().search([
            ('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('hr_dr_management.responsible')))],
            limit=1)
        if len(hr_responsible) == 1:
            return hr_responsible[0]
        else:
            return False

    def get_hr_dr_management_responsible_email(self):
        email = ''
        config_parameter = self.env['ir.config_parameter'].sudo()
        id = int(config_parameter.get_param('hr_dr_management.responsible'))
        responsible = self.env['hr.employee'].sudo().search([('id', '=', int(id))], limit=1)
        if len(responsible) > 0:
            if responsible.work_email:
                email = responsible.work_email
        return email

    def get_en_apply_in_profession_celebration_date(self):
        apply_in_profession_celebration_date = self.env['ir.config_parameter'].sudo().\
            get_param('en.apply.in.profession.celebration.date', '')
        if apply_in_profession_celebration_date != '':
            return bool(int(self.env['ir.config_parameter'].sudo().
                            get_param('en.apply.in.profession.celebration.date')))
        else:
            return False

    def get_en_notify_administrators(self):
        en_notify_administrators = self.env['ir.config_parameter'].sudo().get_param('en.notify.administrators', '')
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

    def report_bug(self, technical_message):
        template = self.env.ref('hr_dr_employee_notifications.email_template_report_bug', False)
        template = self.env['mail.template'].browse(template.id)
        local_context = self.env.context.copy()
        local_context['technical_message'] = technical_message
        template.with_context(local_context).send_mail(self.id, force_send=True)

    def get_en_email_for_mass_notifications(self):
        return self.env['ir.config_parameter'].sudo().get_param('en.email.for.mass.notifications', '')

    def throw_error(self, call_from_cron, function, message, report_bug=False):
        if call_from_cron:
            message_log = _("ERROR: Function: {}. Message: {}").format(function,message)
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

    def get_en_anticipation_days(self):
        en_anticipation_days = self.env['ir.config_parameter'].sudo().get_param('en.anticipation.days', '')
        if en_anticipation_days != '':
            return int(self.env['ir.config_parameter'].sudo().get_param('en.anticipation.days'))
        else:
            return 0

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

    def get_today_celebration_date(self):
        professions = self.search([('active', '=', True)])
        profession_celebration_dates = []
        for profession in professions:
            if profession.celebration_date:
                current_date = datetime.utcnow().date()
                celebration_date = profession.celebration_date + relativedelta(
                    days=self.get_en_anticipation_days() * -1, year=current_date.year)
                if celebration_date == current_date:
                    profession_celebration_dates.append(profession)
        return profession_celebration_dates

    def cron_notify_profession_celebration_date(self):
        profession_celebration_dates = self.get_today_celebration_date()
        call_from_cron = True
        if len(profession_celebration_dates) > 0:
            if self.get_en_apply_in_profession_celebration_date():
                # Notificar según la configuración
                if self.get_en_notify_administrators():
                    # Notificar a la lista de administradores
                    emails_to = self.get_administrators_emails()
                    if emails_to != '':
                        try:
                            self.notify_profession_celebration_date(emails_to, profession_celebration_dates)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", e,
                                             report_bug=True)
                    else:
                        # "Por favor defina los administradores en la configuración de notificaciones."
                        message = _("Please define administrators in the notification settings.")
                        self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", message,
                                         report_bug=True)
                else:
                    # Notificar al correo para notificaciones masivas si existe.
                    # Caso contrario notificar a todos los colaboradores
                    emails_to = self.get_en_email_for_mass_notifications()
                    if emails_to == '':
                        emails_to = ','.join(self.get_employees_emails())

                    if emails_to != '':
                        try:
                            self.notify_profession_celebration_date(emails_to,profession_celebration_dates)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", e,
                                             report_bug=True)
                    else:
                        # Por favor defina el correo para notificaciones masivas o el correo de trabajo para
                        # al menos un colaborador para que esta funcionalidad tenga sentido.
                        message = _(
                            "Please define the email for mass notifications or the work email for "
                            "at least one collaborator for this functionality to make sense.")
                        self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", message,
                                         report_bug=True)
            else:
                # Notificar al administrador de talento humano
                if 'hr_dr_management' in self.env.registry._init_modules:
                    emails_to = self.get_hr_dr_management_responsible_email()
                    if emails_to != '':
                        try:
                            self.notify_profession_celebration_date(emails_to,profession_celebration_dates)
                        except Exception as e:
                            self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", e,
                                             report_bug=True)
                    else:
                        # Por favor defina el responsable de talento humano en la configuración del módulo
                        # 'Administración de Talento Humano'
                        message = _("Please define the responsible of human talent in the configuration of module "
                                    "'Human talent management'.")
                        self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", message,
                                         report_bug=True)
                else:
                    message = _("Please install the 'Human talent management' module and define the responsible "
                                "of human talent or change the notification settings.")
                    # Por favor instale el módulo 'Administración de Talento Humano' y defina el responsable
                    # de talento humano o cambie la configuración de notificaciones.
                    self.throw_error(call_from_cron, "cron_notify_profession_celebration_date", message,
                                     report_bug=True)

    def notify_profession_celebration_date(self, emails_to, profession_celebration_dates):
        default_template = self.env.ref(
            'hr_dr_employee_notifications.email_template_notify_profession_celebration_date', False)
        default_template = self.env['mail.template'].browse(default_template.id)
        default_template.write({
            'email_to': emails_to
        })
        department = 'Dirección de Talento Humano'
        management_responsible = self.get_hr_dr_management_responsible()
        if management_responsible and management_responsible.department_id:
            department = management_responsible.department_id.name

        for pcd in profession_celebration_dates:
            if not pcd.email_template_id:
                # Enviar email en función de la plantilla genérica
                local_context = self.env.context.copy()
                local_context['department'] = department
                default_template.with_context(local_context).send_mail(pcd.id, force_send=True)
            else:
                # Enviar email en función de la plantilla específica del cargo
                local_context = self.env.context.copy()
                pcd.email_template_id.with_context(local_context).send_mail(pcd.id, force_send=True)