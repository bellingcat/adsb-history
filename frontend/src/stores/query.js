import { defineStore } from 'pinia';
import { useQueryHistoryStore } from './queryHistory'; // Import the history store
import { useUiStore } from './ui'; // Import the UI store
import { api } from '../services/api'; // Import the API service

export const useQueryStore = defineStore('query', {
  state: () => ({
    startDate: null,
    endDate: null,
    rois: [],
    minAltitude: null,
    maxAltitude: null,
    minSpeed: null,
    maxSpeed: null,
    minBearing: null,
    maxBearing: null,
    hexCode: null,
    flightCode: null,
    military: false,
    category: '',
    typeCode: '',
    resultLimit: 1000,
    minTimeDiff: null,
    maxTimeDiff: null,
    searchResults: null,
    isLoading: false,
    error: null,
    isLargeResult: false, // New state to track if results are large
  }),

  getters: {
    boundingBoxes: (state) => {
      if (state.rois.length === 0) return [];
      
      return state.rois.map(roi => {
        const coordinates = roi.coordinates[0];
        const minX = Math.min(...coordinates.map((coord) => coord[0]));
        const maxX = Math.max(...coordinates.map((coord) => coord[0]));
        const minY = Math.min(...coordinates.map((coord) => coord[1]));
        const maxY = Math.max(...coordinates.map((coord) => coord[1]));
        
        return {
          minX,
          maxX,
          minY,
          maxY,
          toString: () => `${minX},${minY},${maxX},${maxY}`
        };
      });
    },

    // Filtered search results based on aircraft filter from UI store
    filteredSearchResults: (state) => {
      const uiStore = useUiStore();
      
      if (!state.searchResults?.results) {
        return null;
      }

      if (!uiStore.aircraftFilter) {
        return state.searchResults;
      }

      const query = uiStore.aircraftFilter.toLowerCase();
      const filteredResults = state.searchResults.results.filter(record => {
        // First aggregate the record to match aircraft aggregate table logic
        const aircraftData = {
          hex: record.hex,
          registration: record.registration,
          aircraft: record.aircraft,
          typecode: record.typecode,
          owner: record.owner,
          category: record.category,
          military: record.military,
          flight: record.flight
        };

        // Apply the same filtering logic as aircraft aggregate table
        return (
          (aircraftData.hex && aircraftData.hex.toLowerCase().includes(query)) ||
          (aircraftData.flight && aircraftData.flight.toLowerCase().includes(query)) ||
          (aircraftData.registration && aircraftData.registration.toLowerCase().includes(query)) ||
          (aircraftData.aircraft && aircraftData.aircraft.toLowerCase().includes(query)) ||
          (aircraftData.typecode && aircraftData.typecode.toLowerCase().includes(query)) ||
          (aircraftData.owner && aircraftData.owner.toLowerCase().includes(query)) ||
          (aircraftData.category && aircraftData.category.toLowerCase().includes(query)) ||
          (aircraftData.military !== null && aircraftData.military.toString().toLowerCase().includes(query))
        );
      });

      return {
        ...state.searchResults,
        results: filteredResults,
        count: filteredResults.length
      };
    }
  },

  actions: {
    updateQueryParams(params) {
      Object.assign(this, params);
    },

    resetQueryParams() {
      this.startDate = null;
      this.endDate = null;
      this.rois = [];
      this.minAltitude = null;
      this.maxAltitude = null;
      this.minSpeed = null;
      this.maxSpeed = null;
      this.minBearing = null;
      this.maxBearing = null;
      this.hexCode = null;
      this.flightCode = null;
      this.military = false;
      this.category = '';
      this.typeCode = '';
      this.resultLimit = 1000;
      this.minTimeDiff = null;
      this.maxTimeDiff = null;
      this.searchResults = null;
      this.error = null;
      this.isLargeResult = false;
    },

    async search() {
      this.isLoading = true;
      this.error = null;
      const queryHistoryStore = useQueryHistoryStore(); // Instantiate the history store

      try {
        // Build query parameters object, only including non-null values
        const params = new URLSearchParams();

        if (this.startDate) params.append('start_time', this.startDate);
        if (this.endDate) params.append('end_time', this.endDate);
        if (this.minAltitude) params.append('min_alt', this.minAltitude);
        if (this.maxAltitude) params.append('max_alt', this.maxAltitude);
        if (this.minSpeed) params.append('min_speed', this.minSpeed);
        if (this.maxSpeed) params.append('max_speed', this.maxSpeed);
        if (this.minBearing) params.append('min_bearing', this.minBearing/360 * 2 * Math.PI);
        if (this.maxBearing) params.append('max_bearing', this.maxBearing/360 * 2 * Math.PI);
        if (this.hexCode) params.append('hex', this.hexCode);
        if (this.flightCode) params.append('flight', this.flightCode);
        if (this.military) params.append('military', 'true');
        if (this.category) params.append('category', this.category);
        if (this.typeCode) params.append('typecode', this.typeCode);
        if (this.resultLimit) params.append('limit', this.resultLimit);
        if (this.minTimeDiff) params.append('min_time_diff', this.minTimeDiff);
        if (this.maxTimeDiff) params.append('max_time_diff', this.maxTimeDiff);

        // Determine which endpoint to use based on the number of ROIs
        let endpoint = '/api/adsb/bbox';
        
        if (this.rois.length === 2) {
          // Use the intersect_bboxes endpoint when exactly two ROIs are active
          endpoint = '/api/adsb/intersect_bboxes';
          
          // Add both bounding boxes as parameters
          params.append('bbox1', this.boundingBoxes[0].toString());
          params.append('bbox2', this.boundingBoxes[1].toString());
        } else if (this.rois.length === 1) {
          // Use the original bbox parameter for a single ROI
          params.append('bbox', this.boundingBoxes[0].toString());
        }

        // Use the API service to make the request
        const response = await api.get(`${endpoint}?${params.toString()}`);
        this.searchResults = response.data;
        this.isLargeResult = this.searchResults?.count > 1000;

        // Add to history after successful search
        if (!this.error && this.searchResults) {
          queryHistoryStore.addQuery(
            {
              startDate: this.startDate,
              endDate: this.endDate,
              rois: this.rois,
              minAltitude: this.minAltitude,
              maxAltitude: this.maxAltitude,
              minSpeed: this.minSpeed,
              maxSpeed: this.maxSpeed,
              minBearing: this.minBearing,
              maxBearing: this.maxBearing,
              hexCode: this.hexCode,
              flightCode: this.flightCode,
              military: this.military,
              category: this.category,
              typeCode: this.typeCode,
              resultLimit: this.resultLimit,
              minTimeDiff: this.minTimeDiff,
              maxTimeDiff: this.maxTimeDiff
            },
            this.searchResults
          );
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    }
  },
});
