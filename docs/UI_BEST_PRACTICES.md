# UI Best Practices — Vue 3 + TypeScript + Element Plus

> Defaults: **Vite**, **strict TypeScript**, **Pinia**, **Element Plus**, **OpenAPI-typed client**, **Vitest + Vue Testing Library**, **ESLint+Prettier**, **S3+CloudFront** deploy, **Axe/Lighthouse** checks, **RUM/Synthetics** optional.

---

## 0. Golden Rules

### Strict TypeScript ("strict": true); vue-tsc --noEmit in CI
**Why:** Strict TypeScript catches type errors at compile time, preventing runtime bugs and improving code reliability. The strict mode enables all type checking features, providing maximum safety. Running vue-tsc in CI ensures type safety is maintained across the entire codebase, including Vue single-file components. This prevents "works on my machine" issues and catches integration problems early.

### Generate a typed API client from OpenAPI; no ad-hoc DTOs
**Why:** OpenAPI-generated clients ensure your frontend and backend stay in sync automatically. When the API changes, TypeScript compilation will fail if the frontend code is incompatible, catching breaking changes immediately. Ad-hoc DTOs create maintenance overhead and can drift from the actual API, leading to runtime errors and data inconsistencies.

### Centralize API access with Axios interceptors (auth, tracing, retries)
**Why:** Centralized API handling ensures consistent behavior across all HTTP requests. Interceptors provide a single place to handle authentication, add tracing headers, implement retry logic, and manage global error handling. This reduces code duplication and ensures all API calls follow the same patterns for observability and reliability.

### Element Plus with auto-imported components; theme via SCSS tokens
**Why:** Element Plus provides a comprehensive, well-tested component library that accelerates development and ensures consistent UX. Auto-import reduces bundle size through tree-shaking and eliminates manual import statements. SCSS tokens enable consistent theming and make it easy to maintain brand consistency across the application.

### Accessibility and performance budgets enforced in CI
**Why:** Automated accessibility and performance checks prevent regressions and ensure your application remains usable for all users. CI enforcement makes these quality gates non-negotiable, preventing accessibility debt and performance degradation from accumulating over time. This is crucial for compliance and user experience.

---

## 1. Project Structure

### Organized by feature and responsibility
**Why:** A well-organized project structure makes it easier for developers to find and modify code. Separating concerns (API, components, business logic, state management) reduces cognitive load and makes the codebase more maintainable. The composables pattern encourages reusable logic, while keeping pages focused on layout and routing.

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

### ESLint + Prettier; fail on warnings
**Why:** ESLint catches potential bugs, enforces coding standards, and identifies problematic patterns before they reach production. Prettier ensures consistent code formatting across the team, reducing merge conflicts and cognitive load during code reviews. Failing on warnings prevents technical debt accumulation and maintains code quality standards.

### Vitest + @testing-library/vue; coverage gate (target 80%+)
**Why:** Vitest provides fast, modern testing with excellent TypeScript support and Vue integration. Testing Library encourages testing user behavior rather than implementation details, leading to more robust tests. Coverage gates ensure critical code paths are tested, reducing the risk of regressions and improving code reliability.

### Storybook for component docs; Loki/Chromatic for visual regression
**Why:** Storybook provides isolated component development and serves as living documentation for your design system. Visual regression testing catches unintended UI changes that unit tests might miss, ensuring consistent visual appearance across releases. This is especially important for component libraries and design systems.

### unplugin-auto-import + Element Plus resolver for tree-shaking
**Why:** Auto-import eliminates boilerplate import statements while maintaining tree-shaking benefits. This reduces bundle size by only including components that are actually used. The Element Plus resolver ensures optimal bundle size by automatically importing only the necessary components and styles.

### @vueuse/core for utilities
**Why:** VueUse provides well-tested, composable utilities that handle common patterns like local storage, window events, and API calls. Using established utilities reduces bugs, improves consistency, and saves development time compared to writing custom implementations.

---

## 3. API Layer

### Generate via openapi-typescript for strong typing end-to-end
**Why:** Code generation from OpenAPI specifications ensures your frontend types always match your backend API. This catches breaking changes at compile time rather than runtime, preventing integration bugs. Strong typing improves developer experience with better autocomplete and refactoring support, while reducing the need for manual type definitions.

### Axios client with comprehensive interceptors
**Why:** Centralized request/response handling ensures consistent behavior across all API calls. Authorization header injection eliminates the need to manually add auth to every request. Request/trace ID headers enable distributed tracing and debugging. Global error mapping provides consistent user feedback and reduces code duplication throughout the application.

- Generate via `openapi-typescript` (or NSwag/NJPX) → strong typing end-to-end.
- Axios client with:
  - `Authorization` header injection (from BFF/Cognito/IAM)
  - request id/trace id headers
  - global error mapping → `ElNotification` / `ElMessageBox`

---

## 4. UX & Components

### Element Plus with typed forms and efficient data handling
**Why:** Element Plus provides battle-tested components with consistent design and accessibility features. Typed form models catch validation errors at compile time and improve developer experience. Server-side paging and sorting reduce memory usage and improve performance for large datasets. Virtual scrolling handles thousands of items without performance degradation.

### Separation of concerns: components for UI, composables/stores for logic
**Why:** Keeping components focused on presentation makes them easier to test, reuse, and maintain. Moving business logic to composables and stores enables better testing, reusability across components, and clearer separation of concerns. This architectural pattern makes the codebase more maintainable and scalable.

