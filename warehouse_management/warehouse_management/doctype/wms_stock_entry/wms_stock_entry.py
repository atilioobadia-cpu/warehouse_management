import frappe
from frappe.model.document import Document


class WMSStockEntry(Document):
    def before_save(self):
        total = 0
        for item in self.items:
            item.amount = (item.qty or 0) * (item.rate or 0)
            total += item.amount
        self.total_amount = total

    def on_submit(self):
        self.create_stock_ledger_entries()

    def create_stock_ledger_entries(self):
        for item in self.items:
            if self.stock_entry_type == "Receipt":
                self._process_receipt(item)
            elif self.stock_entry_type == "Consume":
                self._process_consume(item)
            elif self.stock_entry_type == "Transfer":
                self._process_transfer(item)

    def _get_current_state(self, item_code, warehouse):
        """Get current qty and value for moving average."""
        sle = frappe.db.sql("""
            SELECT COALESCE(SUM(qty_change), 0) as qty,
                   COALESCE(SUM(qty_change * rate), 0) as value
            FROM `tabWMS Stock Ledger Entry`
            WHERE item = %s AND warehouse = %s
        """, (item_code, warehouse), as_dict=True)[0]
        return sle.qty or 0, sle.value or 0

    def _process_receipt(self, item):
        warehouse = item.target_warehouse
        if not warehouse:
            frappe.throw("Target Warehouse is required for Receipt")
        
        current_qty, current_value = self._get_current_state(item.item, warehouse)
        new_qty = current_qty + item.qty
        new_value = current_value + (item.qty * item.rate)
        new_rate = new_value / new_qty if new_qty else item.rate
        
        sle = frappe.new_doc("WMS Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.qty_change = item.qty
        sle.rate = item.rate
        sle.valuation_rate = new_rate
        sle.stock_value = new_value
        sle.balance_qty = new_qty
        sle.balance_value = new_value
        sle.insert(ignore_permissions=True)

    def _process_consume(self, item):
        warehouse = item.source_warehouse
        if not warehouse:
            frappe.throw("Source Warehouse is required for Consume")
        
        current_qty, current_value = self._get_current_state(item.item, warehouse)
        if current_qty < item.qty:
            frappe.throw(f"Insufficient stock: {current_qty} available, {item.qty} requested")
        
        consume_rate = current_value / current_qty if current_qty else item.rate
        new_qty = current_qty - item.qty
        new_value = current_value - (item.qty * consume_rate)
        new_rate = new_value / new_qty if new_qty else consume_rate
        
        sle = frappe.new_doc("WMS Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.qty_change = -item.qty
        sle.rate = consume_rate
        sle.valuation_rate = new_rate
        sle.stock_value = new_value
        sle.balance_qty = new_qty
        sle.balance_value = new_value
        sle.insert(ignore_permissions=True)

    def _process_transfer(self, item):
        source = item.source_warehouse
        target = item.target_warehouse
        if not source or not target:
            frappe.throw("Source and Target Warehouse are required for Transfer")
        
        # Remove from source
        current_qty, current_value = self._get_current_state(item.item, source)
        if current_qty < item.qty:
            frappe.throw(f"Insufficient stock in source: {current_qty} available, {item.qty} requested")
        
        transfer_rate = current_value / current_qty if current_qty else item.rate
        new_source_qty = current_qty - item.qty
        new_source_value = current_value - (item.qty * transfer_rate)
        new_source_rate = new_source_value / new_source_qty if new_source_qty else transfer_rate
        
        sle_out = frappe.new_doc("WMS Stock Ledger Entry")
        sle_out.item = item.item
        sle_out.warehouse = source
        sle_out.posting_date = self.posting_date
        sle_out.posting_time = self.posting_time
        sle_out.voucher_type = "Stock Entry"
        sle_out.voucher_no = self.name
        sle_out.qty_change = -item.qty
        sle_out.rate = transfer_rate
        sle_out.valuation_rate = new_source_rate
        sle_out.stock_value = new_source_value
        sle_out.balance_qty = new_source_qty
        sle_out.balance_value = new_source_value
        sle_out.insert(ignore_permissions=True)
        
        # Add to target at transfer rate
        target_qty, target_value = self._get_current_state(item.item, target)
        new_target_qty = target_qty + item.qty
        new_target_value = target_value + (item.qty * transfer_rate)
        new_target_rate = new_target_value / new_target_qty if new_target_qty else transfer_rate
        
        sle_in = frappe.new_doc("WMS Stock Ledger Entry")
        sle_in.item = item.item
        sle_in.warehouse = target
        sle_in.posting_date = self.posting_date
        sle_in.posting_time = self.posting_time
        sle_in.voucher_type = "Stock Entry"
        sle_in.voucher_no = self.name
        sle_in.qty_change = item.qty
        sle_in.rate = transfer_rate
        sle_in.valuation_rate = new_target_rate
        sle_in.stock_value = new_target_value
        sle_in.balance_qty = new_target_qty
        sle_in.balance_value = new_target_value
        sle_in.insert(ignore_permissions=True)
