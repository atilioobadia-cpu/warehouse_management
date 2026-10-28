# Warehouse Management System

A warehouse management system built with Frappe Framework for X Electronics.

## Features

- **Item Management** — Products with valuation method and standard rate
- **Warehouse** — Tree-structured warehouses (Store, Transit, Scrap)
- **Stock Entry** — Receipt, Consume, Transfer with moving average valuation
- **Stock Ledger Entry** — Stateless ledger (balances computed on the fly)
- **Reports** — Stock Ledger (movement per line), Stock Balance (consolidated balance)
- **Tests** — 5 unit tests covering all stock operations

## Tech Stack

- Frappe Framework v16
- MariaDB, Redis

## Setup

```bash
bench new-site mysite.local
bench --site mysite.local install-app warehouse_management
bench --site mysite.local set-config developer_mode 1
```

## License

MIT
