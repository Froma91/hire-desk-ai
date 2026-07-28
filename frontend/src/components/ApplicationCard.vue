<script setup lang="ts">
import type { Application } from '@/stores/applications'

const props = defineProps<{
  application: Application
}>()

const emit = defineEmits<{
  open: [application: Application]
}>()

function onDragStart(event: DragEvent): void {
  if (event.dataTransfer) {
    event.dataTransfer.setData('text/plain', props.application.applicationId)
    event.dataTransfer.effectAllowed = 'move'
  }
}

/**
 * Open the details modal. Ignores activations that originate from within the
 * drag handle so dragging never opens the modal.
 */
function onOpen(event: Event): void {
  const target = event.target as HTMLElement | null
  if (target && target.closest('.app-card-drag-handle')) {
    return
  }
  emit('open', props.application)
}
</script>

<template>
  <article
    class="app-card"
    :data-status="props.application.status"
    draggable="true"
    tabindex="0"
    @dragstart="onDragStart"
    @click="onOpen"
    @keydown.enter.prevent="onOpen"
    @keydown.space.prevent="onOpen"
    :aria-label="`${props.application.jobTitle} at ${props.application.company ?? 'Unknown company'}`"
    role="listitem"
  >
    <div class="app-card-header">
      <span class="app-card-badge">
        {{ props.application.status }}
      </span>
      <span
        class="app-card-drag-handle"
        aria-label="Drag handle"
        title="Drag to change status"
        @click.stop
      >
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
  position: relative;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  cursor: pointer;
  transition: box-shadow var(--transition-base), transform var(--transition-fast),
    border-color var(--transition-fast);
  user-select: none;
  box-shadow: var(--shadow-sm);
}

.app-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.app-card:active {
  cursor: grabbing;
  transform: scale(0.99);
}

.app-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.app-card-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-text-secondary);
  background-color: var(--color-surface-muted);
}

.app-card-drag-handle {
  font-size: 1.1rem;
  color: var(--color-border-strong);
  cursor: grab;
  line-height: 1;
}

.app-card-drag-handle:active {
  cursor: grabbing;
}

.app-card-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 0.25rem;
  line-height: 1.3;
}

.app-card-company {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin: 0;
}

/* Per-status accent + badge colors driven by data-status */
.app-card[data-status='Wishlist'] {
  border-left-color: var(--color-wishlist);
}
.app-card[data-status='Wishlist'] .app-card-badge {
  color: var(--color-wishlist);
  background-color: var(--color-wishlist-soft);
}

.app-card[data-status='Applied'] {
  border-left-color: var(--color-applied);
}
.app-card[data-status='Applied'] .app-card-badge {
  color: var(--color-applied);
  background-color: var(--color-applied-soft);
}

.app-card[data-status='Interview'] {
  border-left-color: var(--color-interview);
}
.app-card[data-status='Interview'] .app-card-badge {
  color: var(--color-interview);
  background-color: var(--color-interview-soft);
}

.app-card[data-status='Offer'] {
  border-left-color: var(--color-offer);
}
.app-card[data-status='Offer'] .app-card-badge {
  color: var(--color-offer);
  background-color: var(--color-offer-soft);
}

.app-card[data-status='Rejected'] {
  border-left-color: var(--color-rejected);
}
.app-card[data-status='Rejected'] .app-card-badge {
  color: var(--color-rejected);
  background-color: var(--color-rejected-soft);
}
</style>
