/**
 * Applications store — manages job application state and API communication.
 *
 * - All HTTP calls use src/api/client.ts
 * - Updates local state after successful API operations
 * - Avoids duplicating applications in local state
 * - Clears stale errors before starting a new operation
 * - Always resets loading in a finally block
 * - updateStatus uses optimistic update with rollback on failure
 * - Never exposes AWS details or raw stack traces
 *
 * Requirements: 7.2, 7.3, 8.3
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import { get, post, patch, del, ApiError } from '@/api/client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ApplicationStatus = 'Wishlist' | 'Applied' | 'Interview' | 'Offer' | 'Rejected'

export interface StatusEntry {
  status: string
  timestamp: string
}

export interface NextAction {
  label: string
  priority: string
  explanation: string | null
  dueDate?: string | null // ISO 8601; optional — backend may omit it
}

export interface Application {
  userId: string
  applicationId: string
  jobTitle: string
  company: string | null
  location: string | null
  skills: string[]
  responsibilities: string[]
  languages: string[]
  experienceLevel: string | null
  status: ApplicationStatus
  createdAt: string
  updatedAt: string
  statusHistory: StatusEntry[]
  nextAction: NextAction | null
}

export interface CreateApplicationPayload {
  jobTitle: string
  company?: string | null
  location?: string | null
  skills?: string[]
  responsibilities?: string[]
  languages?: string[]
  experienceLevel?: string | null
  status?: ApplicationStatus
}

export interface UpdateApplicationPayload {
  jobTitle?: string
  company?: string | null
  location?: string | null
  skills?: string[]
  responsibilities?: string[]
  languages?: string[]
  experienceLevel?: string | null
  status?: ApplicationStatus
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useApplicationsStore = defineStore('applications', () => {
  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const applications = ref<Application[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  function clearError(): void {
    error.value = null
  }

  function safeErrorMessage(e: unknown): string {
    if (e instanceof ApiError) {
      return e.message
    }
    return 'An unexpected error occurred'
  }

  /**
   * Upsert an application into the local state.
   * Replaces if applicationId already exists; appends otherwise.
   */
  function upsert(app: Application): void {
    const index = applications.value.findIndex(
      (a) => a.applicationId === app.applicationId,
    )
    if (index !== -1) {
      applications.value[index] = app
    } else {
      applications.value.unshift(app)
    }
  }

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  /**
   * Fetch all applications from the API.
   */
  async function fetchAll(): Promise<void> {
    clearError()
    loading.value = true
    try {
      const data = await get<Application[]>('/applications')
      applications.value = data
    } catch (e: unknown) {
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch a single application by ID and upsert into local state.
   */
  async function fetchOne(id: string): Promise<Application> {
    clearError()
    loading.value = true
    try {
      const app = await get<Application>(`/applications/${id}`)
      upsert(app)
      return app
    } catch (e: unknown) {
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new application.
   */
  async function create(data: CreateApplicationPayload): Promise<Application> {
    clearError()
    loading.value = true
    try {
      const app = await post<Application>('/applications', data)
      upsert(app)
      return app
    } catch (e: unknown) {
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Partially update an existing application.
   */
  async function update(id: string, data: UpdateApplicationPayload): Promise<Application> {
    clearError()
    loading.value = true
    try {
      const app = await patch<Application>(`/applications/${id}`, data)
      upsert(app)
      return app
    } catch (e: unknown) {
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete an application by ID.
   */
  async function remove(id: string): Promise<void> {
    clearError()
    loading.value = true
    try {
      await del(`/applications/${id}`)
      applications.value = applications.value.filter(
        (a) => a.applicationId !== id,
      )
    } catch (e: unknown) {
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * Optimistically update application status.
   * Preserves previous status; restores it if the API call fails.
   */
  async function updateStatus(id: string, status: ApplicationStatus): Promise<Application> {
    clearError()

    // Find the application and preserve its previous status for rollback
    const index = applications.value.findIndex((a) => a.applicationId === id)
    let previousStatus: ApplicationStatus | null = null

    if (index !== -1) {
      previousStatus = applications.value[index].status
      // Optimistic update
      applications.value[index] = {
        ...applications.value[index],
        status,
      }
    }

    loading.value = true
    try {
      const app = await patch<Application>(`/applications/${id}/status`, { status })
      upsert(app)
      return app
    } catch (e: unknown) {
      // Rollback optimistic update
      if (index !== -1 && previousStatus !== null) {
        applications.value[index] = {
          ...applications.value[index],
          status: previousStatus,
        }
      }
      error.value = safeErrorMessage(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    applications,
    loading,
    error,
    // Actions
    fetchAll,
    fetchOne,
    create,
    update,
    delete: remove,
    updateStatus,
  }
})
