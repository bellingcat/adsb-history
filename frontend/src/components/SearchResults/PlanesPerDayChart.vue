<script setup>
import { ref, computed, watch } from 'vue';
import { useQueryStore } from '../../stores/query';
import { useUiStore } from '../../stores/ui';
import { storeToRefs } from 'pinia';
import { Bar } from 'vue-chartjs';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend 
} from 'chart.js';
import { getConsistentColor } from '../../utils/colors';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const queryStore = useQueryStore();
const uiStore = useUiStore();
const { filteredSearchResults, searchResults } = storeToRefs(queryStore);
const { selectedAircraft } = storeToRefs(uiStore);

// Toggle for stacked mode: 'total', 'aircraft', or 'aircraftType'
const stackedMode = ref('total');

// Toggle for aggregation period (week vs month)
const isMonthlyMode = ref(false);

// Threshold for disabling stacked modes (too many results)
const STACKED_MODE_DISABLED_THRESHOLD = 100000;

const isStackedModeDisabled = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results) {
    return false;
  }
  return filteredSearchResults.value.results.length > STACKED_MODE_DISABLED_THRESHOLD;
});

const isStacked = computed(() => stackedMode.value !== 'total');

// Chart options (computed to handle stacked mode)
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  onClick: handleBarClick,
  scales: {
    y: {
      beginAtZero: true,
      stacked: isStacked.value,
      title: {
        display: true,
        text: stackedMode.value === 'aircraft'
          ? 'Average Aircraft per Day (by Aircraft)'
          : stackedMode.value === 'aircraftType'
          ? 'Average Aircraft per Day (by Type)'
          : 'Average Aircraft per Day'
      }
    },
    x: {
      stacked: isStacked.value,
      title: {
        display: true,
        text: isMonthlyMode.value ? 'Month' : 'Week'
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: 'Aircraft Per Day',
    },
    legend: {
      display: stackedMode.value === 'aircraftType',
      position: 'right',
      labels: {
        boxWidth: 12,
        padding: 8,
        font: {
          size: 11
        }
      },
      onClick: (evt, legendItem) => {
        const typecode = legendItem.text;
        toggleTypecodeSelection(typecode);
      }
    }
  }
}));

// Store planesPerDay data for click handling and chart computation
const planesPerDay = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results || filteredSearchResults.value.results.length === 0) {
    return {};
  }

  const dates = filteredSearchResults.value.results.map(result => new Date(result.t).toISOString().split('T')[0]);

  const timestamps = dates.map(d => new Date(d).getTime());
  const minTimestamp = timestamps.reduce((min, t) => t < min ? t : min, timestamps[0]);
  const maxTimestamp = timestamps.reduce((max, t) => t > max ? t : max, timestamps[0]);
  const minDate = new Date(minTimestamp);
  const maxDate = new Date(maxTimestamp);
  
  // Set maxDate to 00:00 on the following day to ensure the last date is fully included
  maxDate.setDate(maxDate.getDate() + 1);
  
  const planesPerDay = {};
  
  // Initialize all days in the range with empty sets
  const currentDate = new Date(minDate);
  while (currentDate < maxDate) {
    const dateStr = currentDate.toISOString().split('T')[0];
    planesPerDay[dateStr] = new Set();
    currentDate.setDate(currentDate.getDate() + 1);
  }
  
  // Add the actual data
  filteredSearchResults.value.results.forEach(result => {
    if (!result || !result.t || !result.hex) return;
    
    try {
      const date = new Date(result.t).toISOString().split('T')[0];
      if (planesPerDay[date] && typeof planesPerDay[date].add === 'function') {
        planesPerDay[date].add(result.hex);
      }
    } catch (error) {
      console.error('Error processing result:', error, result);
    }
  });

  return planesPerDay;
});

// Build a lookup map from hex to typecode for aircraft type stacking
const hexToTypecode = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results) {
    return {};
  }
  const map = {};
  filteredSearchResults.value.results.forEach(result => {
    if (result.hex && !map[result.hex]) {
      map[result.hex] = result.typecode || '-';
    }
  });
  return map;
});

