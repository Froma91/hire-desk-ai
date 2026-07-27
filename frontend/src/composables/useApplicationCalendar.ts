/**
 * useApplicationCalendar — pure, unit-testable date/calendar helpers plus a
 * small reactive factory used by ApplicationCalendarPopover.vue.
 *
 * Design decisions:
 * - The "application date" is the FIRST `statusHistory` entry whose status is
 *   'Applied'. `createdAt` / `updatedAt` are never used for this.
 * - All date-key math is done in LOCAL time (getFullYear/getMonth/getDate),
 *   never via toISOString(), so a late-in-day UTC timestamp lands on the
 *   correct local calendar day.
 * - The calendar week is MONDAY-START (Mon..Sun). This convention is used both
 *   for "current week" counting and for the leading empty cells in the grid.
 * - All helpers are defensive: malformed/missing data is ignored and never
 *   throws.
 *
 * This module has no side effects and performs no I/O.
 */

import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { Application } from '@/stores/applications'

// ---------------------------------------------------------------------------
// Applied-date extraction
// ---------------------------------------------------------------------------

/**
 * Return the timestamp of the FIRST status-history entry with status
 * 'Applied', or null when there is none / the data is malformed.
 *
 * Guards against: missing/null/non-array statusHistory, non-object entries,
 * and entries whose `status` or `timestamp` is missing / empty / non-string.
 */
export function getAppliedAt(app: Application | null | undefined): string | null {
  if (!app || typeof app !== 'object') return null
  const history = (app as Application).statusHistory
  if (!Array.isArray(history)) return null

  for (const entry of history) {
    if (!entry || typeof entry !== 'object') continue
    const status = (entry as { status?: unknown }).status
    const timestamp = (entry as { timestamp?: unknown }).timestamp
    if (typeof status !== 'string' || status.trim() !== 'Applied') continue
    if (typeof timestamp !== 'string' || timestamp.trim().length === 0) continue
    return timestamp
  }
  return null
}

// ---------------------------------------------------------------------------
// Local date-key helpers
// ---------------------------------------------------------------------------

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

/**
 * Build a local-timezone date key (YYYY-MM-DD) from a Date using local getters.
 */
export function dateToLocalKey(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

/**
 * Parse an ISO timestamp and produce a LOCAL date key YYYY-MM-DD.
 * Uses local getFullYear/getMonth/getDate (NOT UTC/toISOString).
 * Returns null for invalid / non-string input.
 */
export function toLocalDateKey(timestamp: string | null | undefined): string | null {
  if (typeof timestamp !== 'string' || timestamp.trim().length === 0) return null
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return null
  return dateToLocalKey(date)
}

// ---------------------------------------------------------------------------
// Grouping
// ---------------------------------------------------------------------------

/**
 * Group applications by the LOCAL date of their FIRST 'Applied' event.
 * Applications without a valid Applied event are excluded entirely.
 */
export function groupApplicationsByAppliedDate(
  apps: Application[] | null | undefined,
): Map<string, Application[]> {
  const map = new Map<string, Application[]>()
  if (!Array.isArray(apps)) return map

  for (const app of apps) {
    const appliedAt = getAppliedAt(app)
    if (!appliedAt) continue
    const key = toLocalDateKey(appliedAt)
    if (!key) continue
    const bucket = map.get(key)
    if (bucket) {
      bucket.push(app)
    } else {
      map.set(key, [app])
    }
  }
  return map
}

// ---------------------------------------------------------------------------
// Week helpers (Monday-start)
// ---------------------------------------------------------------------------

/**
 * Return a new Date set to local midnight (00:00:00.000) of the same day.
 */
function localMidnight(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

/**
 * Return local midnight of the Monday that starts the week containing `date`.
 */
export function startOfLocalWeek(date: Date): Date {
  const midnight = localMidnight(date)
  // getDay(): 0=Sun..6=Sat. Monday-start offset: Mon->0 ... Sun->6.
  const offset = (midnight.getDay() + 6) % 7
  midnight.setDate(midnight.getDate() - offset)
  return midnight
}

/**
 * Parse a date key (YYYY-MM-DD) into a LOCAL Date at midnight, or null.
 */
export function localKeyToDate(dateKey: string): Date | null {
  if (typeof dateKey !== 'string') return null
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateKey.trim())
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const date = new Date(year, month - 1, day)
  // Reject overflow (e.g. 2025-02-31 -> March).
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null
  }
  return date
}

/**
 * Is the given date-key or Date within the current LOCAL calendar week
 * (Monday-start) relative to `now`?
 */
export function isInCurrentLocalWeek(
  value: string | Date,
  now: Date = new Date(),
): boolean {
  let target: Date | null
  if (value instanceof Date) {
    target = Number.isNaN(value.getTime()) ? null : localMidnight(value)
  } else {
    target = localKeyToDate(value)
  }
  if (!target) return false

  const weekStart = startOfLocalWeek(now)
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekEnd.getDate() + 7) // exclusive upper bound (next Monday)

  const t = target.getTime()
  return t >= weekStart.getTime() && t < weekEnd.getTime()
}

