<script setup>
import { onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

onMounted(() => {
  authStore.initAuth();
});

const handleLogin = async () => {
  await authStore.login();
};

const handleLogout = async () => {
  await authStore.logout();
};
</script>

<template>
  <div class="auth-container">
    <div v-if="authStore.loading" class="loading">
      <v-progress-circular indeterminate></v-progress-circular>
    </div>
    <div v-else-if="authStore.error" class="error">
      <v-alert type="error" text>{{ authStore.error }}</v-alert>
      <v-btn color="primary" @click="handleLogin">Try Again</v-btn>
    </div>
    <div v-else-if="authStore.isAuthenticated" class="authenticated">
      <v-avatar color="primary" class="mr-2">
        <v-img v-if="authStore.user.photoURL" :src="authStore.user.photoURL"></v-img>
        <span v-else>{{ authStore.user.email.charAt(0).toUpperCase() }}</span>
      </v-avatar>
      <span class="user-email">{{ authStore.user.email }}</span>
      <v-btn color="error" variant="text" @click="handleLogout">Logout</v-btn>
    </div>
    <div v-else class="not-authenticated">
      <v-btn color="primary" @click="handleLogin">
        <v-icon start>mdi-google</v-icon>
        Sign in with Google
      </v-btn>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
}

.loading, .error, .authenticated, .not-authenticated {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.user-email {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style> 