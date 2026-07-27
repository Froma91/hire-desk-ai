<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import IconBriefcase from '@/components/icons/IconBriefcase.vue'
import IconCalendar from '@/components/icons/IconCalendar.vue'
import IconBookmark from '@/components/icons/IconBookmark.vue'
import IconSend from '@/components/icons/IconSend.vue'
import IconUser from '@/components/icons/IconUser.vue'
import IconStar from '@/components/icons/IconStar.vue'
import IconCircleX from '@/components/icons/IconCircleX.vue'
import ApplicationCalendarPopover from '@/components/ApplicationCalendarPopover.vue'
import { useApplicationsStore, type Application } from '@/stores/applications'
import { countAppliedThisWeek } from '@/composables/useApplicationCalendar'

export interface DashboardStatsData {
  total: number
  byStatus: Record<string, number>
  currentWeek: number
}

defineProps<{
  stats: DashboardStatsData
}>()

const emit = defineEmits<{
  'select-application': [application: Application]
}>()

const applicationsStore = useApplicationsStore()

// The "Applied This Week" value is derived from the applications store — the
// count of applications whose FIRST 'Applied' event falls in the current local
// week — NOT the backend `stats.currentWeek`.
const appliedThisWeek = computed(() =>
  countAppliedThisWeek(applicationsStore.applications),
)

const calendarOpen = ref(false)

/**
 * Open/close the calendar popover. On first open, lazily load applications if
 * the store is empty (reusing the existing store action — no new endpoint).
 * The fetch is intentionally lazy (not on mount) so the dashboard's existing
 * stats-only load flow and its tests remain intact.
 */
async function toggleCalendar(): Promise<void> {
  calendarOpen.value = !calendarOpen.value
  if (calendarOpen.value && applicationsStore.applications.length === 0) {
    try {
      await applicationsStore.fetchAll()
    } catch {
      // Applications failing to load must not break the dashboard; the calendar
      // simply shows an empty month.
    }
  }
}

function closeCalendar(): void {
  calendarOpen.value = false
}

function onSelectApplication(application: Application): void {
  // Bubble up so the parent (DashboardView) can open the shared details modal.
  emit('select-application', application)
}

interface StatusVisual {
  icon: Component
  key: string
}

// Map each known status name to an icon + a CSS modifier key.
// Unknown keys fall back to a neutral style so the component never crashes.
const STATUS_VISUALS: Record<string, StatusVisual> = {
  Wishlist: { icon: IconBookmark, key: 'wishlist' },
  Applied: { icon: IconSend, key: 'applied' },
  Interview: { icon: IconUser, key: 'interview' },
  Offer: { icon: IconStar, key: 'offer' },
  Rejected: { icon: IconCircleX, key: 'rejected' },
}

const DEFAULT_VISUAL: StatusVisual = { icon: IconBriefcase, key: 'neutral' }

function visualFor(status: string): StatusVisual {
  return STATUS_VISUALS[status] ?? DEFAULT_VISUAL
}
</script>

<template>
  <div class="dashboard-stats" role="region" aria-label="Dashboard statistics">
    <!-- Summary cards row -->
    <div class="stats-summary">
      <div class="stats-card stats-card--primary">
        <span class="stats-card-icon" aria-hidden="true">
          <IconBriefcase size="1.5rem" />
        </span>
        <span class="stats-card-value">{{ stats.total }}</span>
        <span class="stats-card-label">Total Applications</span>
      </div>
      <div class="stats-card stats-card--accent">
        <button
          type="button"
          class="stats-card-calendar-btn"
          aria-label="Open applications calendar"
          :aria-expanded="calendarOpen"
          @click="toggleCalendar"
        >
          <IconCalendar size="1.35rem" />
        </button>
        <span class="stats-card-value">{{ appliedThisWeek }}</span>
        <span class="stats-card-label">Applied This Week</span>
      </div>
    </div>

    <!-- Interactive application calendar (frontend-only) -->
    <ApplicationCalendarPopover
      v-if="calendarOpen"
      :applications="applicationsStore.applications"
      @close="closeCalendar"
      @select-application="onSelectApplication"
    />

    <!-- Per-status breakdown -->
    <div class="stats-breakdown">
      <h3 class="stats-breakdown-title">By Status</h3>
      <div class="stats-status-grid">
        <div
          v-for="(count, status) in stats.byStatus"
          :key="status"
          class="stats-status-item"
          :class="`stats-status-item--${visualFor(String(status)).key}`"
          :aria-label="`${status}: ${count} applications`"
        >
          <span class="stats-status-icon" aria-hidden="true">
            <component :is="visualFor(String(status)).icon" size="1.35rem" />
          </span>
          <span class="stats-status-count">{{ count }}</span>
          <span class="stats-status-label">{{ status }}</span>
          <span class="stats-status-accent" aria-hidden="true"></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  width: 100%;
}

