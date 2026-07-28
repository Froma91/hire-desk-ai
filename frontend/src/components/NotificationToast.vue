<script setup lang="ts">
import type { Component } from 'vue'
import { useUiStore } from '@/stores/ui'
import IconCheckCircle from '@/components/icons/IconCheckCircle.vue'
import IconCircleX from '@/components/icons/IconCircleX.vue'
import IconAlertTriangle from '@/components/icons/IconAlertTriangle.vue'
import IconInfo from '@/components/icons/IconInfo.vue'

const uiStore = useUiStore()

const TYPE_ICONS: Record<string, Component> = {
  success: IconCheckCircle,
  error: IconCircleX,
  warning: IconAlertTriangle,
  info: IconInfo,
}

function iconFor(type: string): Component {
  return TYPE_ICONS[type] ?? IconInfo
}
</script>

<template>
  <div class="toast-container" aria-live="polite" aria-atomic="true">
    <div
      v-for="notification in uiStore.notifications"
      :key="notification.id"
      :class="['toast', `toast--${notification.type}`]"
      role="alert"
    >
      <span class="toast-icon" aria-hidden="true">
        <component :is="iconFor(notification.type)" size="1.15rem" />
      </span>
      <span class="toast-message">{{ notification.message }}</span>
      <button
        class="toast-dismiss"
        type="button"
        aria-label="Dismiss notification"
        @click="uiStore.clearNotification(notification.id)"
      >
        &times;
      </button>
    </div>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
  width: calc(100% - 2rem);
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  line-height: 1.4;
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-left-width: 4px;
  box-shadow: var(--shadow-md);
  pointer-events: auto;
  animation: slide-in 0.25s ease-out;
}

.toast-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toast--success {
  border-left-color: var(--color-applied);
}
.toast--success .toast-icon {
  color: var(--color-applied);
}

.toast--error {
  border-left-color: var(--color-rejected);
}
.toast--error .toast-icon {
  color: var(--color-rejected);
}

.toast--warning {
  border-left-color: var(--color-interview);
}
.toast--warning .toast-icon {
  color: var(--color-interview);
}

.toast--info {
  border-left-color: var(--color-blue-600);
}
.toast--info .toast-icon {
  color: var(--color-blue-600);
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-dismiss {
  background: none;
  border: none;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
  padding: 0 0.25rem;
  flex-shrink: 0;
}

.toast-dismiss:hover {
  opacity: 1;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(1rem);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .toast {
    animation: none;
  }
}

/* Responsive: full width on small screens */
@media (max-width: 600px) {
  .toast-container {
    top: 0.5rem;
    right: 0.5rem;
    left: 0.5rem;
    max-width: none;
    width: auto;
  }
}
</style>
