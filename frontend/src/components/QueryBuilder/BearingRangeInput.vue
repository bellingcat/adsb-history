<script setup>
import { ref, watch, computed } from 'vue'
import { useQueryStore } from '@/stores/query'
import { storeToRefs } from 'pinia'
import CompassDial from './CompassDial.vue'

const queryStore = useQueryStore()
const { minBearing: storeMinBearing, maxBearing: storeMaxBearing } = storeToRefs(queryStore)

// Bearing range refs
const minBearing = ref(storeMinBearing.value)
const maxBearing = ref(storeMaxBearing.value)

// Computed properties for validation
const minBearingError = computed(() => {
  if (minBearing.value === null || minBearing.value === '') return false
  const value = Number(minBearing.value)
  return isNaN(value) || value < 0 || value > 360
})

const maxBearingError = computed(() => {
  if (maxBearing.value === null || maxBearing.value === '') return false
  const value = Number(maxBearing.value)
  return isNaN(value) || value < 0 || value > 360
})

// Watch for changes and update the store
watch([minBearing, maxBearing], ([newMin, newMax]) => {
  // Only update if values are valid
  if (!minBearingError.value && !maxBearingError.value) {
    queryStore.updateQueryParams({
      minBearing: newMin,
      maxBearing: newMax
    })
  }
})

// Watch for changes in the store and update local refs
watch([storeMinBearing, storeMaxBearing], ([newMin, newMax]) => {
  minBearing.value = newMin
  maxBearing.value = newMax
})
</script>

<template>
  <v-card>
    <v-card-title>
      <v-icon icon="mdi-compass"></v-icon>
      Bearing Range (degrees)
    </v-card-title>
    
    <v-divider></v-divider>
    
    <v-card-text>
      <v-row align="center">
        <v-col cols="12" sm="5">
          <v-label class="text-subtitle-2 mb-1 d-block">Minimum Bearing</v-label>
          <v-text-field
            v-model="minBearing"
            type="number"
            variant="outlined"
            density="comfortable"
            :error-messages="minBearingError ? 'Value must be between 0 and 360' : ''"
            :error="minBearingError"
            min="0"
            max="360"
            placeholder="0"
          ></v-text-field>
        </v-col>
        
        <v-col cols="12" sm="5">
          <v-label class="text-subtitle-2 mb-1 d-block">Maximum Bearing</v-label>
          <v-text-field
            v-model="maxBearing"
            type="number"
            variant="outlined"
            density="comfortable"
            :error-messages="maxBearingError ? 'Value must be between 0 and 360' : ''"
            :error="maxBearingError"
            min="0"
            max="360"
            placeholder="360"
          ></v-text-field>
        </v-col>

        <v-col cols="12" sm="2" class="d-flex justify-center">
          <CompassDial
            :min-bearing="minBearing"
            :max-bearing="maxBearing"
            :size="70"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.v-card {
  background-color: rgb(var(--v-theme-surface));
}
</style> 