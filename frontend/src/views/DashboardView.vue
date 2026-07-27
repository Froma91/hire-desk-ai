<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useStatsStore } from '@/stores/stats'
import DashboardStats from '@/components/DashboardStats.vue'
import ApplicationDetailsModal from '@/components/ApplicationDetailsModal.vue'
import type { Application } from '@/stores/applications'

const statsStore = useStatsStore()

// Application selected from the calendar popover — opens the shared modal.
const selectedApplication = ref<Application | null>(null)

// Track whether the initial fetch has completed
const initialized = ref(false)
const fetchFailed = ref(false)

async function loadStats(): Promise<void> {
  fetchFailed.value = false
  try {
    await statsStore.fetchStats()
  } catch {
    fetchFailed.value = true
  } finally {
    initialized.value = true
  }
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="dashboard-view">
    <h1 class="dashboard-view-title">Dashboard</h1>

    <!-- Loading state -->
    <div v-if="statsStore.loading && !initialized" class="dashboard-view-loading" aria-live="polite">
      <div class="dashboard-view-spinner" aria-hidden="true"></div>
      <span>Loading statistics...</span>
    </div>

    <!-- Error state — no stale stats shown -->
    <div
      v-else-if="fetchFailed"
      class="dashboard-view-error"
      role="alert"
      aria-live="assertive"
    >
      <p class="dashboard-view-error-message">
        {{ statsStore.error ?? 'Unable to load statistics. Please try again.' }}
      </p>
      <button class="dashboard-view-retry" @click="loadStats">
        Retry
      </button>
    </div>

    <!-- Success state — render DashboardStats component -->
    <DashboardStats
      v-else-if="initialized && !fetchFailed && statsStore.stats"
      :stats="statsStore.stats"
      @select-application="selectedApplication = $event"
    />

    <!-- Shared details modal, opened from the calendar popover -->
    <ApplicationDetailsModal
      v-if="selectedApplication"
      :application="selectedApplication"
      @close="selectedApplication = null"
    />
  </div>
</template>

<style scoped>
.dashboard-view {
  width: 100%;
  max-width: 64rem;
  margin: 0 auto;
}

.dashboard-view-title {
  font-family: var(--font-serif);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-6);
}

.dashboard-view-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  gap: var(--space-4);
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.dashboard-view-spinner {
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

.dashboard-view-error {
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

.dashboard-view-error-message {
  color: #991b1b;
  font-size: 0.95rem;
  margin: 0;
}

.dashboard-view-retry {
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

.dashboard-view-retry:hover {
  background-color: var(--color-blue-700);
}

@media (prefers-reduced-motion: reduce) {
  .dashboard-view-spinner {
    animation: none;
  }
}
</style>
