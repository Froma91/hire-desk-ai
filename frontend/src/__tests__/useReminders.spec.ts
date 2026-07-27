import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import {
  isNotificationSupported,
  isDueOrOverdue,
  sessionKey,
  alreadyNotified,
  markNotified,
  requestReminderPermission,
  notifyDueApplications,
} from '@/composables/useReminders'
import type { Application, ApplicationStatus, NextAction } from '@/stores/applications'

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

function nextAction(overrides: Partial<NextAction> = {}): NextAction {
  return {
    label: 'Follow up',
    priority: 'high',
    explanation: null,
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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useReminders', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.sessionStorage.clear()
    removeNotification()
  })

  afterEach(() => {
    removeNotification()
    window.sessionStorage.clear()
  })

  describe('isNotificationSupported', () => {
    it('is false when Notification is absent', () => {
      removeNotification()
      expect(isNotificationSupported()).toBe(false)
    })

    it('is true when Notification is present', () => {
      installNotification()
      expect(isNotificationSupported()).toBe(true)
    })
  })

  describe('isDueOrOverdue', () => {
    const now = new Date('2025-06-15T12:00:00Z')

    it('is false for null/undefined/empty', () => {
      expect(isDueOrOverdue(null, now)).toBe(false)
      expect(isDueOrOverdue(undefined, now)).toBe(false)
      expect(isDueOrOverdue('', now)).toBe(false)
    })

    it('is false for unparseable dates', () => {
      expect(isDueOrOverdue('not-a-date', now)).toBe(false)
    })

    it('is true for a past date', () => {
      expect(isDueOrOverdue('2025-06-14T12:00:00Z', now)).toBe(true)
    })

    it('is true for exactly now', () => {
      expect(isDueOrOverdue('2025-06-15T12:00:00Z', now)).toBe(true)
    })

    it('is false for a future date', () => {
      expect(isDueOrOverdue('2025-06-16T12:00:00Z', now)).toBe(false)
    })
  })

  describe('sessionKey / dedupe', () => {
    it('builds a namespaced key', () => {
      expect(sessionKey('abc')).toBe('hda:notified:abc')
    })

    it('markNotified then alreadyNotified is true', () => {
      expect(alreadyNotified('abc')).toBe(false)
      markNotified('abc')
      expect(alreadyNotified('abc')).toBe(true)
    })
  })

  describe('requestReminderPermission', () => {
    it('returns denied when unsupported', async () => {
      removeNotification()
      await expect(requestReminderPermission()).resolves.toBe('denied')
    })

    it('resolves the granted permission from a promise-based API', async () => {
      installNotification('granted')
      await expect(requestReminderPermission()).resolves.toBe('granted')
    })
  })

  describe('notifyDueApplications', () => {
    const now = new Date('2025-06-15T12:00:00Z')

    it('returns 0 when unsupported', () => {
      removeNotification()
      const apps = [makeApp({ nextAction: nextAction({ dueDate: '2025-01-01T00:00:00Z' }) })]
      expect(notifyDueApplications(apps, now)).toBe(0)
    })

    it('returns 0 when permission is not granted', () => {
      installNotification('denied')
      const apps = [makeApp({ nextAction: nextAction({ dueDate: '2025-01-01T00:00:00Z' }) })]
      expect(notifyDueApplications(apps, now)).toBe(0)
    })

    it('notifies due apps with only title + label in the body', () => {
      const ctor = installNotification('granted')
      const apps = [
        makeApp({
          jobTitle: 'Backend Dev',
          company: 'SecretCorp',
          location: 'Berlin',
          nextAction: nextAction({ label: 'Send CV', dueDate: '2025-01-01T00:00:00Z' }),
        }),
      ]
      const count = notifyDueApplications(apps, now)
      expect(count).toBe(1)
      expect(ctor).toHaveBeenCalledTimes(1)
      const [title, options] = (ctor as unknown as { mock: { calls: [string, NotificationOptions][] } }).mock.calls[0]
      expect(title).toBe('Hire Desk AI')
      expect(options.body).toBe('Backend Dev — Send CV')
      expect(options.body).not.toContain('SecretCorp')
      expect(options.body).not.toContain('Berlin')
    })

    it('does not re-notify the same app in a second scan', () => {
      const ctor = installNotification('granted')
      const apps = [
        makeApp({
          applicationId: 'dup-1',
          nextAction: nextAction({ dueDate: '2025-01-01T00:00:00Z' }),
        }),
      ]
      expect(notifyDueApplications(apps, now)).toBe(1)
      expect(notifyDueApplications(apps, now)).toBe(0)
      expect(ctor).toHaveBeenCalledTimes(1)
    })

    it('skips apps with no nextAction or no dueDate', () => {
      installNotification('granted')
      const apps = [
        makeApp({ nextAction: null }),
        makeApp({ nextAction: nextAction({ dueDate: null }) }),
        makeApp({ nextAction: nextAction({}) }),
      ]
      expect(notifyDueApplications(apps, now)).toBe(0)
    })

    it('skips future dueDates', () => {
      installNotification('granted')
      const apps = [
        makeApp({ nextAction: nextAction({ dueDate: '2025-12-31T00:00:00Z' }) }),
      ]
      expect(notifyDueApplications(apps, now)).toBe(0)
    })
  })
})