// Build a lookup map from typecode to list of hex codes (from full search results)
const typecodeToHexList = computed(() => {
  if (!searchResults.value || !searchResults.value.results) {
    return {};
  }
  const map = {};
  searchResults.value.results.forEach(result => {
    const typecode = result.typecode || '-';
    if (!map[typecode]) {
      map[typecode] = new Set();
    }
    if (result.hex) {
      map[typecode].add(result.hex);
    }
  });
  const result = {};
  for (const [typecode, hexSet] of Object.entries(map)) {
    result[typecode] = Array.from(hexSet);
  }
  return result;
});

const isTypecodeHidden = (typecode) => {
  const hexList = typecodeToHexList.value[typecode];
  if (!hexList || hexList.length === 0) return false;
  return hexList.every(hex => !selectedAircraft.value.has(hex));
};

const toggleTypecodeSelection = (typecode) => {
  const hexList = typecodeToHexList.value[typecode];
  if (!hexList || hexList.length === 0) return;

  const newSet = new Set(selectedAircraft.value);
  const allHidden = hexList.every(hex => !newSet.has(hex));

  if (allHidden) {
    hexList.forEach(hex => newSet.add(hex));
  } else {
    hexList.forEach(hex => newSet.delete(hex));
  }

  uiStore.setSelectedAircraft(newSet);
};

