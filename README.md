# Warehouse Management System

A warehouse management system built with Frappe Framework for X Electronics.

## Architecture Overview

```
warehouse_management/
├── warehouse_management/
│   ├── doctype/
│   │   ├── item/                    # Product master
│   │   │   ├── item.py              # (no custom logic)
│   │   │   ├── item.json            # DocType definition
│   │   │   └── item.js
│   │   ├── warehouse/               # Tree-structured warehouse
│   │   │   ├── warehouse.json
│   │   │   └── warehouse_tree.js
│   │   ├── stock_entry/             # Stock movements (submittable)
│   │   │   ├── stock_entry.py       # Controller: moving average + SLE creation
│   │   │   ├── stock_entry.json
│   │   │   ├── stock_entry.js
│   │   │   └── test_stock_entry.py  # 5 unit tests
│   │   ├── stock_entry_detail/      # Child table (line items)
│   │   │   ├── stock_entry_detail.json
│   │   │   └── stock_entry_detail.py
│   │   └── stock_ledger_entry/      # Stateless ledger
│   │       ├── stock_ledger_entry.json
│   │       └── stock_ledger_entry.py
│   ├── report/
│   │   ├── stock_ledger/            # Stock Ledger Report (Query Report)
│   │   │   └── stock_ledger.json
│   │   └── stock_balance/           # Stock Balance Report (Query Report)
│   │       └── stock_balance.json
│   └── __init__.py
├── hooks.py
├── modules.txt
└── README.md
```

## DocTypes

### 1. Item (Product)
- **Naming:** Set by user (item_code used as name)
- **Fields:** Item Name, Item Code (unique), Stock UOM, Disabled, Item Group, Description, Image, Barcode, Reorder Level, Allow Negative Stock, Valuation Method (read-only, "Moving Average"), Standard Rate

### 2. Warehouse (Tree DocType)
- **is_tree = 1** (Frappe adds tree view + nested set behavior)
- **Fields:** Warehouse Name, Is Group, Parent Warehouse, Warehouse Type, Disabled, lft, rgt, old_parent
- Group warehouses cannot hold stock. Leaf warehouses only.

### 3. Stock Entry (Submittable)
- **Naming:** SE-.YYYY.-.#####
- **Types:** Receipt, Consume, Transfer
- **Fields:** Stock Entry Type, Posting Date, Posting Time, From/To Warehouse, Items (child table), Total Amount (read-only), Remarks, Amended From
- **Controller:** `before_save` calculates line amounts and total. `on_submit` creates Stock Ledger Entries. `on_cancel` creates reversal entries.

### 4. Stock Entry Detail (Child Table)
- **Fields:** Item, Item Name (fetch), Stock UOM (fetch), Qty, Basic Rate, Rate, Amount (read-only), Valuation Rate (read-only), Source Warehouse, Target Warehouse
- `basic_rate` is auto-filled from moving average for Consume/Transfer

### 5. Stock Ledger Entry (Stateless)
- **No stored running balance** — balances computed via SQL window functions
- **Fields:** Item, Warehouse, Posting Date, Posting Time, Posting Datetime, Voucher Type, Voucher No, Voucher Detail No, Actual Qty (signed), Incoming Rate, Rate, Valuation Rate, Stock Value Difference, Stock UOM
- `actual_qty` > 0 means stock in, < 0 means stock out

## Moving Average Valuation

```
Receipt:  new_rate = (current_value + new_qty × new_rate) / (current_qty + new_qty)
Consume:  consume_rate = current_value / current_qty
          new_rate = (current_value - consumed_qty × consume_rate) / (current_qty - consumed_qty)
Transfer: source rate used for both sides
```

Implementation: `_get_current_state()` queries SUM(qty) and SUM(value) from ledger. Rate is frozen into each SLE row.

## Cancellation (Reversal)

Instead of deleting ledger entries, `on_cancel` creates **negated entries** (opposite qty and value). The ledger stays append-only and auditable.

## Reports

### Stock Ledger (Query Report)
- Columns: Item, Warehouse, Posting Datetime, Voucher Type, Voucher No, In Qty, Out Qty, Balance Qty (window function), Incoming Rate, Valuation Rate, Balance Value (window function)
- Balance Qty = `SUM(actual_qty) OVER (PARTITION BY item, warehouse ORDER BY posting_datetime, name)`

### Stock Balance (Query Report)
- Columns: Item, Warehouse, Balance Qty, Valuation Rate, Balance Value
- Consolidated: `GROUP BY item, warehouse HAVING SUM(qty) != 0`
- Valuation Rate = latest SLE's valuation_rate

## Tests (5 unit tests)

| Test | Description |
|------|-------------|
| Receipt creates ledger entry | Verifies SLE created with correct qty, rate, valuation, balance |
| Consume reduces stock | Verifies balance decreases after consume |
| Transfer moves stock | Verifies 2 SLEs created (source -qty, target +qty) |
| Moving average valuation | Receipt 10@100 then 5@200 → avg = 133.33 |
| Insufficient stock consume | Consume blocked when qty > available |

Run: `bench --site nvr.local run-tests --app warehouse_management`

## Key Design Decisions

1. **Stateless Ledger**: No stored running balance. Computed via SQL window functions.
2. **Moving Average**: Single SQL query for current state. Rate frozen into each row.
3. **Cancellation = Reversal**: Append-only ledger.
4. **Shared `_get_current_state()`**: One method reused by all operations.
5. **Validation**: Mandatory fields, warehouse type checks, insufficient stock prevention.

## Setup

```bash
bench new-site mysite.local
bench --site mysite.local install-app warehouse_management
bench --site mysite.local set-config developer_mode 1
```

## License

MIT
