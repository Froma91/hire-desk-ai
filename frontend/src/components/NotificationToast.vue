<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
</script>

<template>
  <div class="toast-container" aria-live="polite" aria-atomic="true">
    <div
      v-for="notification in uiStore.notifications"
      :key="notification.id"
      :class="['toast', `toast--${notification.type}`]"
      role="alert"
    >
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
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
  line-height: 1.4;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: auto;
  animation: slide-in 0.25s ease-out;
}

.toast--success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.toast--error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.toast--warning {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.toast--info {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
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
