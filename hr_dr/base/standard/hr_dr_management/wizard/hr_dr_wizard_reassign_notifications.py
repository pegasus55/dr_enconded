# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class ReassignNotifications(models.TransientModel):
    _name = "hr.reassign.notifications"
    _description = 'Reassign notifications'

    def action_reassign_notifications(self):
        if len(self.notifications_ids) > 0:
            for n in self.notifications_ids:
                new_notification = self.env['hr.notifications'].create({
                    'level': n.level,
                    'employee_requests_id': n.employee_requests_id.id,
                    'employee_approve_id': self.new_approver_id.id,
                    'parent_id': n.id,
                    'state': n.state,
                    'commentary': n.commentary,
                    'send': n.send,
                    'processed': n.processed,
                    'res_id': n.res_id,
                    'res_model_id': n.res_model_id.id
                })

                n.state = 'reassigned'

                if (new_notification and new_notification.send and new_notification.state == 'pending'
                        and not new_notification.processed):
                    # TODO: Enviar correo relacionado a la nueva notificacion
                    object = self.env[new_notification.res_model].search([
                        ('id', '=', new_notification.res_id),
                    ], limit=1)
                    if object:
                        new_notification.send_mail(object.get_local_context(new_notification.id))

            view_id = self.env.ref('hr_dr_management.hr_notifications_view_tree').id
            return {'type': 'ir.actions.act_window',
                    'name': 'hr.notifications.tree',
                    'res_model': 'hr.notifications',
                    'target': 'current',
                    'view_mode': 'tree',
                    'views': [[view_id, 'tree']],
                    }

        else:
            raise UserError(_("There are no notifications to reassign."))

    current_approver_id = fields.Many2one('hr.employee', string="Current approver", required=True)
    new_approver_id = fields.Many2one('hr.employee', string="New approver", required=True)
    model_ids = fields.Many2many('ir.model', string='Models')
    notifications_ids = fields.Many2many('hr.notifications', string='Notifications')

    @api.onchange('current_approver_id')
    def _onchange_current_approver_id(self):

        self.notifications_ids = [(6, 0, [])]
        self.model_ids = [(6, 0, [])]
        self.notifications_ids = self.env['hr.notifications'].sudo().search([
            ('state', '=', 'pending'),
            ('processed', '=', False),
            ('employee_approve_id', '=', self.current_approver_id.id)
        ])

    @api.onchange('model_ids')
    def _onchange_model_ids(self):
        if self.model_ids:
            self.notifications_ids = self.env['hr.notifications'].sudo().search([
                ('state', '=', 'pending'),
                ('processed', '=', False),
                ('employee_approve_id', '=', self.current_approver_id.id),
                ('res_model_id', 'in', [m.id for m in self.model_ids])
            ])
        else:
            self.notifications_ids = self.env['hr.notifications'].sudo().search([
                ('state', '=', 'pending'),
                ('processed', '=', False),
                ('employee_approve_id', '=', self.current_approver_id.id)
            ])