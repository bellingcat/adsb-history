<script setup>
import { useQueryStore } from '../../stores/query';
import { useUiStore } from '../../stores/ui';
import { useQueryHistoryStore } from '../../stores/queryHistory';
import { storeToRefs } from 'pinia';
import SearchResultsMap from './SearchResultsMap.vue';
import SearchResultsDataTable from './SearchResultsDataTable.vue';
import AircraftAggregateTable from './AircraftAggregateTable.vue';
import { ref } from 'vue';

const queryStore = useQueryStore();
const uiStore = useUiStore();
const queryHistoryStore = useQueryHistoryStore();
const { searchResults, isLargeResult } = storeToRefs(queryStore);
const { missingDataError } = storeToRefs(queryHistoryStore);
</script>

<template>
  <div>
    <v-card class="mb-4">
      <v-card-title>Search Results</v-card-title>
      <v-card-text>
        <div v-if="searchResults">
          <p class="text-h6">Total Results: {{ searchResults.count }}</p>
          <v-alert v-if="isLargeResult" type="info" class="mt-2">
            This is a large result set (over 1,000 records). Results will not be saved to the database.
          </v-alert>
        </div>
        <div v-else>
          <v-alert v-if="missingDataError" type="warning" class="mt-2">
            {{ missingDataError }}
          </v-alert>
          <v-alert v-else type="info" class="mt-2">
            No search results available. Perform a search to see results.
          </v-alert>
        </div>
      </v-card-text>
    </v-card>

    <!-- Aircraft summary table -->
    <AircraftAggregateTable />

    <!-- Map component to display results -->
    <SearchResultsMap />

    <!-- Data table component to display results -->
    <SearchResultsDataTable />
  </div>
</template>

<style scoped></style>
