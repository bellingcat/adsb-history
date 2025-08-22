<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQueryStore } from '../../stores/query';
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
const { filteredSearchResults } = storeToRefs(queryStore);

// Toggle for stacked mode
const isStackedMode = ref(false);

// Toggle for aggregation period (week vs month)
const isMonthlyMode = ref(false);

// Chart options (computed to handle stacked mode)
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  onClick: handleBarClick,
  scales: {
    y: {
      beginAtZero: true,
      stacked: isStackedMode.value,
      title: {
        display: true,
        text: isStackedMode.value ? 'Average Aircraft per Day (by Aircraft)' : 'Average Aircraft per Day'
      }
    },
    x: {
      stacked: isStackedMode.value,
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
      display: false
    }
  }
}));

// Store planesPerDay data for click handling and chart computation
const planesPerDay = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results || filteredSearchResults.value.results.length === 0) {
    return {};
  }

  const dates = filteredSearchResults.value.results.map(result => new Date(result.t).toISOString().split('T')[0]);
  const minDate = new Date(Math.min(...dates.map(d => new Date(d))));
  const maxDate = new Date(Math.max(...dates.map(d => new Date(d))));
  
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

// Compute the data for the chart
const chartData = computed(() => {
  console.log('Computing chart data, filteredSearchResults:', filteredSearchResults.value, 'stacked mode:', isStackedMode.value);
  
  if (!filteredSearchResults.value || !filteredSearchResults.value.results || filteredSearchResults.value.results.length === 0) {
    console.log('No search results available');
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

  if (!isStackedMode.value) {
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

    console.log(`Processed ${isMonthlyMode.value ? 'monthly' : 'weekly'} chart data:`, { 
      periods: formattedLabels, 
      totals: periodTotals 
    });

    return {
      labels: formattedLabels,
      datasets: [{
        label: 'Average Aircraft per Day',
        data: periodTotals,
        backgroundColor: '#3f51b5'
      }]
    };
  } else {
    // Stacked mode: track individual aircraft contributions by period
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

    console.log(`Processed stacked ${isMonthlyMode.value ? 'monthly' : 'weekly'} chart data:`, { 
      periods: formattedLabels, 
      aircraft: aircraftList.length, 
      datasets: datasets.length 
    });

    return {
      labels: formattedLabels,
      datasets: datasets
    };
  }
});

// Helper function to get consistent color for aircraft hex code
//   attempts to ensure that the colors are relatively distinct
function getConsistentColor(hex) {
  // Shuffled saturated color palette for better distribution
  const baseColors = [
    '#26DE81', '#B33771', '#FF4757', '#0652DD', '#F39C12',
    '#70A1FF', '#E84393', '#00D8D6', '#C0392B', '#A742FA',
    '#FD7E14', '#1ABC9C', '#6C5CE7', '#FF9F43', '#009432',
    '#74B9FF', '#D63384', '#EE5A24', '#3498DB', '#A55EEA',
    '#CD6133', '#2980B9', '#FF6B35', '#20C997', '#6F42C1',
    '#FFDA79', '#833471', '#0D6EFD', '#E67E22', '#1DD1A1',
    '#FC427B', '#40407A', '#F1C40F', '#00A8CC', '#DC3545',
    '#A5B1C2', '#3742FA', '#218C74', '#FFA502', '#8E44AD',
    '#FF5E5B', '#006BA6', '#2ED573', '#10AC84', '#6610F2',
    '#FDCB6E', '#7158E2', '#0ABDE3', '#C44569', '#27AE60',
    '#FF3838', '#5758BB', '#16A085', '#FEA47F', '#9B59B6',
    '#F8B500', '#00CEC9', '#D35400', '#1289A7', '#FFDD59',
    '#006266', '#4834D4', '#00D2D3', '#E74C3C', '#198754',
    '#FD79A8', '#00B894', '#FF6348'
  ];
  
  // Create a deterministic hash from the hex string using djb2 algorithm
  let hash = 5381; // djb2 initial value
  for (let i = hex.length - 1; i >= 0; i--) {
    const char = hex.charCodeAt(i);
    hash = ((hash << 5) + hash) + char; // hash * 33 + char
  }

  hash = Math.abs(hash);
  
  // Use hash to select from predefined colors for better visual separation
  return baseColors[hash % baseColors.length];
}

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
  
  console.log(`Clicked bar ${clickedIndex}: ${formattedStartDate} to ${formattedEndDate}`);
};

// Debug on mount
onMounted(() => {
  console.log('Component mounted, chartData:', chartData.value);
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
          v-model="isStackedMode"
          mandatory
          density="compact"
          color="primary"
          variant="outlined"
          divided
        >
          <v-btn :value="false" class="px-4">Total</v-btn>
          <v-btn :value="true" class="px-4">By Aircraft</v-btn>
        </v-btn-toggle>
      </div>
    </v-card-title>
    <v-card-text>
      <div v-if="filteredSearchResults && filteredSearchResults.results && filteredSearchResults.results.length > 0" style="height: 400px; position: relative; cursor: pointer;" title="Click on a bar to filter by that time period">
        <Bar 
          :key="`${isStackedMode ? 'stacked' : 'total'}-${isMonthlyMode ? 'monthly' : 'weekly'}`"
          :data="chartData" 
          :options="chartOptions" 
          @chart:render="() => console.log('Chart rendered')"
          @chart:error="(error) => console.error('Chart error:', error)"
        />
      </div>
      <div v-else>
        <p>No search results available to display the chart.</p>
      </div>
    </v-card-text>
  </v-card>
</template> 