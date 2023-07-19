/** @odoo-module **/
const {xml, Component} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";

export class AppList extends Component {
    setup() {
        super.setup();
        this.content = JSON.parse(this.props.value);
        this.total = this.content.length;
    }
}

AppList.template = "dr_license_customer.appList";
AppList.props = standardFieldProps;
registry.category("fields").add("app-list", AppList);