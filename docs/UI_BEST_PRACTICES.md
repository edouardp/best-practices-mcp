# UI Best Practices — Vue 3 + TypeScript + Element Plus

> Defaults: **Vite**, **strict TypeScript**, **Pinia**, **Element Plus**, **OpenAPI-typed client**, **Vitest + Vue Testing Library**, **ESLint+Prettier**, **S3+CloudFront** deploy, **Axe/Lighthouse** checks, **RUM/Synthetics** optional.

---

## 0. Golden Rules

### Strict TypeScript ("strict": true); vue-tsc --noEmit in CI
**Why:** Strict TypeScript catches type errors at compile time, preventing runtime bugs and improving code reliability. The strict mode enables all type checking features, providing maximum safety. Running vue-tsc in CI ensures type safety is maintained across the entire codebase, including Vue single-file components. This prevents "works on my machine" issues and catches integration problems early.

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

```yaml
# CI pipeline
- name: Type Check
  run: vue-tsc --noEmit --skipLibCheck
```

### Generate a typed API client from OpenAPI; no ad-hoc DTOs
**Why:** OpenAPI-generated clients ensure your frontend and backend stay in sync automatically. When the API changes, TypeScript compilation will fail if the frontend code is incompatible, catching breaking changes immediately. Ad-hoc DTOs create maintenance overhead and can drift from the actual API, leading to runtime errors and data inconsistencies.

```bash
# Generate typed client from OpenAPI spec
npx openapi-typescript http://localhost:3000/api/openapi.json -o src/api/types.ts

# Or from local file
npx openapi-typescript ./api-spec.yaml -o src/api/types.ts
```

```typescript
// src/api/client.ts
import type { paths } from './types'
import axios from 'axios'

type ApiClient = {
  [K in keyof paths]: {
    [M in keyof paths[K]]: paths[K][M] extends { requestBody: infer B; responses: infer R }
      ? (body: B) => Promise<R[200]['content']['application/json']>
      : paths[K][M] extends { responses: infer R }
      ? () => Promise<R[200]['content']['application/json']>
      : never
  }
}

// Usage with full type safety
const api = createApiClient()
const user = await api['/users/{id}'].get() // Fully typed response
```

### Centralize API access with Axios interceptors (auth, tracing, retries)
**Why:** Centralized API handling ensures consistent behavior across all HTTP requests. Interceptors provide a single place to handle authentication, add tracing headers, implement retry logic, and manage global error handling. This reduces code duplication and ensures all API calls follow the same patterns for observability and reliability.

```typescript
// src/api/client.ts
import axios from 'axios'
import { ElNotification } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
})

// Request interceptor for auth and tracing
apiClient.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  const requestId = crypto.randomUUID()
  
  config.headers.Authorization = `Bearer ${authStore.token}`
  config.headers['X-Request-ID'] = requestId
  config.headers['X-Trace-ID'] = getTraceId()
  
  return config
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || 'An error occurred'
    
    if (error.response?.status === 401) {
      useAuthStore().logout()
      ElNotification.error({ title: 'Authentication Error', message: 'Please log in again' })
    } else if (error.response?.status >= 500) {
      ElNotification.error({ title: 'Server Error', message })
    }
    
    return Promise.reject(error)
  }
)

export { apiClient }
```

### Element Plus with auto-imported components; theme via SCSS tokens
**Why:** Element Plus provides a comprehensive, well-tested component library that accelerates development and ensures consistent UX. Auto-import reduces bundle size through tree-shaking and eliminates manual import statements. SCSS tokens enable consistent theming and make it easy to maintain brand consistency across the application.

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
})
```

```scss
// src/styles/variables.scss
:root {
  --el-color-primary: #409eff;
  --el-color-success: #67c23a;
  --el-color-warning: #e6a23c;
  --el-color-danger: #f56c6c;
  --el-border-radius-base: 4px;
  --el-font-size-base: 14px;
}

// Custom theme tokens
$brand-primary: #1976d2;
$brand-secondary: #424242;
$spacing-unit: 8px;
```

```vue
<!-- Components auto-imported, no manual imports needed -->
<template>
  <el-form :model="form" :rules="rules" ref="formRef">
    <el-form-item label="Email" prop="email">
      <el-input v-model="form.email" type="email" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="submitForm">Submit</el-button>
    </el-form-item>
  </el-form>
</template>
```

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

```typescript
// tests/components/OrderList.test.ts
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'
import OrderList from '@/components/OrderList.vue'
import type { Order } from '@/api/types'

const mockOrders: Order[] = [
  { id: '1', status: 'pending', customerName: 'John Doe' },
  { id: '2', status: 'completed', customerName: 'Jane Smith' }
]

describe('OrderList', () => {
  it('should render orders correctly', () => {
    render(OrderList, {
      props: {
        orders: mockOrders,
        loading: false,
        error: null
      }
    })

    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
  })

  it('should emit update-status when complete button is clicked', async () => {
    const { emitted } = render(OrderList, {
      props: {
        orders: mockOrders,
        loading: false,
        error: null
      }
    })

    const completeButton = screen.getAllByText('Complete')[0]
    await fireEvent.click(completeButton)

    expect(emitted()['update-status']).toEqual([['1', 'completed']])
  })

  it('should show loading state', () => {
    render(OrderList, {
      props: {
        orders: [],
        loading: true,
        error: null
      }
    })

    expect(screen.getByTestId('loading')).toBeInTheDocument()
  })
})
```

```json
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    }
  }
})
```

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

```typescript
// src/composables/useOrders.ts
import { ref, computed } from 'vue'
import { apiClient } from '@/api/client'
import type { Order } from '@/api/types'

