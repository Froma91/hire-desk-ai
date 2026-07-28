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
import IconBell from '@/components/icons/IconBell.vue'

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
    <IconBell class="reminder-button-icon" size="1.05em" />
    {{ enabled ? 'Reminders on' : 'Enable reminders' }}
  </button>
</template>

<style scoped>
.reminder-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: rgba(255, 255, 255, 0.82);
  background-color: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.24);
  padding: 0.5rem 0.85rem;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: color var(--transition-fast), background-color var(--transition-fast),
    border-color var(--transition-fast);
}

.reminder-button-icon {
  flex-shrink: 0;
}

.reminder-button:hover:not(:disabled) {
  color: var(--color-text-inverse);
  background-color: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.4);
}

.reminder-button:disabled {
  color: var(--color-text-inverse);
  background-color: rgba(67, 136, 242, 0.28);
  border-color: var(--color-blue-500);
  cursor: default;
}
</style>
