from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError


class RegisterVacationsPaid(models.TransientModel):
    _name = "register.vacations.paid"
    _description = 'Register Vacations Paid'

    def _default_employee_vacation_detail(self):
        return self.env.context.get('employee_vacation_detail_id')

    employee_vacation_detail_id = fields.Many2one('hr.employee.vacation.detail', string='Employee vacation detail',
                                                  default=_default_employee_vacation_detail, required=True,
                                                  ondelete='cascade')
    paid = fields.Float(string='Vacations paid', required=True)

    def action_paid(self):
        if self.paid > self.employee_vacation_detail_id.available:
            # Las vacaciones disponibles del período deben ser mayor o igual a las vacaciones pagadas.
            raise UserError(_('The vacations available for the period must be greater than or '
                              'equal to the paid vacations.'))
        else:
            self.employee_vacation_detail_id.paid = self.paid
            self.employee_vacation_detail_id.employee_id.update_vacations_available()
        return True