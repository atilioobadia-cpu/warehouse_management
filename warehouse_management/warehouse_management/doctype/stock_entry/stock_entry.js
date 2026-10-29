// Copyright (c) 2026, X Electronics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Entry", {
    refresh: function(frm) {

    }
});

frappe.ui.form.on("Stock Entry Detail", {
    item: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item) {
            frappe.db.get_value("Item", row.item, ["standard_rate", "stock_uom", "item_name"], function(r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "stock_uom", r.stock_uom);
                    frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
                    if (r.standard_rate) {
                        frappe.model.set_value(cdt, cdn, "rate", r.standard_rate);
                        frappe.model.set_value(cdt, cdn, "basic_rate", r.standard_rate);
                    }
                    if (row.qty) {
                        frappe.model.set_value(cdt, cdn, "amount", row.qty * (row.rate || r.standard_rate || 0));
                    } else {
                        frappe.model.set_value(cdt, cdn, "qty", 1);
                        frappe.model.set_value(cdt, cdn, "amount", 1 * (row.rate || r.standard_rate || 0));
                    }
                }
            });
        }
    },
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
        } else if (row.qty && !row.rate) {
            // try to get rate
            if (row.item) {
                frappe.db.get_value("Item", row.item, "standard_rate", function(r) {
                    if (r && r.standard_rate) {
                        frappe.model.set_value(cdt, cdn, "rate", r.standard_rate);
                        frappe.model.set_value(cdt, cdn, "amount", row.qty * r.standard_rate);
                    }
                });
            }
        }
    },
    rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
        }
    }
});