### Loading states and perceived performance
**Why:** ElLoading and skeleton loaders provide immediate feedback to users, improving perceived performance even when actual loading times remain the same. This reduces user frustration and abandonment rates. Proper loading states also prevent users from triggering duplicate actions while requests are in progress.

- Element Plus:
  - ElForm with typed models + validation.
  - ElTable with server-side paging/sorting; prefer **virtual scroll** for large lists.
  - ElLoading for async states; skeleton loaders for perceived performance.
- Keep components focused; business logic in composables/stores.

---

## 5. Accessibility & i18n

### Automated accessibility testing with Axe
**Why:** Axe testing catches common accessibility issues automatically, ensuring your application is usable by people with disabilities. Running these tests on key routes prevents accessibility regressions and helps maintain compliance with WCAG guidelines. This is both a legal requirement in many jurisdictions and improves user experience for all users.

### Keyboard navigation and focus management
**Why:** Proper keyboard navigation ensures your application is usable without a mouse, which is essential for users with motor disabilities and power users. Focus management after modals and toasts prevents users from losing their place in the interface and provides clear visual feedback about the current interactive element.

### vue-i18n for internationalization patterns
**Why:** Even for English-only applications, vue-i18n enforces good patterns for text management and makes future internationalization much easier. It centralizes all user-facing text, making it easier to maintain consistent messaging and enables features like pluralization and text interpolation.

- Run **Axe** (Playwright or CI plugin) on key routes.
- Keyboard navigation; focus management after modals/toasts.
- `vue-i18n` (even EN-only) to enforce patterns and future-proof.

---

## 6. Security

### Strict Content Security Policy (CSP)
**Why:** CSP prevents cross-site scripting (XSS) attacks by controlling which resources can be loaded and executed. Prohibiting inline scripts forces developers to use safer patterns and reduces the attack surface. Subresource Integrity ensures that third-party resources haven't been tampered with, preventing supply chain attacks.

### HSTS and input sanitization
**Why:** HSTS (HTTP Strict Transport Security) via CloudFront ensures all connections use HTTPS, preventing man-in-the-middle attacks. Sanitizing dynamic HTML prevents XSS attacks when displaying user-generated content. These measures provide defense-in-depth security.

### Token-based authentication without embedded secrets
**Why:** Never embedding secrets in frontend code prevents credential exposure through source code, browser dev tools, or network inspection. Obtaining tokens from BFF (Backend for Frontend) or Cognito provides secure authentication flows while keeping sensitive credentials on the server side.

- Strict **CSP**; no inline scripts; Subresource Integrity on 3rd party.
- HSTS via CloudFront; sanitize any dynamic HTML.
- Never embed secrets; obtain tokens from BFF or Cognito.

---

## 7. Performance

### Code splitting and intelligent loading
**Why:** Route-level code splitting reduces initial bundle size, improving first load performance. Users only download code for the routes they visit. Prefetching next routes provides instant navigation while balancing bandwidth usage. This is especially important for mobile users and slow connections.

### Bundle analysis and optimization
**Why:** Regular bundle analysis helps identify bloated dependencies and optimization opportunities. Element Plus can significantly impact bundle size if not properly tree-shaken. Monitoring import weight prevents performance regressions and keeps the application fast as it grows.

### Caching strategy and asset optimization
**Why:** Immutable assets with hash filenames enable aggressive caching, reducing repeat visit load times. Short TTL for HTML shell ensures users get updates quickly while still benefiting from caching. Image optimization and non-blocking fonts prevent render delays and improve perceived performance.

- Route-level code splitting; prefetch next routes.
- Analyze bundle (rollup-plugin-visualizer); watch Element Plus import weight.
- Cache immutable assets (hash filenames); short TTL for HTML shell.
- Image optimization; avoid blocking fonts.

---

## 8. Deploy & Monitor

### S3 + CloudFront with Origin Access Control (OAC)
**Why:** S3 provides cost-effective static hosting with high availability. CloudFront CDN improves global performance and provides additional security features. OAC (Origin Access Control) ensures S3 buckets aren't directly accessible, improving security. WAF on the distribution protects against common web attacks and bot traffic.

### Efficient cache invalidation
**Why:** Invalidating only changed paths reduces costs and improves deployment speed. Full cache invalidations are expensive and unnecessary when only specific files have changed. This approach enables faster deployments and better user experience during updates.

### Real User Monitoring (RUM) and synthetic monitoring
**Why:** CloudWatch RUM provides insights into actual user experience, including performance metrics and error rates. Synthetic canaries proactively monitor key user flows, catching issues before users report them. This observability is crucial for maintaining good user experience and identifying performance regressions.

- Build once, deploy to **S3 + CloudFront (OAC)**; WAF on distribution.
- Invalidate changed paths only.
- Optional: **CloudWatch RUM** and **Synthetics canaries** for key flows.

---

## 9. Checklist

**Why this checklist matters:** This checklist serves as a final verification that all critical practices are implemented. Each item represents a decision that significantly impacts user experience, security, performance, or maintainability. Regular checklist reviews during code reviews and before releases help ensure consistency across projects and prevent regression of important practices.

- [ ] OpenAPI-typed client + Axios interceptors
- [ ] ESLint+Prettier passing; vue-tsc passes
- [ ] Vitest coverage ≥ 80%
- [ ] Element Plus auto-import + theme tokens
- [ ] Axe/Lighthouse thresholds enforced
- [ ] S3+CloudFront deploy (OAC), WAF enabled
- [ ] No secrets in code; CSP strict
