import { defineStore } from 'pinia';

export const useIndexedDBStore = defineStore('indexedDB', {
  state: () => ({
    db: null,
  }),

  actions: {
    async initDB() {
      return new Promise((resolve, reject) => {
const DB_NAME = 'adsbHistoryDB';
const DB_VERSION = 2;

        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => {
          console.error('Error opening IndexedDB');
          reject(request.error);
        };

        request.onsuccess = () => {
          this.db = request.result;
          resolve();
        };

        request.onupgradeneeded = (event) => {
          const db = event.target.result;
          if (!db.objectStoreNames.contains('largeResults')) {
            db.createObjectStore('largeResults', { keyPath: 'queryId' });
          }
          if (!db.objectStoreNames.contains('queryMetadata')) {
            db.createObjectStore('queryMetadata', { keyPath: 'id' });
          }
        };
      });
    },

    // Helper function to serialize data
    serializeData(data) {
      return JSON.parse(JSON.stringify(data));
    },

    // Helper function to deserialize data
    deserializeData(data) {
      return data ? JSON.parse(JSON.stringify(data)) : null;
    },

    async storeLargeResults(queryId, results) {
      if (!this.db) await this.initDB();

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(['largeResults'], 'readwrite');
        const store = transaction.objectStore('largeResults');
        
        // Serialize the data before storing
        const serializedData = {
          queryId,
          results: this.serializeData(results)
        };
        
        const request = store.put(serializedData);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    async getLargeResults(queryId) {
      if (!this.db) await this.initDB();

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(['largeResults'], 'readonly');
        const store = transaction.objectStore('largeResults');
        const request = store.get(queryId);

        request.onsuccess = () => {
          const data = request.result;
          // Deserialize the data when retrieving
          resolve(data ? this.deserializeData(data.results) : null);
        };
        request.onerror = () => reject(request.error);
      });
    },

    async deleteLargeResults(queryId) {
      if (!this.db) await this.initDB();

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(['largeResults'], 'readwrite');
        const store = transaction.objectStore('largeResults');
        const request = store.delete(queryId);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    async clearAllLargeResults() {
      if (!this.db) await this.initDB();

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(['largeResults'], 'readwrite');
        const store = transaction.objectStore('largeResults');
        const request = store.clear();

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    // --- Local query history (when no Firebase) ---
    async getAllMetadata() {
      if (!this.db) await this.initDB();
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(['queryMetadata'], 'readonly');
        const store = tx.objectStore('queryMetadata');
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });
    },

    async putMetadata(entry) {
      if (!this.db) await this.initDB();
      const plain = this.serializeData(entry);
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(['queryMetadata'], 'readwrite');
        const store = tx.objectStore('queryMetadata');
        const request = store.put(plain);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    async getMetadata(id) {
      if (!this.db) await this.initDB();
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(['queryMetadata'], 'readonly');
        const store = tx.objectStore('queryMetadata');
        const request = store.get(id);
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    },

    async deleteMetadata(id) {
      if (!this.db) await this.initDB();
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(['queryMetadata'], 'readwrite');
        const store = tx.objectStore('queryMetadata');
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    async clearAllMetadata() {
      if (!this.db) await this.initDB();
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(['queryMetadata'], 'readwrite');
        const store = tx.objectStore('queryMetadata');
        const request = store.clear();
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },
  },
}); 