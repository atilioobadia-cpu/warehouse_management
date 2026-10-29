# Warehouse Management System

A clean, minimal warehouse management module built on **Frappe Framework (v16)**. Designed for learning and practical stock tracking with accurate valuation using the **Moving Average** method.

## Overview

The Warehouse Management System handles basic stock transactions (Receipt, Consume, Transfer), maintains a stateless Stock Ledger, and provides real-time reports with running balances. All stock movements are tracked through an append-only ledger for full auditability.

## Features

- **Item Management** – Products with Item Code, Item Name, Item Group, Stock UOM, and Standard Rate
- **Warehouse Management** – Hierarchical (Tree) Warehouses with support for parent-child structure
- **Stock Entry** – Submittable document to record Receipts, Consumption, and Transfers
- **Stock Ledger Entry (SLE)** – Immutable, system-generated ledger of all stock movements
- **Moving Average Valuation** – Automatic recalculation of valuation rate on each transaction
- **Reversal on Cancellation** – Cancelled entries create opposite ledger entries (no deletions)
- **Stock Reports** – Stock Ledger and Stock Balance with running balances
- **Clean UI** – Organized forms with sections, column breaks, and smart field defaults

## DocTypes

| DocType | Type | Description |
| --- | --- | --- |
| **Item** | Master | Product master with auto-generated Item Code (`ITEM-#####`). UOM options: `Pcs` (default), `Nos`, `Kg`, `Litre`, `Meter`. Item Group: `Raw Material`, `Finished Goods`, `Consumable`, `Sub Assemblies`, `Services`. |
| **Warehouse** | Master (Tree) | Supports nested warehouses using parent-child hierarchy. |
| **Stock Entry** | Transaction (Submittable) | Main stock transaction document with types `Receipt`, `Consume`, and `Transfer`. Auto-calculates totals. |
| **Stock Entry Detail** | Child Table | Line items with Item, Qty (defaults to 1), Rate (auto-filled from Item Standard Rate), Amount, and Source/Target Warehouses. |
| **Stock Ledger Entry** | Ledger (System Generated) | Append-only record of every stock movement. Never edited or deleted directly. |

## How It Works

### Stock Entry Types

| Type | Behavior | Warehouses |
| --- | --- | --- |
| **Receipt** | Increases stock | Target Warehouse (`To Warehouse`) |
| **Consume** | Decreases stock (blocked if insufficient) | Source Warehouse (`From Warehouse`) |
| **Transfer** | Moves stock between warehouses | Source & Target Warehouses (both required) |

### Moving Average Valuation

Valuation is calculated dynamically from the ledger using the Moving Average method:

- **Receipt:** `New Valuation Rate = (Current Value + (Qty × Rate)) / (Current Qty + Qty)`
- **Consume:** `Consumption Rate = Current Value / Current Qty`. New rate recalculated after reduction.
- **Transfer:** Stock moves at the source warehouse's current moving average rate. The target warehouse updates its own moving average with the transferred quantity at that rate.

### Cancellation

When a submitted Stock Entry is cancelled, the system creates **reversal entries** with opposite quantities and values. This keeps the Stock Ledger fully traceable and audit-safe.

## Reports

### Stock Ledger
Displays all stock movements with full transaction history. Includes Item, Item Name, Warehouse, Posting Date, Posting Time, Voucher Type/No, In Qty, Out Qty, Running Balance Qty, Incoming Rate, Valuation Rate, and Running Balance Value. Balances are computed using SQL window functions.

### Stock Balance
Shows current stock position by Item and Warehouse. Displays Balance Qty, Valuation Rate (latest), and Balance Value. Only shows warehouses with non-zero balances.

## Validation Rules

- **Insufficient Stock** – Prevents Consume or Transfer if available quantity is lower than requested
- **Warehouse Validation** – Enforces correct warehouse fields based on transaction type
- **Mandatory Fields** – Validates required fields before submission
- **System-Generated Ledger** – Stock Ledger Entries are created only on submission and cannot be manually created

## Installation

```bash
bench get-app https://github.com/atilioobadia-cpu/warehouse_management.git
bench --site <your-site> install-app warehouse_management
bench --site <your-site> migrate
```

## GitHub Repository

[https://github.com/atilioobadia-cpu/warehouse_management](https://github.com/atilioobadia-cpu/warehouse_management)

## License

MIT
