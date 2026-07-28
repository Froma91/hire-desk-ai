<script setup lang="ts">
import { ref, computed } from 'vue'

const MAX_CHARS = 10_000

// Props
const props = defineProps<{
  loading: boolean
}>()

// Emits
const emit = defineEmits<{
  analyze: [jobDescription: string]
}>()

// State
const jobDescription = ref('')

// Computed
const charCount = computed(() => jobDescription.value.length)
const isOverLimit = computed(() => charCount.value > MAX_CHARS)
const isEmpty = computed(() => jobDescription.value.trim().length === 0)
const isDisabled = computed(() => isEmpty.value || isOverLimit.value || props.loading)

// Handle input — enforce max length at the model level
function onInput(event: Event): void {
  const target = event.target as HTMLTextAreaElement
  if (target.value.length > MAX_CHARS) {
    // Truncate to max and update the textarea value
    target.value = target.value.slice(0, MAX_CHARS)
  }
  jobDescription.value = target.value
}

// Handle form submission
function handleSubmit(): void {
  if (isDisabled.value) return
  if (jobDescription.value.length > MAX_CHARS) return
  emit('analyze', jobDescription.value.trim())
}
</script>

<template>
  <form class="jd-form" @submit.prevent="handleSubmit" aria-label="Job description analysis form">
    <div class="jd-form-field">
      <label for="job-description-input" class="jd-form-label">
        Paste the job description
      </label>
      <textarea
        id="job-description-input"
        class="jd-form-textarea"
        :class="{ 'jd-form-textarea--error': isOverLimit }"
        :value="jobDescription"
        @input="onInput"
        :maxlength="MAX_CHARS"
        placeholder="Paste the full job description here..."
        rows="12"
        aria-describedby="jd-char-count jd-validation-message"
      ></textarea>
    </div>

    <div class="jd-form-footer">
      <span
        id="jd-char-count"
        class="jd-form-count"
        :class="{ 'jd-form-count--error': isOverLimit }"
        aria-live="polite"
      >
        {{ charCount.toLocaleString() }} / {{ MAX_CHARS.toLocaleString() }} characters
      </span>

      <span
        v-if="isOverLimit"
        id="jd-validation-message"
        class="jd-form-validation"
        role="alert"
      >
        Job description must not exceed {{ MAX_CHARS.toLocaleString() }} characters.
      </span>

      <button
        type="submit"
        class="jd-form-button"
        :disabled="isDisabled"
        :aria-busy="props.loading"
      >
        <span v-if="props.loading" class="jd-form-button-spinner" aria-hidden="true"></span>
        {{ props.loading ? 'Analyzing...' : 'Analyze' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.jd-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.jd-form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.jd-form-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-navy-800);
}

.jd-form-textarea {
  width: 100%;
  min-height: 14rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-text-primary);
  background-color: var(--color-surface);
  resize: vertical;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.jd-form-textarea:focus {
  outline: none;
  border-color: var(--color-blue-600);
  box-shadow: 0 0 0 3px var(--color-blue-100);
}

.jd-form-textarea--error {
  border-color: var(--color-rejected);
}

.jd-form-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.jd-form-count {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.jd-form-count--error {
  color: var(--color-rejected);
  font-weight: 600;
}

.jd-form-validation {
  font-size: 0.8rem;
  color: var(--color-rejected);
  font-weight: 500;
}

.jd-form-button {
  margin-left: auto;
  min-height: 44px;
  padding: 0.6rem 1.75rem;
  background-color: var(--color-blue-600);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: background-color var(--transition-fast), opacity var(--transition-fast);
}

.jd-form-button:hover:not(:disabled) {
  background-color: var(--color-blue-700);
}

.jd-form-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.jd-form-button-spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .jd-form-button-spinner {
    animation: none;
  }
}

/* Responsive */
@media (max-width: 600px) {
  .jd-form-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .jd-form-button {
    margin-left: 0;
    justify-content: center;
  }
}
</style>
