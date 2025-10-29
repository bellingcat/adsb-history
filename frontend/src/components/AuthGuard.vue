<script setup>
import { onMounted, ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import Auth from './Auth.vue';

const authStore = useAuthStore();
const initialized = ref(false);

onMounted(() => {
  authStore.initAuth();
  initialized.value = true;
});
</script>

<template>
  <div v-if="!initialized" class="loading-container">
    <v-progress-circular indeterminate size="64"></v-progress-circular>
  </div>
  <div v-else-if="!authStore.isAuthenticated" class="auth-required">
    <v-card class="auth-card mt-16">
      <v-card-title>Authentication Required</v-card-title>
      <v-card-text>
        <p>Please sign in with your Google account to access the ADS-B History Search.</p>
        <Auth />
      </v-card-text>
    </v-card>
  </div>
  <div v-else>
    <slot></slot>
  </div>
</template>

<style scoped>
.loading-container, .auth-required {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  padding: 20px;
}

.auth-card {
  max-width: 500px;
  width: 100%;
  text-align: center;
}
</style> 