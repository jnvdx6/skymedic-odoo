/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonRenderer.prototype, {
    /**
     * @override
     * Add commercial status CSS classes to calendar events
     */
    eventClassNames({ el, event }) {
        const classesToAdd = super.eventClassNames(...arguments);
        const record = this.props.model.records[event.id];
        if (record && record.rawRecord && record.rawRecord.is_commercial) {
            classesToAdd.push("o_commercial_event");
            const status = record.rawRecord.commercial_status;
            if (status) {
                classesToAdd.push(`o_commercial_status_${status}`);
            }
            if (record.rawRecord.commercial_feedback) {
                classesToAdd.push("o_commercial_has_feedback");
            }
        }
        return classesToAdd;
    },
});
