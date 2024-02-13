# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Controller, route

# class PermissionNotification(http.Controller):
#
#     @http.route('/web/aprove_permission/<int:id>', type='http', auth='public', website=True)
#     def aprovePermission(self, id, **kwargs):
#         notification = request.env['hr.permission.notification.employee'].sudo().search([('id','=',id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_permissions.permission_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_permissions.permission_error", {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_permissions.permission_error", {'error':'Esta notificación ya fue procesada.'})
#         else:
#             notification.approve_permission()
#             return request.render("hr_dr_permissions.permission_aprove", {})
#
#
#
#     @http.route('/web/reject_permission/<int:id>', type='http', auth='public', website=True)
#     def rejectPermission(self, id, **kwargs):
#         notification = request.env['hr.notification.employee'].sudo().search([('id', '=', id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_permissions.permission_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_permissions.permission_error", {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_permissions.permission_error", {'error':'Esta notificación ya fue procesada.'})
#         else:
#             notification.reject_permission()
#             return request.render("hr_dr_permissions.permission_rejected", {})