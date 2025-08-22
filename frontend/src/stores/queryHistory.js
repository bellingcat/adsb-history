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
  }),

  actions: {
    async addQuery(queryParams, searchResults) {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      if (!authStore.user) return;

      this.isLoading = true;
      this.error = null;
      this.missingDataError = null;

      try {
        const timestamp = new Date().toISOString();
        const resultCount = searchResults?.count || 0;
        
        // Transform rois to be Firestore-compatible by flattening the structure
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
        
        const metadataEntry = {
          name: null,
          timestamp,
          params: transformedParams,
          userId: authStore.user.uid,
          userEmail: authStore.user.email,
          resultCount,
          isLargeResult: resultCount > 1000,
        };

        console.log('metadataEntry', metadataEntry);

        const metadataRef = await addDoc(collection(db, 'queryMetadata'), metadataEntry);
        
        // Store results based on size
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
        // Query Firestore for user's metadata
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
        const metadataRef = doc(db, 'queryMetadata', queryId);
        const metadataSnap = await getDoc(metadataRef);
        
        if (!metadataSnap.exists()) return null;

        const metadata = metadataSnap.data();
        let results = null;

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

        const fullQuery = { id: metadataSnap.id, ...transformedMetadata, results };
        
        // Update local state
        const index = this.metadata.findIndex((q) => q.id === queryId);
        if (index !== -1) {
          this.metadata[index] = fullQuery;
        } else {
          this.metadata.unshift(fullQuery);
        }
        
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
        const docRef = doc(db, 'queryMetadata', queryId);
        await updateDoc(docRef, { name });
        
        // Update local state
        const index = this.metadata.findIndex((q) => q.id === queryId);
        if (index !== -1) {
          this.metadata[index].name = name;
        }
      } catch (error) {
        console.error('Error updating query name:', error);
        this.error = error.message;
      }
    },

    async deleteQuery(queryId) {
      const authStore = useAuthStore();
      const indexedDBStore = useIndexedDBStore();
      if (!authStore.user) return;

      try {
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
        const metadataQuery = query(
          collection(db, 'queryMetadata'),
          where('userId', '==', authStore.user.uid)
        );
        const metadataSnapshot = await getDocs(metadataQuery);
        
        // Delete all results and metadata
        await Promise.all(metadataSnapshot.docs.map(async (doc) => {
          const metadata = doc.data();
          if (metadata.isLargeResult) {
            await indexedDBStore.deleteLargeResults(doc.id);
          } else {
            const resultsQuery = query(
              collection(db, 'queryResults'),
              where('queryId', '==', doc.id),
              where('userId', '==', authStore.user.uid)
            );
            const resultsSnapshot = await getDocs(resultsQuery);
            await Promise.all(resultsSnapshot.docs.map(doc => deleteDoc(doc.ref)));
          }
          await deleteDoc(doc.ref);
        }));
        
        this.metadata = [];
      } catch (error) {
        console.error('Error clearing history:', error);
        this.error = error.message;
      }
    },
  },
});
