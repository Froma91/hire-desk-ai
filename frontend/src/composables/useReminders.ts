/**
 * useReminders — pure, unit-testable browser-reminder helpers.
 *
 * Frontend-only enhancement using the browser Notifications API while the app
 * is open. No service workers, no push, no polling, no new dependencies.
 *
 * Design notes:
 * - All sessionStorage access is wrapped in try/catch so a throwing storage
 *   (private mode, disabled storage) never breaks the app.
 * - Notification construction is wrapped in try/catch so a single failure
 *   never blocks the remaining notifications or the app.
 * - Notification bodies expose ONLY the job title and the action label — never
 *   company, location, ids, AWS details, or error text.
 */

import type { Application } from '@/stores/applications'

/**
 * True when running in a browser that exposes the Notifications API.
 */
export function isNotificationSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

/**
 * True when the given ISO date string is due now or overdue relative to `now`.
 * Returns false for missing/empty/unparseable dates.
 */
export function isDueOrOverdue(
  dueDate: string | null | undefined,
  now: Date,
): boolean {
  if (!dueDate) {
    return false
  }
  const due = new Date(dueDate).getTime()
  if (Number.isNaN(due)) {
    return false
  }
  return due <= now.getTime()
}

/**
 * sessionStorage key used to dedupe notifications per application per session.
 */
export function sessionKey(applicationId: string): string {
  return `hda:notified:${applicationId}`
}

/**
 * True when the given application has already been notified this session.
 * Never throws — a failing sessionStorage yields `false`.
 */
export function alreadyNotified(applicationId: string): boolean {
  try {
    return window.sessionStorage.getItem(sessionKey(applicationId)) !== null
  } catch {
    return false
  }
}

/**
 * Marks the given application as notified for this session.
 * Never throws — a failing sessionStorage is silently ignored.
 */
export function markNotified(applicationId: string): void {
  try {
    window.sessionStorage.setItem(sessionKey(applicationId), '1')
  } catch {
    // ignore — dedupe is best-effort
  }
}

/**
 * Requests notification permission from the user.
 *
 * Supports both the modern promise-based form and the legacy callback form
 * defensively. Never throws; resolves with the resulting permission (or
 * 'denied' when unsupported / on error).
 */
export function requestReminderPermission(): Promise<NotificationPermission> {
  if (!isNotificationSupported()) {
    return Promise.resolve('denied')
  }
  try {
    const result = Notification.requestPermission((perm) => perm)
    // Modern browsers return a Promise.
    if (result && typeof (result as Promise<NotificationPermission>).then === 'function') {
      return (result as Promise<NotificationPermission>).catch(() => 'denied' as NotificationPermission)
    }
    // Legacy callback form: fall back to the current permission value.
    return Promise.resolve(
      (result as unknown as NotificationPermission) ?? Notification.permission,
    )
  } catch {
    return Promise.resolve('denied')
  }
}

/**
 * Scans applications and shows a notification for each one whose nextAction is
 * due/overdue and has not already been notified this session.
 *
 * Only runs when the Notifications API is supported AND permission is granted.
 * Notification body contains ONLY `${jobTitle} — ${label}`.
 *
 * @returns the number of notifications shown.
 */
export function notifyDueApplications(
  apps: Application[],
  now: Date = new Date(),
): number {
  if (!isNotificationSupported() || Notification.permission !== 'granted') {
    return 0
  }

  let shown = 0

  for (const app of apps) {
    const nextAction = app.nextAction
    if (!nextAction || !nextAction.dueDate) {
      continue
    }
    if (!isDueOrOverdue(nextAction.dueDate, now)) {
      continue
    }
    if (alreadyNotified(app.applicationId)) {
      continue
    }

    try {
      // Body exposes ONLY the job title and action label.
      // eslint-disable-next-line no-new
      new Notification('Hire Desk AI', {
        body: `${app.jobTitle} — ${nextAction.label}`,
      })
      markNotified(app.applicationId)
      shown += 1
    } catch {
      // One failure must not block the rest or the app.
    }
  }

  return shown
}
