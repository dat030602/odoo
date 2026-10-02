# Credit Control (Delivery)

## Overview
While the Sales Credit Control module stops bad debt at the ordering phase, this module acts as a final safeguard at the warehouse level. It prevents warehouse staff from dispatching goods to customers who currently have severely overdue invoices.

## Key Features
* **Pre-Validation Block:** When a warehouse worker attempts to validate a delivery, the system checks the accounting ledger in real-time. If overdue invoices are found, the delivery is blocked and a red banner is displayed.
* **Management Override:** Authorized personnel (e.g., Chief Accountant or Logistics Manager) can use the "Release Delivery" button to bypass the block for specific shipments.
* **Delivery Logging:** Exception approvals are recorded directly on the picking document.

## Usage
This module operates silently in the background on all Outgoing Transfers (`stock.picking`). Override controls are available to users in the `Credit Approver` security group.
