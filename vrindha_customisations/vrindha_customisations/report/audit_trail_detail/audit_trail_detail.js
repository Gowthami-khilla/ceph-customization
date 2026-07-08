// Copyright (c) 2023, Resilient Tech and contributors
// For license information, please see license.txt

const REPORT_TYPES = ["Detailed", "Summary by DocType", "Summary by User"];

const DATE_OPTIONS = [
    "Today",
    "Yesterday",
    "This Week",
    "This Month",
    "This Quarter",
    "This Year",
    "Last Week",
    "Last Month",
    "Last Quarter",
    "Last Year",
    "Custom",
];

frappe.query_reports["Audit Trail Detail"] = {
    filters: [

        // =====================
        // COMPANY
        // =====================
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },

        // =====================
        // REPORT TYPE
        // =====================
        {
            fieldname: "report",
            label: __("Report"),
            fieldtype: "Select",
            options: REPORT_TYPES,
            default: "Detailed",
            reqd: 1
        },

        // =====================
        // DATE OPTION
        // =====================
        {
            fieldname: "date_option",
            label: __("Select Day"),
            fieldtype: "Select",
            options: DATE_OPTIONS,
            default: "This Week",
            reqd: 1
        },

        // =====================
        // DATE RANGE (Custom only)
        // =====================
        {
            fieldname: "date_range",
            label: __("Select Dates"),
            fieldtype: "DateRange",
            depends_on: "eval: doc.date_option == 'Custom'",
            default: [frappe.datetime.month_start(), frappe.datetime.now_date()]
        },

        // =====================
        // USER
        // =====================
        {
            fieldname: "user",
            label: __("User"),
            fieldtype: "Link",
            options: "User"
        },

        // =====================
        // DOCTYPE (FIXED - IMPORTANT)
        // =====================
        {
            fieldname: "doctype",
            label: __("DocType"),
            fieldtype: "Link",
            options: "DocType"
        }
    ],

    // =====================
    // SAFE REFRESH HANDLING
    // =====================
    onload: function (report) {
        report.page.clear_menu(); // avoids UI conflicts
    },

    after_datatable_render: function (report) {
        // safe hook (no breaking UI)
    }
};