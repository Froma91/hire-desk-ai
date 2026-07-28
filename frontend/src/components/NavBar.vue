<script setup lang="ts">
import { RouterLink } from 'vue-router'
import ReminderButton from '@/components/ReminderButton.vue'
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <span class="navbar-brand-name">Hire Desk</span><span class="navbar-brand-accent">AI</span>
    </div>
    <div class="navbar-links">
      <RouterLink to="/board" class="nav-link">Board</RouterLink>
      <RouterLink to="/dashboard" class="nav-link">Dashboard</RouterLink>
      <RouterLink to="/new" class="nav-link">New Application</RouterLink>
      <ReminderButton />
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 76px;
  padding: 0 var(--space-6);
  background: linear-gradient(135deg, var(--color-navy-900) 0%, var(--color-navy-800) 100%);
  color: var(--color-text-inverse);
}

.navbar-brand {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: 0.01em;
  font-family: var(--font-serif);
}

.navbar-brand-name {
  color: var(--color-text-inverse);
}

.navbar-brand-accent {
  color: var(--color-blue-500);
  margin-left: 0.15rem;
}

.navbar-links {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.nav-link {
  position: relative;
  color: rgba(255, 255, 255, 0.72);
  text-decoration: none;
  padding: 0.6rem 0.85rem;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  transition: color var(--transition-fast), background-color var(--transition-fast);
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 0.85rem;
  right: 0.85rem;
  bottom: 0.15rem;
  height: 2px;
  border-radius: 2px;
  background-color: transparent;
  transition: background-color var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text-inverse);
  background-color: rgba(255, 255, 255, 0.08);
}

.nav-link.router-link-active {
  color: var(--color-text-inverse);
  font-weight: 600;
}

.nav-link.router-link-active::after {
  background-color: var(--color-blue-500);
}

/* Responsive: stack on small screens */
@media (max-width: 600px) {
  .navbar {
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
  }

  .navbar-links {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>
