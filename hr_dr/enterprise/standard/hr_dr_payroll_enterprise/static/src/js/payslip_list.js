/** @odoo-module **/

import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { PayslipListController } from "@hr_payroll/js/payslip_list";

export class CustomPayslipListController extends PayslipListController {
  async onPrintClick() {
    const selectedIds = await this.getSelectedResIds();
    if (selectedIds.length == 0) {
        return;
    }
    const results = await this.orm.call('hr.payslip', 'action_print_payslip', [selectedIds]);
    console.log(results);
    if (results.type === "ir.actions.act_window") {
      results.views = [[false, "form"]];
    }
    this.actionService.doAction(results);
  }
}

registry.category('views').remove('hr_payroll_payslip_tree');
registry.category('views').add('hr_payroll_payslip_tree', {
    ...listView,
    Controller: CustomPayslipListController,
    buttonTemplate: 'PayslipListView.print_button',
})