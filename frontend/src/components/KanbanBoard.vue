<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useApplicationsStore, type ApplicationStatus, type Application } from '@/stores/applications'
import { useUiStore } from '@/stores/ui'
import KanbanColumn from '@/components/KanbanColumn.vue'
import ApplicationDetailsModal from '@/components/ApplicationDetailsModal.vue'

const applicationsStore = useApplicationsStore()
const uiStore = useUiStore()

// ---------------------------------------------------------------------------
// Column definitions (ordered)
// ---------------------------------------------------------------------------

const STATUSES: ApplicationStatus[] = [
  'Wishlist',
  'Applied',
  'Interview',
  'Offer',
  'Rejected',
]

// ---------------------------------------------------------------------------
// Derived state: applications grouped by status
// ---------------------------------------------------------------------------

function applicationsByStatus(status: ApplicationStatus): Application[] {
  return applicationsStore.applications.filter((app) => app.status === status)
}

// ---------------------------------------------------------------------------
// Pending status updates — prevents duplicate requests for the same card
// ---------------------------------------------------------------------------

const pendingUpdates = reactive(new Set<string>())

// ---------------------------------------------------------------------------
// Details modal state
// ---------------------------------------------------------------------------

const selectedApplication = ref<Application | null>(null)

// ---------------------------------------------------------------------------
// Drop handler
// ---------------------------------------------------------------------------

async function handleDrop(payload: { applicationId: string; status: ApplicationStatus }): Promise<void> {
  const { applicationId, status: destinationStatus } = payload

  // Ignore if already in the target column
  const app = applicationsStore.applications.find((a) => a.applicationId === applicationId)
  if (!app || app.status === destinationStatus) {
    return
  }

  // Prevent duplicate requests for the same card
  if (pendingUpdates.has(applicationId)) {
    return
  }

  pendingUpdates.add(applicationId)

  try {
    await applicationsStore.updateStatus(applicationId, destinationStatus)
  } catch {
    // The store already rolled back the optimistic update.
    // Show a safe error notification.
    uiStore.notify('Failed to update status. Please try again.', 'error')
  } finally {
    pendingUpdates.delete(applicationId)
  }
}
</script>

<template>
  <div class="kanban-board" role="region" aria-label="Application board">
    <KanbanColumn
      v-for="status in STATUSES"
      :key="status"
      :status="status"
      :applications="applicationsByStatus(status)"
      @drop="handleDrop"
      @open="selectedApplication = $event"
    />

    <ApplicationDetailsModal
      v-if="selectedApplication"
      :application="selectedApplication"
      @close="selectedApplication = null"
    />
  </div>
</template>

<style scoped>
.kanban-board {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1rem;
  min-height: 24rem;
}

/* Responsive: ensure horizontal scrolling on smaller screens */
@media (max-width: 768px) {
  .kanban-board {
    padding-bottom: 0.75rem;
  }
}
</style>
