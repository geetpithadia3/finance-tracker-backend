# V2 Execution Roadmap: The "Fast MVP" Path

This roadmap is designed for **incremental delivery**. We will build the robust "Double-Entry" engine first, but expose it slowly to keep the app usable at every step.

## Phase 1: The Iron Core (Foundation)
**Goal**: Get the database schema live and prove the concept with scripts. No UI changes yet.

- [x] **Step 1.1: Schema Migration**
    - Create new tables (`parties`, `accounts`, `transactions`, `entries`, `budget_rules`).
    - *Constraint*: Keep existing `users` table for Auth, but link it to `parties`.
- [x] **Step 1.2: Auth Integration**
    - Update `User` model to have `party_id`.
    - Signal: On User Creation -> Create Party -> Create Default Accounts.
- [x] **Step 1.3: The "Ledger" Service**
    - Implement internal Python service `LedgerService.record_transaction()`.
    - Verification: Write a unit test that records a $50 expense and asserts that `Sum(Entries) == 0`.

## Phase 2: MVP Input (API & CSV)
**Goal**: Connect the Frontend and enable Bulk Data Entry immediately.

- [x] **Step 2.1: GET /categories**
    - Wire this endpoint to query the `accounts` table (Type=EXPENSE).
- [x] **Step 2.2: POST /transactions (Simple)**
    - Implement the "Simple" payload (Date, Description, Amount, CategoryID).
    - Backend converts this to the 2-leg entry.
- [x] **Step 2.3: CSV Import Service**
    - Build parser for simple bank CSVs.
    - Loop over rows -> Call `record_transaction`.
    - *Hack*: Auto-assign "Uncategorized" if no match found.
- [x] **Step 2.4: Basic Reporting**
    - Implement `GET /reports` to sum up the `entries` table.

## Phase 3: Power Features (Incremental Upgrades)
**Goal**: Unlock the features that required the rewrite.

- [x] **Step 3.1: Explicit Sources**
    - Update UI (and API) to allow selecting "Paid via Credit Card" vs "Paid via Cash".
    - Keep "Payment Method" dropdown in Transaction Form.
- [x] **Step 3.2: Transfers & Splits**
    - Add "Transfer" and "Split" UI buttons.
    - Wire to `POST /transactions` with `type=TRANSFER` or `splits=[]`.
- [ ] **Step 3.3: Recurring Engine** (Skipped for now)
    - `POST /recurring` endpoint.
    - Background Worker (Cron) to wake up daily and process `recurring_templates`.
- [x] **Step 3.4: Auto-Rules**
    - "If description contains 'Uber' -> Assign to 'Transport'".

## Summary of Phases

| Phase | Duration (Est) | User Value | Technical State |
| :--- | :--- | :--- | :--- |
| **1. Foundation** | 3 Days | None (Backend only) | DB Schema & Core Service ready |
| **2. MVP Input** | 5 Days | **Working App + Import** | Manual + Bulk CSV entry working. |
| **3. Power Features** | 1 Week | Transfers, Splits, Rules | Fully utilizing Double-Entry power. |


## Phase 4: Optimization & Deployment Preparation
**Goal**: Make the application robust, performant, and ready for production.

- [x] **Step 4.1: Database Optimization**
    - Add Indexes to `entries` (account_id, transaction_id) and `ledger_transactions` (date, owner_id).
    - Introduce Alembic for proper migration management.
- [x] **Step 4.2: Application Hardening**
    - Audit strict Pydantic validation.
    - Review Error Handling and Status Codes.
- [x] **Step 4.3: Deployment Config**
    - Create `Dockerfile`.
    - Create `docker-compose.yml` for local prod-like testing.
    - Script for entrypoint (migrations + app start).
