<script setup lang="ts">
import type { Application, ApplicationStatus } from '@/stores/applications'

const props = defineProps<{
  application: Application
}>()

// Status badge colors
const statusColors: Record<ApplicationStatus, string> = {
  Wishlist: '#6366f1',
  Applied: '#0891b2',
  Interview: '#d97706',
  Offer: '#16a34a',
  Rejected: '#dc2626',
}

function onDragStart(event: DragEvent): void {
  if (event.dataTransfer) {
    event.dataTransfer.setData('text/plain', props.application.applicationId)
    event.dataTransfer.effectAllowed = 'move'
  }
}
</script>

<template>
  <article
    class="app-card"
    draggable="true"
    @dragstart="onDragStart"
    :aria-label="`${props.application.jobTitle} at ${props.application.company ?? 'Unknown company'}`"
    role="listitem"
  >
    <div class="app-card-header">
      <span
        class="app-card-badge"
        :style="{ backgroundColor: statusColors[props.application.status] }"
      >
        {{ props.application.status }}
      </span>
      <span class="app-card-drag-handle" aria-label="Drag handle" title="Drag to change status">
        ⠿
      </span>
    </div>

    <h3 class="app-card-title">{{ props.application.jobTitle }}</h3>

    <p v-if="props.application.company" class="app-card-company">
      {{ props.application.company }}
    </p>
  </article>
</template>

<style scoped>
.app-card {
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.75rem;
  cursor: grab;
  transition: box-shadow 0.2s, transform 0.1s;
  user-select: none;
}

.app-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-card:active {
  cursor: grabbing;
  transform: scale(0.98);
  opacity: 0.8;
}

.app-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.app-card-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: #ffffff;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.app-card-drag-handle {
  font-size: 1.1rem;
  color: #9ca3af;
  cursor: grab;
  line-height: 1;
}

.app-card-drag-handle:active {
  cursor: grabbing;
}

.app-card-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 0.25rem;
  line-height: 1.3;
}

.app-card-company {
  font-size: 0.8rem;
  color: #6b7280;
  margin: 0;
}
</style>
