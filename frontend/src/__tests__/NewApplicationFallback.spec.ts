/**
 * Task 11.1 — Verify NewApplicationView analysis fallback and
 * recommendation explanation: null rendering.
 *
 * No production code was modified — these tests prove existing behaviour.
 *
 * Validates: Requirements 1.5, 1.6, 1.8, 6.8
 */

import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'
import NewApplicationView from '@/views/NewApplicationView.vue'
import ApplicationCard from '@/components/ApplicationCard.vue'
import { useUiStore } from '@/stores/ui'
import type { Application } from '@/stores/applications'

// ---------------------------------------------------------------------------
// Mock API client
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

import { post as mockPost, ApiError } from '@/api/client'

// ---------------------------------------------------------------------------
// Mock vue-router
// ---------------------------------------------------------------------------

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mountNewApplicationView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(NewApplicationView, {
    global: { plugins: [pinia] },
  })
}

function makeApp(overrides: Partial<Application> = {}): Application {
  return {
    userId: 'demo-user',
    applicationId: 'app-1',
    jobTitle: 'Engineer',
    company: 'Acme',
    location: null,
    skills: [],
    responsibilities: [],
    languages: [],
    experienceLevel: null,
    status: 'Interview',
    createdAt: '2025-01-15T10:00:00Z',
    updatedAt: '2025-01-15T10:00:00Z',
    statusHistory: [],
    nextAction: { label: 'Prepare for interview', priority: 'High', explanation: null },
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// PART 1: Analysis fallback
// ---------------------------------------------------------------------------

describe('NewApplicationView — analysis fallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('populates ExtractionReviewForm when POST /analyze succeeds', async () => {
    const extraction = {
      jobTitle: 'Dev',
      company: 'Co',
      location: 'Paris',
      skills: ['Python'],
      responsibilities: ['Code'],
      languages: ['EN'],
      experienceLevel: 'Senior',
    }
    vi.mocked(mockPost).mockResolvedValueOnce(extraction)

    const wrapper = mountNewApplicationView()

    // Simulate analyze event from JobDescriptionForm
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Some job description')
    await flushPromises()

    // Should now show ExtractionReviewForm with populated fields
    const reviewForm = wrapper.find('#review-job-title')
    expect(reviewForm.exists()).toBe(true)
    expect((reviewForm.element as HTMLInputElement).value).toBe('Dev')
  })

  it('switches to blank manual entry on HTTP 408 (timeout)', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(new ApiError(408, 'Analysis timed out'))

    const wrapper = mountNewApplicationView()
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    // ExtractionReviewForm rendered with empty fields
    const reviewForm = wrapper.find('#review-job-title')
    expect(reviewForm.exists()).toBe(true)
    expect((reviewForm.element as HTMLInputElement).value).toBe('')
  })

  it('switches to blank manual entry on HTTP 422', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(new ApiError(422, 'Analysis failed'))

    const wrapper = mountNewApplicationView()
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    const reviewForm = wrapper.find('#review-job-title')
    expect(reviewForm.exists()).toBe(true)
    expect((reviewForm.element as HTMLInputElement).value).toBe('')
  })

  it('switches to blank manual entry on HTTP 502', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(new ApiError(502, 'Service unavailable'))

    const wrapper = mountNewApplicationView()
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    const reviewForm = wrapper.find('#review-job-title')
    expect(reviewForm.exists()).toBe(true)
    expect((reviewForm.element as HTMLInputElement).value).toBe('')
  })

  it('switches to blank manual entry on HTTP 500', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(new ApiError(500, 'Internal error'))

    const wrapper = mountNewApplicationView()
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    const reviewForm = wrapper.find('#review-job-title')
    expect(reviewForm.exists()).toBe(true)
    expect((reviewForm.element as HTMLInputElement).value).toBe('')
  })

  it('shows exactly the safe toast "Analysis failed. Enter details manually."', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(new ApiError(408, 'some internal message'))

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(NewApplicationView, { global: { plugins: [pinia] } })
    const uiStore = useUiStore()

    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    expect(uiStore.notifications).toHaveLength(1)
    expect(uiStore.notifications[0].message).toBe('Analysis failed. Enter details manually.')
    expect(uiStore.notifications[0].type).toBe('warning')
  })

  it('never displays raw API error message in the toast', async () => {
    vi.mocked(mockPost).mockRejectedValueOnce(
      new ApiError(502, 'arn:aws:bedrock:us-east-1:123456:model/anthropic'),
    )

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(NewApplicationView, { global: { plugins: [pinia] } })
    const uiStore = useUiStore()

    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    // The toast should show the safe message, NOT the raw API error
    expect(uiStore.notifications[0].message).toBe('Analysis failed. Enter details manually.')
    expect(uiStore.notifications[0].message).not.toContain('arn:aws')
  })

  it('does not block subsequent POST /applications after analysis failure', async () => {
    vi.mocked(mockPost)
      .mockRejectedValueOnce(new ApiError(408, 'timeout')) // /analyze fails
      .mockResolvedValueOnce({
        // /applications succeeds
        userId: 'demo-user',
        applicationId: 'new-id',
        jobTitle: 'Manual Entry',
        company: null,
        location: null,
        skills: [],
        responsibilities: [],
        languages: [],
        experienceLevel: null,
        status: 'Wishlist',
        createdAt: '2025-01-15T10:00:00Z',
        updatedAt: '2025-01-15T10:00:00Z',
        statusHistory: [],
        nextAction: null,
      })

    const wrapper = mountNewApplicationView()
    const form = wrapper.findComponent({ name: 'JobDescriptionForm' })
    await form.vm.$emit('analyze', 'Job text')
    await flushPromises()

    // Now in review step — fill in jobTitle and submit
    await wrapper.find('#review-job-title').setValue('Manual Entry')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // POST /applications should have been called (second call to mockPost)
    expect(mockPost).toHaveBeenCalledTimes(2)
    expect(mockPost).toHaveBeenLastCalledWith(
      '/applications',
      expect.objectContaining({
        jobTitle: 'Manual Entry',
      }),
    )
  })
})

