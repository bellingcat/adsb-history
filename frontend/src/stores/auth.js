import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  signInWithGoogle,
  signOut,
  getCurrentUser,
  getIdToken,
  onAuthStateChanged,
} from '../firebase';

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null);
  const loading = ref(true);
  const error = ref(null);

  // Computed property to check if user is authenticated
  const isAuthenticated = computed(() => !!user.value);

  // Initialize auth state
  const initAuth = () => {
    loading.value = true;
    onAuthStateChanged((newUser) => {
      user.value = newUser;
      loading.value = false;
    });
  };

  // Sign in with Google
  const login = async () => {
    try {
      loading.value = true;
      error.value = null;
      await signInWithGoogle();
      // User will be updated by the onAuthStateChanged listener
    } catch (err) {
      error.value = err.message;
      console.error('Login error:', err);
    } finally {
      loading.value = false;
    }
  };

  // Sign out
  const logout = async () => {
    try {
      loading.value = true;
      error.value = null;
      await signOut();
      // User will be updated by the onAuthStateChanged listener
    } catch (err) {
      error.value = err.message;
      console.error('Logout error:', err);
    } finally {
      loading.value = false;
    }
  };

  // Get the current ID token
  const getToken = async () => {
    try {
      return await getIdToken();
    } catch (err) {
      error.value = err.message;
      console.error('Error getting token:', err);
      return null;
    }
  };

  return {
    user,
    loading,
    error,
    isAuthenticated,
    initAuth,
    login,
    logout,
    getToken,
  };
});
