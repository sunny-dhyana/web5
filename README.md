# Mercury Marketplace

## Branches

- main branch - Clean base code with no vulns

- **only_vulns branch - Intentional vulns present in the code.**
> (use this branch "only_vulns" for testing against agents)

- with_vulns_and_poc branch - Intentional vulns present in the code with POCs and their documentation.

---

A production-quality online marketplace platform built with FastAPI + React.

## Features

- **Marketplace** — Browse, search, and filter products by category
- **Wallet System** — Add funds, track balance, full transaction ledger
- **Escrow Payments** — Funds held securely until order completion
- **Order Lifecycle** — `pending_payment → paid → shipped → delivered → completed`
- **Dispute System** — Messaging thread between buyer & seller, admin resolution
- **Seller Dashboard** — List products, manage orders, request payouts
- **Admin Panel** — Manage users, view orders, resolve disputes
- **JWT Auth** — Access + refresh tokens, email verification, password reset

## Quick Start (Docker)

```bash
docker compose up --build
```

Open **http://localhost:8005**

## Demo Accounts

| Role   | Email                  | Password    |
|--------|------------------------|-------------|
| Admin  | admin@mercury.com      | Admin123!   |
| Seller | alice@mercury.com      | Seller123!  |
| Seller | bob@mercury.com        | Seller123!  |
| Buyer  | charlie@mercury.com    | Buyer123!   |
| Buyer  | diana@mercury.com      | Buyer123!   |

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p data
python seed.py
uvicorn app.main:app --reload --port 8005
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # Proxies /api → http://localhost:8005
```

Open **http://localhost:5173**

## API Documentation

Interactive docs available at **http://localhost:8005/api/docs**

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.11, FastAPI, SQLAlchemy    |
| Database   | SQLite (WAL mode)                   |
| Auth       | JWT (access + refresh), bcrypt      |
| Frontend   | React 18, TypeScript, Vite          |
| Routing    | React Router v6                     |
| Deployment | Docker, uvicorn                     |

## Project Structure

```
mercury/
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── routers/      # FastAPI route handlers
│   │   ├── services/     # Business logic (wallet, orders)
│   │   ├── core/         # Security, deps, email simulation
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── seed.py           # Demo data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        # React page components
│       ├── components/   # Shared UI components
│       ├── contexts/     # Auth & Cart context
│       ├── api/          # API client with token refresh
│       └── types/        # TypeScript types
├── Dockerfile
├── docker-compose.yml
└── entrypoint.sh
```
