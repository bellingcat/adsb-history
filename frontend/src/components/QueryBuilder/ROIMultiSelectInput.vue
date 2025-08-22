<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useQueryStore } from '@/stores/query';
import { storeToRefs } from 'pinia';
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import 'maplibre-gl/dist/maplibre-gl.css';

// MapLibre 2.3 specific configuration
MapboxDraw.constants.classes.CONTROL_BASE = 'maplibregl-ctrl';
MapboxDraw.constants.classes.CONTROL_PREFIX = 'maplibregl-ctrl-';
MapboxDraw.constants.classes.CONTROL_GROUP = 'maplibregl-ctrl-group';

const queryStore = useQueryStore();
const { rois } = storeToRefs(queryStore);
const mapRef = ref(null);
const drawRef = ref(null);
const center = ref([-122.4194, 37.7749]);
const zoom = ref(10);

// Function to delete all ROIs
const deleteAllROIs = () => {
  if (drawRef.value) {
    const features = drawRef.value.getAll();
    features.features.forEach((feature) => {
      drawRef.value.delete(feature.id);
    });
    queryStore.updateQueryParams({ rois: [] });
  }
};

// Map options for MapLibre 2.3
const mapOptions = {
  style: {
    version: 8,
    sources: {
      'osm-tiles': {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors'
      }
    },
    "glyphs": "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    layers: [
      {
        id: 'osm-tiles',
        type: 'raster',
        source: 'osm-tiles',
        minzoom: 0,
        maxzoom: 19
      }
    ]
  },
  center: [-122.4194, 37.7749], // San Francisco coordinates
  zoom: 10,
  attributionControl: true,
  transformRequest: (url, resourceType) => {
    if (resourceType === 'Source' || resourceType === 'Style') {
      return {
        url,
        credentials: 'include',
      };
    }
    return { url };
  },
};

// Draw control options
const drawOptions = {
  displayControlsDefault: false,
  controls: {
    polygon: true,
    trash: true,
  },
  styles: [
    {
      id: 'gl-draw-polygon-fill',
      type: 'fill',
      filter: ['all', ['==', '$type', 'Polygon']],
      paint: {
        'fill-color': '#3bb2d0',
        'fill-outline-color': '#3bb2d0',
        'fill-opacity': 0.1,
      },
    },
    {
      id: 'gl-draw-polygon-stroke',
      type: 'line',
      filter: ['all', ['==', '$type', 'Polygon']],
      paint: {
        'line-color': '#3bb2d0',
        'line-width': 2,
      },
    },
    {
      id: 'gl-draw-lines',
      type: 'line',
      filter: ['all', ['==', '$type', 'LineString'], ['!=', 'mode', 'static']],
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
      },
      paint: {
        'line-color': '#3bb2d0',
        'line-width': 2,
        'line-dasharray': ['literal', [2, 2]],
      },
    },
    {
      id: 'gl-draw-points',
      type: 'circle',
      filter: ['all', ['==', '$type', 'Point'], ['==', 'meta', 'vertex']],
      paint: {
        'circle-radius': 5,
        'circle-color': '#fff',
        'circle-stroke-color': '#3bb2d0',
        'circle-stroke-width': 2,
      },
    },
    {
      id: 'gl-draw-points-active',
      type: 'circle',
      filter: ['all', ['==', '$type', 'Point'], ['==', 'meta', 'vertex'], ['==', 'active', 'true']],
      paint: {
        'circle-radius': 7,
        'circle-color': '#fff',
        'circle-stroke-color': '#3bb2d0',
        'circle-stroke-width': 2,
      },
    },
  ],
};

// Update ROIs in the store when features change
const updateROIs = (e) => {
  const features = drawRef.value.getAll();
  queryStore.updateQueryParams({
    rois: features.features.map((feature) => ({
      type: 'Polygon',
      coordinates: feature.geometry.coordinates,
    })),
  });
};

// Initialize draw control after map is loaded
const onMapLoad = (map) => {
  mapRef.value = map.map;

  drawRef.value = new MapboxDraw(drawOptions);
  map.map.addControl(drawRef.value, 'top-left');

  // Add event listeners
  map.map.on('draw.create', updateROIs);
  map.map.on('draw.update', updateROIs);
  map.map.on('draw.delete', updateROIs);
  
  // Add event listener to check ROI count before allowing new ROIs
  map.map.on('draw.modechange', (e) => {
    if (e.mode === 'draw_polygon') {
      const features = drawRef.value.getAll();
      if (features.features.length > 2) {
        // If already have 2 ROIs, prevent drawing more
        drawRef.value.changeMode('simple_select');
        alert('Maximum of 2 ROIs allowed. Please delete an existing ROI before adding a new one.');
      }
    }
  });
};

// Watch for changes in the query store's ROIs
watch(
  rois,
  (newRois) => {
    if (drawRef.value && newRois) {
      // Clear existing features
      const features = drawRef.value.getAll();
      features.features.forEach((feature) => {
        drawRef.value.delete(feature.id);
      });

      // Add new features
      newRois.forEach((roi) => {
        drawRef.value.add({
          type: 'Feature',
          properties: {},
          geometry: roi,
        });
      });
    }
  },
  { immediate: true },
);

// Cleanup on component unmount
onUnmounted(() => {
  if (mapRef.value && drawRef.value) {
    try {
      // Remove event listeners first
      mapRef.value.off('draw.create', updateROIs);
      mapRef.value.off('draw.update', updateROIs);
      mapRef.value.off('draw.delete', updateROIs);
      mapRef.value.off('draw.modechange');

      // Instead of using removeControl, manually remove the control's elements
      const controlContainer = drawRef.value._container;
      if (controlContainer && controlContainer.parentNode) {
        controlContainer.parentNode.removeChild(controlContainer);
      }

      // Clear references
      drawRef.value = null;
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }
});
</script>

<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <div class="d-flex align-center">
        <v-icon icon="mdi-map-marker-multiple"></v-icon>
        Region of Interest
      </div>
      <v-btn
        color="error"
        variant="tonal"
        size="small"
        @click="deleteAllROIs"
        :disabled="!rois.length"
      >
        <v-icon start icon="mdi-delete"></v-icon>
        Delete All
      </v-btn>
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text>
      <MglMap
        :center="center"
        :zoom="zoom"
        style="height: 534px; width: 100%"
        @map:load="onMapLoad"
        :map-style="mapOptions.style"
      >
        <mgl-navigation-control />
      </MglMap>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.v-card {
  background-color: rgb(var(--v-theme-surface));
}
</style>
