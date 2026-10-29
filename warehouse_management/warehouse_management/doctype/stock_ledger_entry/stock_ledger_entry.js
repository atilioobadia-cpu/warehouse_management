// Copyright (c) 2026, X Electronics and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Ledger Entry', {
	item: function(frm) {
		if (frm.doc.item) {
			frappe.db.get_value('Item', frm.doc.item, ['stock_uom', 'standard_rate', 'item_name', 'item_code'], (r) => {
				if (r) {
					if (r.stock_uom) frm.set_value('stock_uom', r.stock_uom);
					if (r.standard_rate) frm.set_value('rate', r.standard_rate);
					if (r.standard_rate) frm.set_value('valuation_rate', r.standard_rate);
					frm.refresh_field('item');
				}
			});
		}
	},
	actual_qty: function(frm) {
		if (frm.doc.rate && frm.doc.actual_qty) {
			frm.set_value('stock_value_difference', frm.doc.rate * frm.doc.actual_qty);
		}
	},
	rate: function(frm) {
		if (frm.doc.rate && frm.doc.actual_qty) {
			frm.set_value('stock_value_difference', frm.doc.rate * frm.doc.actual_qty);
		}
	}
});
