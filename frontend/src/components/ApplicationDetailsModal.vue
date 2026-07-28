<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { Application, StatusEntry } from '@/stores/applications'

const props = defineProps<{
  application: Application
}>()

const emit = defineEmits<{
  close: []
}>()

// ---------------------------------------------------------------------------
// Accessible title id (stable per instance)
// ---------------------------------------------------------------------------

const titleId = `app-details-title-${Math.random().toString(36).slice(2, 9)}`

const dialogRef = ref<HTMLElement | null>(null)
const closeButtonRef = ref<HTMLButtonElement | null>(null)

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const NOT_SPECIFIED = 'Not specified'

/** Format a scalar field, falling back to "Not specified" when empty/null. */
function displayScalar(value: string | null | undefined): string {
  if (value === null || value === undefined) return NOT_SPECIFIED
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : NOT_SPECIFIED
}

/** Format an ISO 8601 date string into a readable local string. */
function formatDate(iso: string | null | undefined): string {
  if (!iso) return NOT_SPECIFIED
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ---------------------------------------------------------------------------
// Derived values
// ---------------------------------------------------------------------------

const hasSkills = computed(() => props.application.skills.length > 0)
const hasLanguages = computed(() => props.application.languages.length > 0)
const hasResponsibilities = computed(() => props.application.responsibilities.length > 0)

/** Status history sorted chronologically ascending (works on a copy). */
const sortedStatusHistory = computed<StatusEntry[]>(() => {
  return [...props.application.statusHistory].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )
})

// ---------------------------------------------------------------------------
// Close behaviour
// ---------------------------------------------------------------------------

function close(): void {
  emit('close')
}

