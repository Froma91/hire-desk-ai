<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
import NotificationToast from '@/components/NotificationToast.vue'
</script>

<template>
  <div id="app">
    <NavBar />
    <NotificationToast />
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
main {
  padding: var(--space-6) var(--space-5);
  max-width: 80rem;
  margin: 0 auto;
}

@media (max-width: 600px) {
  main {
    padding: var(--space-4) var(--space-4);
  }
}
</style>
