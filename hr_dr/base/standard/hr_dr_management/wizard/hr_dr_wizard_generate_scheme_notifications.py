# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class GenerateSchemeNotifications(models.TransientModel):
    _name = "hr.generate.scheme.notifications"
    _description = 'Generate scheme notifications'

    def action_generate_scheme_notifications(self):
        if self.generate_mode == 'personalized':
            if len(self.employee_ids) > 0:
                employees = self.employee_ids
            else:
                employees = self.env['hr.employee'].sudo().search([
                    ('active', '=', True),
                    ('employee_admin', '=', False),
                    ('state', 'in', ['affiliate', 'temporary', 'intern'])])

            for employee in employees:
                for line in self.line_ids:
                    self.env['hr.scheme.notifications'].sudo().create({
                        'model_id': self.model_id.id,
                        'sub_model_id': self.sub_model_id.id,
                        'res_id': self.res_id,
                        'employee_requests_id': employee.id,
                        'employee_approve_id': line.employee_approve_id.id,
                        'level': line.level
                    })

        elif self.generate_mode == 'bylevels':
            if len(self.employee_ids) > 0:
                employees = self.employee_ids
            else:
                employees = self.env['hr.employee'].sudo().search([
                    ('active', '=', True),
                    ('employee_admin', '=', False),
                    ('state', 'in', ['affiliate', 'temporary', 'intern'])])

            for e in employees:
                departments = self._get_parent_by_department(e.department_id.id)
                cont_level = 1

                if self.is_department_manager(e):
                    for d in departments[1:int(self.level) + 1]:
                        self.env['hr.scheme.notifications'].sudo().create({
                            'model_id': self.model_id.id,
                            'sub_model_id': self.sub_model_id.id,
                            'res_id': self.res_id,
                            'employee_requests_id': e.id,
                            'employee_approve_id': d.manager_id.id,
                            'level': cont_level
                        })

                        if self.include_additional_managers and 'hr_dr_department_additional_manager' \
                                in self.env.registry._init_modules:
                            if d.additional_manager_ids:
                                for am in d.additional_manager_ids:
                                    self.env['hr.scheme.notifications'].sudo().create({
                                        'model_id': self.model_id.id,
                                        'sub_model_id': self.sub_model_id.id,
                                        'res_id': self.res_id,
                                        'employee_requests_id': e.id,
                                        'employee_approve_id': am.id,
                                        'level': cont_level
                                    })

                        cont_level += 1
                else:
                    for d in departments[0:int(self.level)]:
                        self.env['hr.scheme.notifications'].sudo().create({
                            'model_id': self.model_id.id,
                            'sub_model_id': self.sub_model_id.id,
                            'res_id': self.res_id,
                            'employee_requests_id': e.id,
                            'employee_approve_id': d.manager_id.id,
                            'level': cont_level
                        })

                        if self.include_additional_managers and 'hr_dr_department_additional_manager' \
                                in self.env.registry._init_modules:
                            if d.additional_manager_ids:
                                for am in d.additional_manager_ids:
                                    self.env['hr.scheme.notifications'].sudo().create({
                                        'model_id': self.model_id.id,
                                        'sub_model_id': self.sub_model_id.id,
                                        'res_id': self.res_id,
                                        'employee_requests_id': e.id,
                                        'employee_approve_id': am.id,
                                        'level': cont_level
                                    })

                        cont_level += 1
                # Agregar la notificación de último nivel

                if self.include_last_level:
                    self.env['hr.scheme.notifications'].sudo().create({
                        'model_id': self.model_id.id,
                        'sub_model_id': self.sub_model_id.id,
                        'res_id': self.res_id,
                        'employee_requests_id': e.id,
                        'employee_approve_id': self.last_level_employee_approve_id.id,
                        'level': cont_level
                    })

        view_id = self.env.ref('hr_dr_management.scheme_notifications_list').id
        return {'type': 'ir.actions.act_window',
                'name': 'Scheme notifications list',
                'res_model': 'hr.scheme.notifications',
                'target': 'current',
                'view_mode': 'tree',
                'views': [[view_id, 'tree']],
                }

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
                    raise ValidationError(_("ID field is required."))

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

    def _get_parent_by_department(self, id):
        return self.env['hr.department'].search([('parent_id', 'parent_of', id)], order='complete_name asc')[::-1]

    def is_department_manager(self, employee):
        if employee.department_id.manager_id == employee:
            return True
        if 'hr_dr_department_additional_manager' in self.env.registry._init_modules:
            if employee.department_id.additional_manager_ids:
                for am in employee.department_id.additional_manager_ids:
                    if employee == am:
                        return True
        return False

    @api.onchange('department_ids')
    def _onchange_departments(self):
        self.employee_ids = self.env['hr.employee'].sudo().search(
            [('department_id', 'in', self.department_ids.ids)])

    @api.onchange('input_mode')
    def _onchange_input_mode(self):
        self.employee_ids = [(6, 0, [])]
        self.department_ids = [(6, 0, [])]

    _GENERATE_MODE = [
        ('personalized', _('Personalized')),
        ('bylevels', _('By levels'))
    ]
    generate_mode = fields.Selection(_GENERATE_MODE, string='Generate mode', required=True, default='personalized',
                                     help='')
    model_id = fields.Many2one('ir.model', string="Model", required=True)
    sub_model_id = fields.Many2one('ir.model', string='Sub model', ondelete='cascade')
    res_id = fields.Integer(string='ID')
    _MODE = [
        ('employee', _('Collaborator')),
        ('department', _('Department'))
    ]
    input_mode = fields.Selection(_MODE, string='Mode', default='employee', help='')
    department_ids = fields.Many2many('hr.department', string='Departments')
    employee_ids = fields.Many2many('hr.employee', string='Collaborator')
    line_ids = fields.One2many('hr.generate.scheme.notifications.line', 'wizard_line_id', string='Levels')
    level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Level', default='1')
    include_last_level = fields.Boolean(string='Include last level', default=True, help='')
    last_level_employee_approve_id = fields.Many2one('hr.employee', string="Last level")
    include_additional_managers = fields.Boolean(string='Include additional managers', default=True, help='')


class GenerateSchemeNotificationsLine(models.TransientModel):
    _name = "hr.generate.scheme.notifications.line"
    _description = 'Generate scheme notifications detail'

    wizard_line_id = fields.Many2one('hr.generate.scheme.notifications', string='Wizard')
    level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Level', required=True, default='1')
    employee_approve_id = fields.Many2one('hr.employee', string="Approving collaborator", required=True)


class Employee(models.Model):
    _inherit = 'hr.employee'

    wizard_generate_id = fields.Many2one('hr.generate.scheme.notifications', string='Wizard', store=False, index=True)
    wizard_generate_line_id = fields.Many2one('hr.generate.scheme.notifications.line', string='Wizard line',
                                              store=False, index=True)