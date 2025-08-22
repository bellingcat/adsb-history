<script setup>
import { ref, watch } from 'vue'
import { useQueryStore } from '@/stores/query'
import { storeToRefs } from 'pinia'

const queryStore = useQueryStore()
const { minSpeed: storeMinSpeed, maxSpeed: storeMaxSpeed } = storeToRefs(queryStore)

// Speed range refs
const minSpeed = ref(storeMinSpeed.value)
const maxSpeed = ref(storeMaxSpeed.value)

// Watch for changes and update the store
watch([minSpeed, maxSpeed], ([newMin, newMax]) => {
  queryStore.updateQueryParams({
    minSpeed: newMin,
    maxSpeed: newMax
  })
})

// Watch for changes in the store and update local refs
watch([storeMinSpeed, storeMaxSpeed], ([newMin, newMax]) => {
  minSpeed.value = newMin
  maxSpeed.value = newMax
})
</script>

<template>
  <v-card>
    <v-card-title>
      <v-icon icon="mdi-speedometer"></v-icon>
      Speed Range (knots)
    </v-card-title>
    
    <v-divider></v-divider>
    
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Minimum Speed</v-label>
          <v-text-field
            v-model="minSpeed"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="0"
          ></v-text-field>
        </v-col>
        
        <v-col cols="12" sm="6">
          <v-label class="text-subtitle-2 mb-1 d-block">Maximum Speed</v-label>
          <v-text-field
            v-model="maxSpeed"
            type="number"
            variant="outlined"
            density="comfortable"
            hide-details
            placeholder="500"
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