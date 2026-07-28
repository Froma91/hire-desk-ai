<script setup lang="ts">
import { ref, computed, watch } from 'vue'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractionResult {
  jobTitle: string | null
  company: string | null
  location: string | null
  skills: string[]
  responsibilities: string[]
  languages: string[]
  experienceLevel: string | null
}

export interface ConfirmPayload {
  jobTitle: string
  company: string | null
  location: string | null
  skills: string[]
  responsibilities: string[]
  languages: string[]
  experienceLevel: string | null
}

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------

const props = withDefaults(
  defineProps<{
    extraction?: ExtractionResult | null
    saveError?: string | null
    loading?: boolean
  }>(),
  {
    extraction: null,
    saveError: null,
    loading: false,
  },
)

const emit = defineEmits<{
  confirm: [formData: ConfirmPayload]
}>()

// ---------------------------------------------------------------------------
// Local form state (changes stay local until confirm)
// ---------------------------------------------------------------------------

const jobTitle = ref('')
const company = ref('')
const location = ref('')
const experienceLevel = ref('')
const skills = ref<string[]>([])
const responsibilities = ref<string[]>([])
const languages = ref<string[]>([])

// List field input buffers
const newSkill = ref('')
const newResponsibility = ref('')
const newLanguage = ref('')

// ---------------------------------------------------------------------------
// Initialize / re-initialize form when extraction prop changes
// ---------------------------------------------------------------------------

function initializeForm(data: ExtractionResult | null): void {
  jobTitle.value = data?.jobTitle ?? ''
  company.value = data?.company ?? ''
  location.value = data?.location ?? ''
  experienceLevel.value = data?.experienceLevel ?? ''
  skills.value = [...(data?.skills ?? [])]
  responsibilities.value = [...(data?.responsibilities ?? [])]
  languages.value = [...(data?.languages ?? [])]
}

// Watch for new extraction results
watch(
  () => props.extraction,
  (newVal) => {
    initializeForm(newVal)
  },
  { immediate: true },
)

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

const isJobTitleEmpty = computed(() => jobTitle.value.trim().length === 0)
const isDisabled = computed(() => isJobTitleEmpty.value || props.loading)

// ---------------------------------------------------------------------------
// List management helpers
// ---------------------------------------------------------------------------

function addToList(list: string[], inputRef: { value: string }): void {
  const trimmed = inputRef.value.trim()
  if (trimmed && !list.includes(trimmed)) {
    list.push(trimmed)
  }
  inputRef.value = ''
}

function removeFromList(list: string[], index: number): void {
  list.splice(index, 1)
}

function addSkill(): void {
  addToList(skills.value, newSkill)
}

function addResponsibility(): void {
  addToList(responsibilities.value, newResponsibility)
}

function addLanguage(): void {
  addToList(languages.value, newLanguage)
}

// ---------------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------------

function handleConfirm(): void {
  if (isDisabled.value) return

  const formData: ConfirmPayload = {
    jobTitle: jobTitle.value.trim(),
    company: company.value.trim() || null,
    location: location.value.trim() || null,
    skills: [...skills.value],
    responsibilities: [...responsibilities.value],
    languages: [...languages.value],
    experienceLevel: experienceLevel.value.trim() || null,
  }

  emit('confirm', formData)
}
</script>

