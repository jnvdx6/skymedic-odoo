/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

const COMMERCIAL_TYPE_ICONS = {
    "Visita Comercial": "fa fa-building",
    "Demo": "fa fa-desktop",
    "Formación": "fa fa-graduation-cap",
    "Llamada Comercial": "fa fa-phone",
    "Seguimiento": "fa fa-refresh",
    "Presentación": "fa fa-file-powerpoint-o",
};

patch(AttendeeCalendarModel.prototype, {
    /**
     * @override
     * Add commercial fields to the normalized record
     */
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(...arguments);
        if (rawRecord.is_commercial && rawRecord.commercial_activity_type_id) {
            const typeName = rawRecord.commercial_activity_type_id[1];
            if (COMMERCIAL_TYPE_ICONS[typeName]) {
                result.commercialIcon = COMMERCIAL_TYPE_ICONS[typeName];
            }
        }
        return result;
    },
});
