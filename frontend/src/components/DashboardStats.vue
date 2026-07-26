<script setup lang="ts">
export interface DashboardStatsData {
  total: number
  byStatus: Record<string, number>
  currentWeek: number
}

defineProps<{
  stats: DashboardStatsData
}>()
</script>

<template>
  <div class="dashboard-stats" role="region" aria-label="Dashboard statistics">
    <!-- Summary cards row -->
    <div class="stats-summary">
      <div class="stats-card stats-card--primary">
        <span class="stats-card-value">{{ stats.total }}</span>
        <span class="stats-card-label">Total Applications</span>
      </div>
      <div class="stats-card stats-card--accent">
        <span class="stats-card-value">{{ stats.currentWeek }}</span>
        <span class="stats-card-label">This Week</span>
      </div>
    </div>

    <!-- Per-status breakdown -->
    <div class="stats-breakdown">
      <h3 class="stats-breakdown-title">By Status</h3>
      <div class="stats-status-grid">
        <div
          v-for="(count, status) in stats.byStatus"
          :key="status"
          class="stats-status-item"
          :aria-label="`${status}: ${count} applications`"
        >
          <span class="stats-status-count">{{ count }}</span>
          <span class="stats-status-label">{{ status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-stats {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
}

.stats-summary {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stats-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.25rem 2rem;
  border-radius: 8px;
  min-width: 10rem;
  flex: 1;
}

.stats-card--primary {
  background-color: #1a1a2e;
  color: #ffffff;
}

.stats-card--accent {
  background-color: #e94560;
  color: #ffffff;
}

.stats-card-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.stats-card-label {
  font-size: 0.85rem;
  opacity: 0.85;
  margin-top: 0.25rem;
}

.stats-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stats-breakdown-title {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.stats-status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.75rem;
}

.stats-status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem 0.75rem;
  background-color: #f3f4f6;
  border-radius: 6px;
  text-align: center;
}

.stats-status-count {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
}

.stats-status-label {
  font-size: 0.8rem;
  color: #6b7280;
  margin-top: 0.25rem;
  text-transform: capitalize;
}

/* Responsive */
@media (max-width: 600px) {
  .stats-summary {
    flex-direction: column;
  }

  .stats-card {
    min-width: auto;
  }

  .stats-status-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
