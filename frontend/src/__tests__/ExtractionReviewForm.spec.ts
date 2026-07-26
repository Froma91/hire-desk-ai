import { mount } from '@vue/test-utils'
import ExtractionReviewForm from '@/components/ExtractionReviewForm.vue'
import type { ExtractionResult } from '@/components/ExtractionReviewForm.vue'

describe('ExtractionReviewForm', () => {
  function mountForm(props: {
    extraction?: ExtractionResult | null
    saveError?: string | null
    loading?: boolean
  } = {}) {
    return mount(ExtractionReviewForm, {
      props: {
        extraction: props.extraction ?? null,
        saveError: props.saveError ?? null,
        loading: props.loading ?? false,
      },
    })
  }

  const sampleExtraction: ExtractionResult = {
    jobTitle: 'Software Engineer',
    company: 'Acme Corp',
    location: 'Paris',
    skills: ['Python', 'AWS'],
    responsibilities: ['Design systems'],
    languages: ['English'],
    experienceLevel: 'Senior',
  }

  it('disables Confirm when jobTitle is empty', () => {
    const wrapper = mountForm({ extraction: null })
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('disables Confirm when jobTitle is whitespace-only', async () => {
    const wrapper = mountForm({ extraction: null })
    const input = wrapper.find('#review-job-title')
    await input.setValue('   ')
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('enables Confirm when jobTitle has valid text', async () => {
    const wrapper = mountForm({ extraction: null })
    const input = wrapper.find('#review-job-title')
    await input.setValue('Engineer')
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('renders null extraction fields as empty values', () => {
    const nullExtraction: ExtractionResult = {
      jobTitle: null,
      company: null,
      location: null,
      skills: [],
      responsibilities: [],
      languages: [],
      experienceLevel: null,
    }
    const wrapper = mountForm({ extraction: nullExtraction })

    const jobTitleInput = wrapper.find('#review-job-title').element as HTMLInputElement
    const companyInput = wrapper.find('#review-company').element as HTMLInputElement
    const locationInput = wrapper.find('#review-location').element as HTMLInputElement
    const expInput = wrapper.find('#review-experience').element as HTMLInputElement

    expect(jobTitleInput.value).toBe('')
    expect(companyInput.value).toBe('')
    expect(locationInput.value).toBe('')
    expect(expInput.value).toBe('')
  })

  it('preserves edited values in form state', async () => {
    const wrapper = mountForm({ extraction: sampleExtraction })

    const companyInput = wrapper.find('#review-company')
    await companyInput.setValue('New Company')

    expect((companyInput.element as HTMLInputElement).value).toBe('New Company')

    const jobTitleInput = wrapper.find('#review-job-title')
    expect((jobTitleInput.element as HTMLInputElement).value).toBe('Software Engineer')
  })

  it('emits confirm event with edited form data', async () => {
    const wrapper = mountForm({ extraction: sampleExtraction })

    await wrapper.find('#review-company').setValue('Edited Corp')

    await wrapper.find('form').trigger('submit')

    const emitted = wrapper.emitted('confirm')
    expect(emitted).toBeTruthy()
    expect(emitted!.length).toBe(1)

    const payload = emitted![0][0] as Record<string, unknown>
    expect(payload.jobTitle).toBe('Software Engineer')
    expect(payload.company).toBe('Edited Corp')
    expect(payload.location).toBe('Paris')
    expect(payload.skills).toEqual(['Python', 'AWS'])
    expect(payload.languages).toEqual(['English'])
    expect(payload.experienceLevel).toBe('Senior')
  })

  it('displays save error without clearing the form', () => {
    const wrapper = mountForm({
      extraction: sampleExtraction,
      saveError: 'Validation failed: jobTitle too long',
    })

    const errorDiv = wrapper.find('.review-form-error')
    expect(errorDiv.exists()).toBe(true)
    expect(errorDiv.text()).toContain('Validation failed: jobTitle too long')

    const jobTitleInput = wrapper.find('#review-job-title').element as HTMLInputElement
    expect(jobTitleInput.value).toBe('Software Engineer')
    const companyInput = wrapper.find('#review-company').element as HTMLInputElement
    expect(companyInput.value).toBe('Acme Corp')
  })

  it('does not emit confirm when jobTitle is empty', async () => {
    const wrapper = mountForm({ extraction: null })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')).toBeFalsy()
  })

  it('populates form fields from extraction prop', () => {
    const wrapper = mountForm({ extraction: sampleExtraction })

    const jobTitleInput = wrapper.find('#review-job-title').element as HTMLInputElement
    expect(jobTitleInput.value).toBe('Software Engineer')

    const companyInput = wrapper.find('#review-company').element as HTMLInputElement
    expect(companyInput.value).toBe('Acme Corp')

    const skillTags = wrapper.findAll('.review-form-tag')
    expect(skillTags.length).toBeGreaterThanOrEqual(2)
  })
})
