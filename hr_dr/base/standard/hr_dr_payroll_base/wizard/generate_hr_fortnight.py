from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class GenerateFortnight(models.TransientModel):
    _name = "generate.hr.fortnight"
    _description = "Generate fortnight"

    # TODO Incorporar al cálculo de quincena novedades.
    date = fields.Date('Payment date', default=datetime.today())
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  related='company_id.currency_id')
    employee_ids = fields.Many2many('hr.employee', string='Collaborators')
    input_ids = fields.One2many('hr.input', 'generate_hr_fortnight_id', string="News (Other Income / Expenses)")

    @api.onchange('date')
    def get_input_domain(self):
        input_ids = self.env['hr.input'].search([
            ('date', '>=', self.date.replace(day=1)),
            ('date', '<=', self.date)
        ])
        return {'domain': {'input_ids': [('id', 'in', input_ids.ids)]}}

    def generate_fortnight(self):
        if len(self.employee_ids) > 0:
            employees = self.employee_ids
        else:
            employees = self.env['hr.employee'].search([
                ('active', '=', True),
                ('employee_admin', '=', False),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['affiliate', 'temporary'])
            ])

        obj_fortnight = self.env['hr.fortnight']
        lines = []

        for e in employees:
            if e.contract_id.state == 'open' and \
                    e.contract_id.date_start <= self.date and \
                    not e.contract_id.date_end:
                if e.contract_id.receive_fortnight and e.contract_id.fortnight > 0:
                    fortnight = e.contract_id.fortnight
                    if fortnight > 0:
                        fortnight_data = self.get_fortnight_data(e, fortnight)
                        obj_fortnight.create(fortnight_data)
                        lines = self.generate_account_move_line(e, lines, fortnight)
                        self.create_payment(e, fortnight)
                    else:
                        raise ValidationError(_("The value of the fortnight for the {} collaborator is "
                                                "less than or equal to zero.").format(e.name))
        self.create_account_move(lines)

        tree_view_id = self.env.ref('hr_dr_payroll_base.hr_fortnight_view_tree').id
        search_view_id = self.env.ref('hr_dr_payroll_base.hr_fortnight_view_search').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fortnight',
            'res_model': 'hr.fortnight',
            'target': 'current',
            'view_mode': 'tree',
            'context': {'search_default_group_by_date': 1},
            'search_view_id': [search_view_id, 'search'],
            'views': [(tree_view_id, 'tree')]
        }

    def get_fortnight_data(self, employee, amount):
        date_from = self.date.replace(day=1)
        return {
            'employee_id': employee.id,
            'amount': amount,
            'date_from': date_from,
            'date_to': self.date,
            'company_id': self.company_id.id,
            'name': _('Fortnight corresponding to {}.').format(
                str(self.date.strftime("%B/%Y"))
            )
        }

    def create_account_move(self, lines):
        pass

    def generate_account_move_line(self, employee, lines, fortnight):
        return lines

    def create_payment(self, employee, amount):
        pass