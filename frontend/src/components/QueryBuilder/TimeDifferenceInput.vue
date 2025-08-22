<script setup>
import { ref, watch, computed } from 'vue'
import { useQueryStore } from '@/stores/query'
import { storeToRefs } from 'pinia'

const queryStore = useQueryStore()
const { rois, minTimeDiff: storeMinTimeDiff, maxTimeDiff: storeMaxTimeDiff } = storeToRefs(queryStore)

// Time difference refs
const minTimeDiff = ref(storeMinTimeDiff.value)
const maxTimeDiff = ref(storeMaxTimeDiff.value)

// Computed property to check if component should be shown
const shouldShow = computed(() => rois.value.length === 2)

// Watch for changes and update the store
watch([minTimeDiff, maxTimeDiff], ([newMin, newMax]) => {
  queryStore.updateQueryParams({
    minTimeDiff: newMin,
    maxTimeDiff: newMax
  })
})

// Watch for changes in the store and update local refs
watch([storeMinTimeDiff, storeMaxTimeDiff], ([newMin, newMax]) => {
  minTimeDiff.value = newMin
  maxTimeDiff.value = newMax
})
</script>

<template>
  <v-card v-if="shouldShow">
    <v-card-title>
      <v-icon icon="mdi-clock-time-four"></v-icon>
      Time Difference Between ROIs (seconds)
    </v-card-title>
    
    <v-divider></v-divider>
    
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Minimum Time Difference</v-label>
          <v-text-field
            v-model="minTimeDiff"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="0"
          ></v-text-field>
        </v-col>
        
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Maximum Time Difference</v-label>
          <v-text-field
            v-model="maxTimeDiff"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="86400"
          ></v-text-field>
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