export function useOrders() {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const pendingOrders = computed(() => 
    orders.value.filter(order => order.status === 'pending')
  )

  async function fetchOrders() {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.get('/orders')
      orders.value = response.data
    } catch (err) {
      error.value = 'Failed to fetch orders'
    } finally {
      loading.value = false
    }
  }

  async function updateOrderStatus(orderId: string, status: string) {
    try {
      await apiClient.patch(`/orders/${orderId}`, { status })
      const order = orders.value.find(o => o.id === orderId)
      if (order) order.status = status
    } catch (err) {
      error.value = 'Failed to update order'
    }
  }

  return {
    orders: readonly(orders),
    loading: readonly(loading),
    error: readonly(error),
    pendingOrders,
    fetchOrders,
    updateOrderStatus
  }
}
```

```vue
<!-- src/components/OrderList.vue - Pure presentation component -->
<template>
  <div class="order-list">
    <el-loading-directive v-loading="loading">
      <el-table :data="orders" v-if="!error">
        <el-table-column prop="id" label="Order ID" />
        <el-table-column prop="status" label="Status">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="$emit('update-status', row.id, 'completed')"
            >
              Complete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-alert v-if="error" type="error" :title="error" />
    </el-loading-directive>
  </div>
</template>

<script setup lang="ts">
import type { Order } from '@/api/types'

defineProps<{
  orders: Order[]
  loading: boolean
  error: string | null
}>()

defineEmits<{
  'update-status': [orderId: string, status: string]
}>()

function getStatusType(status: string) {
  return status === 'completed' ? 'success' : 'warning'
}
</script>
```

```vue
<!-- src/pages/OrdersPage.vue - Container component -->
<template>
  <div class="orders-page">
    <OrderList 
      :orders="orders"
      :loading="loading"
      :error="error"
      @update-status="updateOrderStatus"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useOrders } from '@/composables/useOrders'
import OrderList from '@/components/OrderList.vue'

const { orders, loading, error, fetchOrders, updateOrderStatus } = useOrders()

onMounted(() => {
  fetchOrders()
})
</script>
```

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

```typescript
// tests/accessibility.spec.ts
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Tests', () => {
  test('should not have accessibility violations on login page', async ({ page }) => {
    await page.goto('/login')
    
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should not have accessibility violations on dashboard', async ({ page }) => {
    await page.goto('/dashboard')
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    
    expect(accessibilityScanResults.violations).toEqual([])
  })
})
```

```vue
<!-- Example of accessible form component -->
<template>
  <el-form 
    ref="formRef" 
    :model="form" 
    :rules="rules"
    label-position="top"
    @submit.prevent="handleSubmit"
  >
    <el-form-item 
      label="Email Address" 
      prop="email"
      :error="emailError"
    >
      <el-input
        v-model="form.email"
        type="email"
        autocomplete="email"
        :aria-describedby="emailError ? 'email-error' : undefined"
        placeholder="Enter your email address"
      />
      <div v-if="emailError" id="email-error" class="error-text">
        {{ emailError }}
      </div>
    </el-form-item>

    <el-form-item>
      <el-button 
        type="primary" 
        native-type="submit"
        :loading="loading"
        :aria-label="loading ? 'Submitting form...' : 'Submit form'"
      >
        {{ loading ? 'Submitting...' : 'Submit' }}
      </el-button>
    </el-form-item>
  </el-form>
</template>
```

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

```html
<!-- index.html with strict CSP -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-eval';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: https:;
  connect-src 'self' https://api.example.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
">

<!-- Third-party resources with integrity checks -->
<link 
  rel="stylesheet" 
  href="https://cdn.jsdelivr.net/npm/element-plus@2.4.0/dist/index.css"
  integrity="sha384-..."
  crossorigin="anonymous"
>
```

```typescript
// src/utils/sanitize.ts
import DOMPurify from 'dompurify'

export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'target'],
    ALLOW_DATA_ATTR: false
  })
}

// Usage in component
function displayUserContent(content: string) {
  return sanitizeHtml(content)
}
```

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

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/pages/HomePage.vue') // Lazy loaded
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
      meta: { prefetch: true } // Prefetch this route
    },
    {
      path: '/reports',
      name: 'Reports',
      // Heavy component loaded only when needed
      component: () => import('@/pages/ReportsPage.vue')
    }
  ]
})

// Prefetch routes marked for prefetching
router.beforeEach((to, from, next) => {
  if (to.meta?.prefetch) {
    // Prefetch next likely routes
    import('@/pages/SettingsPage.vue')
  }
  next()
})
```

```typescript
// vite.config.ts - Bundle analysis
import { defineConfig } from 'vite'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    // ... other plugins
    visualizer({
      filename: 'dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'charts': ['echarts', 'vue-echarts'],
          'utils': ['lodash-es', 'date-fns']
        }
      }
    }
  }
})
```

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
