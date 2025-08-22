<script setup>
import { useQueryStore } from '@/stores/query';
import { useQueryHistoryStore } from '@/stores/queryHistory';
import { storeToRefs } from 'pinia';

const queryStore = useQueryStore();
const queryHistoryStore = useQueryHistoryStore();
const { isLoading, error, resultLimit } = storeToRefs(queryStore);

const handleResultLimitChange = (value) => {
  queryStore.updateQueryParams({ resultLimit: value });
};

const handleSearch = async () => {
  await queryStore.search();
  // The history adding logic will be moved to the store action
};
</script>

<template>
  <div>
    <v-card class="pa-4">
      <!-- <v-card-title class="text-h6 text-center mb-4">
        Search Controls
      </v-card-title> -->
      <v-card-text>
        <v-select
          v-model="resultLimit"
          :items="[
            { title: '1,000 results', value: 1000 },
            { title: '10,000 results', value: 10000 },
            { title: '100,000 results', value: 100000 },
            { title: '1,000,000 results', value: 1000000 }
          ]"
          label="Result Limit"
          variant="outlined"
          density="comfortable"
          class="mb-4"
          hide-details
          @update:model-value="handleResultLimitChange"
        ></v-select>
        <v-btn
          color="primary"
          size="large"
          block
          @click="handleSearch"
          :loading="isLoading"
        >
          Search
        </v-btn>
      </v-card-text>
    </v-card>
    <v-alert
      v-if="error"
      type="error"
      class="mt-4"
    >
      {{ error }}
    </v-alert>
  </div>
</template> 