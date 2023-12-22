# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class ReentryEmployee(models.TransientModel):
    _name = 'hr.reentry.employee'
    _description = 'Reenter collaborator.'

    employee_id = fields.Many2one('hr.employee', string="Collaborator",
                                  default=lambda self: self._context.get('active_id'), required=True,
                                  ondelete='cascade')
    actual_department_id = fields.Many2one('hr.department', string='Actual department', readonly=True,
                                           related='employee_id.department_id')
    department_id = fields.Many2one('hr.department', string='Reenter department', required=True)
    # Día que reingresa a la empresa.
    reentry_date = fields.Date('Reenter date', required=True, default=fields.Date.context_today,
                               help="Day you reenter the company.")
    state = fields.Selection([
        ('affiliate', _('Affiliate')),
        ('temporary', _('Temporary')),
        ('intern', _('Intern')),
    ], string='State', default='affiliate', required=True)

    def action_reentry(self):
        if self.actual_department_id != self.department_id:
            edh = self.env['hr.employee.department.history'].search([
                ('employee_id', '=', self.employee_id.id), ('date_to', '=', False)
            ])
            if edh and len(edh) == 1:
                edh = edh[0]
                if edh.date_from > self.reentry_date:
                    # La fecha de inicio tiene que ser menor o igual a la fecha de fin.
                    raise UserError(_('The start date has to be less than or equal to the end date.'))

                date_to = self.reentry_date + relativedelta(days=-1)
                if date_to < edh.date_from:
                    date_to = edh.date_from

                edh.date_to = date_to
                self.env['hr.employee.department.history'].create({
                    'employee_id': self.employee_id.id,
                    'department_id': self.department_id.id,
                    'date_from': self.reentry_date
                    })

                self.env['hr.employee.company.history'].create({
                    'employee_id': self.employee_id.id,
                    'date_from': self.reentry_date
                })

                self.employee_id.department_id = self.department_id
                self.employee_id.active = True
                self.employee_id.state = self.state

                self.employee_id.with_context(reenter='1').write({'last_company_entry_date': self.reentry_date})

                if 'hr_dr_employee_notifications' in self.env.registry._init_modules:
                    self.employee_id.notified_income = False
                    self.employee_id.notified_exit = False
                    self.employee_id.action_notify_personal_income()

                address_home_id = self.employee_id.address_home_id
                if address_home_id:
                    employee_with_same_address_home_id = self.env['hr.employee'].with_context(active_test=False). \
                        search([('address_home_id', '=', address_home_id.id), ('id', '!=', self.employee_id.id)],
                               limit=1)
                    if len(employee_with_same_address_home_id) == 0:
                        address_home_id.toggle_active()
                    else:
                        # El colaborador {} tiene asociada la dirección privada del colaborador que intenta reingresar.
                        raise UserError(_('The {} collaborator has associated the private address of the collaborator '
                                          'who tries to reenter.').format(employee_with_same_address_home_id.name))
                else:
                    default_country_id = self.get_default_country_id()
                    partner_with_same_vat = self.env['res.partner'].with_context(active_test=False).search([
                        ('vat', '=', self.employee_id.identification_id)
                    ])
                    if partner_with_same_vat:
                        employee_with_same_address_home_id = self.env['hr.employee'].with_context(active_test=False). \
                            search([('address_home_id', '=', partner_with_same_vat.id),
                                    ('id', '!=', self.employee_id.id)], limit=1)

                        if len(employee_with_same_address_home_id) == 0:
                            self.employee_id.address_home_id = partner_with_same_vat
                            partner_with_same_vat.toggle_active()
                            partner_with_same_vat.name = self.employee_id.name
                            partner_with_same_vat.email = self.employee_id.private_email
                            partner_with_same_vat.country_id = default_country_id
                        else:
                            # No se definió la dirección privada del colaborador.
                            # Además existe una dirección privada con identificación
                            # %s asociada a un colaborador existente con nombre %s.
                            # Tenga en cuenta que algunos datos pueden estar inactivos.
                            raise UserError(_("The collaborator's private address was not defined. "
                                              "In addition, there is a private address with identification %s associated "
                                              "with an existing collaborator with name %s. "
                                              "Please note that some data may be inactive.") %
                                            (partner_with_same_vat.vat, employee_with_same_address_home_id.name))
                    else:
                        partner = self.env['res.partner'].create({
                            'name': self.employee_id.name,
                            'email': self.employee_id.private_email,
                            'country_id': default_country_id,
                            'vat': self.employee_id.identification_id,
                        })
                        self.employee_id.address_home_id = partner

                if self.employee_id.get_create_user_when_creating_employee():
                    if self.employee_id.state in ["affiliate"]:
                        user_id = self.employee_id.user_id
                        if user_id:
                            employee_with_same_user_id = self.env['hr.employee'].with_context(active_test=False).\
                                search([('user_id', '=', user_id.id), ('id', '!=', self.employee_id.id)], limit=1)
                            if len(employee_with_same_user_id) == 0:
                                user_id.toggle_active()
                            else:
                                # El colaborador {} tiene asociado el usuario del colaborador que intenta reingresar.
                                raise UserError(_('The {} collaborator has associated the user of the collaborator '
                                                  'trying to reenter.').format(employee_with_same_user_id.name))
                        else:
                            user_with_same_login = self.env['res.users'].with_context(active_test=False).search([
                                ('login', '=', self.employee_id.identification_id)
                            ])
                            if user_with_same_login:
                                employee_with_same_user_id = self.env['hr.employee'].with_context(active_test=False). \
                                    search([('user_id', '=', user_with_same_login.id),
                                            ('id', '!=', self.employee_id.id)], limit=1)

                                if len(employee_with_same_user_id) == 0:
                                    self.employee_id.user_id = user_with_same_login
                                    if not user_with_same_login.active:
                                        user_with_same_login.active = True
                                    user_with_same_login.name = self.employee_id.name
                                    user_with_same_login.email = \
                                        self.employee_id.private_email or self.employee_id.work_email
                                    user_with_same_login.work_email = \
                                        self.employee_id.work_email or self.employee_id.private_email
                                    user_with_same_login.partner_id = self.employee_id.address_home_id.id
                                    user_with_same_login.password = self.employee_id.get_password(self.employee_id)
                                else:
                                    # El usuario del colaborador no fue definido.
                                    # Además existe un usuario con nombre %s y login %s asociado
                                    # a un colaborador con nombre %s.
                                    # Tenga en cuenta que algunos datos pueden estar inactivos.
                                    raise UserError(_("The collaborator's user was not defined. "
                                                      "There is also a user with name %s and login %s "
                                                      "associated with a collaborator with name %s."
                                                      "Please note that some data may be inactive.") %
                                                    (user_with_same_login.name, user_with_same_login.login,
                                                     employee_with_same_user_id.name))
                            else:
                                user = self.env['res.users'].create({
                                    'name': self.employee_id.name,
                                    'login': self.employee_id.identification_id,
                                    'partner_id': self.employee_id.address_home_id.id,
                                    'password': self.employee_id.get_password(self.employee_id),
                                })
                                self.employee_id.user_id = user
                                user.email = self.employee_id.private_email or self.employee_id.work_email
                                user.work_email = self.employee_id.work_email or self.employee_id.private_email
            else:
                # Para realizar un reingreso debe haber existido un proceso previo de salida.
                # Sólo puede existir un historial por departamento sin fecha de fin.
                raise UserError(_('To make a reenter there must have been a previous exit process. '
                                  'There can only be one history per department without an end date.'))
        else:
            raise UserError(_('The destination department must be different from the current department.'))