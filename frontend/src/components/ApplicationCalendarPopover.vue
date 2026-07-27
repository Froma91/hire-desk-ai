<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, toRef } from 'vue'
import type { Application } from '@/stores/applications'
import { useApplicationCalendar, isToday } from '@/composables/useApplicationCalendar'
import IconChevronLeft from '@/components/icons/IconChevronLeft.vue'
import IconChevronRight from '@/components/icons/IconChevronRight.vue'

const props = defineProps<{
  applications: Application[]
}>()

const emit = defineEmits<{
  close: []
  'select-application': [application: Application]
}>()

// ---------------------------------------------------------------------------
// Calendar state (composable)
// ---------------------------------------------------------------------------

const applicationsRef = toRef(props, 'applications')
const {
  currentYear,
  currentMonth,
  selectedDateKey,
  monthLabel,
  monthGrid,
  weekdayLabels,
  selectedApplications,
  goToPreviousMonth,
  goToNextMonth,
  selectDate,
  countFor,
} = useApplicationCalendar(applicationsRef)

const titleId = `calendar-title-${Math.random().toString(36).slice(2, 9)}`

const dialogRef = ref<HTMLElement | null>(null)

// A stable "now" for the lifetime of this popover, so `today` marking is
// consistent across re-renders.
const now = new Date()

function cellIsToday(dateKey: string | null): boolean {
  return isToday(dateKey, now)
}

function cellIsSelected(dateKey: string | null): boolean {
  return dateKey !== null && dateKey === selectedDateKey.value
}

const selectedDateLabel = computed(() => {
  if (!selectedDateKey.value) return ''
  const parts = selectedDateKey.value.split('-')
  const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

// ---------------------------------------------------------------------------
// Interaction handlers
// ---------------------------------------------------------------------------

function onCellClick(dateKey: string | null): void {
  if (!dateKey) return
  selectDate(dateKey)
}

function onSelectApplication(application: Application): void {
  emit('select-application', application)
}

function close(): void {
  emit('close')
}

function onBackdrop(): void {
  close()
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.stopPropagation()
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // Move focus into the popover for keyboard / screen-reader users.
  dialogRef.value?.focus()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="calendar-backdrop" @click.self="onBackdrop">
    <div
      ref="dialogRef"
      class="calendar-popover"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
    >
      <!-- Header: month navigation -->
      <header class="calendar-header">
        <button
          type="button"
          class="calendar-nav-btn"
          aria-label="Previous month"
          @click="goToPreviousMonth"
        >
          <IconChevronLeft size="1.15rem" />
        </button>
        <h2 :id="titleId" class="calendar-title" aria-live="polite">
          {{ monthLabel }}
        </h2>
        <button
          type="button"
          class="calendar-nav-btn"
          aria-label="Next month"
          @click="goToNextMonth"
        >
          <IconChevronRight size="1.15rem" />
        </button>
        <button
          type="button"
          class="calendar-close"
          aria-label="Close calendar"
          @click="close"
        >
          &times;
        </button>
      </header>

      <!-- Weekday headers -->
      <div class="calendar-weekdays" aria-hidden="true">
        <span v-for="label in weekdayLabels" :key="label" class="calendar-weekday">
          {{ label }}
        </span>
      </div>

      <!-- Grid -->
      <div
        class="calendar-grid"
        role="grid"
        :aria-label="`${monthLabel} calendar`"
      >
        <div
          v-for="(week, wIndex) in monthGrid"
          :key="`week-${currentYear}-${currentMonth}-${wIndex}`"
          class="calendar-week"
          role="row"
        >
          <template v-for="(cell, cIndex) in week" :key="`cell-${wIndex}-${cIndex}`">
            <span
              v-if="cell.dateKey === null"
              class="calendar-cell calendar-cell--empty"
              role="gridcell"
              aria-hidden="true"
            ></span>
            <button
              v-else
              type="button"
              class="calendar-cell calendar-cell--day"
              :class="{
                'calendar-cell--today': cellIsToday(cell.dateKey),
                'calendar-cell--selected': cellIsSelected(cell.dateKey),
                'calendar-cell--has-events': countFor(cell.dateKey) > 0,
              }"
              role="gridcell"
              :aria-selected="cellIsSelected(cell.dateKey)"
              :aria-label="
                `${cell.day}${cellIsToday(cell.dateKey) ? ', today' : ''}` +
                (countFor(cell.dateKey) > 0
                  ? `, ${countFor(cell.dateKey)} application${countFor(cell.dateKey) > 1 ? 's' : ''} submitted`
                  : '')
              "
              @click="onCellClick(cell.dateKey)"
            >
              <span class="calendar-cell-day">{{ cell.day }}</span>
              <span
                v-if="countFor(cell.dateKey) > 0"
                class="calendar-cell-indicator"
                aria-hidden="true"
              >
                <span v-if="countFor(cell.dateKey) > 1" class="calendar-cell-count">
                  {{ countFor(cell.dateKey) }}
                </span>
                <span v-else class="calendar-cell-dot"></span>
              </span>
            </button>
          </template>
        </div>
      </div>

      <!-- Selected-day application list -->
      <section
        v-if="selectedDateKey"
        class="calendar-day-list"
        aria-label="Applications for selected date"
      >
        <h3 class="calendar-day-list-title">{{ selectedDateLabel }}</h3>
        <ul v-if="selectedApplications.length" class="calendar-app-list">
          <li
            v-for="app in selectedApplications"
            :key="app.applicationId"
            class="calendar-app-item"
          >
            <button
              type="button"
              class="calendar-app-btn"
              @click="onSelectApplication(app)"
            >
              <span class="calendar-app-main">
                <span class="calendar-app-title">{{ app.jobTitle }}</span>
                <span v-if="app.company" class="calendar-app-company">{{ app.company }}</span>
              </span>
              <span class="calendar-app-status">
                <span
                  class="calendar-app-badge"
                  :class="`calendar-app-badge--${app.status.toLowerCase()}`"
                  aria-hidden="true"
                ></span>
                <span class="calendar-app-status-text">{{ app.status }}</span>
              </span>
            </button>
          </li>
        </ul>
        <p v-else class="calendar-empty">No applications submitted on this date.</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.calendar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background-color: rgba(7, 26, 54, 0.45);
}

.calendar-popover {
  width: 100%;
  max-width: 24rem;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  color: var(--color-text-primary);
}

.calendar-popover:focus {
  outline: none;
}

/* --- Header ---------------------------------------------------------------- */
.calendar-header {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: var(--space-2);
}

.calendar-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-primary);
  text-align: center;
  margin: 0;
}

