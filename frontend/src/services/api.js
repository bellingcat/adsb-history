import axios from 'axios';
import { useAuthStore } from '../stores/auth';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to add the Firebase token to each request
api.interceptors.request.use(
  async (config) => {
    const authStore = useAuthStore();
    const token = await authStore.getToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Handle unauthorized error (e.g., redirect to login)
      console.error('Authentication error:', error);
    }
    return Promise.reject(error);
  }
);

export const dispatchQuery = async (queryParams) => {
  try {
    const response = await api.post('/api/query', queryParams);
    return response.data;
  } catch (error) {
    console.error('Error dispatching query:', error);
    throw error;
  }
};

// Export the api instance directly
export { api }; 