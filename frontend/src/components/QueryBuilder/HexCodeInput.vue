<script setup>
import { useQueryStore } from '../../stores/query';
import { storeToRefs } from 'pinia';

const queryStore = useQueryStore();
const { hexCode } = storeToRefs(queryStore);

const handleHexCodeChange = (value) => {
  queryStore.updateQueryParams({ hexCode: value });
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title>Aircraft Hex Code</v-card-title>
    <v-card-text>
      <v-text-field
        v-model="hexCode"
        label="Hex Code (ICAO address)"
        placeholder="e.g., a0b1c2"
        variant="outlined"
        density="comfortable"
        clearable
        hide-details
        @update:model-value="handleHexCodeChange"
      ></v-text-field>
    </v-card-text>
  </v-card>
</template> 