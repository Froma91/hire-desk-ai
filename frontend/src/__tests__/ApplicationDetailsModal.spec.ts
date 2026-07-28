import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { vi } from 'vitest'
import ApplicationDetailsModal from '@/components/ApplicationDetailsModal.vue'
import ApplicationCard from '@/components/ApplicationCard.vue'
import KanbanBoard from '@/components/KanbanBoard.vue'
import KanbanColumn from '@/components/KanbanColumn.vue'
import { useApplicationsStore, type Application, type ApplicationStatus } from '@/stores/applications'

// ---------------------------------------------------------------------------
// Mock the API client module (same pattern as KanbanBoard tests)
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

// ---------------------------------------------------------------------------
// Helper: sample application factory
// ---------------------------------------------------------------------------

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
    status: 'Wishlist' as ApplicationStatus,
    createdAt: '2025-01-15T10:00:00Z',
    updatedAt: '2025-01-15T10:00:00Z',
    statusHistory: [{ status: 'Wishlist', timestamp: '2025-01-15T10:00:00Z' }],
    nextAction: null,
    ...overrides,
  }
}

function fullApp(): Application {
  return makeApp({
    applicationId: 'app-full',
    jobTitle: 'Senior Frontend Engineer',
    company: 'Globex',
    location: 'Paris, France',
    experienceLevel: 'Senior',
    status: 'Interview',
    skills: ['Vue', 'TypeScript', 'CSS'],
    languages: ['English', 'French'],
    responsibilities: ['Build UI', 'Review code', 'Mentor juniors'],
    createdAt: '2025-01-10T09:00:00Z',
    updatedAt: '2025-01-20T15:30:00Z',
    statusHistory: [
      { status: 'Applied', timestamp: '2025-01-12T08:00:00Z' },
      { status: 'Wishlist', timestamp: '2025-01-10T09:00:00Z' },
      { status: 'Interview', timestamp: '2025-01-18T11:00:00Z' },
    ],
    nextAction: {
      label: 'Prepare for interview',
      priority: 'high',
      explanation: 'Interview scheduled soon; review company background.',
      dueDate: '2025-01-25T09:00:00Z',
    },
  })
}

// ---------------------------------------------------------------------------
// Modal unit tests
// ---------------------------------------------------------------------------

describe('ApplicationDetailsModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders all available fields when populated', () => {
    const app = fullApp()
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: app },
    })

    const text = wrapper.text()
    expect(text).toContain('Senior Frontend Engineer')
    expect(text).toContain('Globex')
    expect(text).toContain('Paris, France')
    expect(text).toContain('Senior')
    expect(text).toContain('Interview')

    // Skills as tags
    expect(text).toContain('Vue')
    expect(text).toContain('TypeScript')
    expect(text).toContain('CSS')

    // Languages
    expect(text).toContain('English')
    expect(text).toContain('French')

    // Responsibilities
    expect(text).toContain('Build UI')
    expect(text).toContain('Review code')
    expect(text).toContain('Mentor juniors')

    // Next action
    expect(text).toContain('Prepare for interview')
    expect(text).toContain('Interview scheduled soon')
  })

  it('shows status history in ascending chronological order without mutating the prop', () => {
    const app = fullApp()
    const originalOrder = app.statusHistory.map((e) => e.status)

    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: app },
    })

    const items = wrapper.findAll('.modal-history-item .modal-history-status')
    const rendered = items.map((i) => i.text())
    expect(rendered).toEqual(['Wishlist', 'Applied', 'Interview'])

    // Prop must not be mutated
    expect(app.statusHistory.map((e) => e.status)).toEqual(originalOrder)
  })

  it('does not crash and shows "Not specified" when nextAction is null', () => {
    const app = makeApp({ nextAction: null, skills: [], languages: [], responsibilities: [] })
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: app },
    })
    expect(wrapper.text()).toContain('Not specified')
    // Should render without error
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  })

  it('has accessible dialog semantics', () => {
    const app = fullApp()
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: app },
    })
    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('aria-modal')).toBe('true')
    const labelledby = dialog.attributes('aria-labelledby')
    expect(labelledby).toBeTruthy()
    const title = wrapper.find('h2.modal-title')
    expect(title.attributes('id')).toBe(labelledby)
  })

  it('close button emits close', async () => {
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: fullApp() },
    })
    await wrapper.find('.modal-close').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('Escape key emits close', async () => {
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: fullApp() },
      attachTo: document.body,
    })
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
    wrapper.unmount()
  })

  it('backdrop click emits close but inner dialog click does not', async () => {
    const wrapper = mount(ApplicationDetailsModal, {
      props: { application: fullApp() },
    })

    // Clicking inside the dialog should NOT close
    await wrapper.find('.modal-dialog').trigger('click')
    expect(wrapper.emitted('close')).toBeFalsy()

    // Clicking the backdrop itself should close (self target)
    await wrapper.find('.modal-backdrop').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// ApplicationCard interaction tests
// ---------------------------------------------------------------------------

describe('ApplicationCard open behaviour', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('clicking the card body emits open with the application', async () => {
    const app = makeApp({ jobTitle: 'Clickable' })
    const wrapper = mount(ApplicationCard, {
      props: { application: app },
    })
    await wrapper.find('.app-card').trigger('click')
    const emitted = wrapper.emitted('open')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatchObject({ jobTitle: 'Clickable' })
  })

  it('clicking the drag handle does NOT emit open', async () => {
    const app = makeApp()
    const wrapper = mount(ApplicationCard, {
      props: { application: app },
    })
    await wrapper.find('.app-card-drag-handle').trigger('click')
    expect(wrapper.emitted('open')).toBeFalsy()
  })

  it('keeps draggable attribute for drag-and-drop', () => {
    const wrapper = mount(ApplicationCard, {
      props: { application: makeApp() },
    })
    expect(wrapper.find('.app-card').attributes('draggable')).toBe('true')
  })
})

// ---------------------------------------------------------------------------
// KanbanBoard integration tests
// ---------------------------------------------------------------------------

describe('KanbanBoard details modal integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('clicking a card body opens the modal with the correct application', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-open', status: 'Applied', jobTitle: 'Backend Dev' })
    store.applications.push(app)

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    expect(wrapper.findComponent(ApplicationDetailsModal).exists()).toBe(false)

    await wrapper.find('.app-card').trigger('click')
    await flushPromises()

    const modal = wrapper.findComponent(ApplicationDetailsModal)
    expect(modal.exists()).toBe(true)
    expect(modal.text()).toContain('Backend Dev')
  })

  it('clicking the drag handle does not open the modal', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    store.applications.push(makeApp({ applicationId: 'app-handle', status: 'Applied' }))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    await wrapper.find('.app-card-drag-handle').trigger('click')
    await flushPromises()

    expect(wrapper.findComponent(ApplicationDetailsModal).exists()).toBe(false)
  })

  it('close button removes the modal from the board', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    store.applications.push(makeApp({ applicationId: 'app-close', status: 'Applied', jobTitle: 'Closer' }))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    await wrapper.find('.app-card').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(ApplicationDetailsModal).exists()).toBe(true)

    await wrapper.find('.modal-close').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(ApplicationDetailsModal).exists()).toBe(false)
  })

  it('the open event forwards through KanbanColumn', async () => {
    const app = makeApp({ jobTitle: 'Column Forward' })
    const wrapper = mount(KanbanColumn, {
      props: { status: 'Applied' as ApplicationStatus, applications: [app] },
    })
    await wrapper.find('.app-card').trigger('click')
    const emitted = wrapper.emitted('open')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatchObject({ jobTitle: 'Column Forward' })
  })
})
