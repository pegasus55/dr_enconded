/** @odoo-module **/
const {xml, Component} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";

export class DeviceList extends Component {
    setup() {
        super.setup();
        this.content = JSON.parse(this.props.value);
        this.total = this.content.length;
    }
}

DeviceList.template = "dr_license_customer.deviceList";
DeviceList.props = standardFieldProps;
registry.category("fields").add("device-list", DeviceList);
