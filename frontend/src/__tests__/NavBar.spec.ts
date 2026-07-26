import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import NavBar from '@/components/NavBar.vue'
import BoardView from '@/views/BoardView.vue'
import DashboardView from '@/views/DashboardView.vue'
import NewApplicationView from '@/views/NewApplicationView.vue'

function createTestRouter(initialRoute = '/board') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/board', name: 'board', component: BoardView },
      { path: '/dashboard', name: 'dashboard', component: DashboardView },
      { path: '/new', name: 'new', component: NewApplicationView },
      { path: '/:pathMatch(.*)*', redirect: '/board' },
    ],
  })
  router.push(initialRoute)
  return router
}

describe('NavBar', () => {
  it('contains a link to /board', async () => {
    const router = createTestRouter()
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const links = wrapper.findAll('a')
    const boardLink = links.find((l) => l.attributes('href') === '/board')
    expect(boardLink).toBeDefined()
    expect(boardLink!.text()).toBe('Board')
  })

  it('contains a link to /dashboard', async () => {
    const router = createTestRouter()
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const links = wrapper.findAll('a')
    const dashLink = links.find((l) => l.attributes('href') === '/dashboard')
    expect(dashLink).toBeDefined()
    expect(dashLink!.text()).toBe('Dashboard')
  })

  it('contains a link to /new', async () => {
    const router = createTestRouter()
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const links = wrapper.findAll('a')
    const newLink = links.find((l) => l.attributes('href') === '/new')
    expect(newLink).toBeDefined()
    expect(newLink!.text()).toBe('New Application')
  })

  it('applies router-link-active class to the link matching /board', async () => {
    const router = createTestRouter('/board')
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const boardLink = wrapper.findAll('a').find((l) => l.attributes('href') === '/board')
    expect(boardLink!.classes()).toContain('router-link-active')
  })

  it('applies router-link-active class to the link matching /dashboard', async () => {
    const router = createTestRouter('/dashboard')
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const dashLink = wrapper.findAll('a').find((l) => l.attributes('href') === '/dashboard')
    expect(dashLink!.classes()).toContain('router-link-active')
  })

  it('applies router-link-active class to the link matching /new', async () => {
    const router = createTestRouter('/new')
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const newLink = wrapper.findAll('a').find((l) => l.attributes('href') === '/new')
    expect(newLink!.classes()).toContain('router-link-active')
  })

  it('does not apply active class to non-matching links', async () => {
    const router = createTestRouter('/board')
    await router.isReady()

    const wrapper = mount(NavBar, {
      global: {
        plugins: [router, createPinia()],
      },
    })
    await flushPromises()

    const dashLink = wrapper.findAll('a').find((l) => l.attributes('href') === '/dashboard')
    expect(dashLink!.classes()).not.toContain('router-link-active')

    const newLink = wrapper.findAll('a').find((l) => l.attributes('href') === '/new')
    expect(newLink!.classes()).not.toContain('router-link-active')
  })
})
