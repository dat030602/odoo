# Advanced ATP (Available-To-Promise)

## Overview
By default, Odoo reserves inventory using a strict "First-In, First-Out" (FIFO) principle. This module introduces a smart allocation engine to override this behavior, allowing businesses to automatically reallocate reserved stock based on priority rules (e.g., VIP customers, urgent deadlines, high-value orders).

## Key Features
* **Scoring Rules Engine:** Administrators can configure scoring criteria and assign weights (e.g., VIP Customer = +100 points, Urgent Delivery = +50 points).
* **Simulation Mode:** Before applying changes, warehouse managers can simulate an allocation run to preview how stock will be unreserved and reallocated.
* **Automated Reallocation:** The system can automatically strip reservations from low-priority orders and reassign them to high-priority ones, complete with chatter tracking for full auditability.
* **Protection Mechanism:** Outgoing shipments that have already started physical processing are protected from reallocation.

## Usage
Navigate to **Inventory > Operations > Allocation Runs** to configure rules, simulate stock distribution, and apply reallocations.
