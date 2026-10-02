# Period Closing Control

## Overview
Extends Odoo's default Accounting lock dates by introducing strict operational lock dates for Inventory, Sales, and Purchasing departments. This prevents staff from backdating operational documents (like stock moves or sales orders) into closed financial periods.

## Key Features
* **Multi-Department Locks:** The Chief Accountant can set independent lock dates for `Inventory`, `Sales`, and `Purchases`.
* **Strict Enforcement:** Any attempt to create, modify, or delete operational records prior to the lock date is blocked with a validation error.
* **Temporary Unlock Workflow:** Employees can submit an "Unlock Request" with a reason. Upon approval, the system grants a temporary 2-hour bypass window for that specific user.
* **Automated Expiry:** A cron job automatically revokes the temporary bypass access after the 2-hour window expires, ensuring strict compliance.

## Usage
Navigate to **Settings > Period Locks** (accessible to Period Lock Managers) to define operational boundaries and manage Unlock Requests.
