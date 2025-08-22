<script setup>
import { useQueryStore } from '@/stores/query';
import { useQueryHistoryStore } from '@/stores/queryHistory';
import { storeToRefs } from 'pinia';
import { ref, nextTick, onMounted } from 'vue';

const queryStore = useQueryStore();
const queryHistoryStore = useQueryHistoryStore();
const { metadata, isLoading, error } = storeToRefs(queryHistoryStore);

const editingQueryId = ref(null);
const editName = ref('');
const nameInputRef = ref(null);

// Load history when component is mounted
onMounted(async () => {
  await queryHistoryStore.loadHistory();
});

const loadHistoricalQuery = async (queryId) => {
  console.log('loadHistoricalQuery', queryId);
  const query = await queryHistoryStore.loadQuery(queryId);
  if (query) {
    queryStore.updateQueryParams(query.params);
    queryStore.searchResults = query.results;
    queryStore.isLargeResult = query.isLargeResult;
  }
};

const deleteQuery = (queryId, event) => {
  event.stopPropagation(); // Prevent triggering the load query
  queryHistoryStore.deleteQuery(queryId);
};

const startEditing = async (query, event) => {
  event.stopPropagation();
  editingQueryId.value = query.id;
  editName.value = query.name || '';
  await nextTick();
  nameInputRef.value?.focus();
};

const saveEdit = (queryId, event) => {
  event.stopPropagation();
  queryHistoryStore.updateQueryName(queryId, editName.value);
  editingQueryId.value = null;
};

const cancelEdit = (event) => {
  event.stopPropagation();
  editingQueryId.value = null;
};

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString();
};

const formatRoiCount = (count) => {
  return `${count} ${count === 1 ? 'ROI' : 'ROIs'}`;
};

const getQueryTitle = (query) => {
  if (query.name) return query.name;
  return `${formatRoiCount(query.params.rois.length)}${query.params.hexCode ? ' | ' + query.params.hexCode : ''}${query.params.flightCode ? ' | ' + query.params.flightCode : ''}`;
};
</script>

<template>
  <v-list nav>
    <v-list-item
      title="New Search"
      @click="queryStore.resetQueryParams()"
    >
      <template v-slot:prepend>
        <v-icon>mdi-magnify</v-icon>
      </template>
    </v-list-item>
    <v-divider class="my-2"></v-divider>
    
    <!-- Loading state -->
    <v-list-item v-if="isLoading">
      <template v-slot:prepend>
        <v-progress-circular indeterminate></v-progress-circular>
      </template>
      <v-list-item-title>Loading history...</v-list-item-title>
    </v-list-item>
    
    <!-- Error state -->
    <v-alert
      v-if="error"
      type="error"
      class="ma-2"
    >
      {{ error }}
    </v-alert>
    
    <!-- History items -->
    <v-list-item
      v-for="query in metadata"
      :key="query.id"
      :title="getQueryTitle(query)"
      @click="loadHistoricalQuery(query.id)"
    >
      <template v-slot:prepend>
        <v-icon>mdi-history</v-icon>
      </template>
      <template v-slot:append>
        <v-btn
          v-if="editingQueryId !== query.id"
          icon="mdi-pencil"
          variant="text"
          size="small"
          @click="startEditing(query, $event)"
        ></v-btn>
        <v-btn
          icon="mdi-delete"
          variant="text"
          size="small"
          @click="deleteQuery(query.id, $event)"
        ></v-btn>
      </template>
      <template v-slot:subtitle>
        <div v-if="editingQueryId === query.id" class="d-flex align-center">
          <v-text-field
            ref="nameInputRef"
            v-model="editName"
            density="comfortable"
            variant="outlined"
            placeholder="Name"
            hide-details
            class="edit-name-field"
            @keyup.enter="saveEdit(query.id, $event)"
            @keyup.esc="cancelEdit($event)"
          ></v-text-field>
          <v-btn
            icon="mdi-check"
            variant="text"
            size="small"
            color="success"
            @click="saveEdit(query.id, $event)"
          ></v-btn>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            color="error"
            @click="cancelEdit($event)"
          ></v-btn>
        </div>
        <div v-else>
          <div>{{ formatDate(query.timestamp) }}</div>
          <div>{{ query.resultCount }} results</div>
          <div v-if="query.isLargeResult" class="text-caption text-info">
            <v-icon size="small" color="info">mdi-information</v-icon>
            Stored locally
          </div>
        </div>
      </template>
    </v-list-item>
    <v-divider class="my-2"></v-divider>
    <v-list-item
      v-if="metadata.length > 0"
      title="Clear History"
      @click="queryHistoryStore.clearHistory()"
    >
      <template v-slot:prepend>
        <v-icon>mdi-delete</v-icon>
      </template>
    </v-list-item>
  </v-list>
</template>

<style>
.v-list-item-subtitle {
  height: 30px !important;
  white-space: nowrap;
}

.edit-name-field {
  flex-grow: 1;
  margin-right: 8px;
  margin-top: -8px;
}

.edit-name-field .v-field__input {
  font-size: 0.8rem;
  padding-top: 0;
  padding-bottom: 0;
  line-height: 1.2;
}

.edit-name-field .v-field {
  background-color: rgb(var(--v-theme-surface));
  min-height: 24px;
  padding-top: 0;
  padding-bottom: 0;
}

.edit-name-field .v-field__input {
  min-height: 24px;
}

.edit-name-field .v-field__field {
  padding-top: 0;
  padding-bottom: 0;
}
</style>