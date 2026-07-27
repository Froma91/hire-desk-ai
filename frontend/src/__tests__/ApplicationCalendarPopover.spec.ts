import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Mock the API client (matches existing dashboard test conventions)
// ---------------------------------------------------------------------------

vi.mock('@/api/client', () => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
      this.name = 'ApiError'
    }
  },
}))

import ApplicationCalendarPopover from '@/components/ApplicationCalendarPopover.vue'
import DashboardStats from '@/components/DashboardStats.vue'
import DashboardView from '@/views/DashboardView.vue'
import ApplicationDetailsModal from '@/components/ApplicationDetailsModal.vue'
import { useApplicationsStore, type Application, type ApplicationStatus } from '@/stores/applications'
import { get as mockGet } from '@/api/client'

// A fixed "now" inside June 2025 (Wednesday 2025-06-11 12:00 local).
const FIXED_NOW = new Date(2025, 5, 11, 12, 0, 0)

function makeApp(overrides: Partial<Application> = {}): Application {
  return {
    userId: 'demo-user',
    applicationId: `app-${Math.random().toString(36).slice(2, 8)}`,
    jobTitle: 'Engineer',
    company: 'Acme',
    location: null,
    skills: [],
    responsibilities: [],
    languages: [],
    experienceLevel: null,
    status: 'Applied' as ApplicationStatus,
    createdAt: '2025-06-01T00:00:00Z',
    updatedAt: '2025-06-01T00:00:00Z',
    statusHistory: [],
    nextAction: null,
    ...overrides,
  }
}

/** Application applied on a specific local day in June 2025. */
function appliedOn(day: number, overrides: Partial<Application> = {}): Application {
  return makeApp({
    statusHistory: [
      { status: 'Applied', timestamp: new Date(2025, 5, day, 10, 0, 0).toISOString() },
    ],
    ...overrides,
  })
}

/** Find the day-cell button whose day number matches. */
function dayButton(wrapper: ReturnType<typeof mount>, day: number) {
  return wrapper
    .findAll('.calendar-cell--day')
    .find((btn) => btn.find('.calendar-cell-day').text() === String(day))
}