// ---------------------------------------------------------------------------
// PART 2: Recommendation explanation: null rendering
// ---------------------------------------------------------------------------

describe('ApplicationCard — recommendation explanation: null', () => {
  it('renders normally when nextAction.explanation is null', () => {
    const app = makeApp({
      nextAction: { label: 'Prepare for interview', priority: 'High', explanation: null },
    })

    const wrapper = mount(ApplicationCard, {
      props: { application: app },
    })

    // Card renders without error
    expect(wrapper.find('.app-card-title').text()).toBe('Engineer')
    expect(wrapper.find('.app-card-badge').text()).toBe('Interview')

    // No "null" or "undefined" text anywhere
    const html = wrapper.html()
    expect(html).not.toContain('>null<')
    expect(html).not.toContain('>undefined<')
    expect(html).not.toContain('explanation')
  })

  it('renders normally when nextAction is null entirely', () => {
    const app = makeApp({ nextAction: null })

    const wrapper = mount(ApplicationCard, {
      props: { application: app },
    })

    expect(wrapper.find('.app-card-title').text()).toBe('Engineer')
    const html = wrapper.html()
    expect(html).not.toContain('>null<')
    expect(html).not.toContain('>undefined<')
  })

  it('does not render explanation section when explanation is null', () => {
    const app = makeApp({
      nextAction: { label: 'Apply now', priority: 'High', explanation: null },
    })

    const wrapper = mount(ApplicationCard, {
      props: { application: app },
    })

    // The card should not have any explanation text
    expect(wrapper.text()).not.toContain('null')
    expect(wrapper.text()).not.toContain('undefined')
  })
})
