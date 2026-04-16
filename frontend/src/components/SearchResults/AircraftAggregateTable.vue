<script setup>
import { useQueryStore } from '../../stores/query';
import { useQueryHistoryStore } from '../../stores/queryHistory';
import { useUiStore } from '../../stores/ui';
import { storeToRefs } from 'pinia';
import { computed, ref, watch } from 'vue';
import { downloadCSV } from '../../utils/csvExport';

// Debounce helper
const debounce = (fn, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
};

const queryStore = useQueryStore();
const queryHistoryStore = useQueryHistoryStore();
const uiStore = useUiStore();
const { searchResults } = storeToRefs(queryStore);
const { hoveredAircraft, aircraftFilter, selectedAircraft } = storeToRefs(uiStore);

// Debounced function to save selection changes to history (1.5s delay for efficiency)
const debouncedSaveSelection = debounce((selection) => {
  queryHistoryStore.updateSelectedAircraft(selection);
}, 1500);

const currentItems = ref([]);
const searchQuery = ref('');
const checkedFilter = ref('all'); // 'all', 'checked', 'unchecked'

// Define table headers
const headers = [
  { title: '', key: 'checkbox', sortable: false, width: '48px' },
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

// Filtered data based on search query and checked state
const filteredData = computed(() => {
  if (!aggregatedData.value) return [];

  let data = aggregatedData.value;

  // Filter by checked state
  if (checkedFilter.value === 'checked') {
    data = data.filter(item => uiStore.isAircraftSelected(item.hex));
  } else if (checkedFilter.value === 'unchecked') {
    data = data.filter(item => !uiStore.isAircraftSelected(item.hex));
  }

  // Filter by search query
  if (!searchQuery.value) return data;

  const query = searchQuery.value.toLowerCase();
  return data.filter((item) => {
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

// Check if all visible aircraft are selected
const allSelected = computed(() => {
  if (!filteredData.value || filteredData.value.length === 0) return false;
  return filteredData.value.every(item => uiStore.isAircraftSelected(item.hex));
});

// Check if some (but not all) visible aircraft are selected
const someSelected = computed(() => {
  if (!filteredData.value || filteredData.value.length === 0) return false;
  const selectedCount = filteredData.value.filter(item => uiStore.isAircraftSelected(item.hex)).length;
  return selectedCount > 0 && selectedCount < filteredData.value.length;
});

// Toggle all visible aircraft selection
const toggleSelectAll = () => {
  if (!filteredData.value || filteredData.value.length === 0) return;

  const newSet = new Set(selectedAircraft.value);
  const allHexCodes = filteredData.value.map(item => item.hex);

  if (allSelected.value) {
    allHexCodes.forEach(hex => newSet.delete(hex));
  } else {
    allHexCodes.forEach(hex => newSet.add(hex));
  }

  uiStore.setSelectedAircraft(newSet);
  triggerSelectionSave();
};

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

// Track if we're restoring from history (to skip the auto-save on restore)
const isRestoringFromHistory = ref(false);

// Initialize selected aircraft when search results change
watch(() => searchResults.value?.results, (newResults) => {
  if (newResults && newResults.length > 0) {
    const currentQueryMeta = queryHistoryStore.metadata.find(
      q => q.id === queryHistoryStore.currentQueryId
    );

    if (currentQueryMeta?.selectedAircraft && currentQueryMeta.selectedAircraft.length > 0) {
      isRestoringFromHistory.value = true;
      uiStore.setSelectedAircraft(new Set(currentQueryMeta.selectedAircraft));
      setTimeout(() => { isRestoringFromHistory.value = false; }, 100);
    } else {
      const allHexCodes = new Set(newResults.map(record => record.hex));
      uiStore.setSelectedAircraft(allHexCodes);
    }
  } else {
    uiStore.setSelectedAircraft(new Set());
  }
}, { immediate: true });

// Function to trigger save after selection change
const triggerSelectionSave = () => {
  if (isRestoringFromHistory.value || !queryHistoryStore.currentQueryId) return;
  if (!searchResults.value?.results?.length) return;
  debouncedSaveSelection(selectedAircraft.value);
};

// Function to handle current items update
const handleCurrentItemsUpdate = (items) => {
  currentItems.value = items;
};

// Handle clicking on a hex code chip
const searchByHex = (hex) => {
  queryStore.resetQueryParams();
  queryStore.updateQueryParams({ hexCode: hex });
  queryStore.search();
};

// Handle clicking on a flight code chip
const searchByFlight = (flight) => {
  queryStore.resetQueryParams();
  queryStore.updateQueryParams({ flightCode: flight });
  queryStore.search();
};

// Handle CSV download
const handleDownload = () => {
  if (!aggregatedData.value.length) return;

  const formattedData = aggregatedData.value.map((item) => ({
    hex: item.hex,
    checked: uiStore.isAircraftSelected(item.hex) ? 'Yes' : 'No',
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
      <div class="d-flex gap-8 align-center">
        <v-btn-toggle
          v-if="searchResults && searchResults.results"
          v-model="checkedFilter"
          mandatory
          density="compact"
          variant="outlined"
          divided
          class="mr-4"
        >
          <v-btn value="all" size="small">All</v-btn>
          <v-btn value="checked" size="small">
            <v-icon size="small" class="mr-1">mdi-checkbox-marked</v-icon>
          </v-btn>
          <v-btn value="unchecked" size="small">
            <v-icon size="small" class="mr-1">mdi-checkbox-blank-outline</v-icon>
          </v-btn>
        </v-btn-toggle>

        <v-text-field
          v-if="searchResults && searchResults.results"
          v-model="searchQuery"
          prepend-icon="mdi-magnify"
          label="Search aircraft"
          clearable
          hide-details
          density="compact"
          style="width: 200px"
          class="mr-4"
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
        <template v-slot:header.checkbox>
          <v-checkbox
            :model-value="allSelected"
            :indeterminate="someSelected"
            @update:model-value="toggleSelectAll"
            hide-details
            density="compact"
          ></v-checkbox>
        </template>
        <template v-slot:item="{ item, columns }">
          <tr
            @mouseenter="enableHover ? uiStore.setHoveredAircraft(item.hex) : null"
            @mouseleave="enableHover ? uiStore.setHoveredAircraft(null) : null"
            :class="{ 'hover-row': uiStore.hoveredAircraft === item.hex }"
          >
            <td v-for="column in columns" :key="column.key">
              <template v-if="column.key === 'checkbox'">
                <v-checkbox
                  :model-value="uiStore.isAircraftSelected(item.hex)"
                  @update:model-value="(value) => {
                    if (value) {
                      const newSet = new Set(uiStore.selectedAircraft);
                      newSet.add(item.hex);
                      uiStore.setSelectedAircraft(newSet);
                    } else {
                      const newSet = new Set(uiStore.selectedAircraft);
                      newSet.delete(item.hex);
                      uiStore.setSelectedAircraft(newSet);
                    }
                    triggerSelectionSave();
                  }"
                  hide-details
                  density="compact"
                ></v-checkbox>
              </template>
              <template v-else-if="column.key === 'hex'">
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
