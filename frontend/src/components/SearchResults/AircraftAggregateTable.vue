<script setup>
import { useQueryStore } from '../../stores/query';
import { useUiStore } from '../../stores/ui';
import { storeToRefs } from 'pinia';
import { computed, ref, watch } from 'vue';
import { downloadCSV } from '../../utils/csvExport';

const queryStore = useQueryStore();
const uiStore = useUiStore();
const { searchResults } = storeToRefs(queryStore);
const { hoveredAircraft, aircraftFilter } = storeToRefs(uiStore);

const currentItems = ref([]);
const searchQuery = ref('');

// Define table headers
const headers = [
  { title: 'ICAO', key: 'hex' },
  { title: 'Flight Codes', key: 'flights' },
  { title: 'First Seen', key: 'firstSeen' },
  { title: 'Last Seen', key: 'lastSeen' },
  { title: 'Lowest Altitude', key: 'lowestAlt' },
  { title: 'Lowest Speed', key: 'lowestSpeed' },
  { title: 'Times Seen', key: 'timesSeen' },
  { title: 'Days Seen', key: 'daysSeen' },
  { title: 'Registration', key: 'registration' },
  { title: 'Aircraft Type', key: 'aircraft' },
  { title: 'Type Code', key: 'typecode' },
  { title: 'Owner', key: 'owner' },
  { title: 'Category', key: 'category' },
  { title: 'Military', key: 'military' },
];

// Format date for display
const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toUTCString().slice(0, -4);
};

// Format numeric values
const formatNumber = (value, unit = '') => {
  if (value === null || value === undefined || value === '') return '-';
  if (value === -123 && unit === ' ft') return 'ground';
  return `${value}${unit}`;
};

// Compute aggregated data
const aggregatedData = computed(() => {
  if (!searchResults.value?.results) return [];

  const aircraftMap = new Map();

  searchResults.value.results.forEach((record) => {
    if (!aircraftMap.has(record.hex)) {
      aircraftMap.set(record.hex, {
        hex: record.hex,
        registration: record.registration,
        aircraft: record.aircraft,
        typecode: record.typecode,
        owner: record.owner,
        category: record.category,
        military: record.military,
        flights: new Set(),
        firstSeen: record.t,
        lastSeen: record.t,
        lowestAlt: record.alt,
        lowestSpeed: record.gs,
        timesSeen: 1,
        daysSeen: new Set([new Date(record.t).toDateString()]),
      });
    } else {
      const aircraft = aircraftMap.get(record.hex);
      if (record.flight) aircraft.flights.add(record.flight.trim());
      if (new Date(record.t) < new Date(aircraft.firstSeen)) {
        aircraft.firstSeen = record.t;
      }
      if (new Date(record.t) > new Date(aircraft.lastSeen)) {
        aircraft.lastSeen = record.t;
      }
      if (record.alt < aircraft.lowestAlt) {
        aircraft.lowestAlt = record.alt;
      }
      if (
        (record.gs != null && record.gs < aircraft.lowestSpeed) ||
        (aircraft.lowestSpeed === null && record.gs !== null)
      ) {
        aircraft.lowestSpeed = record.gs;
      }
      aircraft.timesSeen++;
      aircraft.daysSeen.add(new Date(record.t).toDateString());
    }
  });

  return Array.from(aircraftMap.values()).map((aircraft) => ({
    ...aircraft,
    flights: Array.from(aircraft.flights).join(', '),
    daysSeen: aircraft.daysSeen.size,
  }));
});

// Filtered data based on search query
const filteredData = computed(() => {
  if (!aggregatedData.value) return [];
  if (!searchQuery.value) return aggregatedData.value;

  const query = searchQuery.value.toLowerCase();
  return aggregatedData.value.filter((item) => {
    return (
      (item.hex && item.hex.toLowerCase().includes(query)) ||
      (item.flights && item.flights.toLowerCase().includes(query)) ||
      (item.firstSeen && formatDate(item.firstSeen).toLowerCase().includes(query)) ||
      (item.lastSeen && formatDate(item.lastSeen).toLowerCase().includes(query)) ||
      (item.lowestAlt && item.lowestAlt.toString().includes(query)) ||
      (item.lowestSpeed && item.lowestSpeed.toString().includes(query)) ||
      (item.timesSeen && item.timesSeen.toString().includes(query)) ||
      (item.daysSeen && item.daysSeen.toString().includes(query)) ||
      (item.registration && item.registration.toLowerCase().includes(query)) ||
      (item.aircraft && item.aircraft.toLowerCase().includes(query)) ||
      (item.typecode && item.typecode.toLowerCase().includes(query)) ||
      (item.owner && item.owner.toLowerCase().includes(query)) ||
      (item.category && item.category.toLowerCase().includes(query)) ||
      (item.military !== null && item.military.toString().toLowerCase().includes(query))
    );
  });
});

// Add after other computed properties
const enableHover = computed(() => {
  return searchResults.value?.results?.length <= 10000;
});

// Watch for changes in local searchQuery and sync to UI store
watch(searchQuery, (newValue) => {
  uiStore.setAircraftFilter(newValue);
});

// Watch for changes in UI store aircraftFilter and sync to local searchQuery
watch(aircraftFilter, (newValue) => {
  if (searchQuery.value !== newValue) {
    searchQuery.value = newValue || '';
  }
});



