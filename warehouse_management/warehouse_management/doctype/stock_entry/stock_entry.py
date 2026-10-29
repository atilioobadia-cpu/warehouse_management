import frappe
from frappe.model.document import Document


class StockEntry(Document):
    def before_save(self):
        total = 0
        for item in self.items:
            item.amount = (item.qty or 0) * (item.rate or 0)
            total += item.amount
        self.total_amount = total

    def on_submit(self):
        self.create_stock_ledger_entries()

    def on_cancel(self):
        self.create_reversal_entries()

    def create_stock_ledger_entries(self):
        for item in self.items:
            if self.stock_entry_type == "Receipt":
                self._process_receipt(item)
            elif self.stock_entry_type == "Consume":
                self._process_consume(item)
            elif self.stock_entry_type == "Transfer":
                self._process_transfer(item)

    def create_reversal_entries(self):
        for item in self.items:
            if self.stock_entry_type == "Receipt":
                self._reverse_receipt(item)
            elif self.stock_entry_type == "Consume":
                self._reverse_consume(item)
            elif self.stock_entry_type == "Transfer":
                self._reverse_transfer(item)

    def _get_current_state(self, item_code, warehouse):
        """Get current qty and value for moving average (stateless - computed from ledger)."""
        result = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty), 0) as qty,
                   COALESCE(SUM(stock_value_difference), 0) as value
            FROM `tabStock Ledger Entry`
            WHERE item = %s AND warehouse = %s
        """, (item_code, warehouse), as_dict=True)[0]
        return result.qty or 0, result.value or 0

    def _process_receipt(self, item):
        warehouse = getattr(item, 't_warehouse', None) or getattr(item, 'target_warehouse', None) or getattr(self, 'to_warehouse', None) or getattr(self, 'target_warehouse', None)
        if not warehouse:
            frappe.throw("Target Warehouse is required for Receipt")

        current_qty, current_value = self._get_current_state(item.item, warehouse)
        new_qty = current_qty + item.qty
        new_value = current_value + (item.qty * item.rate)
        new_rate = new_value / new_qty if new_qty else item.rate

        sle = frappe.new_doc("Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.voucher_detail_no = item.name
        sle.actual_qty = item.qty
        sle.rate = item.rate
        sle.incoming_rate = item.rate
        sle.valuation_rate = new_rate
        sle.stock_value_difference = item.qty * item.rate
        sle.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle.insert(ignore_permissions=True)

    def _process_consume(self, item):
        warehouse = getattr(item, 's_warehouse', None) or getattr(item, 'source_warehouse', None) or getattr(self, 'from_warehouse', None) or getattr(self, 'source_warehouse', None)
        if not warehouse:
            frappe.throw("Source Warehouse is required for Consume")

        current_qty, current_value = self._get_current_state(item.item, warehouse)
        if current_qty < item.qty:
            frappe.throw(f"Insufficient stock: {current_qty} available, {item.qty} requested")

        consume_rate = current_value / current_qty if current_qty else item.rate
        new_qty = current_qty - item.qty
        new_value = current_value - (item.qty * consume_rate)
        new_rate = new_value / new_qty if new_qty else consume_rate

        sle = frappe.new_doc("Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.voucher_detail_no = item.name
        sle.actual_qty = -item.qty
        sle.rate = consume_rate
        sle.incoming_rate = 0
        sle.valuation_rate = new_rate
        sle.stock_value_difference = -(item.qty * consume_rate)
        sle.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle.insert(ignore_permissions=True)

    def _process_transfer(self, item):
        source = getattr(item, 's_warehouse', None) or getattr(item, 'source_warehouse', None) or getattr(self, 'from_warehouse', None) or getattr(self, 'source_warehouse', None)
        target = getattr(item, 't_warehouse', None) or getattr(item, 'target_warehouse', None) or getattr(self, 'to_warehouse', None) or getattr(self, 'target_warehouse', None)
        if not source or not target:
            frappe.throw("Source and Target Warehouse are required for Transfer")

        current_qty, current_value = self._get_current_state(item.item, source)
        if current_qty < item.qty:
            frappe.throw(f"Insufficient stock in source: {current_qty} available, {item.qty} requested")

        transfer_rate = current_value / current_qty if current_qty else item.rate
        new_source_qty = current_qty - item.qty
        new_source_value = current_value - (item.qty * transfer_rate)
        new_source_rate = new_source_value / new_source_qty if new_source_qty else transfer_rate

        # Out row (source)
        sle_out = frappe.new_doc("Stock Ledger Entry")
        sle_out.item = item.item
        sle_out.warehouse = source
        sle_out.posting_date = self.posting_date
        sle_out.posting_time = self.posting_time
        sle_out.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle_out.voucher_type = "Stock Entry"
        sle_out.voucher_no = self.name
        sle_out.voucher_detail_no = item.name
        sle_out.actual_qty = -item.qty
        sle_out.rate = transfer_rate
        sle_out.incoming_rate = 0
        sle_out.valuation_rate = new_source_rate
        sle_out.stock_value_difference = -(item.qty * transfer_rate)
        sle_out.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle_out.insert(ignore_permissions=True)

        # In row (target) at transfer rate
        target_qty, target_value = self._get_current_state(item.item, target)
        new_target_qty = target_qty + item.qty
        new_target_value = target_value + (item.qty * transfer_rate)
        new_target_rate = new_target_value / new_target_qty if new_target_qty else transfer_rate

        sle_in = frappe.new_doc("Stock Ledger Entry")
        sle_in.item = item.item
        sle_in.warehouse = target
        sle_in.posting_date = self.posting_date
        sle_in.posting_time = self.posting_time
        sle_in.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle_in.voucher_type = "Stock Entry"
        sle_in.voucher_no = self.name
        sle_in.voucher_detail_no = item.name
        sle_in.actual_qty = item.qty
        sle_in.rate = transfer_rate
        sle_in.incoming_rate = transfer_rate
        sle_in.valuation_rate = new_target_rate
        sle_in.stock_value_difference = item.qty * transfer_rate
        sle_in.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle_in.insert(ignore_permissions=True)

    def _reverse_receipt(self, item):
        warehouse = getattr(item, 't_warehouse', None) or getattr(item, 'target_warehouse', None) or getattr(self, 'to_warehouse', None) or getattr(self, 'target_warehouse', None)
        current_qty, current_value = self._get_current_state(item.item, warehouse)
        new_qty = current_qty - item.qty
        new_value = current_value - (item.qty * item.rate)
        new_rate = new_value / new_qty if new_qty else item.rate

        sle = frappe.new_doc("Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.voucher_detail_no = item.name
        sle.actual_qty = -item.qty
        sle.rate = item.rate
        sle.incoming_rate = 0
        sle.valuation_rate = new_rate
        sle.stock_value_difference = -(item.qty * item.rate)
        sle.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle.insert(ignore_permissions=True)

    def _reverse_consume(self, item):
        warehouse = getattr(item, 's_warehouse', None) or getattr(item, 'source_warehouse', None) or getattr(self, 'from_warehouse', None) or getattr(self, 'source_warehouse', None)
        current_qty, current_value = self._get_current_state(item.item, warehouse)
        consume_rate = current_value / current_qty if current_qty else item.rate
        new_qty = current_qty + item.qty
        new_value = current_value + (item.qty * consume_rate)
        new_rate = new_value / new_qty if new_qty else consume_rate

        sle = frappe.new_doc("Stock Ledger Entry")
        sle.item = item.item
        sle.warehouse = warehouse
        sle.posting_date = self.posting_date
        sle.posting_time = self.posting_time
        sle.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle.voucher_type = "Stock Entry"
        sle.voucher_no = self.name
        sle.voucher_detail_no = item.name
        sle.actual_qty = item.qty
        sle.rate = consume_rate
        sle.incoming_rate = consume_rate
        sle.valuation_rate = new_rate
        sle.stock_value_difference = item.qty * consume_rate
        sle.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle.insert(ignore_permissions=True)

    def _reverse_transfer(self, item):
        source = getattr(item, 's_warehouse', None) or getattr(item, 'source_warehouse', None) or getattr(self, 'from_warehouse', None) or getattr(self, 'source_warehouse', None)
        target = getattr(item, 't_warehouse', None) or getattr(item, 'target_warehouse', None) or getattr(self, 'to_warehouse', None) or getattr(self, 'target_warehouse', None)

        # Reverse: add back to source
        current_qty, current_value = self._get_current_state(item.item, source)
        transfer_rate = current_value / current_qty if current_qty else item.rate
        # Use the original transfer rate from the ledger
        sle_list = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": self.name, "warehouse": source, "actual_qty": ["<", 0]}, fields=["rate"], limit=1)
        if sle_list:
            transfer_rate = sle_list[0].rate

        new_source_qty = current_qty + item.qty
        new_source_value = current_value + (item.qty * transfer_rate)
        new_source_rate = new_source_value / new_source_qty if new_source_qty else transfer_rate

        sle_in = frappe.new_doc("Stock Ledger Entry")
        sle_in.item = item.item
        sle_in.warehouse = source
        sle_in.posting_date = self.posting_date
        sle_in.posting_time = self.posting_time
        sle_in.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle_in.voucher_type = "Stock Entry"
        sle_in.voucher_no = self.name
        sle_in.voucher_detail_no = item.name
        sle_in.actual_qty = item.qty
        sle_in.rate = transfer_rate
        sle_in.incoming_rate = transfer_rate
        sle_in.valuation_rate = new_source_rate
        sle_in.stock_value_difference = item.qty * transfer_rate
        sle_in.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle_in.insert(ignore_permissions=True)

        # Remove from target
        target_qty, target_value = self._get_current_state(item.item, target)
        new_target_qty = target_qty - item.qty
        new_target_value = target_value - (item.qty * transfer_rate)
        new_target_rate = new_target_value / new_target_qty if new_target_qty else transfer_rate

        sle_out = frappe.new_doc("Stock Ledger Entry")
        sle_out.item = item.item
        sle_out.warehouse = target
        sle_out.posting_date = self.posting_date
        sle_out.posting_time = self.posting_time
        sle_out.posting_datetime = f"{self.posting_date} {self.posting_time}"
        sle_out.voucher_type = "Stock Entry"
        sle_out.voucher_no = self.name
        sle_out.voucher_detail_no = item.name
        sle_out.actual_qty = -item.qty
        sle_out.rate = transfer_rate
        sle_out.incoming_rate = 0
        sle_out.valuation_rate = new_target_rate
        sle_out.stock_value_difference = -(item.qty * transfer_rate)
        sle_out.stock_uom = getattr(item, 'stock_uom', None) or "Nos"
        sle_out.insert(ignore_permissions=True)
