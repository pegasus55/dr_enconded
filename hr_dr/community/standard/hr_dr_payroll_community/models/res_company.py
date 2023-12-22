# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def get_account_payable_payslip_id(self):
        """
        Este método setea el valor por defecto en la "Cuenta por pagar para nóminas"
        """
        return ''
        payable_payslip = self.env.ref('l10n_ec.1_a201070401', False)
        if payable_payslip:
            payable_payslip = payable_payslip.id
        return payable_payslip

    @api.model
    def get_journal_wage_id(self):
        """
        Este método setea el diario del contrato con el "Diario de Sueldos" como valor por defecto
        """
        return ''
        journal_wage = self.env.ref('hr_rxr_payroll.journal_wage', False)
        if journal_wage:
            journal_wage = journal_wage.id
        return journal_wage

    # Columns
    account_payable_payslip_id = fields.Many2one('account.account', string='Account payable payslip',
                                                 default=get_account_payable_payslip_id,
                                                 help='Select the default account to be used for payslip '
                                                      'can be changed in the contract or directly in the payslip')
    journal_wage_id = fields.Many2one('account.journal', string='Journal wage', default=get_journal_wage_id, help='')













    @api.model
    def get_journal_fourteenth_id(self):
        """
        Este método se encarga de configurar el "Diario de Costos de décimo cuarto" en la compañía
        """
        journal = self.env.ref('ecua_hr_severances.journal_fourteenth', False)
        if journal:
            journal = journal.id
        return journal

    @api.model
    def get_journal_thirteenth_id(self):
        """
        Este método se encarga de configurar el "Diario de Costos de décimo tercero" en la compañía
        """
        journal = self.env.ref('ecua_hr_severances.journal_thirteenth', False)
        if journal:
            journal = journal.id
        return journal

    @api.model
    def get_utility_journal_id(self):
        """
        Este método se encarga de configurar el "Diario de pago de utilidades" en la compañía
        """
        journal = self.env.ref('ecua_hr_severances.journal_utility', False)
        if journal:
            journal = journal.id
        return journal

    #Columns
    #Decimo cuarto
    journal_fourteenth_id = fields.Many2one(
        'account.journal',
        string='Diario Liq. Décimo Cuarto',
        default=get_journal_fourteenth_id,
        help='Diario utilizado para los asientos de liquidación anual del de décimo cuarto sueldo',
        )
    xiv_adjust_admin_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste Administrativa',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo cuarto sueldo',
        )
    xiv_adjust_sales_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste Ventas',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo cuarto sueldo',
        )
    xiv_adjust_direct_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste M.O. Directa',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo cuarto sueldo',
        )
    xiv_adjust_indirect_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste M.O. Indirecta',
        help = 'Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo cuarto sueldo',
        )
    xiv_provision_account = fields.Many2one(
        'account.account',
        string='Cta Provisión',
        help='Cta para computar y liquidar las provisiones para el pago anual del décimo cuarto sueldo'
        )
    xiv_earnings_attachment_account = fields.Many2one(
        'account.account',
        string='Cta Ret. Judicial',
        help='Cta para liquidar las retenciones judiciales en el pago anual del décimo cuarto sueldo'
        )
    xiv_advance_account = fields.Many2one(
        'account.account',
        string='Cta Anticipos',
        help='Cta para liquidar los anticipos entregados sobre el XIV sueldo, para el pago anual del décimo cuarto sueldo'
        )
    xiv_payable_account = fields.Many2one(
        'account.account',
        string='Cta x Pagar',
        help='Cta por pagar al liquidar el décimo cuarto sueldo'
        )
    xiv_exclude_dif_less_than = fields.Float(
        string='Omitir diferencia menor a',
        default=0.0,
        help='Se omiten las diferencias menores o iguales a este monto para el calculo del decimo cuarto sueldo'
        )
    #Decimo tercero
    journal_thirteenth_id = fields.Many2one(
        'account.journal',
        string='Diario Liq. Décimo Tercero',
        default=get_journal_thirteenth_id,
        help='Diario utilizado para los asientos de liquidación anual del de décimo tercer sueldo',
        )
    xiii_adjust_admin_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste Administrativa',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo tercer sueldo',
        )
    xiii_adjust_sales_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste Ventas',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo tercer sueldo',
        )
    xiii_adjust_direct_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste M.O. Directa',
        help='Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo tercer sueldo',
        )
    xiii_adjust_indirect_account = fields.Many2one(
        'account.account',
        string='Cta Ajuste M.O. Indirecta',
        help = 'Cta para las diferencias entre lo provisionado y lo calculado al liquidar anualmente el décimo tercer sueldo',
        )
    xiii_provision_account = fields.Many2one(
        'account.account',
        string='Cta Provisión',
        help='Cta para computar y liquidar las provisiones para el pago anual del décimo tercer sueldo'
        )
    xiii_earnings_attachment_account = fields.Many2one(
        'account.account',
        string='Cta Ret. Judicial',
        help='Cta para liquidar las retenciones judiciales en el pago anual del décimo tercer sueldo'
        )
    xiii_advance_account = fields.Many2one(
        'account.account',
        string='Cta Anticipos',
        help='Cta para liquidar los anticipos entregados sobre el XIII sueldo, para el pago anual del décimo tercer sueldo'
        )
    xiii_payable_account = fields.Many2one(
        'account.account',
        string='Cta x Pagar',
        help='Cta por pagar al liquidar el décimo tercer sueldo'
        )
    xiii_exclude_dif_less_than = fields.Float(
        string='Omitir diferencia menor a',
        default=0.1,
        help='Se omiten las diferencias menores o iguales a este monto para el calculo del decimo cuarto sueldo'
        )
    #Otros
    utility_journal_id = fields.Many2one(
        'account.journal',
        string='Diario de pago de utilidades',
        default=get_utility_journal_id,
        help='',
        )
    utility_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de utilidad',
        help='',
        )
    judicial_retention_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de retenciones judiciales',
        help='',
        )
    advance_utility_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de anticipo utilidades',
        help='',
        )
    employee_participation_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de participación trabajadores',
        help='',
        )
