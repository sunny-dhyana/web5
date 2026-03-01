# Mercury Lab — Vulnerability Tracker

```
+----------+--------------------------------------------------+---------------------------------------+----------+-------------------------------+
| ID       | Name                                             | Category                              | Severity | Auth                          |
+----------+--------------------------------------------------+---------------------------------------+----------+-------------------------------+
| VULN-001 | OS Command Injection                             | OS Command Injection (CWE-78)         | Critical | Seller / Admin                |
| VULN-002 | File Upload Bypass                               | Unrestricted File Upload (CWE-434)    | High     | Seller / Admin                |
| VULN-003 | SSRF via Profile Picture URL                     | SSRF (CWE-918)                        | High     | Any auth user                 |
| VULN-004 | Partial Refund Accumulation                      | Business Logic (CWE-840)              | Critical | Buyer + Admin                 |
| BAC-1    | Mass Assignment -> Role Escalation               | Mass Assignment (CWE-915)             | Critical | Any auth user                 |
| BAC-2    | IDOR on Wallet Transaction History               | IDOR (CWE-639)                        | High     | Any auth user                 |
| BAC-3    | BOLA: Any Seller Ships Any Order                 | BOLA (CWE-285)                        | High     | Any seller                    |
| BAC-4    | Horizontal BAC: Any User Reads Any Order         | BOLA (CWE-639)                        | High     | Any auth user                 |
| BAC-5    | Function-Level AuthZ: Admin Stats Exposed        | Broken Function Level AuthZ (CWE-285) | Medium   | Any auth user                 |
| BAC-6    | Wallet Transfer: IDOR + Self-Transfer Inflation  | IDOR + Business Logic (CWE-639/840)   | Critical | Any auth user                 |
| BL-1     | Negative Quantity -> Wallet Inflation            | Business Logic (CWE-840)              | Critical | Any buyer                     |
| BL-2     | Negative Payout -> Pending Balance Inflation     | Business Logic (CWE-840)              | Critical | Seller                        |
| BL-3     | TOCTOU Race Condition on Inventory               | Race Condition (CWE-367)              | High     | Any two buyers                |
| BL-4     | Float Precision: Zero-Total Order                | Numeric Error (CWE-682)               | High     | Seller + Buyer                |
| BL-5     | Frozen Escrow via Seller-Cancelled Shipped Order | Business Logic (CWE-840)              | High     | Seller                        |
| XSS-1    | Stored XSS via Product Description               | Stored XSS (CWE-79)                   | High     | Seller (plant) / Any (trigger)|
| SQLI-1   | UNION-Based SQL Injection via Product Search     | SQL Injection (CWE-89)                | Critical | None                          |
| SQLI-2   | Second-Order SQL Injection via Product Category  | SQL Injection (CWE-89)                | Critical | Seller (plant) / Any (trigger)|
| SSTI-1   | SSTI via Product Thank-You Message (Jinja2 RCE)  | SSTI / RCE (CWE-94)                   | Critical | Seller (plant) / Buyer        |
| AUTHN-1  | JWT kid Path Traversal -> Admin Escalation       | Auth Bypass / Path Traversal (CWE-22) | Critical | None                          |
+----------+--------------------------------------------------+---------------------------------------+----------+-------------------------------+
```

---

## VULN-001 — OS Command Injection
- **Category**: OS Command Injection (CWE-78)
- **Severity**: Critical
- **Auth**: Seller or Admin
- **Endpoint**: `GET /api/drive/{file_id}/info`

**What**: `subprocess.run(..., shell=True)` interpolates `drive_file.file_name` directly into the shell command. `file_name` is stored from the multipart upload filename, which is fully client-controlled.

**Exploit**:
1. Upload a PDF with filename `report$(id).pdf`
2. `GET /api/drive/{file_id}/info` → command output returned in `metadata` field

**PoC**: `pocs/poc_001_os_command_injection.py`

**Changes**: `backend/app/routers/drive.py`
- Added `import subprocess`
- Added `GET /{file_id}/info` endpoint that runs `stat` with `shell=True` using unsanitized `file_name`

