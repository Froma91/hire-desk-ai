import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import BoardView from '@/views/BoardView.vue'
import DashboardView from '@/views/DashboardView.vue'
import NewApplicationView from '@/views/NewApplicationView.vue'

// Create a fresh router for each test using memory history
function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/board', name: 'board', component: BoardView },
      { path: '/dashboard', name: 'dashboard', component: DashboardView },
      { path: '/new', name: 'new', component: NewApplicationView },
      { path: '/:pathMatch(.*)*', redirect: '/board' },
    ],
  })
}

describe('Router', () => {
  it('renders BoardView at /board', async () => {
    const router = createTestRouter()
    router.push('/board')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Application Board')
  })

  it('renders DashboardView at /dashboard', async () => {
    const router = createTestRouter()
    router.push('/dashboard')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Dashboard View')
  })

  it('renders NewApplicationView at /new', async () => {
    const router = createTestRouter()
    router.push('/new')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Paste the job description')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('redirects unknown routes to /board', async () => {
    const router = createTestRouter()
    router.push('/unknown-path')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/board')
    expect(wrapper.text()).toContain('Application Board')
  })

  it('redirects root / to /board', async () => {
    const router = createTestRouter()
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/board')
  })
})
