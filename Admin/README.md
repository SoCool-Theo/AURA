# Aura Admin Panel

Independent React + TypeScript administration frontend for Aura. Keep this folder beside the investor web and mobile apps:

```text
AURA/
├── Admin/                  # this project — administrators only
├── backend/                # shared FastAPI backend
├── web-prototype-react/    # investor/customer web
├── mobile/                 # investor/customer mobile
├── data/
└── docs/
```

## Admin source structure

```text
Admin/
├── app/
│   ├── globals.css         # Aura theme and responsive styles
│   ├── layout.tsx          # metadata and root layout
│   └── page.tsx            # admin application entry
├── components/
│   ├── admin/
│   │   ├── AdminApp.tsx
│   │   ├── AdminSidebar.tsx
│   │   ├── AdminTopbar.tsx
│   │   ├── SectionCard.tsx
│   │   ├── mockData.ts
│   │   ├── types.ts
│   │   └── pages/
│   │       ├── DashboardPage.tsx
│   │       ├── UsersPage.tsx
│   │       ├── OtherPages.tsx
│   │       └── SettingsPage.tsx
│   └── ui/                 # reusable accessible UI controls
├── public/
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

## Included pages

- Dashboard
- Users
- Portfolios
- Market Data
- Reports
- System Health
- AI Oversight (planned-provider status)
- Activity Logs
- Settings

Settings includes admin profile, dark/light/system appearance, compact sidebar, notifications, security, MFA preference, session timeout, active-session controls, market-data schedule, timezone, registration control, and maintenance mode. Saved settings use browser storage until Aura admin APIs are implemented.

## Run locally

Requirements: Node.js 22.13 or later.

```bash
cd Admin
npm install
npm run dev
```

The dashboard and controls use frontend prototype state. Financial calculations and permanent data changes must remain in the FastAPI backend; do not duplicate analytics formulas in this frontend.
