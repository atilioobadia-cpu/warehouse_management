// Copyright (c) 2026, X Electronics and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Ledger Entry', {
	item: function(frm) {
		if (frm.doc.item) {
			frappe.db.get_value('Item', frm.doc.item, 'stock_uom', (r) => {
				if (r && r.stock_uom) {
					frm.set_value('stock_uom', r.stock_uom);
				}
			});
		}
	}
});