---

## VULN-002 — File Upload Bypass
- **Category**: Unrestricted File Upload (CWE-434)
- **Severity**: High
- **Auth**: Seller or Admin
- **Endpoint**: `POST /api/drive/upload`

**What**: Two bypassable checks — (1) `file.content_type` is client-controlled so spoofing `application/pdf` passes it; (2) magic bytes check only reads the first 4 bytes (`%PDF`), so prepending `%PDF` to any file content bypasses it. The file extension is taken directly from `file.filename`, so any extension is stored on disk.

**Exploit**:
1. Create a file whose content starts with `%PDF` followed by any payload (e.g. HTML/script/shell)
2. Upload with filename `evil.html` and `Content-Type: application/pdf`
3. Both checks pass — file stored on disk with attacker-chosen extension
4. Download via `GET /api/drive/{file_id}/download` returns the malicious file as-is

**PoC**: `pocs/poc_002_file_upload_bypass.py`

**Changes**: `backend/app/routers/drive.py`
- Added magic bytes check (reads first 4 bytes, checks for `%PDF`) — looks secure but bypassed by prepending `%PDF` to any content

---

## VULN-003 — SSRF via Profile Picture URL
- **Category**: Server-Side Request Forgery (CWE-918)
- **Severity**: High
- **Auth**: Any authenticated user
- **Endpoint**: `PUT /api/users/me` → field `profile_picture_url`

**What**: Server fetches the supplied URL via `httpx.get()` to verify it's an image. No scheme or host restrictions. When the response isn't `image/*` content-type, the first 300 bytes of the fetched body are reflected in the error response — making it a **reflected SSRF** with full read of internal services.

**Exploit**:
1. `PUT /api/users/me` with `{"profile_picture_url": "http://169.254.169.254/latest/meta-data/"}`
2. Server fetches the URL; response is `text/plain`, not `image/*`
3. First 300 bytes of the internal response returned in the `detail` error field

**PoC**: `pocs/poc_003_ssrf_profile_picture.py`

**Changes**: `backend/app/routers/users.py`
- Added `import httpx`
- Added `httpx.get(url)` call before storing `profile_picture_url`, with response body reflected in error when content-type is not `image/*`

---

## BAC-1 — Mass Assignment → Role Escalation
- **Category**: Mass Assignment / Privilege Escalation (CWE-915)
- **Severity**: Critical
- **Auth**: Any authenticated user
- **Endpoint**: `PUT /api/users/me`

**What**: `UpdateProfileRequest` schema was expanded to include `role` and `is_verified` fields. The endpoint applies them directly to the user model. Any buyer can send `{"role": "admin"}` and become admin.

**Exploit**: `PUT /api/users/me` with `{"role": "admin", "is_verified": true}`

**PoC**: `pocs/poc_005_mass_assignment_role_escalation.py`

**Changes**:
- `backend/app/schemas/user.py` — Added `role: Optional[UserRole] = None` and `is_verified: Optional[bool] = None` to `UpdateProfileRequest`
- `backend/app/routers/users.py` — Added handling to apply `body.role` and `body.is_verified` to the user model

---

## BAC-2 — IDOR on Wallet Transaction History
- **Category**: IDOR / Broken Object Level Authorization (CWE-639)
- **Severity**: High
- **Auth**: Any authenticated user
- **Endpoint**: `GET /api/wallet/transactions?user_id=<target>`

**What**: An optional `user_id` query param was added to the transactions endpoint. When supplied, it overrides the authenticated user's wallet lookup — any user can read any other user's full financial transaction history.

**Exploit**: `GET /api/wallet/transactions?user_id=2` as any authenticated user

**PoC**: `pocs/poc_006_idor_transaction_history.py`

**Changes**: `backend/app/routers/wallet.py`
- Added `user_id: Optional[int] = Query(None)` param; uses `target_user_id = user_id if user_id else current_user.id`

---

## BAC-3 — BOLA: Any Seller Ships Any Order
- **Category**: Broken Object Level Authorization (CWE-285)
- **Severity**: High
- **Auth**: Any seller account
- **Endpoint**: `PUT /api/orders/{order_id}/ship`

