import { describe, it, expect, afterEach, vi } from 'vitest'
import type { Application, ApplicationStatus, StatusEntry } from '@/stores/applications'
import {
  getAppliedAt,
  toLocalDateKey,
  dateToLocalKey,
  groupApplicationsByAppliedDate,
  isInCurrentLocalWeek,
  countAppliedThisWeek,
  buildMonthGrid,
  isToday,
  formatMonthLabel,
  startOfLocalWeek,
} from '@/composables/useApplicationCalendar'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeApp(overrides: Partial<Application> = {}): Application {
  return {
    userId: 'demo-user',
    applicationId: `app-${Math.random().toString(36).slice(2, 8)}`,
    jobTitle: 'Engineer',
    company: 'Acme',
    location: null,
    skills: [],
    responsibilities: [],
    languages: [],
    experienceLevel: null,
    status: 'Applied' as ApplicationStatus,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
    statusHistory: [],
    nextAction: null,
    ...overrides,
  }
}

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// getAppliedAt
// ---------------------------------------------------------------------------

describe('getAppliedAt', () => {
  it('1. uses the FIRST Applied status-history event (not createdAt/updatedAt)', () => {
    const app = makeApp({
      createdAt: '2025-06-01T09:00:00Z',
      updatedAt: '2025-06-20T09:00:00Z',
      statusHistory: [
        { status: 'Wishlist', timestamp: '2025-06-03T10:00:00Z' },
        { status: 'Applied', timestamp: '2025-06-05T10:00:00Z' },
      ],
    })
    expect(getAppliedAt(app)).toBe('2025-06-05T10:00:00Z')
  })

  it('2. returns null for a Wishlist app with no Applied event', () => {
    const app = makeApp({
      status: 'Wishlist',
      statusHistory: [{ status: 'Wishlist', timestamp: '2025-06-03T10:00:00Z' }],
    })
    expect(getAppliedAt(app)).toBeNull()
  })

  it('3. returns the FIRST Applied event when there are repeated Applied events', () => {
    const app = makeApp({
      statusHistory: [
        { status: 'Applied', timestamp: '2025-06-05T10:00:00Z' },
        { status: 'Rejected', timestamp: '2025-06-10T10:00:00Z' },
        { status: 'Applied', timestamp: '2025-06-15T10:00:00Z' },
      ],
    })
    expect(getAppliedAt(app)).toBe('2025-06-05T10:00:00Z')
  })

  it('4. does not crash when statusHistory is undefined or null', () => {
    const undef = makeApp({ statusHistory: undefined as unknown as StatusEntry[] })
    const nul = makeApp({ statusHistory: null as unknown as StatusEntry[] })
    expect(getAppliedAt(undef)).toBeNull()
    expect(getAppliedAt(nul)).toBeNull()
    expect(getAppliedAt(null)).toBeNull()
    expect(getAppliedAt(undefined)).toBeNull()
  })

  it('5. ignores malformed status-history entries safely', () => {
    const app = makeApp({
      statusHistory: [
        null as unknown as StatusEntry,
        'not-an-object' as unknown as StatusEntry,
        { status: 123 as unknown as string, timestamp: '2025-06-01T10:00:00Z' },
        { status: 'Applied' } as unknown as StatusEntry, // missing timestamp
        { status: 'Applied', timestamp: '' }, // empty timestamp
        { timestamp: '2025-06-02T10:00:00Z' } as unknown as StatusEntry, // missing status
        { status: 'Applied', timestamp: '2025-06-07T10:00:00Z' }, // first valid
      ],
    })
    expect(getAppliedAt(app)).toBe('2025-06-07T10:00:00Z')
  })

  it('5b. returns null when every entry is malformed', () => {
    const app = makeApp({
      statusHistory: [
        { status: 'Applied' } as unknown as StatusEntry,
        { timestamp: '2025-06-02T10:00:00Z' } as unknown as StatusEntry,
        {} as unknown as StatusEntry,
      ],
    })
    expect(getAppliedAt(app)).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// toLocalDateKey (local timezone behaviour)
// ---------------------------------------------------------------------------

describe('toLocalDateKey', () => {
  it('returns null for invalid / empty input', () => {
    expect(toLocalDateKey('not-a-date')).toBeNull()
    expect(toLocalDateKey('')).toBeNull()
    expect(toLocalDateKey(null)).toBeNull()
    expect(toLocalDateKey(undefined)).toBeNull()
  })

  it('14. uses LOCAL getters, not toISOString (constructed local timestamp maps to its local day)', () => {
    // Construct a Date from explicit LOCAL components: 2025-03-10 23:30 local.
    const localLate = new Date(2025, 2, 10, 23, 30, 0)
    // Regardless of the machine timezone, the local date key must be the local
    // Y/M/D — this is exactly what dateToLocalKey/toLocalDateKey guarantee.
    expect(toLocalDateKey(localLate.toISOString())).toBe('2025-03-10')
    expect(dateToLocalKey(localLate)).toBe('2025-03-10')

    // Sanity: a naive toISOString-based key could differ when local != UTC.
    // We assert the helper agrees with LOCAL getters explicitly.
    const expected = `${localLate.getFullYear()}-${String(
      localLate.getMonth() + 1,
    ).padStart(2, '0')}-${String(localLate.getDate()).padStart(2, '0')}`
    expect(toLocalDateKey(localLate.toISOString())).toBe(expected)
  })
})

// ---------------------------------------------------------------------------
// groupApplicationsByAppliedDate
// ---------------------------------------------------------------------------

describe('groupApplicationsByAppliedDate', () => {
  it('buckets apps by the local date of their first Applied event and excludes non-applied apps', () => {
    const applied1 = makeApp({
      applicationId: 'a1',
      statusHistory: [{ status: 'Applied', timestamp: '2025-06-05T10:00:00Z' }],
    })
    const applied2 = makeApp({
      applicationId: 'a2',
      statusHistory: [{ status: 'Applied', timestamp: '2025-06-05T14:00:00Z' }],
    })
    const wishlistOnly = makeApp({
      applicationId: 'w1',
      status: 'Wishlist',
      statusHistory: [{ status: 'Wishlist', timestamp: '2025-06-05T10:00:00Z' }],
    })

    const map = groupApplicationsByAppliedDate([applied1, applied2, wishlistOnly])
    const key = toLocalDateKey('2025-06-05T10:00:00Z')!
    expect(map.get(key)).toHaveLength(2)
    // wishlist-only app never appears anywhere
    const allApps = [...map.values()].flat()
    expect(allApps.find((a) => a.applicationId === 'w1')).toBeUndefined()
  })

  it('handles empty / non-array input safely', () => {
    expect(groupApplicationsByAppliedDate([]).size).toBe(0)
    expect(groupApplicationsByAppliedDate(null).size).toBe(0)
    expect(groupApplicationsByAppliedDate(undefined).size).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// Week helpers
// ---------------------------------------------------------------------------

describe('current-week helpers (Monday-start)', () => {
  it('startOfLocalWeek returns the local Monday midnight', () => {
    // 2025-06-11 is a Wednesday.
    const wed = new Date(2025, 5, 11, 15, 0, 0)
    const monday = startOfLocalWeek(wed)
    expect(monday.getFullYear()).toBe(2025)
    expect(monday.getMonth()).toBe(5)
    expect(monday.getDate()).toBe(9) // Monday 2025-06-09
    expect(monday.getHours()).toBe(0)
    expect(monday.getMinutes()).toBe(0)
  })

  it('isInCurrentLocalWeek: Monday start and Sunday end are inside, adjacent days are outside', () => {
    const now = new Date(2025, 5, 11, 12, 0, 0) // Wed 2025-06-11
    expect(isInCurrentLocalWeek('2025-06-09', now)).toBe(true) // Monday
    expect(isInCurrentLocalWeek('2025-06-15', now)).toBe(true) // Sunday
    expect(isInCurrentLocalWeek('2025-06-08', now)).toBe(false) // previous Sunday
    expect(isInCurrentLocalWeek('2025-06-16', now)).toBe(false) // next Monday
  })

  it('6. countAppliedThisWeek counts only apps whose first Applied event is in the current local week', () => {
    const now = new Date(2025, 5, 11, 12, 0, 0) // Wed 2025-06-11, week = Jun 9..15

    const inWeek = makeApp({
      applicationId: 'in',
      statusHistory: [{ status: 'Applied', timestamp: new Date(2025, 5, 10, 9, 0, 0).toISOString() }],
    })
    const alsoInWeek = makeApp({
      applicationId: 'in2',
      statusHistory: [{ status: 'Applied', timestamp: new Date(2025, 5, 15, 20, 0, 0).toISOString() }],
    })
    const outOfWeek = makeApp({
      applicationId: 'out',
      statusHistory: [{ status: 'Applied', timestamp: new Date(2025, 5, 3, 9, 0, 0).toISOString() }],
    })
    const noApplied = makeApp({
      applicationId: 'none',
      status: 'Wishlist',
      statusHistory: [{ status: 'Wishlist', timestamp: new Date(2025, 5, 11, 9, 0, 0).toISOString() }],
    })

    expect(countAppliedThisWeek([inWeek, alsoInWeek, outOfWeek, noApplied], now)).toBe(2)
  })

  it('6b. repeated Applied events use the FIRST for week counting', () => {
    const now = new Date(2025, 5, 11, 12, 0, 0) // week Jun 9..15
    // First Applied is BEFORE the week; a later Applied is inside the week.
    const app = makeApp({
      statusHistory: [
        { status: 'Applied', timestamp: new Date(2025, 5, 2, 9, 0, 0).toISOString() },
        { status: 'Applied', timestamp: new Date(2025, 5, 10, 9, 0, 0).toISOString() },
      ],
    })
    // Because the FIRST Applied is used (outside the week) the count is 0.
    expect(countAppliedThisWeek([app], now)).toBe(0)
  })

  it('countAppliedThisWeek is safe for non-array input', () => {
    expect(countAppliedThisWeek(null)).toBe(0)
    expect(countAppliedThisWeek(undefined)).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// Grid helpers
// ---------------------------------------------------------------------------

describe('buildMonthGrid', () => {
  it('produces 7-column weeks with correct leading empty cells (Monday-start)', () => {
    // June 2025: 1st is a Sunday -> Monday-start leading empties = 6.
    const grid = buildMonthGrid(2025, 5)
    const flat = grid.flat()
    // Every week has 7 cells.
    grid.forEach((week) => expect(week).toHaveLength(7))
    // Leading empties before day 1.
    const firstDayIndex = flat.findIndex((c) => c.day === 1)
    expect(firstDayIndex).toBe(6)
    for (let i = 0; i < 6; i++) {
      expect(flat[i].dateKey).toBeNull()
      expect(flat[i].day).toBeNull()
    }
    // Day 1 has the right key.
    expect(flat[6].dateKey).toBe('2025-06-01')
    // 30 days present.
    expect(flat.filter((c) => c.day !== null)).toHaveLength(30)
  })

  it('handles a month that starts on Monday with no leading empties', () => {
    // December 2025: 1st is a Monday.
    const grid = buildMonthGrid(2025, 11)
    expect(grid[0][0].day).toBe(1)
    expect(grid[0][0].dateKey).toBe('2025-12-01')
  })
})

describe('isToday & formatMonthLabel', () => {
  it('isToday matches the local current date only', () => {
    const now = new Date(2025, 5, 11, 8, 0, 0)
    expect(isToday('2025-06-11', now)).toBe(true)
    expect(isToday('2025-06-10', now)).toBe(false)
    expect(isToday(null, now)).toBe(false)
  })

  it('formatMonthLabel formats "Month YYYY"', () => {
    expect(formatMonthLabel(2025, 5)).toBe('June 2025')
    expect(formatMonthLabel(2025, 0)).toBe('January 2025')
    expect(formatMonthLabel(2025, 11)).toBe('December 2025')
  })
})