/**
 * Count applications whose FIRST 'Applied' event falls in the current LOCAL
 * week (Monday-start). Repeated Applied events use the FIRST only.
 */
export function countAppliedThisWeek(
  apps: Application[] | null | undefined,
  now: Date = new Date(),
): number {
  if (!Array.isArray(apps)) return 0
  let count = 0
  for (const app of apps) {
    const appliedAt = getAppliedAt(app)
    if (!appliedAt) continue
    const key = toLocalDateKey(appliedAt)
    if (!key) continue
    if (isInCurrentLocalWeek(key, now)) count += 1
  }
  return count
}

// ---------------------------------------------------------------------------
// Calendar-grid helpers
// ---------------------------------------------------------------------------

export interface MonthGridCell {
  /** Local date key YYYY-MM-DD, or null for a leading/trailing empty cell. */
  dateKey: string | null
  /** Day-of-month (1..31), or null for empty cells. */
  day: number | null
}

/** Weekday headers, Monday-first, matching the week-start convention. */
export const WEEKDAY_LABELS: readonly string[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

/**
 * Build a month grid as an array of weeks (each week = 7 cells).
 * Leading empty cells appear before day 1 according to the Monday-start
 * convention; trailing cells pad the final week to 7.
 */
export function buildMonthGrid(year: number, month: number): MonthGridCell[][] {
  const weeks: MonthGridCell[][] = []
  const first = new Date(year, month, 1)
  const leading = (first.getDay() + 6) % 7 // Monday-start leading empties
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const cells: MonthGridCell[] = []
  for (let i = 0; i < leading; i++) {
    cells.push({ dateKey: null, day: null })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month, day)
    cells.push({ dateKey: dateToLocalKey(date), day })
  }
  // Pad the final week to a multiple of 7.
  while (cells.length % 7 !== 0) {
    cells.push({ dateKey: null, day: null })
  }
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }
  return weeks
}

/** Is the given local date-key equal to today's local date? */
export function isToday(dateKey: string | null, now: Date = new Date()): boolean {
  if (!dateKey) return false
  return dateKey === dateToLocalKey(now)
}

/** Human-readable "Month YYYY" label. */
export function formatMonthLabel(year: number, month: number): string {
  const name = MONTH_NAMES[((month % 12) + 12) % 12]
  return `${name} ${year}`
}

// ---------------------------------------------------------------------------
// Reactive factory
// ---------------------------------------------------------------------------

export interface UseApplicationCalendar {
  currentYear: Ref<number>
  currentMonth: Ref<number>
  selectedDateKey: Ref<string | null>
  monthLabel: ComputedRef<string>
  appliedByDate: ComputedRef<Map<string, Application[]>>
  monthGrid: ComputedRef<MonthGridCell[][]>
  weekdayLabels: readonly string[]
  selectedApplications: ComputedRef<Application[]>
  goToPreviousMonth: () => void
  goToNextMonth: () => void
  selectDate: (dateKey: string | null) => void
  countFor: (dateKey: string | null) => number
}

/**
 * Compose the pure helpers into reactive state for the popover component.
 */
export function useApplicationCalendar(
  applicationsRef: Ref<Application[]> | ComputedRef<Application[]>,
  now: Date = new Date(),
): UseApplicationCalendar {
  const currentYear = ref(now.getFullYear())
  const currentMonth = ref(now.getMonth()) // 0-indexed
  const selectedDateKey = ref<string | null>(null)

  const appliedByDate = computed(() =>
    groupApplicationsByAppliedDate(applicationsRef.value),
  )

  const monthGrid = computed(() =>
    buildMonthGrid(currentYear.value, currentMonth.value),
  )

  const monthLabel = computed(() =>
    formatMonthLabel(currentYear.value, currentMonth.value),
  )

  const selectedApplications = computed<Application[]>(() => {
    if (!selectedDateKey.value) return []
    return appliedByDate.value.get(selectedDateKey.value) ?? []
  })

  function goToPreviousMonth(): void {
    if (currentMonth.value === 0) {
      currentMonth.value = 11
      currentYear.value -= 1
    } else {
      currentMonth.value -= 1
    }
  }

  function goToNextMonth(): void {
    if (currentMonth.value === 11) {
      currentMonth.value = 0
      currentYear.value += 1
    } else {
      currentMonth.value += 1
    }
  }

  function selectDate(dateKey: string | null): void {
    selectedDateKey.value = dateKey
  }

  function countFor(dateKey: string | null): number {
    if (!dateKey) return 0
    return appliedByDate.value.get(dateKey)?.length ?? 0
  }

  return {
    currentYear,
    currentMonth,
    selectedDateKey,
    monthLabel,
    appliedByDate,
    monthGrid,
    weekdayLabels: WEEKDAY_LABELS,
    selectedApplications,
    goToPreviousMonth,
    goToNextMonth,
    selectDate,
    countFor,
  }
}