**What**: The seller-specific ownership check (`is_seller = any(item.seller_id == current_user.id ...)`) was replaced with a role-only check (`current_user.role in ["seller", "admin"]`). Any seller can ship any order regardless of ownership — injecting fake tracking numbers or sabotaging competitors.

**Exploit**: As Bob (unrelated seller), ship Charlie's order with Alice's products

**PoC**: `pocs/poc_007_bola_ship_any_order.py`

**Changes**: `backend/app/routers/orders.py`
- Removed `is_seller` check in `ship_order`; replaced with role-only check

---

## BAC-4 — Horizontal BAC: Any User Reads Any Order
- **Category**: Broken Object Level Authorization (CWE-639)
- **Severity**: High
- **Auth**: Any authenticated user
- **Endpoint**: `GET /api/orders/{order_id}`

**What**: The buyer/seller/admin ownership check was removed from the order detail endpoint. Any authenticated user can access any order by ID — exposing shipping addresses, item details, and order totals of other users.

**Exploit**: As Diana (buyer), fetch Charlie's order ID → full order details returned

**PoC**: `pocs/poc_008_bola_order_detail.py`

**Changes**: `backend/app/routers/orders.py`
- Removed `is_buyer / is_seller / is_admin` check and `Access denied` guard from `get_order`

---

## BAC-5 — Function-Level AuthZ: Admin Stats Exposed to All Users
- **Category**: Broken Function Level Authorization (CWE-285)
- **Severity**: Medium
- **Auth**: Any authenticated user
- **Endpoint**: `GET /api/admin/stats`

**What**: The `get_platform_stats` endpoint dependency was changed from `get_current_admin` to `get_current_user`. Any authenticated user can now read platform-wide statistics: total users, total products, total orders, open disputes.

**Exploit**: `GET /api/admin/stats` as any buyer or seller

**PoC**: `pocs/poc_009_function_level_authz_stats.py`

**Changes**: `backend/app/routers/admin.py`
- Added `get_current_user` to deps import
- Changed `get_platform_stats` dependency from `get_current_admin` to `get_current_user`

---

## BL-1 — Negative Quantity Order → Wallet Inflation + Inventory Increase
- **Category**: Business Logic Flaw (CWE-840)
- **Severity**: Critical
- **Auth**: Any buyer
- **Endpoint**: `POST /api/orders`

**What**: `gt=0` validator removed from `OrderItemCreate.quantity`. Ordering negative quantity causes: `total = price * (-N)` → negative; balance check always passes; `wallet.balance -= negative_total` → wallet inflates; `product.quantity -= (-N)` → inventory increases.

**Exploit**: `POST /api/orders` with `{"items": [{"product_id": 1, "quantity": -5}]}`

**PoC**: `pocs/poc_010_negative_quantity_wallet_inflation.py`

**Changes**: `backend/app/schemas/order.py`
- Removed `gt=0` from `OrderItemCreate.quantity` field validator

---

## BL-2 — Negative Payout → Pending Balance Inflation
- **Category**: Business Logic Flaw (CWE-840)
- **Severity**: Critical
- **Auth**: Seller account
- **Endpoint**: `POST /api/payouts`

**What**: `gt=0` validator removed from `PayoutRequest.amount`. `process_payout_deduction` checks `pending_balance < amount` — with a negative amount this is always False. Then `pending_balance -= (-X)` adds to the balance. Seller can inflate pending_balance to any value, then withdraw via a normal payout.

**Exploit**: `POST /api/payouts` with `{"amount": -500, "method": "bank_transfer"}`

**PoC**: `pocs/poc_011_negative_payout_balance_inflation.py`

**Changes**: `backend/app/schemas/payout.py`
- Removed `gt=0` from `PayoutRequest.amount` field validator

---

## BL-3 — TOCTOU Race Condition on Inventory Check
- **Category**: Race Condition / TOCTOU (CWE-367)
- **Severity**: High
- **Auth**: Any two buyer accounts
- **Endpoint**: `POST /api/orders`