function onBackdrop(): void {
  close()
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // Focus the close button for keyboard/screen-reader usability.
  closeButtonRef.value?.focus()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="modal-backdrop" @click.self="onBackdrop">
    <div
      ref="dialogRef"
      class="modal-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
    >
      <header class="modal-header">
        <div class="modal-header-main">
          <h2 :id="titleId" class="modal-title">
            {{ application.jobTitle }}
          </h2>
          <p v-if="application.company" class="modal-header-company">
            {{ application.company }}
          </p>
          <span class="badge" :class="`badge--${application.status.toLowerCase()}`">
            {{ application.status }}
          </span>
        </div>
        <button
          ref="closeButtonRef"
          type="button"
          class="modal-close"
          aria-label="Close"
          @click="close"
        >
          &times;
        </button>
      </header>

      <div class="modal-body">
        <!-- Core scalar fields -->
        <dl class="modal-fields">
          <div class="modal-field">
            <dt class="modal-field-label">Company</dt>
            <dd class="modal-field-value">{{ displayScalar(application.company) }}</dd>
          </div>
          <div class="modal-field">
            <dt class="modal-field-label">Current status</dt>
            <dd class="modal-field-value">{{ application.status }}</dd>
          </div>
          <div class="modal-field">
            <dt class="modal-field-label">Location</dt>
            <dd class="modal-field-value">{{ displayScalar(application.location) }}</dd>
          </div>
          <div class="modal-field">
            <dt class="modal-field-label">Experience level</dt>
            <dd class="modal-field-value">{{ displayScalar(application.experienceLevel) }}</dd>
          </div>
        </dl>

        <!-- Skills -->
        <section class="modal-section" aria-label="Required skills">
          <h3 class="modal-section-title">Required skills</h3>
          <ul v-if="hasSkills" class="modal-tags">
            <li v-for="(skill, i) in application.skills" :key="`skill-${i}`" class="modal-tag">
              {{ skill }}
            </li>
          </ul>
          <p v-else class="modal-empty">{{ NOT_SPECIFIED }}</p>
        </section>

        <!-- Languages -->
        <section class="modal-section" aria-label="Languages">
          <h3 class="modal-section-title">Languages</h3>
          <ul v-if="hasLanguages" class="modal-tags">
            <li v-for="(lang, i) in application.languages" :key="`lang-${i}`" class="modal-tag">
              {{ lang }}
            </li>
          </ul>
          <p v-else class="modal-empty">{{ NOT_SPECIFIED }}</p>
        </section>

        <!-- Responsibilities -->
        <section class="modal-section" aria-label="Responsibilities">
          <h3 class="modal-section-title">Responsibilities</h3>
          <ul v-if="hasResponsibilities" class="modal-list">
            <li v-for="(resp, i) in application.responsibilities" :key="`resp-${i}`">
              {{ resp }}
            </li>
          </ul>
          <p v-else class="modal-empty">{{ NOT_SPECIFIED }}</p>
        </section>

        <!-- Next action -->
        <section class="modal-section" aria-label="Next action">
          <h3 class="modal-section-title">Next action</h3>
          <dl v-if="application.nextAction" class="modal-fields">
            <div class="modal-field">
              <dt class="modal-field-label">Action</dt>
              <dd class="modal-field-value">{{ displayScalar(application.nextAction.label) }}</dd>
            </div>
            <div class="modal-field">
              <dt class="modal-field-label">Due date</dt>
              <dd class="modal-field-value">{{ formatDate(application.nextAction.dueDate) }}</dd>
            </div>
            <div class="modal-field">
              <dt class="modal-field-label">Explanation</dt>
              <dd class="modal-field-value">
                {{ displayScalar(application.nextAction.explanation) }}
              </dd>
            </div>
          </dl>
          <p v-else class="modal-empty">{{ NOT_SPECIFIED }}</p>
        </section>

        <!-- Dates -->
        <dl class="modal-fields">
          <div class="modal-field">
            <dt class="modal-field-label">Created</dt>
            <dd class="modal-field-value">{{ formatDate(application.createdAt) }}</dd>
          </div>
          <div class="modal-field">
            <dt class="modal-field-label">Updated</dt>
            <dd class="modal-field-value">{{ formatDate(application.updatedAt) }}</dd>
          </div>
        </dl>

        <!-- Status history -->
        <section class="modal-section" aria-label="Status history">
          <h3 class="modal-section-title">Status history</h3>
          <ol v-if="sortedStatusHistory.length" class="modal-history">
            <li v-for="(entry, i) in sortedStatusHistory" :key="`history-${i}`" class="modal-history-item">
              <span class="modal-history-status">{{ entry.status }}</span>
              <span class="modal-history-time">{{ formatDate(entry.timestamp) }}</span>
            </li>
          </ol>
          <p v-else class="modal-empty">{{ NOT_SPECIFIED }}</p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(7, 26, 54, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 1000;
}

.modal-dialog {
  background-color: var(--color-surface);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 36rem;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: var(--space-5) var(--space-5) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.modal-header-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  align-items: flex-start;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.3;
}

.modal-header-company {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.6rem;
  line-height: 1;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0 0.25rem;
  transition: color var(--transition-fast);
}

.modal-close:hover {
  color: var(--color-text-primary);
}

.modal-body {
  padding: 1.25rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.modal-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.75rem 1.25rem;
  margin: 0;
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.modal-field-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.modal-field-value {
  font-size: 0.9rem;
  color: var(--color-text-primary);
  margin: 0;
  word-break: break-word;
}

.modal-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.modal-section-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-navy-800);
  margin: 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.modal-tags {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.modal-tag {
  padding: 0.3rem 0.65rem;
  background-color: var(--color-blue-100);
  border-radius: 999px;
  font-size: 0.85rem;
  color: var(--color-navy-800);
}

.modal-list {
  margin: 0;
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--color-text-primary);
}

.modal-empty {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin: 0;
  font-style: italic;
}

.modal-history {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.modal-history-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background-color: var(--color-surface-muted);
  border-radius: var(--radius-sm);
}

.modal-history-status {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.modal-history-time {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

/* Responsive */
@media (max-width: 600px) {
  .modal-backdrop {
    padding: 0.5rem;
  }

  .modal-dialog {
    max-width: none;
    max-height: 95vh;
  }

  .modal-fields {
    grid-template-columns: 1fr;
  }
}
</style>
