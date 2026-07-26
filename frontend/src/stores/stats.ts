/**
 * Stats store — manages dashboard statistics state.
 *
 * - Uses src/api/client.ts for HTTP calls
 * - Clears stale errors before each request
 * - Clears stats on failure so stale values are never displayed
 * - Always resets loading in a finally block
 * - Never exposes raw API errors, AWS identifiers, or internal details
 *
 * Requirements: 5.4, 5.5
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import { get, ApiError } from '@/api/client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DashboardStats {
  total: number
  byStatus: Record<string, number>
  currentWeek: number
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useStatsStore = defineStore('stats', () => {
  // State
  const stats = ref<DashboardStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Private helpers
  function clearError(): void {
    error.value = null
  }

  function safeErrorMessage(e: unknown): string {
    if (e instanceof ApiError) {
      return e.message
    }
    return 'An unexpected error occurred'
  }

  // Actions
  async function fetchStats(): Promise<void> {
    clearError()
    loading.value = true
    try {
      const data = await get<DashboardStats>('/stats')
      stats.value = data
    } catch (e: unknown) {
      // Clear stats so stale values are never displayed
      stats.value = null
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    stats,
    loading,
    error,
    fetchStats,
  }
})
