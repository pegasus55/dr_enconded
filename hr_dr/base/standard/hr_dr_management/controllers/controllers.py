# -*- coding: utf-8 -*-
import werkzeug

from odoo import http
from odoo.http import request, Controller, route


class Notifications(http.Controller):

    @http.route('/web/aprove_notification/<int:id>', type='http', auth='user')
    def aproveNotification(self, id, **kwargs):
        notification = request.env['hr.notifications'].sudo().search([('id', '=', id)])
        try:
            notification.approve()
            db = request.params['db']
            model = request.params['model']
            res_id = request.params['id']
            action = request.params['action']
            menu_id = request.params['menu_id']

            if (request.session.uid and
                    request.env['res.users'].browse(request.session.uid).user_has_groups('base.group_user')):
                return werkzeug.utils.redirect('/web?db=%s#id=%s&action=%s&model=%s&view_type=form&menu_id=%s' %
                                               (db, res_id, action, model, menu_id))

        except Exception as e:
            return request.render("hr_dr_management.notification_error", {'error': str(e)})

    @http.route('/web/reject_notification/<int:id>', type='http', auth='user')
    def rejectNotification(self, id, **kwargs):
        notification = request.env['hr.notifications'].sudo().search([('id', '=', id)])
        try:
            notification.reject("")
            db = request.params['db']
            model = request.params['model']
            res_id = request.params['id']
            action = request.params['action']
            menu_id = request.params['menu_id']

            if (request.session.uid and
                    request.env['res.users'].browse(request.session.uid).user_has_groups('base.group_user')):
                return werkzeug.utils.redirect('/web?db=%s#id=%s&action=%s&model=%s&view_type=form&menu_id=%s' %
                                               (db, res_id, action, model, menu_id))

        except Exception as e:
            return request.render("hr_dr_management.notification_error", {'error': str(e)})