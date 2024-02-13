# -*- coding: utf-8 -*-

import odoo
from odoo import http, _
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request
from odoo.addons.web.controllers.home import Home, ensure_db
from odoo.addons.dr_license_customer.models.models import License


class HomeInherited(Home):

    @http.route('/web/license', auth="public")
    def license_request_form(self, **kw):
        values = request.params.copy()
        id_number = values.get('id_number', False)

        if id_number:
            try:
                lic = License(request.env['ir.config_parameter'].sudo().get_param)
                lic.request_license(id_number.strip())

                # Actualizo el parámetro del sistema con la nueva fecha. (Para mostrar el valor en la configuración.)
                request.env['ir.config_parameter'].sudo().set_param("license.expiring.date",
                                                                    lic.get_expiration_date(as_str=True))
                request.env['ir.config_parameter'].sudo().set_param("license.max.active.employees",
                                                                    lic.get_max_employees())
                request.env['ir.config_parameter'].sudo().set_param("license.nukleo.version", lic.get_nukleo_version())

                return request.redirect('/web/login')
            except ValidationError as e:
                values['error'] = e.args[0]

        return http.request.render('dr_start_system.license_request', values)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        # so it is correct if overloaded with auth="public"
        if not request.uid:
            request.update_env(user=odoo.SUPERUSER_ID)

        values = request.params.copy()

        lic = License(request.env['ir.config_parameter'].sudo().get_param)
        valid_lic, lic_error = lic.validate_license(request.session.db)
        values['valid_license'] = valid_lic

        # Validar licencia al iniciar sesión
        # if valid_lic:
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            try:
                uid = request.session.authenticate(request.db, request.params['login'],
                                                   request.params['password'])
                request.params['login_success'] = True

                if valid_lic:
                    # Actualizando contadores de la licencia
                    lic.increment_counters()

                    # Actualizando parámetros en res.config
                    lic.update_res_config_params(request.env['ir.config_parameter'].sudo().set_param)

                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True
        # else:
        #     values['error'] = lic_error

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response