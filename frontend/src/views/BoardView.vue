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
  font-family: var(--font-serif);
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-5);
}

.board-view-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  gap: var(--space-4);
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.board-view-spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-blue-600);
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
  gap: var(--space-4);
  padding: var(--space-8) var(--space-4);
  background-color: var(--color-rejected-soft);
  border: 1px solid var(--color-rejected);
  border-radius: var(--radius-md);
  text-align: center;
}

.board-view-error-message {
  color: #991b1b;
  font-size: 0.95rem;
  margin: 0;
}

.board-view-retry {
  min-height: 44px;
  padding: 0.6rem 1.5rem;
  background-color: var(--color-blue-600);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.board-view-retry:hover {
  background-color: var(--color-blue-700);
}

@media (prefers-reduced-motion: reduce) {
  .board-view-spinner {
    animation: none;
  }
}
</style>
