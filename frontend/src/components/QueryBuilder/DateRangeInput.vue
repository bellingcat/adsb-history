<script setup>
import { ref, watch } from 'vue';
import { useQueryStore } from '@/stores/query';
import { storeToRefs } from 'pinia';
import { VTimePicker } from 'vuetify/labs/VTimePicker';

const queryStore = useQueryStore();
const { startDate: storeStartDate, endDate: storeEndDate } = storeToRefs(queryStore);

// Date and time refs
const startDate = ref(null);
const endDate = ref(null);
const startTime = ref(null);
const endTime = ref(null);

const startTimePickerRef = ref(null);
const endTimePickerRef = ref(null);

// Clear functions
const clearStartDate = () => {
  startDate.value = null;
};

const clearStartTime = () => {
  startTime.value = null;
};

const clearEndDate = () => {
  endDate.value = null;
};

const clearEndTime = () => {
  endTime.value = null;
};

// Function to format date/time for store
const formatDateTime = (dateStr, timeStr) => {
  if (!dateStr) return null;
  
  // Create date string in YYYY-MM-DDTHH:mm format
  const timeString = timeStr || '00:00';
  return `${dateStr}T${timeString}`;
};

// Watch for changes and update the store
watch([startDate, endDate, startTime, endTime], () => {
  const formattedStart = formatDateTime(startDate.value, startTime.value);
  const formattedEnd = formatDateTime(endDate.value, endTime.value);
  
  // Only update if values are different to prevent recursive updates
  if (formattedStart !== storeStartDate.value || formattedEnd !== storeEndDate.value) {
    queryStore.updateQueryParams({
      startDate: formattedStart,
      endDate: formattedEnd,
    });
  }
});

// Watch for changes in the store and update local refs
watch([storeStartDate, storeEndDate], ([newStoreStart, newStoreEnd]) => {
  // Parse start date/time from store
  if (newStoreStart) {
    const [datePart, timePart] = newStoreStart.split('T');
    startDate.value = datePart;
    startTime.value = timePart || null;
  } else {
    startDate.value = null;
    startTime.value = null;
  }
  
  // Parse end date/time from store
  if (newStoreEnd) {
    const [datePart, timePart] = newStoreEnd.split('T');
    endDate.value = datePart;
    endTime.value = timePart || null;
  } else {
    endDate.value = null;
    endTime.value = null;
  }
}, { immediate: true });

// Format date for display
const formatDate = (date) => {
  console.log(date);
  return date ? new Date(date).toLocaleDateString() : '';
};

// Format time for display
const formatTime = (time) => {
  return time || '';
};

// Focus time picker after date selection
const focusTimePicker = (pickerRef) => {
  if (pickerRef?.value) {
    pickerRef.value.focus();
  }
};
</script>

<template>
  <v-card>
    <v-card-title>
      <v-icon icon="mdi-calendar-range"></v-icon>
      Date and Time Range
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Start Date & Time</v-label>
          <v-row>
            <v-col :cols="startDate ? 6 : 12">
              <v-menu :close-on-content-click="false">
                <template v-slot:activator="{ props }">
                  <v-text-field
                    v-bind="props"
                    :model-value="formatDate(startDate)"
                    placeholder="Select start date"
                    variant="outlined"
                    density="comfortable"
                    readonly
                    hide-details
                    :append-inner-icon="startDate ? 'mdi-close' : undefined"
                    @click:append-inner="clearStartDate"
                  ></v-text-field>
                </template>
                <v-date-picker
                  v-model="startDate"
                  :max="endDate"
                  elevation="4"
                  class="date-picker"
                  @update:model-value="focusTimePicker(startTimePickerRef)"
                  @click:month="(e) => e.stopPropagation()"
                  @click:year="(e) => e.stopPropagation()"
                  @click:day="(e) => e.stopPropagation()"
                  timezone="UTC"
                ></v-date-picker>
              </v-menu>
            </v-col>
            <v-col cols="6" v-if="startDate">
              <v-menu :close-on-content-click="false">
                <template v-slot:activator="{ props }">
                  <v-text-field
                    ref="startTimePickerRef"
                    v-bind="props"
                    :model-value="formatTime(startTime)"
                    placeholder="Time"
                    variant="outlined"
                    density="comfortable"
                    readonly
                    hide-details
                    :append-inner-icon="startTime ? 'mdi-close' : undefined"
                    @click:append-inner="clearStartTime"
                  ></v-text-field>
                </template>
                <v-time-picker
                  v-model="startTime"
                  format="24hr"
                  elevation="4"
                  class="time-picker"
                ></v-time-picker>
              </v-menu>
            </v-col>
          </v-row>
        </v-col>

        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">End Date & Time</v-label>
          <v-row>
            <v-col :cols="endDate ? 6 : 12">
              <v-menu :close-on-content-click="false">
                <template v-slot:activator="{ props }">
                  <v-text-field
                    v-bind="props"
                    :model-value="formatDate(endDate)"
                    placeholder="Select end date"
                    variant="outlined"
                    density="comfortable"
                    readonly
                    hide-details
                    :append-inner-icon="endDate ? 'mdi-close' : undefined"
                    @click:append-inner="clearEndDate"
                  ></v-text-field>
                </template>
                <v-date-picker
                  v-model="endDate"
                  :min="startDate"
                  elevation="4"
                  class="date-picker"
                  timezone="UTC"
                  @update:model-value="focusTimePicker(endTimePickerRef)"
                  @click:month="(e) => e.stopPropagation()"
                  @click:year="(e) => e.stopPropagation()"
                  @click:day="(e) => e.stopPropagation()"
                ></v-date-picker>
              </v-menu>
            </v-col>
            <v-col cols="6" v-if="endDate">
              <v-menu :close-on-content-click="false">
                <template v-slot:activator="{ props }">
                  <v-text-field
                    ref="endTimePickerRef"
                    v-bind="props"
                    :model-value="formatTime(endTime)"
                    placeholder="Time"
                    variant="outlined"
                    density="comfortable"
                    readonly
                    hide-details
                    :append-inner-icon="endTime ? 'mdi-close' : undefined"
                    @click:append-inner="clearEndTime"
                  ></v-text-field>
                </template>
                <v-time-picker
                  v-model="endTime"
                  format="24hr"
                  elevation="4"
                  class="time-picker"
                ></v-time-picker>
              </v-menu>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.v-card {
  background-color: rgb(var(--v-theme-surface));
}

.date-picker,
.time-picker {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background-color: rgb(var(--v-theme-surface));
}
</style>
