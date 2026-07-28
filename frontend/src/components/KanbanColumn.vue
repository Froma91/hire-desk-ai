<script setup lang="ts">
import { ref } from 'vue'
import type { Application, ApplicationStatus } from '@/stores/applications'
import ApplicationCard from '@/components/ApplicationCard.vue'

const props = defineProps<{
  status: ApplicationStatus
  applications: Application[]
}>()

const emit = defineEmits<{
  drop: [payload: { applicationId: string; status: ApplicationStatus }]
  open: [application: Application]
}>()

const isDragOver = ref(false)

function onDragOver(event: DragEvent): void {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  isDragOver.value = true
}

function onDragLeave(): void {
  isDragOver.value = false
}

function onDrop(event: DragEvent): void {
  event.preventDefault()
  isDragOver.value = false

  const applicationId = event.dataTransfer?.getData('text/plain')
  if (applicationId) {
    emit('drop', { applicationId, status: props.status })
  }
}
</script>

<template>
  <section
    class="kanban-column"
    :class="{ 'kanban-column--drag-over': isDragOver }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    :aria-label="`${props.status} column`"
    role="list"
  >
    <header class="kanban-column-header">
      <h2 class="kanban-column-title">{{ props.status }}</h2>
      <span class="kanban-column-count">{{ props.applications.length }}</span>
    </header>

    <div class="kanban-column-body">
      <!-- Empty state -->
      <div v-if="props.applications.length === 0" class="kanban-column-empty">
        <span class="kanban-column-empty-text">No applications</span>
        <span class="kanban-column-empty-hint">Drag a card here</span>
      </div>

      <!-- Application cards -->
      <ApplicationCard
        v-for="app in props.applications"
        :key="app.applicationId"
        :application="app"
        @open="(application) => emit('open', application)"
      />
    </div>
  </section>
</template>

<style scoped>
.kanban-column {
  display: flex;
  flex-direction: column;
  min-width: 14rem;
  max-width: 20rem;
  flex: 1;
  background-color: var(--color-surface-muted);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  transition: background-color var(--transition-base), border-color var(--transition-base);
  border: 2px solid var(--color-border);
}

.kanban-column--drag-over {
  background-color: var(--color-blue-100);
  border-color: var(--color-blue-500);
}

.kanban-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.kanban-column-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-navy-800);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kanban-column-count {
  background-color: var(--color-border);
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  min-width: 1.5rem;
  text-align: center;
}

.kanban-column-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-height: 4rem;
}

.kanban-column-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-5) var(--space-2);
  text-align: center;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
}

.kanban-column-empty-text {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.kanban-column-empty-hint {
  font-size: 0.75rem;
  color: var(--color-border-strong);
  margin-top: 0.25rem;
}

/* Responsive: allow horizontal scroll on mobile */
@media (max-width: 768px) {
  .kanban-column {
    min-width: 12rem;
  }
}
</style>