// Function to handle current items update
const handleCurrentItemsUpdate = (items) => {
  console.log('items', items);
  currentItems.value = items;
};

// Handle clicking on a hex code chip
const searchByHex = (hex) => {
  // Reset the query parameters
  queryStore.resetQueryParams();

  // Update the hex code in the query parameters
  queryStore.updateQueryParams({ hexCode: hex });

  // Perform the search with the new query
  queryStore.search();
};

// Handle clicking on a flight code chip
const searchByFlight = (flight) => {
  // Reset the query parameters
  queryStore.resetQueryParams();

  // Update the flight code in the query parameters
  queryStore.updateQueryParams({ flightCode: flight });

  // Perform the search with the new query
  queryStore.search();
};

// Handle CSV download
const handleDownload = () => {
  if (!aggregatedData.value.length) return;

  const formattedData = aggregatedData.value.map((item) => ({
    hex: item.hex,
    flights: item.flights,
    firstSeen: formatDate(item.firstSeen),
    lastSeen: formatDate(item.lastSeen),
    lowestAltitude: item.lowestAlt === -123 ? 'ground' : formatNumber(item.lowestAlt, ' ft'),
    lowestSpeed: formatNumber(item.lowestSpeed, ' kts'),
    timesSeen: item.timesSeen,
    daysSeen: item.daysSeen,
    registration: item.registration || '-',
    aircraft: item.aircraft || '-',
    typecode: item.typecode || '-',
    owner: item.owner || '-',
    category: item.category || '-',
    military: item.military ? 'Yes' : 'No',
  }));

  downloadCSV(formattedData, 'adsb-history-summary');
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Aircraft Summary</span>
      <div class="d-flex gap-4 align-center">
        <v-text-field
          v-if="searchResults && searchResults.results"
          v-model="searchQuery"
          prepend-icon="mdi-magnify"
          label="Search aircraft"
          clearable
          hide-details
          density="compact"
          class="mr-6"
          style="width: 200px"
        ></v-text-field>

        <v-btn
          v-if="searchResults && searchResults.results"
          color="primary"
          @click="handleDownload"
          prepend-icon="mdi-download"
        >
          Download CSV
        </v-btn>
      </div>
    </v-card-title>
    <v-card-text>
      <v-data-table
        v-if="searchResults && searchResults.results"
        :headers="headers"
        :items="filteredData"
        :items-per-page="10"
        :items-per-page-options="[10, 25, 50, 100]"
        @update:currentItems="handleCurrentItemsUpdate"
        class="elevation-1"
      >
        <template v-slot:item="{ item, columns }">
          <tr
            @mouseenter="enableHover ? uiStore.setHoveredAircraft(item.hex) : null"
            @mouseleave="enableHover ? uiStore.setHoveredAircraft(null) : null"
            :class="{ 'hover-row': uiStore.hoveredAircraft === item.hex }"
          >
            <td v-for="column in columns" :key="column.key">
              <template v-if="column.key === 'hex'">
                <v-chip
                  @click="searchByHex(item.hex)"
                  variant="outlined"
                  size="small"
                  :color="'#333'"
                  style="cursor: pointer"
                >
                  {{ item.hex }}
                </v-chip>
              </template>
              <template v-else-if="column.key === 'firstSeen'">
                {{ formatDate(item.firstSeen) }}
              </template>
              <template v-else-if="column.key === 'lastSeen'">
                {{ formatDate(item.lastSeen) }}
              </template>
              <template v-else-if="column.key === 'lowestAlt'">
                {{ formatNumber(item.lowestAlt, ' ft') }}
              </template>
              <template v-else-if="column.key === 'lowestSpeed'">
                {{ formatNumber(item.lowestSpeed, ' kts') }}
              </template>
              <template v-else-if="column.key === 'flights'">
                <div class="d-flex flex-wrap" style="width: 240px">
                  <v-chip
                    v-for="flight in item.flights.split(',')"
                    :key="flight"
                    variant="outlined"
                    size="small"
                    class="mr-2"
                    :color="'#444'"
                    :style="{
                      'margin-top': '2px',
                      'margin-bottom': '2px',
                      display: flight == '' ? 'none' : '',
                      cursor: 'pointer'
                    }"
                    @click="searchByFlight(flight.trim())"
                  >
                    {{ flight }}
                  </v-chip>
                </div>
              </template>
              <template v-else-if="column.key === 'registration'">
                {{ item.registration || '-' }}
              </template>
              <template v-else-if="column.key === 'aircraft'">
                {{ item.aircraft || '-' }}
              </template>
              <template v-else-if="column.key === 'typecode'">
                {{ item.typecode || '-' }}
              </template>
              <template v-else-if="column.key === 'owner'">
                {{ item.owner || '-' }}
              </template>
              <template v-else-if="column.key === 'category'">
                {{ item.category || '-' }}
              </template>
              <template v-else-if="column.key === 'military'">
                <v-chip
                  :color="item.military ? 'red' : 'green'"
                  size="small"
                  variant="outlined"
                >
                  {{ item.military ? 'Yes' : 'No' }}
                </v-chip>
              </template>
              <template v-else>
                {{ item[column.key] }}
              </template>
            </td>
          </tr>
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

.hover-row {
  background-color: #f8f8f8;
}
</style>
