# ArthMitra – AI Financial Planning Assistant (Frontend)

ArthMitra is a personal finance platform designed specifically for Indian users, supporting Rupee (₹) formatting, Indian numbering (Lakhs & Crores), and key domestic investment and debt instruments (FD, Mutual Funds / SIP, PPF, NPS, Sovereign Gold Bonds, EMIs).

---

## 1. Architecture Overview (10-Line Summary)
- **Zero Build Tooling**: Pure ES2022 JavaScript modules, semantic HTML5, and CSS3 custom properties with no npm or bundler needed.
- **Client Hash Router**: Single Page App (SPA) driven by hash routes (`#dashboard`, `#profile`, `#goals`, `#debts`, `#investments`, `#chat`, `#reports`, `#settings`, `#login`) with route-level auth guards and automatic chart teardown to prevent memory leaks.
- **Unified API Layer**: `js/api.js` centralizes fetch requests with 15s `AbortController` timeouts, 401 token expiry redirection, and an offline-ready Indian mock database (`USE_MOCK = true`).
- **Four-State Views**: Every data page implements Loading (skeletons), Success, Empty (SVG illustration + CTA), and Error (retry button) states.
- **Accessibility & Contrast**: Built with WCAG AA compliance, semantic markup, focus traps on modals, skip-link, and `:focus-visible` styling.

---

## 2. How to Run Locally

Because the project uses ES2022 native JavaScript modules (`import`/`export`), it must be served over an HTTP server (not directly double-clicked via `file://`).

### Option A: Using Python (Recommended)
```bash
# Navigate to the arthmitra directory
cd arthmitra

# Start Python's built-in static server
python -m http.server 3000
```
Then open your browser at **`http://localhost:3000`**.

### Option B: Using Node.js `npx serve`
```bash
cd arthmitra
npx serve -l 3000
```

---

## 3. Switching Between Mock Mode and Real FastAPI Backend

Open `arthmitra/js/api.js`:

```javascript
// Configuration
export const BASE_URL = 'http://localhost:8000/api/v1';
export const USE_MOCK = true; // Toggle to false to connect to FastAPI backend
```

- When **`USE_MOCK = true`** (default): The frontend runs autonomously with an in-memory/localStorage mock database simulating a ₹85,000 monthly earner with real-time calculations.
- When **`USE_MOCK = false`**: The frontend sends real requests to `BASE_URL` with JWT bearer tokens.

---

## 4. Required FastAPI CORS Configuration

In your FastAPI backend (`main.py`), ensure the CORSMiddleware is enabled to accept requests from your frontend origin:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ArthMitra Backend API", version="1.0.0")

# Allow frontend static server origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 5. Acceptance Checklist

- [x] All 9 pages are reachable via sidebar and hash routes (`#login`, `#dashboard`, `#profile`, `#goals`, `#debts`, `#investments`, `#chat`, `#reports`, `#settings`)
- [x] Dark/light toggle works and persists in `localStorage`, and Chart.js instances re-theme dynamically
- [x] Every page implements skeleton, success, empty, and error states
- [x] All 4 required charts render with ₹ formatting and responsive canvases
- [x] Forms validate inline with `aria-invalid` and `aria-describedby`
- [x] Fully responsive across mobile (360px), tablet (768px), and desktop (1280px+)
- [x] Complete autonomous operation in Mock Mode with zero backend dependency