// Compute the data for the chart
const chartData = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results || filteredSearchResults.value.results.length === 0) {
    return {
      labels: [],
      datasets: [{
        label: 'Average Aircraft per Day',
        data: [],
        backgroundColor: '#3f51b5'
      }]
    };
  }

  // Use the shared planesPerDay computed property
  const planesPerDayData = planesPerDay.value;

  if (stackedMode.value === 'total') {
    // Regular mode: calculate totals by period (week or month)
    const periodData = {};
    const sortedDates = Object.keys(planesPerDayData).sort();
    
    sortedDates.forEach(date => {
      const dateObj = new Date(date);
      let periodKey;
      
      if (isMonthlyMode.value) {
        // Group by month (YYYY-MM format)
        periodKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
      } else {
        // Group by week (start of week Sunday)
        const weekStart = new Date(dateObj);
        weekStart.setDate(dateObj.getDate() - dateObj.getDay());
        periodKey = weekStart.toISOString().split('T')[0];
      }
      
      if (!periodData[periodKey]) {
        periodData[periodKey] = {
          total: 0,
          count: 0
        };
      }
      
      periodData[periodKey].total += planesPerDayData[date].size;
      periodData[periodKey].count += 1;
    });

    // Calculate totals and format labels
    const periodLabels = Object.keys(periodData).sort();
    const periodTotals = periodLabels.map(periodKey => {
      const data = periodData[periodKey];
      if (isMonthlyMode.value) {
        // Get actual number of days in the month for proper normalization
        const [year, month] = periodKey.split('-');
        const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
        return data.total / daysInMonth; // Normalize by actual days in month
      } else {
        return data.total / 7; // Normalize to per-day for weeks
      }
    });

    // Format labels
    const formattedLabels = periodLabels.map(periodKey => {
      if (isMonthlyMode.value) {
        const [year, month] = periodKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
      } else {
        const start = new Date(periodKey);
        const end = new Date(start);
        end.setDate(end.getDate() + 6);
        return `${start.toLocaleDateString()} - ${end.toLocaleDateString()}`;
      }
    });

    return {
      labels: formattedLabels,
      datasets: [{
        label: 'Average Aircraft per Day',
        data: periodTotals,
        backgroundColor: '#3f51b5'
      }]
    };
  } else if (stackedMode.value === 'aircraft') {
    // Stacked by aircraft: track individual aircraft contributions by period
    const periodAircraftData = {};
    const allAircraft = new Set();
    const sortedDates = Object.keys(planesPerDayData).sort();
    
    // Build period aircraft contributions
    sortedDates.forEach(date => {
      const dateObj = new Date(date);
      let periodKey;
      
      if (isMonthlyMode.value) {
        // Group by month (YYYY-MM format)
        periodKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
      } else {
        // Group by week (start of week Sunday)
        const weekStart = new Date(dateObj);
        weekStart.setDate(dateObj.getDate() - dateObj.getDay());
        periodKey = weekStart.toISOString().split('T')[0];
      }
      
      if (!periodAircraftData[periodKey]) {
        periodAircraftData[periodKey] = {};
      }
      
      // For each aircraft seen on this day, increment their count for this period
      planesPerDayData[date].forEach(hex => {
        allAircraft.add(hex);
        if (!periodAircraftData[periodKey][hex]) {
          periodAircraftData[periodKey][hex] = 0;
        }
        periodAircraftData[periodKey][hex] += 1;
      });
    });

    const periodLabels = Object.keys(periodAircraftData).sort();
    
    // Format period labels
    const formattedLabels = periodLabels.map(periodKey => {
      if (isMonthlyMode.value) {
        const [year, month] = periodKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
      } else {
        const start = new Date(periodKey);
        const end = new Date(start);
        end.setDate(end.getDate() + 6);
        return `${start.toLocaleDateString()} - ${end.toLocaleDateString()}`;
      }
    });

    // Generate datasets for each aircraft with consistent colors
    const aircraftList = Array.from(allAircraft).sort();
    
    // Create datasets for each aircraft
    const datasets = aircraftList.map((hex) => ({
      label: hex,
      data: periodLabels.map(periodKey => {
        const count = periodAircraftData[periodKey][hex] || 0;
        if (isMonthlyMode.value) {
          // Normalize by actual days in the month
          const [year, month] = periodKey.split('-');
          const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
          return count / daysInMonth;
        } else {
          return count / 7; // Normalize to per-day for weeks
        }
      }),
      backgroundColor: getConsistentColor(hex),
      borderColor: getConsistentColor(hex),
      borderWidth: 1
    }));

    return {
      labels: formattedLabels,
      datasets: datasets
    };
  } else {
    // Stacked by aircraft type: track aircraft type contributions by period
    const periodTypeData = {};
    const allTypes = new Set();
    const sortedDates = Object.keys(planesPerDayData).sort();
    const typecodeLookup = hexToTypecode.value;

    sortedDates.forEach(date => {
      const dateObj = new Date(date);
      let periodKey;

      if (isMonthlyMode.value) {
        periodKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
      } else {
        const weekStart = new Date(dateObj);
        weekStart.setDate(dateObj.getDate() - dateObj.getDay());
        periodKey = weekStart.toISOString().split('T')[0];
      }

      if (!periodTypeData[periodKey]) {
        periodTypeData[periodKey] = {};
      }

      planesPerDayData[date].forEach(hex => {
        const typecode = typecodeLookup[hex] || '-';
        allTypes.add(typecode);
        if (!periodTypeData[periodKey][typecode]) {
          periodTypeData[periodKey][typecode] = 0;
        }
        periodTypeData[periodKey][typecode] += 1;
      });
    });

    const periodLabels = Object.keys(periodTypeData).sort();

    const formattedLabels = periodLabels.map(periodKey => {
      if (isMonthlyMode.value) {
        const [year, month] = periodKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
      } else {
        const start = new Date(periodKey);
        const end = new Date(start);
        end.setDate(end.getDate() + 6);
        return `${start.toLocaleDateString()} - ${end.toLocaleDateString()}`;
      }
    });

    const typeList = Array.from(allTypes).sort();

    const datasets = typeList.map((typecode) => ({
      label: typecode,
      data: periodLabels.map(periodKey => {
        const count = periodTypeData[periodKey][typecode] || 0;
        if (isMonthlyMode.value) {
          const [year, month] = periodKey.split('-');
          const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
          return count / daysInMonth;
        } else {
          return count / 7;
        }
      }),
      backgroundColor: getConsistentColor(typecode),
      borderColor: getConsistentColor(typecode),
      borderWidth: 1,
      hidden: isTypecodeHidden(typecode)
    }));

    return {
      labels: formattedLabels,
      datasets: datasets
    };
  }
});

