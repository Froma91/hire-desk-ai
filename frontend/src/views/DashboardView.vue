<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useStatsStore } from '@/stores/stats'
import DashboardStats from '@/components/DashboardStats.vue'

const statsStore = useStatsStore()

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
    />
  </div>
</template>

<style scoped>
.dashboard-view {
  width: 100%;
  max-width: 60rem;
  margin: 0 auto;
}

.dashboard-view-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 1.5rem;
}

.dashboard-view-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 1rem;
  gap: 1rem;
  color: #6b7280;
  font-size: 0.95rem;
}

.dashboard-view-spinner {
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

.dashboard-view-error {
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

.dashboard-view-error-message {
  color: #991b1b;
  font-size: 0.95rem;
  margin: 0;
}

.dashboard-view-retry {
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

.dashboard-view-retry:hover {
  background-color: #d63851;
}
</style>
