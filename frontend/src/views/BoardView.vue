<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useApplicationsStore } from '@/stores/applications'
import KanbanBoard from '@/components/KanbanBoard.vue'

const applicationsStore = useApplicationsStore()

// Track whether the initial fetch has completed (success or failure)
const initialized = ref(false)
const fetchFailed = ref(false)

async function loadApplications(): Promise<void> {
  fetchFailed.value = false
  try {
    await applicationsStore.fetchAll()
  } catch {
    fetchFailed.value = true
  } finally {
    initialized.value = true
  }
}

onMounted(() => {
  loadApplications()
})
</script>

<template>
  <div class="board-view">
    <h1 class="board-view-title">Application Board</h1>

    <!-- Loading state -->
    <div v-if="applicationsStore.loading && !initialized" class="board-view-loading" aria-live="polite">
      <div class="board-view-spinner" aria-hidden="true"></div>
      <span>Loading applications...</span>
    </div>

    <!-- Error state — no stale data shown -->
    <div
      v-else-if="fetchFailed"
      class="board-view-error"
      role="alert"
      aria-live="assertive"
    >
      <p class="board-view-error-message">
        {{ applicationsStore.error ?? 'Unable to load applications. Please try again.' }}
      </p>
      <button class="board-view-retry" @click="loadApplications">
        Retry
      </button>
    </div>

    <!-- Success state (including empty response → five empty columns) -->
    <KanbanBoard v-else-if="initialized && !fetchFailed" />
  </div>
</template>

<style scoped>
.board-view {
  width: 100%;
}

.board-view-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 1.25rem;
}

.board-view-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 1rem;
  gap: 1rem;
  color: #6b7280;
  font-size: 0.95rem;
}

.board-view-spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid #e5e7eb;
  border-top-color: #e94560;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.board-view-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem 1rem;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  text-align: center;
}

.board-view-error-message {
  color: #991b1b;
  font-size: 0.95rem;
  margin: 0;
}

.board-view-retry {
  padding: 0.5rem 1.25rem;
  background-color: #e94560;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.board-view-retry:hover {
  background-color: #d63851;
}
</style>
