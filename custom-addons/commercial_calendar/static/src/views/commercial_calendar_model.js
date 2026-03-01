/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

const ACTIVITY_ICONS = {
    "Visita Comercial": "fa-building",
    "Demo": "fa-desktop",
    "Formación": "fa-graduation-cap",
    "Llamada Comercial": "fa-phone",
    "Seguimiento": "fa-refresh",
    "Presentación": "fa-file-powerpoint-o",
};

patch(AttendeeCalendarModel.prototype, {
    normalizeRecord(record) {
        const result = super.normalizeRecord(record);
        if (record.commercial_activity_type_id) {
            const typeName = record.commercial_activity_type_id[1];
            result.commercialIcon = ACTIVITY_ICONS[typeName] || "fa-briefcase";
        }
        return result;
    },
});
