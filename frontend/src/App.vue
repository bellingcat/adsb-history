<script setup>
import DateRangeInput from './components/QueryBuilder/DateRangeInput.vue';
import AltitudeRangeInput from './components/QueryBuilder/AltitudeRangeInput.vue';
import SpeedRangeInput from './components/QueryBuilder/SpeedRangeInput.vue';
import ROIMultiSelectInput from './components/QueryBuilder/ROIMultiSelectInput.vue';
import BearingRangeInput from './components/QueryBuilder/BearingRangeInput.vue';
import HexCodeInput from './components/QueryBuilder/HexCodeInput.vue';
import FlightCodeInput from './components/QueryBuilder/FlightCodeInput.vue';
import AircraftTypeFilters from './components/QueryBuilder/AircraftTypeFilters.vue';
import SearchResults from './components/SearchResults/SearchResults.vue';
import PlanesPerDayChart from './components/SearchResults/PlanesPerDayChart.vue';
import SearchControls from './components/QueryBuilder/SearchControls.vue';
import QueryHistory from './components/QueryHistory.vue';
import TimeDifferenceInput from './components/QueryBuilder/TimeDifferenceInput.vue';
import InfoBox from './components/QueryBuilder/InfoBox.vue';
import AuthGuard from './components/AuthGuard.vue';
import Auth from './components/Auth.vue';
import { useAuthStore } from './stores/auth';
import { onMounted } from 'vue';

const authStore = useAuthStore();

onMounted(() => {
  authStore.initAuth();
});
</script>

<template>
  <v-layout>
    <v-app-bar title="ADS-B History Search">
      <template v-slot:append>
        <Auth />
      </template>
    </v-app-bar>

    <AuthGuard>
      <v-navigation-drawer width="300">
        <QueryHistory />
      </v-navigation-drawer>

      <v-main class="d-flex align-center justify-center">
        <v-container>
          <v-row>
            <v-col cols="12" md="6">
              <v-row>
                <v-col cols="6">
                  <HexCodeInput class="mb-4" />
                </v-col>
                <v-col cols="6">
                  <FlightCodeInput class="mb-4" />
                </v-col>
              </v-row>
              <AircraftTypeFilters class="mb-4" />
              <ROIMultiSelectInput class="mb-4" />
              <TimeDifferenceInput class="mb-4" />
            </v-col>
            <v-col cols="12" md="6">
              <InfoBox class="mb-4" />
              <DateRangeInput class="mb-4" />
              <AltitudeRangeInput class="mb-4" />
              <SpeedRangeInput class="mb-4" />
              <BearingRangeInput class="mb-4" />
            </v-col>
          </v-row>
          <v-row class="mt-4">
            <v-col cols="12" md="4" offset-md="4">
              <SearchControls />
            </v-col>
          </v-row>

          <!-- Search Results Section -->
          <v-row class="mt-4">
            <v-col cols="12">
              <PlanesPerDayChart />
              <SearchResults />
            </v-col>
          </v-row>
        </v-container>
      </v-main>
    </AuthGuard>
  </v-layout>
</template>

<style></style>
