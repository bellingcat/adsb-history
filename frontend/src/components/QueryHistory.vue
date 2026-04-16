<script setup>
import { useQueryStore } from '@/stores/query';
import { useQueryHistoryStore } from '@/stores/queryHistory';
import { useUiStore } from '@/stores/ui';
import { storeToRefs } from 'pinia';
import { ref, nextTick, onMounted } from 'vue';
import { isAuthDisabled } from '@/firebase';
import { getQueryHistoryBackup, saveQueryHistoryBackup } from '@/services/api';

const queryStore = useQueryStore();
const queryHistoryStore = useQueryHistoryStore();
const uiStore = useUiStore();
const { metadata, isLoading, error } = storeToRefs(queryHistoryStore);

const editingQueryId = ref(null);
const editName = ref('');
const nameInputRef = ref(null);
const backupRestoreMessage = ref('');
const backupRestoreLoading = ref(false);

const saveToDataFolder = async () => {
  backupRestoreLoading.value = true;
  backupRestoreMessage.value = '';
  try {
    const data = await queryHistoryStore.exportForBackup();
    if (!data) {
      backupRestoreMessage.value = 'Only available when using local history (no Firebase).';
      return;
    }
    await saveQueryHistoryBackup(data);
    backupRestoreMessage.value = 'Saved to data/query-history-backup.json';
  } catch (e) {
    backupRestoreMessage.value = e.response?.data?.error || e.message || 'Save failed';
  } finally {
    backupRestoreLoading.value = false;
  }
};

const restoreFromDataFolder = async () => {
  backupRestoreLoading.value = true;
  backupRestoreMessage.value = '';
  try {
    const data = await getQueryHistoryBackup();
    await queryHistoryStore.restoreFromBackup(data);
    backupRestoreMessage.value = 'Restored from data folder.';
  } catch (e) {
    backupRestoreMessage.value = e.response?.status === 404 ? 'No backup file found.' : (e.response?.data?.error || e.message || 'Restore failed');
  } finally {
    backupRestoreLoading.value = false;
  }
};

// Load history when component is mounted
onMounted(async () => {
  await queryHistoryStore.loadHistory();
});

const loadHistoricalQuery = async (queryId) => {
  const query = await queryHistoryStore.loadQuery(queryId);
  if (query) {
    queryStore.updateQueryParams(query.params);
    queryStore.searchResults = query.results;
    queryStore.isLargeResult = query.isLargeResult;

    if (query.selectedAircraft && query.selectedAircraft.length > 0) {
      uiStore.setSelectedAircraft(new Set(query.selectedAircraft));
    }
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
  const hexInfo = query.params.hexCodeList?.length > 0
    ? ` | ${query.params.hexCodeList.length} hex codes`
    : (query.params.hexCode ? ' | ' + query.params.hexCode : '');
  return `${formatRoiCount(query.params.rois.length)}${hexInfo}${query.params.flightCode ? ' | ' + query.params.flightCode : ''}`;
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
    <template v-if="isAuthDisabled">
      <v-divider class="my-2"></v-divider>
      <v-list-item
        title="Save to data folder"
        :disabled="backupRestoreLoading"
        @click="saveToDataFolder"
      >
        <template v-slot:prepend>
          <v-progress-circular v-if="backupRestoreLoading" indeterminate size="20"></v-progress-circular>
          <v-icon v-else>mdi-content-save</v-icon>
        </template>
      </v-list-item>
      <v-list-item
        title="Restore from data folder"
        :disabled="backupRestoreLoading"
        @click="restoreFromDataFolder"
      >
        <template v-slot:prepend>
          <v-icon>mdi-folder-download</v-icon>
        </template>
      </v-list-item>
      <v-alert v-if="backupRestoreMessage" type="info" density="compact" class="ma-2" closable>
        {{ backupRestoreMessage }}
      </v-alert>
    </template>
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