**What**: A `time.sleep(0.15)` was inserted in `create_order` between the inventory availability check and the inventory deduction. Two concurrent requests both pass the "enough stock?" check during this 150ms window, both proceed, both deduct — resulting in negative inventory with both orders fulfilled.

**Exploit**: Two simultaneous `POST /api/orders` requests for the last unit of a product

**PoC**: `pocs/poc_012_toctou_inventory_race.py`

**Changes**: `backend/app/services/order_service.py`
- Added `import time` and `time.sleep(0.15)` between inventory validation loop and `deduct_for_purchase`

---

## BL-4 — Float Precision: Zero-Total Order → Free Items
- **Category**: Business Logic Flaw / Numeric Error (CWE-682)
- **Severity**: High
- **Auth**: Seller (to create product) + Buyer (to order)
- **Endpoint**: `POST /api/products` + `POST /api/orders`

**What**: Product price validation changed from `gt=0` to `ge=0`, allowing very small prices. When `round(price * quantity, 2) == 0.00`, the order total is $0.00. The wallet balance check always passes and no funds are deducted — item acquired for free. Trigger: price=`0.004`, quantity=`1`.

**Exploit**: Create product at $0.004, order 1 unit → total rounds to $0.00

**PoC**: `pocs/poc_013_float_precision_zero_total.py`

**Changes**: `backend/app/schemas/product.py`
- Changed `gt=0` to `ge=0` on `price` field in both `ProductCreate` and `ProductUpdate`

---

## BL-5 — Frozen Escrow via Seller-Cancelled Shipped Order
- **Category**: Business Logic Flaw (CWE-840)
- **Severity**: High
- **Auth**: Seller account
- **Endpoint**: `PUT /api/orders/{id}/cancel`

**What**: `OrderStatus.cancelled` was added to the valid transitions from `shipped`. The cancel endpoint only issues a refund when `order.status == paid` — not shipped. A malicious seller ships an order (or fakes it), then immediately cancels. No refund fires, escrow remains `held` permanently with no release mechanism. Buyer loses funds with no recourse.

**Exploit**: Seller ships order → immediately cancels → buyer's escrow frozen forever

**PoC**: `pocs/poc_014_frozen_escrow_shipped_cancel.py`

**Changes**: `backend/app/models/order.py`
- Added `OrderStatus.cancelled` to `shipped`'s valid transitions in `VALID_TRANSITIONS`

---

## XSS-1 — Stored XSS via Product Description
- **Category**: Stored Cross-Site Scripting (CWE-79)
- **Severity**: High
- **Auth**: Seller to plant; any user (including unauthenticated) to trigger
- **Triggered at**: `/products/{id}` (frontend product detail page)

**What**: `ProductDetail.tsx` was changed to render `product.description` via `dangerouslySetInnerHTML` instead of safe JSX interpolation, bypassing React's default escaping. The backend stores description verbatim. Any HTML/JS in the description executes in the browser of every user who visits the product page.

**Exploit**:
1. Seller creates product with description: `<img src=x onerror="alert(document.cookie)">`
2. Any user visits `/products/{id}` → payload executes in their browser

**PoC**: `pocs/poc_015_stored_xss_product_description.py`

**Changes**: `frontend/src/pages/ProductDetail.tsx`
- Changed `<p>{product.description}</p>` to `<div dangerouslySetInnerHTML={{ __html: product.description }} />`

---

## SQLI-1 — UNION-Based SQL Injection via Product Search
- **Category**: SQL Injection (CWE-89)
- **Severity**: Critical
- **Auth**: None — fully unauthenticated
- **Endpoint**: `GET /api/products/search?q=<payload>`

**What**: New `advanced_search` endpoint builds a raw SQL query using an f-string, interpolating `q` directly with no parameterization. The 7-column SELECT structure allows UNION injection. Leaked values surface in `title` and `description` fields of the JSON response.

**Exploit**:
```
# Enumerate tables
GET /api/products/search?q=%') UNION SELECT 1,name,sql,4,5,6,7 FROM sqlite_master WHERE type='table'--

# Dump all user credentials
GET /api/products/search?q=%') UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--
```

