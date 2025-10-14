# UI Best Practices — Vue 3 + TypeScript + Element Plus

> Defaults: **Vite**, **strict TypeScript**, **Pinia**, **Element Plus**, **OpenAPI-typed client**, **Vitest + Vue Testing Library**, **ESLint+Prettier**, **S3+CloudFront** deploy, **Axe/Lighthouse** checks, **RUM/Synthetics** optional.

---

## 0. Golden Rules

- ✅ Strict TypeScript (`"strict": true`); `vue-tsc --noEmit` in CI.
- ✅ Generate a **typed API client from OpenAPI**; no ad-hoc DTOs.
- ✅ Centralize API access with Axios interceptors (auth, tracing, retries).
- ✅ Element Plus with auto-imported components; theme via SCSS tokens.
- ✅ Accessibility and performance budgets enforced in CI.

---

## 1. Project Structure

```
ui/
├─ src/
│  ├─ api/            # OpenAPI generated client
│  ├─ components/
│  ├─ composables/    # useFoo() hooks
│  ├─ stores/         # Pinia
│  ├─ pages/
│  ├─ styles/         # variables, global
│  └─ main.ts
├─ vite.config.ts
└─ tsconfig.json
```

---

## 2. Tooling

- **ESLint + Prettier**; fail on warnings.
- **Vitest + @testing-library/vue**; coverage gate (target 80 %+).
- **Storybook** for component docs; **Loki/Chromatic** for visual regression (critical flows).
- **unplugin-auto-import** + Element Plus resolver for tree-shaking.
- **@vueuse/core** for utilities.

---

## 3. API Layer

- Generate via `openapi-typescript` (or NSwag/NJPX) → strong typing end-to-end.
- Axios client with:
  - `Authorization` header injection (from BFF/Cognito/IAM)
  - request id/trace id headers
  - global error mapping → `ElNotification` / `ElMessageBox`

---

## 4. UX & Components

- Element Plus:
  - ElForm with typed models + validation.
  - ElTable with server-side paging/sorting; prefer **virtual scroll** for large lists.
  - ElLoading for async states; skeleton loaders for perceived performance.
- Keep components focused; business logic in composables/stores.

---

## 5. Accessibility & i18n

- Run **Axe** (Playwright or CI plugin) on key routes.
- Keyboard navigation; focus management after modals/toasts.
- `vue-i18n` (even EN-only) to enforce patterns and future-proof.

---

## 6. Security

- Strict **CSP**; no inline scripts; Subresource Integrity on 3rd party.
- HSTS via CloudFront; sanitize any dynamic HTML.
- Never embed secrets; obtain tokens from BFF or Cognito.

---

## 7. Performance

- Route-level code splitting; prefetch next routes.
- Analyze bundle (rollup-plugin-visualizer); watch Element Plus import weight.
- Cache immutable assets (hash filenames); short TTL for HTML shell.
- Image optimization; avoid blocking fonts.

---

## 8. Deploy & Monitor

- Build once, deploy to **S3 + CloudFront (OAC)**; WAF on distribution.
- Invalidate changed paths only.
- Optional: **CloudWatch RUM** and **Synthetics canaries** for key flows.

---

## 9. Checklist

- [ ] OpenAPI-typed client + Axios interceptors
- [ ] ESLint+Prettier passing; vue-tsc passes
- [ ] Vitest coverage ≥ 80%
- [ ] Element Plus auto-import + theme tokens
- [ ] Axe/Lighthouse thresholds enforced
- [ ] S3+CloudFront deploy (OAC), WAF enabled
- [ ] No secrets in code; CSP strict
