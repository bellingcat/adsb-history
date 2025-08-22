<script setup>
import { useQueryStore } from '../../stores/query';
import { storeToRefs } from 'pinia';

const queryStore = useQueryStore();
const { flightCode } = storeToRefs(queryStore);

const handleFlightCodeChange = (value) => {
  queryStore.updateQueryParams({ flightCode: value });
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title>Flight Code</v-card-title>
    <v-card-text>
      <v-text-field
        v-model="flightCode"
        label="Flight Number/Call Sign"
        placeholder="e.g., AA123, N12345"
        variant="outlined"
        density="comfortable"
        clearable
        hide-details
        @update:model-value="handleFlightCodeChange"
      ></v-text-field>
    </v-card-text>
  </v-card>
</template> 