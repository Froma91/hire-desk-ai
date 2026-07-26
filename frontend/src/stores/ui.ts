/**
 * UI store — manages notification state.
 *
 * - Only one notification visible at a time (new replaces old)
 * - Auto-dismiss after 5 seconds
 * - Clears pending timers when notifications are replaced or manually dismissed
 * - Never exposes technical stack traces or AWS internals to the user
 *
 * Requirements: 8.3, 8.4, 8.5
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'

export type NotificationType = 'success' | 'error' | 'info' | 'warning'

export interface Notification {
  id: string
  message: string
  type: NotificationType
}

const DISMISS_DELAY_MS = 5_000

export const useUiStore = defineStore('ui', () => {
  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const notifications = ref<Notification[]>([])

  // Track active timer so we can clear it on replacement or manual dismiss
  let dismissTimer: ReturnType<typeof setTimeout> | null = null

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  function generateId(): string {
    return `notif-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  }

  function clearTimer(): void {
    if (dismissTimer !== null) {
      clearTimeout(dismissTimer)
      dismissTimer = null
    }
  }

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  /**
   * Show a notification. Replaces any currently visible notification.
   * Auto-dismisses after 5 seconds.
   *
   * @param message - User-facing message (must not contain stack traces or AWS details)
   * @param type - Notification severity
   */
  function notify(message: string, type: NotificationType = 'info'): void {
    // Clear any pending timer from the previous notification
    clearTimer()

    const id = generateId()

    // Replace the array — only one notification visible at a time
    notifications.value = [{ id, message, type }]

    // Schedule auto-dismiss
    dismissTimer = setTimeout(() => {
      clearNotification(id)
    }, DISMISS_DELAY_MS)
  }

  /**
   * Manually dismiss a notification by ID.
   * Clears the pending auto-dismiss timer if it belongs to this notification.
   */
  function clearNotification(id: string): void {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
      // If we just removed the notification that the timer was targeting, clear it
      clearTimer()
    }
  }

  return {
    notifications,
    notify,
    clearNotification,
  }
})
