import { mount } from '@vue/test-utils'
import JobDescriptionForm from '@/components/JobDescriptionForm.vue'

describe('JobDescriptionForm', () => {
  function mountForm(props: { loading: boolean } = { loading: false }) {
    return mount(JobDescriptionForm, { props })
  }

  async function setTextareaValue(wrapper: ReturnType<typeof mount>, value: string) {
    const textarea = wrapper.find('textarea')
    const el = textarea.element as HTMLTextAreaElement
    el.value = value
    await textarea.trigger('input')
  }

  it('disables Analyze button when description is empty', () => {
    const wrapper = mountForm()
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('disables Analyze button when description is whitespace-only', async () => {
    const wrapper = mountForm()
    await setTextareaValue(wrapper, '   ')
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('emits analyze event with trimmed text when input is valid', async () => {
    const wrapper = mountForm()
    await setTextareaValue(wrapper, '  Valid job description  ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('analyze')).toBeTruthy()
    expect(wrapper.emitted('analyze')![0]).toEqual(['Valid job description'])
  })

  it('truncates input to 10,000 characters and emits truncated value', async () => {
    const wrapper = mountForm()
    const longText = 'a'.repeat(10_001)
    await setTextareaValue(wrapper, longText)
    await wrapper.find('form').trigger('submit')

    const emitted = wrapper.emitted('analyze')
    expect(emitted).toBeTruthy()
    expect((emitted![0][0] as string).length).toBe(10_000)
  })

  it('disables Analyze button when loading prop is true', async () => {
    const wrapper = mountForm({ loading: true })
    await setTextareaValue(wrapper, 'Some valid text')
    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('does not emit analyze when loading is true', async () => {
    const wrapper = mountForm({ loading: true })
    await setTextareaValue(wrapper, 'Some valid text')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('analyze')).toBeFalsy()
  })
})