// Handle bar click to filter by date range
const handleBarClick = (event, elements) => {
  if (elements.length === 0) return;
  
  const clickedIndex = elements[0].index;
  const chartDataValue = chartData.value;
  
  if (!chartDataValue || !chartDataValue.labels || clickedIndex >= chartDataValue.labels.length) return;
  
  // Get the date range for the clicked bar
  let startDate, endDate;
  
  if (isMonthlyMode.value) {
    // For monthly mode, calculate the month range
    const sortedDates = Object.keys(planesPerDay.value || {}).sort();
    if (sortedDates.length === 0) return;
    
    // Group dates by month and find the month for this index
    const monthlyGroups = {};
    sortedDates.forEach(date => {
      const dateObj = new Date(date);
      const monthKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
      if (!monthlyGroups[monthKey]) monthlyGroups[monthKey] = [];
      monthlyGroups[monthKey].push(date);
    });
    
    const monthKeys = Object.keys(monthlyGroups).sort();
    if (clickedIndex >= monthKeys.length) return;
    
    const selectedMonth = monthKeys[clickedIndex];
    const [year, month] = selectedMonth.split('-');
    startDate = new Date(parseInt(year), parseInt(month) - 1, 1);
    endDate = new Date(parseInt(year), parseInt(month), 0); // Last day of month
    
  } else {
    // For weekly mode, calculate the week range
    const sortedDates = Object.keys(planesPerDay.value || {}).sort();
    if (sortedDates.length === 0) return;
    
    // Group dates by week and find the week for this index
    const weeklyGroups = {};
    sortedDates.forEach(date => {
      const dateObj = new Date(date);
      const weekStart = new Date(dateObj);
      weekStart.setDate(dateObj.getDate() - dateObj.getDay());
      const weekKey = weekStart.toISOString().split('T')[0];
      if (!weeklyGroups[weekKey]) weeklyGroups[weekKey] = [];
      weeklyGroups[weekKey].push(date);
    });
    
    const weekKeys = Object.keys(weeklyGroups).sort();
    if (clickedIndex >= weekKeys.length) return;
    
    const selectedWeekStart = weekKeys[clickedIndex];
    startDate = new Date(selectedWeekStart);
    endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 6); // End of week
  }
  
  // Format dates for the query store (YYYY-MM-DDTHH:mm)
  const formattedStartDate = startDate.toISOString().split('T')[0] + 'T00:00';
  const formattedEndDate = endDate.toISOString().split('T')[0] + 'T23:59';
  
  // Update the query store with new date range
  queryStore.startDate = formattedStartDate;
  queryStore.endDate = formattedEndDate;
  
  // Trigger new search
  queryStore.search();
  
};

watch(isStackedModeDisabled, (disabled) => {
  if (disabled && stackedMode.value !== 'total') {
    stackedMode.value = 'total';
  }
});

</script>

<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Aircraft Per Day</span>
      <div class="d-flex gap-6">
        <v-btn-toggle
          v-model="isMonthlyMode"
          mandatory
          density="compact"
          color="primary"
          variant="outlined"
          divided
          class="mr-4"
        >
          <v-btn :value="false" class="px-4">Weekly</v-btn>
          <v-btn :value="true" class="px-4">Monthly</v-btn>
        </v-btn-toggle>
        <v-btn-toggle
          v-model="stackedMode"
          mandatory
          density="compact"
          color="primary"
          variant="outlined"
          divided
        >
          <v-btn value="total" class="px-4">Total</v-btn>
          <v-btn
            value="aircraft"
            class="px-4"
            :disabled="isStackedModeDisabled"
            :title="isStackedModeDisabled ? 'Disabled for large datasets' : ''"
          >By Aircraft</v-btn>
          <v-btn
            value="aircraftType"
            class="px-4"
            :disabled="isStackedModeDisabled"
            :title="isStackedModeDisabled ? 'Disabled for large datasets' : ''"
          >By Type</v-btn>
        </v-btn-toggle>
      </div>
    </v-card-title>
    <v-card-text>
      <div v-if="filteredSearchResults && filteredSearchResults.results && filteredSearchResults.results.length > 0" style="height: 400px; position: relative; cursor: pointer;" title="Click on a bar to filter by that time period">
        <Bar 
          :key="`${stackedMode}-${isMonthlyMode ? 'monthly' : 'weekly'}-${selectedAircraft.size}`"
          :data="chartData" 
          :options="chartOptions" 
        />
      </div>
      <div v-else>
        <p>No search results available to display the chart.</p>
      </div>
    </v-card-text>
  </v-card>
</template> 