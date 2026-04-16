import { defineStore } from 'pinia';
import { db } from '../firebase';
import {
  collection,
  addDoc,
  getDocs,
  deleteDoc,
  doc,
  updateDoc,
  query,
  where,
  orderBy,
  limit,
  getDoc,
} from 'firebase/firestore';
import { useAuthStore } from './auth';
import { useIndexedDBStore } from './indexedDB';

export const useQueryHistoryStore = defineStore('queryHistory', {
  state: () => ({
    metadata: [], // Store only query metadata
    isLoading: false,
    error: null,
    missingDataError: null, // New state for tracking missing data
    currentQueryId: null, // Track the ID of the current query for updating selections
  }),

  actions: {
    async addQuery(queryParams, searchResults, selectedAircraft = null) {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      if (!authStore.user) return;

      this.isLoading = true;
      this.error = null;
      this.missingDataError = null;

      try {
        const timestamp = new Date().toISOString();
        const resultCount = searchResults?.count || 0;

        // Transform rois to be storage-compatible (flattened)
        const transformedParams = {
          ...queryParams,
          rois: queryParams.rois.map(roi => ({
            type: roi.type,
            coordinates: roi.coordinates[0].map(coord => ({
              lat: coord[1],
              lng: coord[0]
            }))
          }))
        };

        const selectedAircraftArray = selectedAircraft
          ? Array.from(selectedAircraft)
          : [...new Set(searchResults?.results?.map(r => r.hex) || [])];

        const metadataEntry = {
          name: null,
          timestamp,
          params: transformedParams,
          userId: authStore.user.uid,
          userEmail: authStore.user.email,
          resultCount,
          isLargeResult: resultCount > 1000,
          selectedAircraft: selectedAircraftArray,
        };

        if (db) {
          // Firebase path
          const metadataRef = await addDoc(collection(db, 'queryMetadata'), metadataEntry);
          if (resultCount > 1000) {
            await indexedDBStore.storeLargeResults(metadataRef.id, searchResults);
          } else {
            await addDoc(collection(db, 'queryResults'), {
              queryId: metadataRef.id,
              userId: authStore.user.uid,
              userEmail: authStore.user.email,
              results: searchResults,
            });
          }
          this.metadata.unshift({ id: metadataRef.id, ...metadataEntry });
          this.currentQueryId = metadataRef.id;
        } else {
          // Local IndexedDB path (no Firebase)
          const id = crypto.randomUUID();
          const entry = { id, ...metadataEntry };
          await indexedDBStore.putMetadata(entry);
          await indexedDBStore.storeLargeResults(id, searchResults);
          this.metadata.unshift(entry);
          this.currentQueryId = id;
        }
      } catch (error) {
        console.error('Error adding query to history:', error);
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    },

    async loadHistory() {
      const authStore = useAuthStore();
      if (!authStore.user) return;

      this.isLoading = true;
      this.error = null;
      this.missingDataError = null;

      try {
        if (db) {
          const q = query(
            collection(db, 'queryMetadata'),
            where('userId', '==', authStore.user.uid),
            orderBy('timestamp', 'desc'),
            limit(50),
          );
          const querySnapshot = await getDocs(q);
          this.metadata = querySnapshot.docs.map((doc) => ({
            id: doc.id,
            ...doc.data(),
          }));
        } else {
          const all = await useIndexedDBStore().getAllMetadata();
          this.metadata = all
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 50);
        }
      } catch (error) {
        console.error('Error loading query history:', error);
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    },

    async loadQuery(queryId) {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      this.missingDataError = null;

      try {
        let metadata;
        let results = null;

        if (db) {
          const metadataRef = doc(db, 'queryMetadata', queryId);
          const metadataSnap = await getDoc(metadataRef);
          if (!metadataSnap.exists()) return null;
          metadata = metadataSnap.data();
          if (metadata.isLargeResult) {
            results = await indexedDBStore.getLargeResults(queryId);
            if (!results) {
              this.missingDataError = 'The results for this query are no longer available in your browser. This can happen if you cleared your browser data or if the data was deleted.';
            }
          } else {
            const resultsQuery = query(
              collection(db, 'queryResults'),
              where('queryId', '==', queryId),
              where('userId', '==', authStore.user.uid),
              limit(1)
            );
            const resultsSnapshot = await getDocs(resultsQuery);
            if (!resultsSnapshot.empty) {
              results = resultsSnapshot.docs[0].data().results;
            }
          }
        } else {
          metadata = await indexedDBStore.getMetadata(queryId);
          if (!metadata) return null;
          results = await indexedDBStore.getLargeResults(queryId);
          if (!results) {
            this.missingDataError = 'The results for this query are no longer available in your browser. This can happen if you cleared your browser data or if the data was deleted.';
          }
        }

        // Transform the rois data back to the original format
        const transformedMetadata = {
          ...metadata,
          params: {
            ...metadata.params,
            rois: metadata.params.rois.map(roi => ({
              type: roi.type,
              coordinates: [
                roi.coordinates.map(coord => [coord.lng, coord.lat])
              ]
            }))
          }
        };

        const fullQuery = { id: queryId, ...transformedMetadata, results };

        const index = this.metadata.findIndex((q) => q.id === queryId);
        if (index !== -1) {
          this.metadata[index] = fullQuery;
        } else {
          this.metadata.unshift(fullQuery);
        }
        this.currentQueryId = queryId;
        return fullQuery;
      } catch (error) {
        console.error('Error loading query:', error);
        this.error = error.message;
        return null;
      }
    },

    async updateQueryName(queryId, name) {
      const authStore = useAuthStore();
      if (!authStore.user) return;

      try {
        if (db) {
          const docRef = doc(db, 'queryMetadata', queryId);
          await updateDoc(docRef, { name });
        } else {
          const indexedDBStore = useIndexedDBStore();
          const entry = await indexedDBStore.getMetadata(queryId);
          if (entry) {
            entry.name = name;
            await indexedDBStore.putMetadata(entry);
          }
        }
        const index = this.metadata.findIndex((q) => q.id === queryId);
        if (index !== -1) {
          this.metadata[index].name = name;
        }
      } catch (error) {
        console.error('Error updating query name:', error);
        this.error = error.message;
      }
    },

    async updateSelectedAircraft(selectedAircraft) {
      const authStore = useAuthStore();
      if (!authStore.user || !this.currentQueryId) return;

      try {
        const selectedAircraftArray = Array.from(selectedAircraft);
        if (db) {
          const docRef = doc(db, 'queryMetadata', this.currentQueryId);
          await updateDoc(docRef, { selectedAircraft: selectedAircraftArray });
        } else {
          const indexedDBStore = useIndexedDBStore();
          const entry = await indexedDBStore.getMetadata(this.currentQueryId);
          if (entry) {
            entry.selectedAircraft = selectedAircraftArray;
            await indexedDBStore.putMetadata(entry);
          }
        }
        const index = this.metadata.findIndex((q) => q.id === this.currentQueryId);
        if (index !== -1) {
          this.metadata[index].selectedAircraft = selectedAircraftArray;
        }
      } catch (error) {
        console.error('Error updating selected aircraft:', error);
      }
    },

    async deleteQuery(queryId) {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      if (!authStore.user) return;

      try {
        if (db) {
          const metadataRef = doc(db, 'queryMetadata', queryId);
          const metadataSnap = await getDoc(metadataRef);
          const metadata = metadataSnap.data();
          await deleteDoc(metadataRef);
          if (metadata.isLargeResult) {
            await indexedDBStore.deleteLargeResults(queryId);
          } else {
            const resultsQuery = query(
              collection(db, 'queryResults'),
              where('queryId', '==', queryId),
              where('userId', '==', authStore.user.uid)
            );
            const resultsSnapshot = await getDocs(resultsQuery);
            await Promise.all(resultsSnapshot.docs.map(doc => deleteDoc(doc.ref)));
          }
        } else {
          await indexedDBStore.deleteLargeResults(queryId);
          await indexedDBStore.deleteMetadata(queryId);
        }
        this.metadata = this.metadata.filter((q) => q.id !== queryId);
      } catch (error) {
        console.error('Error deleting query:', error);
        this.error = error.message;
      }
    },

    async clearHistory() {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      if (!authStore.user) return;

      try {
        if (db) {
          const metadataQuery = query(
            collection(db, 'queryMetadata'),
            where('userId', '==', authStore.user.uid)
          );
          const metadataSnapshot = await getDocs(metadataQuery);
          for (const docSnap of metadataSnapshot.docs) {
            const metadata = docSnap.data();
            if (metadata.isLargeResult) {
              await indexedDBStore.deleteLargeResults(docSnap.id);
            } else {
              const resultsQuery = query(
                collection(db, 'queryResults'),
                where('queryId', '==', docSnap.id),
                where('userId', '==', authStore.user.uid)
              );
              const resultsSnapshot = await getDocs(resultsQuery);
              await Promise.all(resultsSnapshot.docs.map(d => deleteDoc(d.ref)));
            }
            await deleteDoc(docSnap.ref);
          }
        } else {
          await indexedDBStore.clearAllMetadata();
          await indexedDBStore.clearAllLargeResults();
        }
        this.metadata = [];
      } catch (error) {
        console.error('Error clearing history:', error);
        this.error = error.message;
      }
    },

    /** Export local history for backup (only when no Firebase). Returns { metadata, resultsByQueryId }. */
    async exportForBackup() {
      if (db) return null;
      const indexedDBStore = useIndexedDBStore();
      const metadata = await indexedDBStore.getAllMetadata();
      const resultsByQueryId = {};
      for (const entry of metadata) {
        const results = await indexedDBStore.getLargeResults(entry.id);
        if (results) resultsByQueryId[entry.id] = results;
      }
      return { metadata, resultsByQueryId };
    },

    /** Restore from backup payload into local IndexedDB, then reload history. */
    async restoreFromBackup(payload) {
      if (db) return;
      const { metadata = [], resultsByQueryId = {} } = payload;
      const indexedDBStore = useIndexedDBStore();
      await indexedDBStore.clearAllMetadata();
      await indexedDBStore.clearAllLargeResults();
      for (const entry of metadata) {
        await indexedDBStore.putMetadata(entry);
        if (resultsByQueryId[entry.id]) {
          await indexedDBStore.storeLargeResults(entry.id, resultsByQueryId[entry.id]);
        }
      }
      await this.loadHistory();
    },
  },
});