/* --- Summary cards --------------------------------------------------------- */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.stats-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

/* Discreet CSS-only decorative pattern */
.stats-card::after {
  content: '';
  position: absolute;
  top: -40%;
  right: -10%;
  width: 12rem;
  height: 12rem;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0) 70%);
  pointer-events: none;
}

.stats-card--primary {
  background: linear-gradient(135deg, var(--color-navy-900) 0%, var(--color-navy-800) 100%);
}

.stats-card--accent {
  background: linear-gradient(135deg, var(--color-blue-600) 0%, var(--color-blue-500) 100%);
}

.stats-card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--radius-md);
  background-color: rgba(255, 255, 255, 0.16);
  color: var(--color-text-inverse);
}

.stats-card-calendar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border: none;
  border-radius: var(--radius-md);
  background-color: rgba(255, 255, 255, 0.16);
  color: var(--color-text-inverse);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.stats-card-calendar-btn:hover {
  background-color: rgba(255, 255, 255, 0.28);
}

.stats-card-calendar-btn:focus-visible {
  outline: 2px solid var(--color-text-inverse);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .stats-card-calendar-btn {
    transition: none;
  }
}

.stats-card-value {
  font-size: 2.75rem;
  font-weight: 800;
  line-height: 1.05;
}

.stats-card-label {
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.88;
}

/* --- Breakdown ------------------------------------------------------------- */
.stats-breakdown {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stats-breakdown-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.stats-status-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
}

.stats-status-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  padding: var(--space-4);
  padding-bottom: calc(var(--space-4) + 4px);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.stats-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  background-color: var(--color-surface-muted);
}

.stats-status-count {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1.1;
}

.stats-status-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.stats-status-accent {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 4px;
  background-color: var(--color-border-strong);
}

/* Per-status colors */
.stats-status-item--wishlist .stats-status-icon {
  color: var(--color-wishlist);
  background-color: var(--color-wishlist-soft);
}
.stats-status-item--wishlist .stats-status-accent {
  background-color: var(--color-wishlist);
}

.stats-status-item--applied .stats-status-icon {
  color: var(--color-applied);
  background-color: var(--color-applied-soft);
}
.stats-status-item--applied .stats-status-accent {
  background-color: var(--color-applied);
}

.stats-status-item--interview .stats-status-icon {
  color: var(--color-interview);
  background-color: var(--color-interview-soft);
}
.stats-status-item--interview .stats-status-accent {
  background-color: var(--color-interview);
}

.stats-status-item--offer .stats-status-icon {
  color: var(--color-offer);
  background-color: var(--color-offer-soft);
}
.stats-status-item--offer .stats-status-accent {
  background-color: var(--color-offer);
}

.stats-status-item--rejected .stats-status-icon {
  color: var(--color-rejected);
  background-color: var(--color-rejected-soft);
}
.stats-status-item--rejected .stats-status-accent {
  background-color: var(--color-rejected);
}

/* --- Responsive ------------------------------------------------------------ */
@media (max-width: 900px) {
  .stats-status-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-summary {
    grid-template-columns: 1fr;
  }

  .stats-status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