<template>
  <form
    class="review-form"
    @submit.prevent="handleConfirm"
    aria-label="Review extracted job information"
  >
    <!-- Save error message -->
    <div
      v-if="props.saveError"
      class="review-form-error"
      role="alert"
      aria-live="assertive"
    >
      {{ props.saveError }}
    </div>

    <!-- Job Title (required) -->
    <div class="review-form-field">
      <label for="review-job-title" class="review-form-label">
        Job Title <span class="review-form-required">*</span>
      </label>
      <input
        id="review-job-title"
        v-model="jobTitle"
        type="text"
        class="review-form-input"
        :class="{ 'review-form-input--error': isJobTitleEmpty && jobTitle !== '' }"
        placeholder="e.g. Software Engineer"
        required
        aria-required="true"
        :aria-invalid="isJobTitleEmpty && jobTitle !== ''"
      />
      <span
        v-if="isJobTitleEmpty && jobTitle !== ''"
        class="review-form-hint review-form-hint--error"
        role="alert"
      >
        Job title is required.
      </span>
    </div>

    <!-- Company -->
    <div class="review-form-field">
      <label for="review-company" class="review-form-label">Company</label>
      <input
        id="review-company"
        v-model="company"
        type="text"
        class="review-form-input"
        placeholder="e.g. Acme Corp"
      />
    </div>

    <!-- Location -->
    <div class="review-form-field">
      <label for="review-location" class="review-form-label">Location</label>
      <input
        id="review-location"
        v-model="location"
        type="text"
        class="review-form-input"
        placeholder="e.g. Paris, France"
      />
    </div>

    <!-- Experience Level -->
    <div class="review-form-field">
      <label for="review-experience" class="review-form-label">Experience Level</label>
      <input
        id="review-experience"
        v-model="experienceLevel"
        type="text"
        class="review-form-input"
        placeholder="e.g. Senior, Junior, 3-5 years"
      />
    </div>

    <!-- Skills (list) -->
    <fieldset class="review-form-field review-form-fieldset">
      <legend class="review-form-label">Skills</legend>
      <div class="review-form-list-input">
        <input
          v-model="newSkill"
          type="text"
          class="review-form-input"
          placeholder="Add a skill..."
          aria-label="New skill"
          @keydown.enter.prevent="addSkill"
        />
        <button
          type="button"
          class="review-form-add-btn"
          @click="addSkill"
          :disabled="!newSkill.trim()"
          aria-label="Add skill"
        >
          +
        </button>
      </div>
      <ul v-if="skills.length" class="review-form-tags" aria-label="Skills list">
        <li v-for="(skill, i) in skills" :key="`skill-${i}`" class="review-form-tag">
          <span>{{ skill }}</span>
          <button
            type="button"
            class="review-form-tag-remove"
            @click="removeFromList(skills, i)"
            :aria-label="`Remove ${skill}`"
          >
            &times;
          </button>
        </li>
      </ul>
    </fieldset>

    <!-- Responsibilities (list) -->
    <fieldset class="review-form-field review-form-fieldset">
      <legend class="review-form-label">Responsibilities</legend>
      <div class="review-form-list-input">
        <input
          v-model="newResponsibility"
          type="text"
          class="review-form-input"
          placeholder="Add a responsibility..."
          aria-label="New responsibility"
          @keydown.enter.prevent="addResponsibility"
        />
        <button
          type="button"
          class="review-form-add-btn"
          @click="addResponsibility"
          :disabled="!newResponsibility.trim()"
          aria-label="Add responsibility"
        >
          +
        </button>
      </div>
      <ul v-if="responsibilities.length" class="review-form-tags" aria-label="Responsibilities list">
        <li v-for="(resp, i) in responsibilities" :key="`resp-${i}`" class="review-form-tag">
          <span>{{ resp }}</span>
          <button
            type="button"
            class="review-form-tag-remove"
            @click="removeFromList(responsibilities, i)"
            :aria-label="`Remove ${resp}`"
          >
            &times;
          </button>
        </li>
      </ul>
    </fieldset>

    <!-- Languages (list) -->
    <fieldset class="review-form-field review-form-fieldset">
      <legend class="review-form-label">Languages</legend>
      <div class="review-form-list-input">
        <input
          v-model="newLanguage"
          type="text"
          class="review-form-input"
          placeholder="Add a language..."
          aria-label="New language"
          @keydown.enter.prevent="addLanguage"
        />
        <button
          type="button"
          class="review-form-add-btn"
          @click="addLanguage"
          :disabled="!newLanguage.trim()"
          aria-label="Add language"
        >
          +
        </button>
      </div>
      <ul v-if="languages.length" class="review-form-tags" aria-label="Languages list">
        <li v-for="(lang, i) in languages" :key="`lang-${i}`" class="review-form-tag">
          <span>{{ lang }}</span>
          <button
            type="button"
            class="review-form-tag-remove"
            @click="removeFromList(languages, i)"
            :aria-label="`Remove ${lang}`"
          >
            &times;
          </button>
        </li>
      </ul>
    </fieldset>

    <!-- Submit -->
    <div class="review-form-actions">
      <button
        type="submit"
        class="review-form-confirm"
        :disabled="isDisabled"
        :aria-busy="props.loading"
      >
        {{ props.loading ? 'Saving...' : 'Confirm & Save' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.review-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  width: 100%;
  max-width: 40rem;
}

.review-form-error {
  padding: 0.75rem 1rem;
  background-color: var(--color-rejected-soft);
  color: #721c24;
  border: 1px solid var(--color-rejected);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.review-form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.review-form-fieldset {
  border: none;
  padding: 0;
  margin: 0;
}

.review-form-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-navy-800);
}

.review-form-required {
  color: var(--color-rejected);
}

.review-form-input {
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-family: inherit;
  color: var(--color-text-primary);
  background-color: var(--color-surface);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.review-form-input:focus {
  outline: none;
  border-color: var(--color-blue-600);
  box-shadow: 0 0 0 3px var(--color-blue-100);
}

.review-form-input--error {
  border-color: var(--color-rejected);
}

.review-form-hint {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.review-form-hint--error {
  color: var(--color-rejected);
}

.review-form-list-input {
  display: flex;
  gap: 0.5rem;
}

.review-form-list-input .review-form-input {
  flex: 1;
}

.review-form-add-btn {
  padding: 0.5rem 0.85rem;
  background-color: var(--color-blue-600);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  line-height: 1;
  transition: background-color var(--transition-fast), opacity var(--transition-fast);
}

.review-form-add-btn:hover:not(:disabled) {
  background-color: var(--color-blue-700);
}

.review-form-add-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.review-form-tags {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.review-form-tag {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.6rem;
  background-color: var(--color-blue-100);
  border-radius: 999px;
  font-size: 0.85rem;
  color: var(--color-navy-800);
}

.review-form-tag-remove {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0 0.15rem;
  line-height: 1;
}

.review-form-tag-remove:hover {
  color: var(--color-blue-700);
}

.review-form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

.review-form-confirm {
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
  transition: background-color var(--transition-fast), opacity var(--transition-fast);
}

.review-form-confirm:hover:not(:disabled) {
  background-color: var(--color-blue-700);
}

.review-form-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 600px) {
  .review-form {
    max-width: none;
  }

  .review-form-actions {
    justify-content: stretch;
  }

  .review-form-confirm {
    width: 100%;
    text-align: center;
  }
}
</style>
