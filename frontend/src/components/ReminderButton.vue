<script setup lang="ts">
/**
 * ReminderButton — one-shot, in-app browser reminders.
 *
 * - Renders nothing when the Notifications API is unsupported (feature hidden).
 * - NEVER requests permission on mount; only the click handler requests it.
 * - On grant: performs a single scan of the store's applications and shows
 *   due/overdue reminders. On denied/default: does nothing visible.
 * - No polling/intervals, no service workers, no push.
 */
import { ref } from 'vue'
import { useApplicationsStore } from '@/stores/applications'
import {
  isNotificationSupported,
  requestReminderPermission,
  notifyDueApplications,
} from '@/composables/useReminders'

const store = useApplicationsStore()

const supported = isNotificationSupported()
const enabled = ref(false)

async function onEnableReminders(): Promise<void> {
  try {
    const permission = await requestReminderPermission()
    if (permission === 'granted') {
      enabled.value = true
      notifyDueApplications(store.applications)
    }
    // 'denied' / 'default' -> do nothing visible, no error.
  } catch {
    // Never surface internal errors to the user.
  }
}
</script>

<template>
  <button
    v-if="supported"
    type="button"
    class="reminder-button"
    :disabled="enabled"
    @click="onEnableReminders"
  >
    {{ enabled ? 'Reminders on' : 'Enable reminders' }}
  </button>
</template>

<style scoped>
.reminder-button {
  color: #a8a8b3;
  background-color: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: color 0.2s, background-color 0.2s, border-color 0.2s;
}

.reminder-button:hover:not(:disabled) {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.1);
}

.reminder-button:disabled {
  color: #ffffff;
  border-color: #e94560;
  cursor: default;
}
</style>
