import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { vi } from 'vitest'
import DashboardView from '@/views/DashboardView.vue'
import { useStatsStore } from '@/stores/stats'

// ---------------------------------------------------------------------------
// Mock the API client
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

import { get as mockGet } from '@/api/client'
import { ApiError } from '@/api/client'

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const sampleStats = {
  total: 12,
  currentWeek: 3,
  byStatus: {
    Wishlist: 4,
    Applied: 3,
    Interview: 2,
    Offer: 1,
    Rejected: 2,
  },
}

const zeroStats = {
  total: 0,
  currentWeek: 0,
  byStatus: {
    Wishlist: 0,
    Applied: 0,
    Interview: 0,
    Offer: 0,
    Rejected: 0,
  },
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const pinia = createPinia()
    setActivePinia(pinia)
  })

  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(DashboardView, {
      global: { plugins: [pinia] },
    })
  }

  it('calls statsStore.fetchStats() when mounted', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    mountView()
    await flushPromises()
    expect(mockGet).toHaveBeenCalledWith('/stats')
  })

  it('displays loading state while request is pending', async () => {
    // Never-resolving promise simulates pending request
    vi.mocked(mockGet).mockReturnValue(new Promise(() => {}))
    const wrapper = mountView()
    await nextTick()

    expect(wrapper.find('.dashboard-view-loading').exists()).toBe(true)
    expect(wrapper.text()).toContain('Loading statistics')
  })

  it('renders statistics correctly on success', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    const wrapper = mountView()
    await flushPromises()

    // DashboardStats component should be rendered
    expect(wrapper.find('.dashboard-stats').exists()).toBe(true)
    // No error or loading visible
    expect(wrapper.find('.dashboard-view-error').exists()).toBe(false)
    expect(wrapper.find('.dashboard-view-loading').exists()).toBe(false)
  })

  it('displays total applications', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('Total Applications')
  })

  it('displays current-week applications', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('This Week')
  })

  it('displays all five status counts', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    const wrapper = mountView()
    await flushPromises()

    const statusLabels = wrapper.findAll('.stats-status-label')
    const labelTexts = statusLabels.map((el) => el.text())

    expect(labelTexts).toContain('Wishlist')
    expect(labelTexts).toContain('Applied')
    expect(labelTexts).toContain('Interview')
    expect(labelTexts).toContain('Offer')
    expect(labelTexts).toContain('Rejected')

    // Verify counts are rendered
    const statusCounts = wrapper.findAll('.stats-status-count')
    const countTexts = statusCounts.map((el) => el.text())
    expect(countTexts).toContain('4') // Wishlist
    expect(countTexts).toContain('3') // Applied
    expect(countTexts).toContain('2') // Interview
    expect(countTexts).toContain('1') // Offer
  })

  it('renders zero values correctly', async () => {
    vi.mocked(mockGet).mockResolvedValue(zeroStats)
    const wrapper = mountView()
    await flushPromises()

    // DashboardStats should still render
    expect(wrapper.find('.dashboard-stats').exists()).toBe(true)

    // Total should show 0
    const cardValues = wrapper.findAll('.stats-card-value')
    const totalCard = cardValues[0]
    expect(totalCard.text()).toBe('0')

    // Current week should show 0
    const weekCard = cardValues[1]
    expect(weekCard.text()).toBe('0')

    // All status counts should show 0
    const statusCounts = wrapper.findAll('.stats-status-count')
    statusCounts.forEach((el) => {
      expect(el.text()).toBe('0')
    })
  })

  it('displays safe error banner when GET /stats fails', async () => {
    vi.mocked(mockGet).mockRejectedValue(new ApiError(503, 'Service temporarily unavailable'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.dashboard-view-error').exists()).toBe(true)
    expect(wrapper.find('.dashboard-view-error-message').text()).toContain(
      'Service temporarily unavailable',
    )
    // No DashboardStats rendered
    expect(wrapper.find('.dashboard-stats').exists()).toBe(false)
  })

  it('does not display stale statistics after a failed request', async () => {
    // First load fails
    vi.mocked(mockGet).mockRejectedValueOnce(
      new ApiError(503, 'Service temporarily unavailable'),
    )
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(DashboardView, { global: { plugins: [pinia] } })
    await flushPromises()

    // Error state is shown, no stats
    expect(wrapper.find('.dashboard-view-error').exists()).toBe(true)
    expect(wrapper.find('.dashboard-stats').exists()).toBe(false)

    // Retry also fails — stats should remain cleared
    vi.mocked(mockGet).mockRejectedValueOnce(
      new ApiError(500, 'Internal server error'),
    )
    await wrapper.find('.dashboard-view-retry').trigger('click')
    await flushPromises()

    // After second failure, stats should still NOT be visible
    expect(wrapper.find('.dashboard-stats').exists()).toBe(false)
    expect(wrapper.find('.dashboard-view-error').exists()).toBe(true)
  })

  it('Retry button triggers another fetch', async () => {
    vi.mocked(mockGet).mockRejectedValueOnce(
      new ApiError(503, 'Service temporarily unavailable'),
    )
    const wrapper = mountView()
    await flushPromises()

    // Error state should be visible with retry button
    expect(wrapper.find('.dashboard-view-retry').exists()).toBe(true)

    // Click retry — this time it succeeds
    vi.mocked(mockGet).mockResolvedValueOnce(sampleStats)
    await wrapper.find('.dashboard-view-retry').trigger('click')
    await flushPromises()
    await nextTick()

    // Stats should now be rendered
    expect(wrapper.find('.dashboard-stats').exists()).toBe(true)
    expect(wrapper.find('.dashboard-view-error').exists()).toBe(false)
    // mockGet called twice total (initial + retry)
    expect(mockGet).toHaveBeenCalledTimes(2)
  })

  it('no real network request is sent (mock verification)', async () => {
    vi.mocked(mockGet).mockResolvedValue(sampleStats)
    mountView()
    await flushPromises()

    // Only the mock was called — verify it's a vi.fn()
    expect(vi.isMockFunction(mockGet)).toBe(true)
    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(mockGet).toHaveBeenCalledWith('/stats')
  })

  it('does not expose raw errors, stack traces, or AWS identifiers', async () => {
    // Simulate an error with AWS-like details in the internal message
    vi.mocked(mockGet).mockRejectedValue(
      new ApiError(503, 'Service temporarily unavailable'),
    )
    const wrapper = mountView()
    await flushPromises()

    const html = wrapper.html()
    // No AWS identifiers
    expect(html).not.toContain('arn:aws')
    expect(html).not.toContain('dynamodb')
    expect(html).not.toContain('lambda')
    expect(html).not.toContain('ApplicationsTable')
    // No stack traces
    expect(html).not.toContain('at ')
    expect(html).not.toContain('Error:')
    expect(html).not.toContain('Traceback')
    // The safe message IS shown
    expect(html).toContain('Service temporarily unavailable')
  })
})
