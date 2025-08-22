<script setup>
import { ref, watch } from 'vue'
import { useQueryStore } from '@/stores/query'
import { storeToRefs } from 'pinia'

const queryStore = useQueryStore()
const { minAltitude: storeMinAltitude, maxAltitude: storeMaxAltitude } = storeToRefs(queryStore)

// Altitude range refs
const minAltitude = ref(storeMinAltitude.value)
const maxAltitude = ref(storeMaxAltitude.value)

// Watch for changes and update the store
watch([minAltitude, maxAltitude], ([newMin, newMax]) => {
  queryStore.updateQueryParams({
    minAltitude: newMin,
    maxAltitude: newMax
  })
})

// Watch for changes in the store and update local refs
watch([storeMinAltitude, storeMaxAltitude], ([newMin, newMax]) => {
  minAltitude.value = newMin
  maxAltitude.value = newMax
})
</script>

<template>
  <v-card>
    <v-card-title>
      <v-icon icon="mdi-altitude"></v-icon>
      Altitude Range (feet)
    </v-card-title>
    
    <v-divider></v-divider>
    
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Minimum Altitude</v-label>
          <v-text-field
            v-model="minAltitude"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="0"
          ></v-text-field>
        </v-col>
        
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Maximum Altitude</v-label>
          <v-text-field
            v-model="maxAltitude"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="45000"
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