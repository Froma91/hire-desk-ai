import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { vi } from 'vitest'
import KanbanBoard from '@/components/KanbanBoard.vue'
import KanbanColumn from '@/components/KanbanColumn.vue'
import { useApplicationsStore, type Application, type ApplicationStatus } from '@/stores/applications'
import { useUiStore } from '@/stores/ui'

// ---------------------------------------------------------------------------
// Mock the API client module
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

import { patch as mockPatch } from '@/api/client'
import { ApiError } from '@/api/client'

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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('KanbanBoard', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  function mountBoard() {
    return mount(KanbanBoard, {
      global: {
        plugins: [createPinia()],
      },
    })
  }

  function mountBoardWithPinia() {
    // Mount using the already-active pinia so we can pre-populate the store
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(KanbanBoard, {
      global: {
        plugins: [pinia],
      },
    })
  }

  it('renders exactly five columns', () => {
    const wrapper = mountBoard()
    const columns = wrapper.findAllComponents(KanbanColumn)
    expect(columns).toHaveLength(5)
  })

  it('application appears in matching status column', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ status: 'Applied', jobTitle: 'Frontend Dev' })
    store.applications.push(app)

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')
    const wishlistColumn = columns.find((c) => c.props('status') === 'Wishlist')

    expect(appliedColumn).toBeDefined()
    expect(appliedColumn!.props('applications')).toEqual(
      expect.arrayContaining([expect.objectContaining({ jobTitle: 'Frontend Dev' })]),
    )
    expect(wishlistColumn!.props('applications')).toHaveLength(0)
  })

  it('empty columns show empty state text', () => {
    const wrapper = mountBoard()
    const emptyTexts = wrapper.findAll('.kanban-column-empty-text')
    // All 5 columns should show "No applications"
    expect(emptyTexts).toHaveLength(5)
    emptyTexts.forEach((el) => {
      expect(el.text()).toBe('No applications')
    })
  })

  it('valid drop calls updateStatus via patch', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-drop-test', status: 'Wishlist', jobTitle: 'Tester' })
    store.applications.push(app)

    const updatedApp = { ...app, status: 'Applied' as ApplicationStatus }
    vi.mocked(mockPatch).mockResolvedValue(updatedApp)

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')

    await appliedColumn!.vm.$emit('drop', { applicationId: 'app-drop-test', status: 'Applied' })
    await flushPromises()

    expect(mockPatch).toHaveBeenCalledWith('/applications/app-drop-test/status', { status: 'Applied' })
  })

  it('drop in same column does not call update', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-same-col', status: 'Wishlist' })
    store.applications.push(app)

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const wishlistColumn = columns.find((c) => c.props('status') === 'Wishlist')

    await wishlistColumn!.vm.$emit('drop', { applicationId: 'app-same-col', status: 'Wishlist' })
    await flushPromises()

    expect(mockPatch).not.toHaveBeenCalled()
  })

  it('optimistic move is visible immediately', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-optimistic', status: 'Wishlist', jobTitle: 'Optimistic Job' })
    store.applications.push(app)

    // Never resolving promise to simulate slow network
    vi.mocked(mockPatch).mockReturnValue(new Promise(() => {}))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')

    appliedColumn!.vm.$emit('drop', { applicationId: 'app-optimistic', status: 'Applied' })
    await nextTick()

    // The store should now have the app in "Applied" status (optimistic)
    const appInStore = store.applications.find((a) => a.applicationId === 'app-optimistic')
    expect(appInStore!.status).toBe('Applied')
  })

  it('api failure rolls back optimistic update', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-rollback', status: 'Wishlist' })
    store.applications.push(app)

    vi.mocked(mockPatch).mockRejectedValue(new ApiError(503, 'Service unavailable'))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')

    await appliedColumn!.vm.$emit('drop', { applicationId: 'app-rollback', status: 'Applied' })
    await flushPromises()

    // Should be rolled back to Wishlist
    const appInStore = store.applications.find((a) => a.applicationId === 'app-rollback')
    expect(appInStore!.status).toBe('Wishlist')
  })

  it('error notification shown after rollback', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const uiStore = useUiStore()
    const app = makeApp({ applicationId: 'app-notif', status: 'Wishlist' })
    store.applications.push(app)

    vi.mocked(mockPatch).mockRejectedValue(new ApiError(503, 'Service unavailable'))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')

    await appliedColumn!.vm.$emit('drop', { applicationId: 'app-notif', status: 'Applied' })
    await flushPromises()

    expect(uiStore.notifications).toHaveLength(1)
    expect(uiStore.notifications[0].type).toBe('error')
    expect(uiStore.notifications[0].message).toContain('Failed to update status')
  })

  it('duplicate pending drops are prevented', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useApplicationsStore()
    const app = makeApp({ applicationId: 'app-dedup', status: 'Wishlist' })
    store.applications.push(app)

    // Never resolving promise
    vi.mocked(mockPatch).mockReturnValue(new Promise(() => {}))

    const wrapper = mount(KanbanBoard, {
      global: { plugins: [pinia] },
    })

    const columns = wrapper.findAllComponents(KanbanColumn)
    const appliedColumn = columns.find((c) => c.props('status') === 'Applied')

    // Emit drop twice rapidly
    appliedColumn!.vm.$emit('drop', { applicationId: 'app-dedup', status: 'Applied' })
    await nextTick()
    appliedColumn!.vm.$emit('drop', { applicationId: 'app-dedup', status: 'Applied' })
    await nextTick()

    // patch should only be called once (second drop ignored because it's pending)
    expect(mockPatch).toHaveBeenCalledTimes(1)
  })
})
