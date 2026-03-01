/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonRenderer.prototype, {
    eventClassNames(info) {
        const classes = super.eventClassNames(info);
        const record = info.event.extendedProps?.record;
        if (record) {
            if (record.is_commercial) {
                classes.push("o_commercial_event");
            }
            if (record.commercial_status) {
                classes.push(`o_commercial_status_${record.commercial_status}`);
            }
            if (record.commercial_feedback) {
                classes.push("o_commercial_has_feedback");
            }
        }
        return classes;
    },
});
