<script setup>
import { useQueryStore } from '../../stores/query';
import { storeToRefs } from 'pinia';

const queryStore = useQueryStore();
const { military, category, typeCode } = storeToRefs(queryStore);

// Aircraft categories with descriptions
const categories = [
  { value: '', label: 'All' },
  { value: 'airliner', label: 'Airliners' },
  { value: 'business jet', label: 'Business jets' },
  { value: 'helicopter', label: 'Helicopters' },
  { value: 'general aviation', label: 'General aviation' },
  { value: 'uav', label: 'UAVs' },
  { value: 'transport', label: 'Military transport' },
  { value: 'fighter', label: 'Fighters' },
  { value: 'bomber', label: 'Bombers' },
  { value: 'trainer', label: 'Trainers' },
  { value: 'tanker', label: 'Tankers' },
  { value: 'reconnaissance', label: 'Reconnaissance' },
  { value: 'liaison', label: 'Liaison' },
  { value: 'maritime patrol', label: 'Maritime patrol' },
  { value: 'electronic warfare', label: 'Electronic warfare' },
  { value: 'glider', label: 'Gliders' },
  { value: 'balloon', label: 'Balloons' },
  { value: 'amphibian', label: 'Amphibious aircraft' },
  { value: 'torpedo bomber', label: 'Torpedo bombers' },
  { value: 'gyrocopter', label: 'Gyrocopters' },
  { value: 'airship', label: 'Airships' }
];

const handleMilitaryChange = (value) => {
  queryStore.updateQueryParams({ military: value });
};

const handleCategoryChange = (value) => {
  queryStore.updateQueryParams({ category: value });
  
  // Show performance warning for large categories
  if (value && ['uav', 'general aviation', 'airliner'].includes(value.toLowerCase())) {
    console.warn(`Warning: Filtering by '${value}' may be slow without additional constraints (time range, geographic bounds, etc.)`);
  }
};

const handleTypeCodeChange = (value) => {
  queryStore.updateQueryParams({ typeCode: value });
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title>Aircraft Type Filters</v-card-title>
    <v-card-text>
      <v-row>
        <v-col cols="12" md="5">
          <v-select
            v-model="category"
            :items="categories"
            item-title="label"
            item-value="value"
            label="Aircraft Category"
            @update:model-value="handleCategoryChange"
            hide-details
            variant="outlined"
          ></v-select>
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model="typeCode"
            label="Type Code"
            @update:model-value="handleTypeCodeChange"
            clearable
            hide-details
            variant="outlined"
            placeholder="e.g. B738, A320"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="3">
          <v-checkbox
            v-model="military"
            label="Military"
            @update:model-value="handleMilitaryChange"
            hide-details
          ></v-checkbox>
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
