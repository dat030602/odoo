# Credit Control (Sales)

## Overview
This module prevents sales representatives from confirming orders for customers who have exceeded their allowable credit limits, thereby reducing financial risk.

## Key Features
* **Real-time Exposure Calculation:** Automatically computes the customer's total risk (unpaid invoices + un-invoiced orders + the current order).
* **Credit Block at Order Confirmation:** If the limit is exceeded, the Sales Order is placed on "Credit Hold" and cannot be processed further.
* **Approval Workflow:** Authorized Credit Approvers can review blocked orders and explicitly grant exceptions via the "Approve Credit" or "Reject Credit" buttons.
* **Audit Trail:** All credit release actions are logged with timestamps and approver details.

## Usage
Configure credit limits on the Partner form. When confirming a Sales Order, the system will automatically validate the customer's financial standing.