**PoC**: `pocs/poc_016_sqli_product_search.py`

**Changes**: `backend/app/routers/products.py`
- Added `text` to sqlalchemy imports
- Added `GET /api/products/search` endpoint using `db.execute(text(f"...{q}..."))` — `q` interpolated directly into the SQL string with no parameterization

---

## SQLI-2 — Second-Order SQL Injection via Product Category
- **Category**: Second-Order SQL Injection (CWE-89)
- **Severity**: Critical
- **Auth**: Seller to store; any user to trigger
- **Endpoints**: `POST /api/products` (store) → `GET /api/products/{id}/similar` (trigger)

**What**: Two-phase attack. Phase 1: seller creates a product with a SQL payload in the `category` field — stored safely via ORM. Phase 2: any user hits `GET /api/products/{id}/similar`; the endpoint retrieves `product.category` via ORM (safe), then interpolates it directly into a raw SQL f-string — the dormant payload executes. Classic second-order injection: storage is safe, execution is not.

**Exploit**:
1. Seller: `POST /api/products` with `"category": "' UNION SELECT id,email,hashed_password,0,0,'users',0 FROM users--"`
2. Any user: `GET /api/products/{id}/similar` → injected query returns user credentials

**PoC**: `pocs/poc_017_second_order_sqli.py`

**Changes**: `backend/app/routers/products.py`
- Added `GET /{product_id}/similar` endpoint; retrieves `product.category` via ORM then interpolates it into `text(f"...category = '{product.category}'...")` — second-order injection

---

## BAC-6 — Wallet Transfer: IDOR + Self-Transfer Balance Inflation
- **Category**: Broken Object Level Authorization (CWE-639) + Business Logic (CWE-840)
- **Severity**: Critical
- **Auth**: Any authenticated user
- **Endpoint**: `POST /api/wallet/transfer`

**What**: Two independent bugs in the new transfer endpoint:
1. **IDOR** — `from_wallet_id` is accepted from the request body without verifying it belongs to `current_user`. Any user can drain any wallet.
2. **Self-Transfer Inflation** — Balances are read into local variables before either is modified (`from_balance = from_wallet.balance; to_balance = to_wallet.balance`). When `from_wallet_id == to_wallet_id`, SQLAlchemy's identity map returns the same object for both queries; `to_balance` holds the pre-deduction value. The credit then writes `to_balance + amount` — overtaking the deduction. Self-transfer of $100 on a $100 balance yields $200.

**Exploit**:
- IDOR: `POST /api/wallet/transfer` with `{"from_wallet_id": <victim_wallet_id>, "to_wallet_id": <own_wallet_id>, "amount": 500}`
- Inflation: `POST /api/wallet/transfer` with `{"from_wallet_id": <own_id>, "to_wallet_id": <own_id>, "amount": <full_balance>}` — repeat to double each time

**PoC**: `pocs/poc_018_wallet_transfer_idor_selftransfer.py`

**Changes**:
- `backend/app/models/wallet.py` — Added `transfer` to `TransactionType` enum
- `backend/app/schemas/wallet.py` — Added `TransferRequest`
- `backend/app/routers/wallet.py` — Added `POST /transfer` endpoint; no ownership check on `from_wallet_id`; balances snapshotted before modification enabling self-transfer inflation

---

## SSTI-1 — Server-Side Template Injection via Product Thank-You Message
- **Category**: Server-Side Template Injection / RCE (CWE-94)
- **Severity**: Critical
- **Auth**: Seller to plant; buyer to trigger
- **Endpoints**: `POST /api/products` (store) → `PUT /api/orders/{id}/complete` (trigger)

**What**: Sellers set a `thank_you_message` on products. When a buyer completes an order, the backend renders the message using `jinja2.Template(product.thank_you_message).render(...)`. Jinja2's default environment allows full Python expression evaluation. The rendered result is returned in the `seller_message` field — making output immediately visible to the attacker.

