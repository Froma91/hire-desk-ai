import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import ReminderButton from '@/components/ReminderButton.vue'
import { useApplicationsStore, type Application, type ApplicationStatus } from '@/stores/applications'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeApp(overrides: Partial<Application> = {}): Application {
  return {
    userId: 'demo-user',
    applicationId: `app-${Math.random().toString(36).slice(2, 8)}`,
    jobTitle: 'Engineer',
    company: 'Acme',
    location: 'Paris',
    skills: [],
    responsibilities: [],
    languages: [],
    experienceLevel: null,
    status: 'Wishlist' as ApplicationStatus,
    createdAt: '2025-01-15T10:00:00Z',
    updatedAt: '2025-01-15T10:00:00Z',
    statusHistory: [{ status: 'Wishlist', timestamp: '2025-01-15T10:00:00Z' }],
    nextAction: null,
    ...overrides,
  }
}

interface MockNotification {
  (title: string, options?: NotificationOptions): void
  permission: NotificationPermission
  requestPermission: ReturnType<typeof vi.fn>
}

function installNotification(permission: NotificationPermission = 'granted') {
  const ctor = vi.fn(function (this: unknown) {}) as unknown as MockNotification
  ctor.permission = permission
  ctor.requestPermission = vi.fn().mockResolvedValue(permission)
  ;(window as unknown as { Notification: MockNotification }).Notification = ctor
  ;(globalThis as unknown as { Notification: MockNotification }).Notification = ctor
  return ctor
}

function removeNotification() {
  delete (window as unknown as { Notification?: unknown }).Notification
  delete (globalThis as unknown as { Notification?: unknown }).Notification
}

function mountButton() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useApplicationsStore()
  const wrapper = mount(ReminderButton, {
    global: { plugins: [pinia] },
  })
  return { wrapper, store }
}

// Past due date relative to any realistic "now".
const PAST_DUE = '2000-01-01T00:00:00Z'
const FUTURE_DUE = '2999-01-01T00:00:00Z'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ReminderButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.sessionStorage.clear()
    removeNotification()
  })

  afterEach(() => {
    removeNotification()
    window.sessionStorage.clear()
  })

  it('does not request permission on mount', () => {
    const ctor = installNotification('granted')
    mountButton()
    expect(ctor.requestPermission).toHaveBeenCalledTimes(0)
  })

  it('renders the "Enable reminders" button when supported', () => {
    installNotification('granted')
    const { wrapper } = mountButton()
    const btn = wrapper.find('button')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('Enable reminders')
  })

  it('clicking requests permission exactly once', async () => {
    const ctor = installNotification('granted')
    const { wrapper } = mountButton()
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(ctor.requestPermission).toHaveBeenCalledTimes(1)
  })

  it('on granted, notifies a due application with title + label only', async () => {
    const ctor = installNotification('granted')
    const { wrapper, store } = mountButton()
    store.applications.push(
      makeApp({
        jobTitle: 'Backend Dev',
        company: 'SecretCorp',
        location: 'Berlin',
        nextAction: { label: 'Send CV', priority: 'high', explanation: null, dueDate: PAST_DUE },
      }),
    )
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(ctor).toHaveBeenCalledTimes(1)
    const [title, options] = (ctor as unknown as { mock: { calls: [string, NotificationOptions][] } }).mock.calls[0]
    expect(title).toBe('Hire Desk AI')
    expect(options.body).toBe('Backend Dev — Send CV')
    expect(options.body).not.toContain('SecretCorp')
    expect(options.body).not.toContain('Berlin')
  })

  it('notifies at most once per application per session', async () => {
    const ctor = installNotification('granted')
    const { wrapper, store } = mountButton()
    store.applications.push(
      makeApp({
        applicationId: 'once-1',
        nextAction: { label: 'Follow up', priority: 'high', explanation: null, dueDate: PAST_DUE },
      }),
    )
    // First scan
    await wrapper.find('button').trigger('click')
    await flushPromises()
    // Second scan (call the handler again via re-click; button is disabled so
    // invoke the component's exposed behaviour by re-mounting store scan).
    // Simulate a second scan directly through the composable path:
    const { notifyDueApplications } = await import('@/composables/useReminders')
    notifyDueApplications(store.applications)

    expect(ctor).toHaveBeenCalledTimes(1)
  })

  it('on denied, constructs no Notification and does not throw; still renders', async () => {
    const ctor = installNotification('denied')
    const { wrapper, store } = mountButton()
    store.applications.push(
      makeApp({
        nextAction: { label: 'Send CV', priority: 'high', explanation: null, dueDate: PAST_DUE },
      }),
    )
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(ctor).toHaveBeenCalledTimes(0)
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('renders nothing when Notification is not in window', () => {
    removeNotification()
    const { wrapper } = mountButton()
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.html()).toBe('<!--v-if-->')
  })

  it('does not notify for future or missing dueDate', async () => {
    const ctor = installNotification('granted')
    const { wrapper, store } = mountButton()
    store.applications.push(
      makeApp({
        nextAction: { label: 'Later', priority: 'low', explanation: null, dueDate: FUTURE_DUE },
      }),
      makeApp({
        nextAction: { label: 'No date', priority: 'low', explanation: null, dueDate: null },
      }),
      makeApp({ nextAction: null }),
    )
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(ctor).toHaveBeenCalledTimes(0)
  })
})
