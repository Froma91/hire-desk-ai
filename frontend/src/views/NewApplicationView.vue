<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { post, ApiError } from '@/api/client'
import { useApplicationsStore, type CreateApplicationPayload } from '@/stores/applications'
import { useUiStore } from '@/stores/ui'
import JobDescriptionForm from '@/components/JobDescriptionForm.vue'
import ExtractionReviewForm from '@/components/ExtractionReviewForm.vue'
import type { ExtractionResult, ConfirmPayload } from '@/components/ExtractionReviewForm.vue'

const router = useRouter()
const applicationsStore = useApplicationsStore()
const uiStore = useUiStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

type ViewStep = 'input' | 'review'

const step = ref<ViewStep>('input')
const analyzing = ref(false)
const saving = ref(false)
const extraction = ref<ExtractionResult | null>(null)
const saveError = ref<string | null>(null)

// ---------------------------------------------------------------------------
// Analysis handler
// ---------------------------------------------------------------------------

async function handleAnalyze(jobDescription: string): Promise<void> {
  if (analyzing.value || saving.value) return

  analyzing.value = true
  saveError.value = null

  try {
    const result = await post<ExtractionResult>('/analyze', { jobDescription })
    extraction.value = result
    step.value = 'review'
  } catch (e: unknown) {
    const message = e instanceof ApiError
      ? 'Analysis failed. Enter details manually.'
      : 'Analysis failed. Enter details manually.'

    uiStore.notify(message, 'warning')
    extraction.value = null
    step.value = 'review'
  } finally {
    analyzing.value = false
  }
}

// ---------------------------------------------------------------------------
// Confirm & save handler
// ---------------------------------------------------------------------------

async function handleConfirm(formData: ConfirmPayload): Promise<void> {
  if (saving.value || analyzing.value) return

  saving.value = true
  saveError.value = null

  try {
    const payload: CreateApplicationPayload = {
      jobTitle: formData.jobTitle,
      company: formData.company,
      location: formData.location,
      skills: formData.skills,
      responsibilities: formData.responsibilities,
      languages: formData.languages,
      experienceLevel: formData.experienceLevel,
    }

    await applicationsStore.create(payload)
    uiStore.notify('Application saved successfully.', 'success')
    router.push('/board')
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
      saveError.value = e.message
    } else {
      saveError.value = 'Failed to save the application. Please try again.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="new-application-view">
    <h1 class="new-application-title">New Application</h1>

    <!-- Step 1: Paste & analyze job description -->
    <JobDescriptionForm
      v-if="step === 'input'"
      :loading="analyzing"
      @analyze="handleAnalyze"
    />

    <!-- Step 2: Review & confirm extracted information -->
    <ExtractionReviewForm
      v-if="step === 'review'"
      :extraction="extraction"
      :save-error="saveError"
      :loading="saving"
      @confirm="handleConfirm"
    />
  </div>
</template>

<style scoped>
.new-application-view {
  max-width: 48rem;
  margin: 0 auto;
}

.new-application-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 1.5rem;
}
</style>
