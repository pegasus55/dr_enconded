from odoo import api, fields, models, _


class ManagementSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _DAYS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('-1', _('Last day of every month')),

    ]
    cutoff_day_reports = fields.Selection(_DAYS, string='Cutoff day for reports', required=True)
    hr_responsible_id = fields.Many2one('hr.employee', string='Human talent responsible', required=True)
    treasury_managers_ids = fields.Many2many('hr.employee', 'rcs_he_management_rel', 'res_config_settings_id',
                                             'employee_id', string='Treasury managers')

    @api.model
    def get_values(self):
        res = super(ManagementSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()
        res.update(cutoff_day_reports=config_parameter.get_param('cutoff.day.reports', default=''))
        res.update(hr_responsible_id=int(config_parameter.get_param('hr_dr_management.responsible')))

        if config_parameter.get_param('treasury.managers.ids'):
            if config_parameter.get_param('treasury.managers.ids') != '':
                res.update(treasury_managers_ids=self.env['hr.employee'].sudo().browse(
                    [int(id) for id in config_parameter.get_param('treasury.managers.ids').split(',')]).exists())

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param("cutoff.day.reports", self.cutoff_day_reports)
        set_param('hr_dr_management.responsible', self.hr_responsible_id.id)
        set_param('treasury.managers.ids', ",".join([str(id) for id in self.treasury_managers_ids.ids]))
        super(ManagementSettings, self).set_values()