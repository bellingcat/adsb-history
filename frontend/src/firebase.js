import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

// Your Firebase configuration
// Replace with your actual Firebase config
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const disableAuth = import.meta.env.VITE_DISABLE_AUTH === '1' || import.meta.env.VITE_DISABLE_AUTH === 'true';
const stubUser = { uid: 'local', email: 'local@dev' };

// Initialize Firebase only when auth is enabled and config present
let app, auth, db, googleProvider;
if (!disableAuth && firebaseConfig.apiKey) {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
  db = getFirestore(app, 'searches');
  googleProvider = new GoogleAuthProvider();
} else {
  auth = null;
  db = null;
  googleProvider = null;
}

// Function to sign in with Google
export const signInWithGoogle = async () => {
  if (!auth) return stubUser;
  try {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (error) {
    console.error('Error signing in with Google:', error);
    throw error;
  }
};

// Function to sign out
export const signOut = async () => {
  if (!auth) return;
  try {
    await auth.signOut();
  } catch (error) {
    console.error('Error signing out:', error);
    throw error;
  }
};

// Function to get the current user
export const getCurrentUser = () => {
  return auth ? auth.currentUser : stubUser;
};

// Function to get the ID token
export const getIdToken = async () => {
  if (!auth || !auth.currentUser) return null;
  try {
    return await auth.currentUser.getIdToken();
  } catch (err) {
    return null;
  }
};

// Auth state change listener
export const onAuthStateChanged = (callback) => {
  if (!auth) {
    setTimeout(() => callback(stubUser), 0);
    return () => {};
  }
  return auth.onAuthStateChanged(callback);
};

// Export both auth and Firestore instances
export { auth, db };
export const isAuthDisabled = disableAuth; 