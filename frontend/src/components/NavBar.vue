<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">Hire Desk AI</div>
    <div class="navbar-links">
      <RouterLink to="/board" class="nav-link">Board</RouterLink>
      <RouterLink to="/dashboard" class="nav-link">Dashboard</RouterLink>
      <RouterLink to="/new" class="nav-link">New Application</RouterLink>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background-color: #1a1a2e;
  color: #ffffff;
}

.navbar-brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e94560;
}

.navbar-links {
  display: flex;
  gap: 1rem;
}

.nav-link {
  color: #a8a8b3;
  text-decoration: none;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: color 0.2s, background-color 0.2s;
}

.nav-link:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.1);
}

.nav-link.router-link-active {
  color: #ffffff;
  background-color: #e94560;
  font-weight: 600;
}

/* Responsive: stack on small screens */
@media (max-width: 600px) {
  .navbar {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
  }

  .navbar-links {
    width: 100%;
    justify-content: center;
  }
}
</style>
