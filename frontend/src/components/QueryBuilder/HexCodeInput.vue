<script setup>
import { ref } from 'vue';
import { useQueryStore } from '../../stores/query';
import { storeToRefs } from 'pinia';

const queryStore = useQueryStore();
const { hexCode, hexCodeList } = storeToRefs(queryStore);

const fileInput = ref(null);
const showListDialog = ref(false);

const handleHexCodeChange = (value) => {
  queryStore.updateQueryParams({ hexCode: value?.toLowerCase() ?? null });
};

const triggerFileUpload = () => {
  fileInput.value?.click();
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    // Parse line-delimited hex codes, trim whitespace, filter empty lines
    const hexCodes = content
      .split(/[\r\n]+/)
      .map(line => line.trim().toLowerCase())
      .filter(line => line && /^[0-9a-f~]+$/i.test(line));

    if (hexCodes.length > 0) {
      queryStore.updateQueryParams({
        hexCodeList: hexCodes,
        hexCode: null // Clear single hex code when list is uploaded
      });
    }
  };
  reader.readAsText(file);

  // Reset the input so the same file can be uploaded again
  event.target.value = '';
};

const clearHexList = () => {
  queryStore.updateQueryParams({ hexCodeList: [] });
};

const removeHexFromList = (hexToRemove) => {
  const newList = hexCodeList.value.filter(h => h !== hexToRemove);
  queryStore.updateQueryParams({ hexCodeList: newList });
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title>Aircraft Hex Code</v-card-title>
    <v-card-text>
      <div class="d-flex align-center gap-2">
        <v-text-field
          v-model="hexCode"
          label="Hex Code (ICAO address)"
          placeholder="e.g., a0b1c2"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          :disabled="hexCodeList && hexCodeList.length > 0"
          @update:model-value="handleHexCodeChange"
          class="flex-grow-1"
        ></v-text-field>

        <v-tooltip text="Upload list of hex codes (line-delimited)">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-upload"
              variant="outlined"
              color="primary"
              size="small"
              @click="triggerFileUpload"
              class="ml-2"
            ></v-btn>
          </template>
        </v-tooltip>

        <input
          ref="fileInput"
          type="file"
          accept=".txt,.csv"
          style="display: none"
          @change="handleFileUpload"
        />
      </div>

      <!-- Show loaded hex codes summary -->
      <div v-if="hexCodeList && hexCodeList.length > 0" class="mt-2 d-flex align-center">
        <span class="text-body-2">{{ hexCodeList.length }} hex codes loaded</span>
        <v-spacer></v-spacer>
        <v-btn
          size="x-small"
          variant="text"
          color="primary"
          @click="showListDialog = true"
        >
          View
        </v-btn>
        <v-btn
          size="x-small"
          variant="text"
          color="error"
          @click="clearHexList"
        >
          Clear
        </v-btn>
      </div>
    </v-card-text>

    <!-- Dialog to view all hex codes -->
    <v-dialog v-model="showListDialog" max-width="500">
      <v-card>
        <v-card-title>Loaded Hex Codes ({{ hexCodeList?.length || 0 }})</v-card-title>
        <v-card-text style="max-height: 400px; overflow-y: auto;">
          <v-chip
            v-for="hex in hexCodeList"
            :key="hex"
            size="small"
            closable
            class="mr-1 mb-1"
            @click:close="removeHexFromList(hex)"
          >
            {{ hex }}
          </v-chip>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showListDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
