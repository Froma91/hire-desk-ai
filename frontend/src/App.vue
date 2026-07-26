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
  padding: 1rem 1.5rem;
}
</style>
