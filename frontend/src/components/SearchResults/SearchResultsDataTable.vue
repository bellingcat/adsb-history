<script setup>
import { useQueryStore } from '../../stores/query';
import { storeToRefs } from 'pinia';
import { downloadCSV } from '../../utils/csvExport';
import { ref, computed } from 'vue';

const queryStore = useQueryStore();
const { filteredSearchResults } = storeToRefs(queryStore);

// Define table headers
const headers = [
  { title: 'ICAO', key: 'hex' },
  { title: 'Flight', key: 'flight' },
  { title: 'Squawk', key: 'squawk' },
  { title: 'Time', key: 't' },
  { title: 'Latitude', key: 'lat' },
  { title: 'Longitude', key: 'lon' },
  { title: 'Altitude', key: 'alt' },
  { title: 'Speed', key: 'gs' },
  { title: 'Heading', key: 'bearing' },
  { title: 'Registration', key: 'registration' },
  { title: 'Aircraft Type', key: 'aircraft_type' },
  { title: 'Manufacturer', key: 'manufacturer' },
  { title: 'Operator', key: 'operator' },
  { title: 'Category', key: 'category' },
  { title: 'Military', key: 'military' },
];

// Use filtered results from the store (filtered by aircraft aggregate table)
const filteredResults = computed(() => {
  return filteredSearchResults.value?.results || [];
});

// Format date for display
const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toUTCString().slice(0, -4);
};

// Format numeric values
const formatNumber = (value, unit = '') => {
  if (value === null || value === undefined || value === '') return '-';
  // Convert to number to handle string values
  const numValue = Number(value);
  // Check if it's a valid number (including zero)
  if (isNaN(numValue)) return '-';
  // Check for special case of altitude -123 (ground level)
  if (numValue === -123 && unit === ' ft') return 'ground';
  // Format the number with one decimal place if it's not a whole number
  const formatted = Number.isInteger(numValue) ? numValue : numValue.toFixed(1);
  return `${formatted}${unit}`;
};

// Convert radians to degrees
const radiansToDegrees = (radians) => {
  if (radians === null || radians === undefined) return '-';
  const degrees = (radians * 180 / Math.PI).toFixed(1);
  return `${degrees}°`;
};

// Handle CSV download
const handleDownload = () => {
  if (!filteredSearchResults.value?.results) return;

  const formattedData = filteredSearchResults.value.results.map(item => ({
    hex: item.hex,
    flight: item.flight || '-',
    squawk: item.squawk || '-',
    time: formatDate(item.t),
    latitude: item.lat ? `${item.lat.toFixed(6)}°` : '-',
    longitude: item.lon ? `${item.lon.toFixed(6)}°` : '-',
    altitude: item.alt === -123 ? 'ground' : (item.alt ? `${item.alt} ft` : '-'),
    speed: item.gs ? `${item.gs} kts` : '-',
    heading: item.bearing ? radiansToDegrees(item.bearing) : '-',
    registration: item.registration || '-',
    aircraft_type: item.aircraft_type || '-',
    manufacturer: item.manufacturer || '-',
    operator: item.operator || '-',
    category: item.category || '-',
    military: item.military ? 'Yes' : 'No'
  }));
  
  downloadCSV(formattedData, 'adsb-history-details');
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Raw Data Table</span>
      <v-btn
        v-if="filteredSearchResults && filteredSearchResults.results"
        color="primary"
        @click="handleDownload"
        prepend-icon="mdi-download"
      >
        Download CSV
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-data-table
        v-if="filteredSearchResults && filteredSearchResults.results"
        :headers="headers"
        :items="filteredResults"
        :items-per-page="10"
        class="elevation-1"
      >
        <template #[`item.t`]="{ item }">
          {{ formatDate(item.t) }}
        </template>
        <template #[`item.lat`]="{ item }">
          {{ item.lat ? `${item.lat.toFixed(6)}°` : '-' }}
        </template>
        <template #[`item.lon`]="{ item }">
          {{ item.lon ? `${item.lon.toFixed(6)}°` : '-' }}
        </template>
        <template #[`item.alt`]="{ item }">
          {{ formatNumber(item.alt, ' ft') }}
        </template>
        <template #[`item.gs`]="{ item }">
          {{ formatNumber(item.gs, ' kts') }}
        </template>
        <template #[`item.bearing`]="{ item }">
          {{ radiansToDegrees(item.bearing) }}
        </template>
        <template #[`item.registration`]="{ item }">
          {{ item.registration || '-' }}
        </template>
        <template #[`item.aircraft_type`]="{ item }">
          {{ item.aircraft_type || '-' }}
        </template>
        <template #[`item.manufacturer`]="{ item }">
          {{ item.manufacturer || '-' }}
        </template>
        <template #[`item.operator`]="{ item }">
          {{ item.operator || '-' }}
        </template>
        <template #[`item.category`]="{ item }">
          {{ item.category || '-' }}
        </template>
        <template #[`item.military`]="{ item }">
          <v-chip
            :color="item.military ? 'red' : 'green'"
            size="small"
            variant="outlined"
          >
            {{ item.military ? 'Yes' : 'No' }}
          </v-chip>
        </template>
      </v-data-table>
      <div v-else class="text-center pa-4">
        <p>No data available. Perform a search to see results.</p>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.v-data-table {
  width: 100%;
}
</style> 