**Exploit**:
1. Seller creates product with `thank_you_message`: `{{ ''.__class__.__mro__[1].__subclasses__()[132].__init__.__globals__['__import__']('os').popen('id').read() }}`
2. Buyer purchases and completes the order
3. `PUT /api/orders/{id}/complete` response → `seller_message` contains shell command output

**PoC**: `pocs/poc_019_ssti_order_confirmation.py`

**Changes**:
- `backend/app/models/product.py` — Added `thank_you_message` column
- `backend/app/schemas/product.py` — Added `thank_you_message` to `ProductCreate`, `ProductUpdate`, `ProductResponse`
- `backend/app/schemas/order.py` — Added `seller_message: Optional[str]` to `OrderResponse`
- `backend/app/routers/orders.py` — Added `import jinja2`; renders `thank_you_message` unsafely in `complete_order`; output reflected in response

---

## AUTHN-1 — JWT `kid` Header Path Traversal → Admin Privilege Escalation
- **Category**: Auth Bypass / Path Traversal (CWE-22 / CWE-287)
- **Severity**: Critical
- **Auth**: None — no credentials required
- **Endpoint**: Any authenticated endpoint

**What**: JWT signing was refactored to support a `kid` (key ID) header so multiple signing keys can be used. On decode, the backend extracts `kid` from the unverified token header and reads the signing key from disk: `open(os.path.join(KEYS_DIR, kid)).read()`. No path sanitization (`os.path.realpath`, `startswith` check) is applied. An attacker sets `kid = "../../../../dev/null"`, causing the server to read `/dev/null` (empty). The signing key becomes `""` (empty string). The attacker signs a forged JWT with `""` as the HMAC key, sets `sub = 1` (admin user ID), and the server accepts it as cryptographically valid.

**Exploit**:
1. Craft JWT: `header={"alg":"HS256","kid":"../../../../dev/null"}`, `payload={"sub":"1","type":"access","exp":<far future>}`, signed with key `""`
2. Send as `Authorization: Bearer <forged>` to any endpoint
3. Server resolves `keys/../../../../dev/null` → `/dev/null` → key `""` → HMAC matches → authenticated as admin

**PoC**: `pocs/poc_020_jwt_kid_path_traversal.py`

**Changes**:
- `backend/keys/default.key` — Created; holds the real signing key for `kid=default`
- `backend/app/core/security.py` — Added `_KEYS_DIR`, `_load_signing_key(kid)`; `decode_token` extracts `kid` from unverified header and reads key from disk with no path sanitization; `create_access_token` / `create_refresh_token` now include `headers={"kid": "default"}`

---

## VULN-004 — Partial Refund Accumulation via Dispute Resolution
- **Category**: Business Logic Flaw
- **Severity**: Critical
- **Auth**: Buyer (to open dispute) + Admin (to resolve)
- **Endpoint**: `PUT /api/admin/disputes/{dispute_id}/resolve`

**What**: Two flaws combine to allow unlimited money extraction from a single escrow:
1. The "already resolved" guard was removed — the same dispute can be resolved unlimited times
2. `resolve` now accepts an optional `refund_amount` field — when set below `order.total_amount`, `process_refund()` marks escrow as `partial_refunded` instead of `refunded`. `partial_refunded` is explicitly re-entrant in `process_refund()`'s guard, so the next call is also allowed. The escrow `amount` field is never decremented — only the status flag changes — so there is no ceiling on cumulative refunds.

**Exploit**:
1. Buyer places $100 order, seller ships, buyer confirms delivery
2. Buyer opens dispute
3. Admin resolves with `refund_amount: 40` → buyer +$40, escrow = `partial_refunded`
4. Admin resolves same dispute again with `refund_amount: 40` → buyer +$40 (no guard)
5. Repeat N times → buyer receives $40×N from a $100 escrow

**PoC**: `pocs/poc_004_partial_refund_accumulation.py`

**Changes**:
- `backend/app/schemas/dispute.py` — Added `refund_amount: Optional[float] = None` to `ResolveDisputeRequest`
- `backend/app/routers/admin.py` — Removed `already resolved` guard; uses `body.refund_amount` when provided instead of always `order.total_amount`

---