describe('ApplicationCalendarPopover', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(FIXED_NOW)
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function mountPopover(applications: Application[]) {
    return mount(ApplicationCalendarPopover, {
      props: { applications },
      attachTo: document.body,
    })
  }

  it('renders the current month title', () => {
    const wrapper = mountPopover([])
    expect(wrapper.find('.calendar-title').text()).toBe('June 2025')
  })

  it('8. previous and next month navigation update the displayed month', async () => {
    const wrapper = mountPopover([])
    expect(wrapper.find('.calendar-title').text()).toBe('June 2025')

    await wrapper.find('[aria-label="Next month"]').trigger('click')
    expect(wrapper.find('.calendar-title').text()).toBe('July 2025')

    await wrapper.find('[aria-label="Previous month"]').trigger('click')
    await wrapper.find('[aria-label="Previous month"]').trigger('click')
    expect(wrapper.find('.calendar-title').text()).toBe('May 2025')
  })

  it('9. clicking a date shows the correct applications for that date', async () => {
    const app5 = appliedOn(5, { jobTitle: 'Backend Dev', company: 'Globex' })
    const app12 = appliedOn(12, { jobTitle: 'Data Analyst', company: 'Initech' })
    const wrapper = mountPopover([app5, app12])

    await dayButton(wrapper, 5)!.trigger('click')

    const items = wrapper.findAll('.calendar-app-item')
    expect(items).toHaveLength(1)
    expect(wrapper.find('.calendar-day-list').text()).toContain('Backend Dev')
    expect(wrapper.find('.calendar-day-list').text()).toContain('Globex')
    expect(wrapper.find('.calendar-day-list').text()).not.toContain('Data Analyst')
  })

  it('10. multiple applications on the same date are all displayed', async () => {
    const a = appliedOn(5, { jobTitle: 'Role A' })
    const b = appliedOn(5, { jobTitle: 'Role B' })
    const c = appliedOn(5, { jobTitle: 'Role C' })
    const wrapper = mountPopover([a, b, c])

    await dayButton(wrapper, 5)!.trigger('click')

    const items = wrapper.findAll('.calendar-app-item')
    expect(items).toHaveLength(3)
    const text = wrapper.find('.calendar-app-list').text()
    expect(text).toContain('Role A')
    expect(text).toContain('Role B')
    expect(text).toContain('Role C')
  })

  it('shows the empty message for a date with no applications', async () => {
    const wrapper = mountPopover([appliedOn(5)])
    await dayButton(wrapper, 20)!.trigger('click')
    expect(wrapper.find('.calendar-empty').text()).toBe('No applications submitted on this date.')
  })

  it('shows status as both a colored badge and text (never color-only)', async () => {
    const wrapper = mountPopover([appliedOn(5, { status: 'Interview' })])
    await dayButton(wrapper, 5)!.trigger('click')
    expect(wrapper.find('.calendar-app-badge--interview').exists()).toBe(true)
    expect(wrapper.find('.calendar-app-status-text').text()).toBe('Interview')
  })

  it('renders a count indicator when more than one application on a day', () => {
    const wrapper = mountPopover([appliedOn(5), appliedOn(5), appliedOn(7)])
    const day5 = dayButton(wrapper, 5)!
    expect(day5.find('.calendar-cell-count').text()).toBe('2')
    const day7 = dayButton(wrapper, 7)!
    expect(day7.find('.calendar-cell-dot').exists()).toBe(true)
  })

  it('11. clicking an application emits select-application with the right app', async () => {
    const app5 = appliedOn(5, { applicationId: 'sel-1', jobTitle: 'Chosen Role' })
    const wrapper = mountPopover([app5])
    await dayButton(wrapper, 5)!.trigger('click')

    await wrapper.find('.calendar-app-btn').trigger('click')

    const emitted = wrapper.emitted('select-application')
    expect(emitted).toBeTruthy()
    expect((emitted![0][0] as Application).applicationId).toBe('sel-1')
  })

  it('12. Escape closes the calendar (emits close)', async () => {
    const wrapper = mountPopover([])
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('13. clicking outside (backdrop) closes the calendar', async () => {
    const wrapper = mountPopover([])
    await wrapper.find('.calendar-backdrop').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('13b. clicking inside the popover does NOT close it', async () => {
    const wrapper = mountPopover([])
    await wrapper.find('.calendar-popover').trigger('click')
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('has an accessible dialog role labelled by the month title', () => {
    const wrapper = mountPopover([])
    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.exists()).toBe(true)
    const labelledby = dialog.attributes('aria-labelledby')
    expect(labelledby).toBeTruthy()
    expect(wrapper.find(`#${labelledby}`).text()).toBe('June 2025')
  })
})

// ---------------------------------------------------------------------------
// Integration with DashboardStats / DashboardView
// ---------------------------------------------------------------------------

describe('DashboardStats calendar integration', () => {
  const sampleStats = {
    total: 5,
    currentWeek: 99,
    byStatus: { Wishlist: 1, Applied: 2, Interview: 1, Offer: 1, Rejected: 0 },
  }

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(FIXED_NOW)
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the "Applied This Week" label and the computed count (not stats.currentWeek)', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    // Two apps applied this week (Jun 9..15), one before the week.
    store.applications.push(appliedOn(10), appliedOn(11), appliedOn(2))

    const wrapper = mount(DashboardStats, {
      props: { stats: sampleStats },
      global: { plugins: [pinia] },
    })

    expect(wrapper.text()).toContain('Applied This Week')
    // Value is the applied-this-week count (2), NOT stats.currentWeek (99).
    const accentValue = wrapper.find('.stats-card--accent .stats-card-value')
    expect(accentValue.text()).toBe('2')
    expect(wrapper.text()).not.toContain('99')
  })

  it('7. clicking the calendar button opens the calendar popover', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    store.applications.push(appliedOn(5))

    const wrapper = mount(DashboardStats, {
      props: { stats: sampleStats },
      global: { plugins: [pinia] },
    })

    expect(wrapper.findComponent(ApplicationCalendarPopover).exists()).toBe(false)
    await wrapper.find('[aria-label="Open applications calendar"]').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(ApplicationCalendarPopover).exists()).toBe(true)
  })

  it('11b. selecting an application in the calendar opens the shared ApplicationDetailsModal in DashboardView', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    store.applications.push(appliedOn(5, { jobTitle: 'Modal Role' }))

    // Stats load succeeds so DashboardStats renders.
    vi.mocked(mockGet).mockResolvedValue(sampleStats)

    const wrapper = mount(DashboardView, {
      global: { plugins: [pinia] },
    })
    await flushPromises()

    // Open the calendar
    await wrapper.find('[aria-label="Open applications calendar"]').trigger('click')
    await flushPromises()

    // Click the day with the application, then the application entry
    await dayButton(wrapper, 5)!.trigger('click')
    await wrapper.find('.calendar-app-btn').trigger('click')
    await nextTick()

    // The shared details modal should now be rendered
    expect(wrapper.findComponent(ApplicationDetailsModal).exists()).toBe(true)
    expect(wrapper.find('.modal-dialog').text()).toContain('Modal Role')
  })
})