.calendar-nav-btn,
.calendar-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background-color: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.calendar-close {
  border-color: transparent;
  font-size: 1.4rem;
  line-height: 1;
}

.calendar-nav-btn:hover,
.calendar-close:hover {
  background-color: var(--color-surface-muted);
  color: var(--color-text-primary);
}

.calendar-nav-btn:focus-visible,
.calendar-close:focus-visible,
.calendar-cell--day:focus-visible,
.calendar-app-btn:focus-visible {
  outline: 2px solid var(--color-blue-600);
  outline-offset: 2px;
}

/* --- Weekday headers ------------------------------------------------------- */
.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.calendar-weekday {
  text-align: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-text-secondary);
  padding: var(--space-1) 0;
}

/* --- Grid ------------------------------------------------------------------ */
.calendar-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.calendar-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.calendar-cell {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: var(--radius-sm);
}

.calendar-cell--empty {
  background-color: transparent;
}

.calendar-cell--day {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  border: 1px solid transparent;
  background-color: var(--color-surface-muted);
  color: var(--color-text-primary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.calendar-cell--day:hover {
  background-color: var(--color-blue-100);
}

.calendar-cell--has-events {
  font-weight: 700;
}

.calendar-cell--today {
  border-color: var(--color-blue-500);
}

.calendar-cell--selected {
  border-color: var(--color-blue-600);
  box-shadow: 0 0 0 2px var(--color-blue-600) inset;
  background-color: var(--color-blue-100);
}

.calendar-cell-day {
  line-height: 1;
}

.calendar-cell-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 0.9rem;
}

.calendar-cell-dot {
  width: 0.35rem;
  height: 0.35rem;
  border-radius: 50%;
  background-color: var(--color-applied);
}

.calendar-cell-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1rem;
  height: 0.95rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  font-size: 0.6rem;
  font-weight: 700;
  color: var(--color-text-inverse);
  background-color: var(--color-applied);
}

/* --- Selected-day list ----------------------------------------------------- */
.calendar-day-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.calendar-day-list-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-navy-800);
  margin: 0;
}

.calendar-app-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.calendar-app-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background-color: var(--color-surface);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--transition-fast), border-color var(--transition-fast);
}

.calendar-app-btn:hover {
  background-color: var(--color-surface-muted);
  border-color: var(--color-border-strong);
}

.calendar-app-main {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.calendar-app-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.calendar-app-company {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.calendar-app-status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.calendar-app-badge {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  background-color: var(--color-border-strong);
}

.calendar-app-status-text {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-text-secondary);
}

.calendar-app-badge--wishlist {
  background-color: var(--color-wishlist);
}
.calendar-app-badge--applied {
  background-color: var(--color-applied);
}
.calendar-app-badge--interview {
  background-color: var(--color-interview);
}
.calendar-app-badge--offer {
  background-color: var(--color-offer);
}
.calendar-app-badge--rejected {
  background-color: var(--color-rejected);
}

.calendar-empty {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  font-style: italic;
  margin: 0;
}

/* --- Motion ---------------------------------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  .calendar-nav-btn,
  .calendar-close,
  .calendar-cell--day,
  .calendar-app-btn {
    transition: none;
  }
}
</style>
