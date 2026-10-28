import frappe
import unittest


class TestWMSStockEntry(unittest.TestCase):
    def setUp(self):
        # Clean up
        frappe.db.delete("WMS Stock Ledger Entry", {})
        frappe.db.delete("WMS Stock Entry", {})
        frappe.db.commit()

    def test_receipt_creates_ledger_entry(self):
        se = frappe.new_doc("WMS Stock Entry")
        se.stock_entry_type = "Receipt"
        se.posting_date = "2026-10-28"
        se.posting_time = "10:00:00"
        se.append("items", {
            "item": "ITEM-001",
            "qty": 10,
            "rate": 100,
            "target_warehouse": "Main Store - SL",
        })
        se.insert(ignore_permissions=True)
        se.submit()
        frappe.db.commit()

        sle = frappe.get_all("WMS Stock Ledger Entry", filters={"voucher_no": se.name})
        self.assertEqual(len(sle), 1)
        sle_doc = frappe.get_doc("WMS Stock Ledger Entry", sle[0].name)
        self.assertEqual(sle_doc.qty_change, 10)
        self.assertEqual(sle_doc.balance_qty, 10)
        self.assertEqual(sle_doc.valuation_rate, 100)

    def test_consume_reduces_stock(self):
        # First receipt
        se1 = frappe.new_doc("WMS Stock Entry")
        se1.stock_entry_type = "Receipt"
        se1.posting_date = "2026-10-28"
        se1.posting_time = "10:00:00"
        se1.append("items", {"item": "ITEM-001", "qty": 10, "rate": 100, "target_warehouse": "Main Store - SL"})
        se1.insert(ignore_permissions=True)
        se1.submit()
        frappe.db.commit()

        # Then consume
        se2 = frappe.new_doc("WMS Stock Entry")
        se2.stock_entry_type = "Consume"
        se2.posting_date = "2026-10-28"
        se2.posting_time = "11:00:00"
        se2.append("items", {"item": "ITEM-001", "qty": 3, "rate": 100, "source_warehouse": "Main Store - SL"})
        se2.insert(ignore_permissions=True)
        se2.submit()
        frappe.db.commit()

        sle = frappe.get_all("WMS Stock Ledger Entry", filters={"voucher_no": se2.name})
        sle_doc = frappe.get_doc("WMS Stock Ledger Entry", sle[0].name)
        self.assertEqual(sle_doc.qty_change, -3)
        self.assertEqual(sle_doc.balance_qty, 7)

    def test_transfer_moves_stock(self):
        # First receipt
        se1 = frappe.new_doc("WMS Stock Entry")
        se1.stock_entry_type = "Receipt"
        se1.posting_date = "2026-10-28"
        se1.posting_time = "10:00:00"
        se1.append("items", {"item": "ITEM-001", "qty": 10, "rate": 100, "target_warehouse": "Main Store - SL"})
        se1.insert(ignore_permissions=True)
        se1.submit()
        frappe.db.commit()

        # Transfer
        se2 = frappe.new_doc("WMS Stock Entry")
        se2.stock_entry_type = "Transfer"
        se2.posting_date = "2026-10-28"
        se2.posting_time = "12:00:00"
        se2.append("items", {"item": "ITEM-001", "qty": 2, "rate": 100, "source_warehouse": "Main Store - SL", "target_warehouse": "Transit Warehouse - SL"})
        se2.insert(ignore_permissions=True)
        se2.submit()
        frappe.db.commit()

        # Check source
        source_sle = frappe.get_all("WMS Stock Ledger Entry", filters={"voucher_no": se2.name, "warehouse": "Main Store - SL"})
        self.assertEqual(len(source_sle), 1)
        # Check target
        target_sle = frappe.get_all("WMS Stock Ledger Entry", filters={"voucher_no": se2.name, "warehouse": "Transit Warehouse - SL"})
        self.assertEqual(len(target_sle), 1)

    def test_moving_average_valuation(self):
        # First receipt at 100
        se1 = frappe.new_doc("WMS Stock Entry")
        se1.stock_entry_type = "Receipt"
        se1.posting_date = "2026-10-28"
        se1.posting_time = "10:00:00"
        se1.append("items", {"item": "ITEM-001", "qty": 10, "rate": 100, "target_warehouse": "Main Store - SL"})
        se1.insert(ignore_permissions=True)
        se1.submit()
        frappe.db.commit()

        # Second receipt at 200
        se2 = frappe.new_doc("WMS Stock Entry")
        se2.stock_entry_type = "Receipt"
        se2.posting_date = "2026-10-28"
        se2.posting_time = "11:00:00"
        se2.append("items", {"item": "ITEM-001", "qty": 5, "rate": 200, "target_warehouse": "Main Store - SL"})
        se2.insert(ignore_permissions=True)
        se2.submit()
        frappe.db.commit()

        sle = frappe.get_all("WMS Stock Ledger Entry", filters={"voucher_no": se2.name})
        sle_doc = frappe.get_doc("WMS Stock Ledger Entry", sle[0].name)
        # Moving average: (10*100 + 5*200) / (10+5) = 2000/15 = 133.33
        self.assertAlmostEqual(sle_doc.valuation_rate, 133.33, places=2)

    def test_insufficient_stock_consume(self):
        se = frappe.new_doc("WMS Stock Entry")
        se.stock_entry_type = "Consume"
        se.posting_date = "2026-10-28"
        se.posting_time = "10:00:00"
        se.append("items", {"item": "ITEM-001", "qty": 100, "rate": 100, "source_warehouse": "Main Store - SL"})
        with self.assertRaises(Exception):
            se.insert(ignore_permissions=True)
            se.submit()
            frappe.db.commit()
