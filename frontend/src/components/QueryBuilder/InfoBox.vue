<template>
    <v-card>
        <v-card-title>
            <v-icon icon="mdi-information-outline"></v-icon>
            Information 
        </v-card-title>
        <v-card-text>
            <p>
                All parameters are optional. ROIs are converted to rectangular bounding boxes. If two ROIs are selected, the search will return aircraft seen in both ROIs (optionally within a time window). Searches may take several minutes to complete. Reducing the size of ROIs or filtering by altitude or speed can decrease search time.
            </p>
        </v-card-text>
    </v-card>
</template>

<style scoped>
.v-card {
  background-color: rgb(var(--v-theme-surface));
}

.date-picker, .time-picker {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background-color: rgb(var(--v-theme-surface));
}
</style>

