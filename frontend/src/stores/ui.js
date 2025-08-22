import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useUiStore = defineStore('ui', () => {
  // State
  const hoveredAircraft = ref(null);
  const aircraftFilter = ref(''); // Filter applied from aircraft aggregate table

  // Actions
  const setHoveredAircraft = (hex) => {
    console.log('setHoveredAircraft', hex);
    hoveredAircraft.value = hex;
  };

  const setAircraftFilter = (filter) => {
    console.log('setAircraftFilter', filter);
    aircraftFilter.value = filter || '';
  };

  return {
    // State
    hoveredAircraft,
    aircraftFilter,
    // Actions
    setHoveredAircraft,
    setAircraftFilter,
  };
}); 