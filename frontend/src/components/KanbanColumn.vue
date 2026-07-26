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
  background-color: #f3f4f6;
  border-radius: 8px;
  padding: 0.75rem;
  transition: background-color 0.2s, border-color 0.2s;
  border: 2px solid transparent;
}

.kanban-column--drag-over {
  background-color: #ede9fe;
  border-color: #8b5cf6;
}

.kanban-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.kanban-column-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: #374151;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kanban-column-count {
  background-color: #e5e7eb;
  color: #374151;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
}

.kanban-column-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 4rem;
}

.kanban-column-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 0.5rem;
  text-align: center;
}

.kanban-column-empty-text {
  font-size: 0.85rem;
  color: #9ca3af;
  font-weight: 500;
}

.kanban-column-empty-hint {
  font-size: 0.75rem;
  color: #d1d5db;
  margin-top: 0.25rem;
}

/* Responsive: allow horizontal scroll on mobile */
@media (max-width: 768px) {
  .kanban-column {
    min-width: 12rem;
  }
}
</style>
