# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Controller, route

# class VacationNotification(http.Controller):
#
#     @http.route('/web/aprove_vacation_planning/<int:id>', type='http', auth='public', website=True)
#     def aproveVacationPlanning(self, id, **kwargs):
#         notification = request.env['hr.notification.employee'].sudo().search([('id','=',id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error':'Esta notificacion ya fue procesada.'})
#         else:
#             notification.approve_vacation_planning()
#             return request.render("hr_dr_vacations.vacations_planning_aprove", {})
#
#     @http.route('/web/aprove_vacation_execution/<int:id>', type='http', auth='public', website=True)
#     def aproveVacationExecution(self, id, **kwargs):
#         notification = request.env['hr.notification.employee'].sudo().search([('id','=',id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_vacations.vacations_execution_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_vacations.vacations_execution_error", {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_vacations.vacations_execution_error", {'error':'Esta notificacion ya fue procesada.'})
#         else:
#             notification.approve_vacation_execution()
#             return request.render("hr_dr_vacations.vacations_request_aprove", {})
#
#
#
#     @http.route('/web/reject_vacation_planning/<int:id>', type='http', auth='public', website=True)
#     def rejectVacationPlanning(self, id, **kwargs):
#         notification = request.env['hr.notification.employee'].sudo().search([('id', '=', id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_vacations.vacations_planning_error", {'error':'Esta notificacion ya fue procesada.'})
#         else:
#             notification.reject_vacation_planning()
#             return request.render("hr_dr_vacations.vacations_planning_rejected", {})
#
#     @http.route('/web/reject_vacation_execution/<int:id>', type='http', auth='public', website=True)
#     def rejectVacationExecution(self, id, **kwargs):
#         notification = request.env['hr.notification.employee'].sudo().search([('id', '=', id)])
#
#         if notification.state == 'cancelled':
#             return request.render("hr_dr_vacations.vacations_execution_error", {'error': 'Esta notificación fue cancelada.'})
#         elif notification.state == 'reassigned':
#             return request.render("hr_dr_vacations.vacations_execution_error",
#                                   {'error': 'Esta notificación fue reasignada.'})
#         elif notification.state != 'pending':
#             return request.render("hr_dr_vacations.vacations_execution_error",
#                                   {'error': 'Esta notificacion ya fue procesada.'})
#         else:
#             notification.reject_vacation_execution()
#             return request.render("hr_dr_vacations.vacations_request_rejected", {})