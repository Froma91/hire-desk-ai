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
  color: #1a1a2e;
}

.jd-form-textarea {
  width: 100%;
  min-height: 14rem;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.5;
  resize: vertical;
  transition: border-color 0.2s;
}

.jd-form-textarea:focus {
  outline: none;
  border-color: #e94560;
  box-shadow: 0 0 0 2px rgba(233, 69, 96, 0.15);
}

.jd-form-textarea--error {
  border-color: #dc3545;
}

.jd-form-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.jd-form-count {
  font-size: 0.8rem;
  color: #6b7280;
}

.jd-form-count--error {
  color: #dc3545;
  font-weight: 600;
}

.jd-form-validation {
  font-size: 0.8rem;
  color: #dc3545;
  font-weight: 500;
}

.jd-form-button {
  margin-left: auto;
  padding: 0.6rem 1.5rem;
  background-color: #e94560;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: background-color 0.2s, opacity 0.2s;
}

.jd-form-button:hover:not(:disabled) {
  background-color: #d63851;
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
