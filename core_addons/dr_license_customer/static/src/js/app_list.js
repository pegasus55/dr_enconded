/** @odoo-module **/
const {xml, Component, useState, onWillUpdateProps} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";

export class AppList extends Component {
    setup() {
        super.setup();

        this.state = useState({
          content: [],
          total: 0
        });

        this.state.content = JSON.parse(this.props.value);
        this.state.total = this.state.content.length;

        onWillUpdateProps((nextProps) => {
          if (this.props.value !== nextProps.value) {
            this.state.content = JSON.parse(nextProps.value);
            this.state.total = this.state.content.length;
          }
        });
    }
}

AppList.template = "dr_license_customer.appList";
AppList.props = standardFieldProps;
registry.category("fields").add("app-list", AppList);