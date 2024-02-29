from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError


class RegisterVacationsLost(models.TransientModel):
    _name = "register.vacations.lost"
    _description = 'Register Vacations Lost'

    def _default_employee_vacation_detail(self):
        return self.env.context.get('employee_vacation_detail_id')

    def _default_lost(self):
        return self.env.context.get('lost')

    employee_vacation_detail_id = fields.Many2one('hr.employee.vacation.detail', string='Employee vacation detail',
                                                  default=_default_employee_vacation_detail, required=True,
                                                  ondelete='cascade')
    lost = fields.Float(string='Value to lose', default=_default_lost, required=True)
    
    def action_lost(self):
        if self.lost > self.employee_vacation_detail_id.available:
            # Las vacaciones disponibles del período deben ser mayor o igual a las vacaciones perdidas.
            raise UserError(_('The vacations available for the period must be greater than or '
                              'equal to the vacations lost.'))
        else:
            self.employee_vacation_detail_id.lost = self.lost
            self.employee_vacation_detail_id.employee_id.update_vacations_available()
        return True