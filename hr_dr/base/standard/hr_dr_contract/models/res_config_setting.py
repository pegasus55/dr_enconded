from odoo import api, fields, models, _


class HrDrContractSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    contract_administrators_ids = fields.Many2many(
        'hr.employee', 'rcs_contract_administrators_employee_rel', 'res_config_settings_id', 'employee_id',
        string='Contract administrators', required=True)
    trial_period_end_anticipation_days = fields.Integer(
        string='Anticipation days',
        help='Days in advance for notification of the end of the trial period.', default=30)

    @api.model
    def get_values(self):
        res = super(HrDrContractSettings, self).get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()

        if config_parameter.get_param('contract.administrators.ids'):
            if config_parameter.get_param('contract.administrators.ids') != '':
                res.update(contract_administrators_ids=self.env['hr.employee'].
                           sudo().browse([int(id) for id in config_parameter.
                                         get_param('contract.administrators.ids').split(',')]).exists())

        if config_parameter.get_param('trial.period.end.anticipation.days'):
            if config_parameter.get_param('trial.period.end.anticipation.days') != '':
                res.update(trial_period_end_anticipation_days=int(config_parameter.get_param(
                    'trial.period.end.anticipation.days', default=30)))

        return res

    def set_values(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('contract.administrators.ids', ",".join([str(id) for id in self.contract_administrators_ids.ids]))
        set_param("trial.period.end.anticipation.days", self.trial_period_end_anticipation_days)
        super(HrDrContractSettings, self).set_values()