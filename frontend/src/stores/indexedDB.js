import { defineStore } from 'pinia';

export const useIndexedDBStore = defineStore('indexedDB', {
  state: () => ({
    db: null,
  }),

  actions: {
    async initDB() {
      return new Promise((resolve, reject) => {
        const request = indexedDB.open('adsbHistoryDB', 1);

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
  },
}); 