from odoo import api, fields, models, _


class EmployeeSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Crear usuario al crear el colaborador
    create_user_when_creating_employee = fields.Boolean(string='Create user when creating collaborator')
    validate_identification = fields.Boolean(string='Validate identification')
    country_id = fields.Many2one('res.country', string='Country', help="", required=True,
                                 default=lambda x: x.env.company.country_id.id)

    @api.model
    def get_values(self):
        res = super(EmployeeSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        if config_parameter.get_param('create.user.when.creating.employee'):
            if config_parameter.get_param('create.user.when.creating.employee') != '':
                res.update(create_user_when_creating_employee=
                           bool(int(config_parameter.get_param('create.user.when.creating.employee', default=1))))

        if config_parameter.get_param('hr_dr.employee.validate.identification'):
            if config_parameter.get_param('hr_dr.employee.validate.identification') != '':
                res.update(validate_identification=
                           bool(int(config_parameter.get_param('hr_dr.employee.validate.identification', default=1))))

        if config_parameter.get_param('hr_dr.employee.country'):
            if config_parameter.get_param('hr_dr.employee.country') != '':
                res.update(country_id=int(config_parameter.get_param('hr_dr.employee.country')))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param("create.user.when.creating.employee", int(self.create_user_when_creating_employee))
        set_param("hr_dr.employee.validate.identification", int(self.validate_identification))
        set_param("hr_dr.employee.country", self.country_id.id)
        super(EmployeeSettings, self).set_values()