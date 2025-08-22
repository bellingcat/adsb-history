<script setup>
import { ref, computed, watch } from 'vue';
import { useQueryStore } from '../../stores/query';
import { useUiStore } from '../../stores/ui';
import { storeToRefs } from 'pinia';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  MglMap,
  MglNavigationControl,
  MglGeoJsonSource,
  MglSymbolLayer,
  MglFillLayer,
} from 'vue-maplibre-gl';

const queryStore = useQueryStore();
const uiStore = useUiStore();
const { filteredSearchResults, boundingBoxes } = storeToRefs(queryStore);
const { hoveredAircraft } = storeToRefs(uiStore);

// Map options
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
  center: [-122.4194, 37.7749], 
  zoom: 10,
  attributionControl: true,
};

// Function to interpolate between two colors
const interpolateColor = (color1, color2, factor) => {
  // Convert hex to RGB
  const r1 = parseInt(color1.substring(1, 3), 16);
  const g1 = parseInt(color1.substring(3, 5), 16);
  const b1 = parseInt(color1.substring(5, 7), 16);

  const r2 = parseInt(color2.substring(1, 3), 16);
  const g2 = parseInt(color2.substring(3, 5), 16);
  const b2 = parseInt(color2.substring(5, 7), 16);

  // Interpolate
  const r = Math.round(r1 + (r2 - r1) * factor);
  const g = Math.round(g1 + (g2 - g1) * factor);
  const b = Math.round(b1 + (b2 - b1) * factor);

  // Convert back to hex
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
};

// Function to get color based on altitude using continuous scale
const getColorByAltitude = (altitude) => {
  // Define color stops for altitude ranges
  const colorStops = [
    { altitude: 0, color: '#1a9850' }, // Green for low altitude
    { altitude: 5000, color: '#d9ef8b' }, // Yellow-green
    { altitude: 10000, color: '#fee08b' }, // Light yellow
    { altitude: 20000, color: '#fc8d59' }, // Orange
    { altitude: 30000, color: '#d73027' }, // Red
    { altitude: 40000, color: '#b2182b' }, // Dark red for very high altitude
  ];

  // Find the appropriate color range
  for (let i = 0; i < colorStops.length - 1; i++) {
    if (altitude < colorStops[i + 1].altitude) {
      const lowerStop = colorStops[i];
      const upperStop = colorStops[i + 1];

      // Calculate interpolation factor
      const factor = (altitude - lowerStop.altitude) / (upperStop.altitude - lowerStop.altitude);

      // Interpolate between the two colors
      return interpolateColor(lowerStop.color, upperStop.color, factor);
    }
  }

  // If altitude is higher than the highest stop, return the highest color
  return colorStops[colorStops.length - 1].color;
};

// Convert search results to GeoJSON features
const mapFeatures = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return {
      type: 'FeatureCollection',
      features: [],
    };
  }

  const features = filteredSearchResults.value.results.map((result) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [result.lon, result.lat],
    },
    properties: {
      hex: result.hex,
      flight: result.flight,
      alt: result.alt,
      gs: result.gs,
      bearing: (result.bearing * 360) / (Math.PI * 2) - 90,
      t: result.t.replace('T', '\n').slice(0, 16),
      color: getColorByAltitude(result.alt),
      isHovered: hoveredAircraft.value === result.hex,
    },
  }));

  return {
    type: 'FeatureCollection',
    features: features,
  };
});

// Create GeoJSON for all bounding boxes
const boundingBoxesGeoJSON = computed(() => {
  if (!boundingBoxes.value || boundingBoxes.value.length === 0) {
    return {
      type: 'FeatureCollection',
      features: [],
    };
  }

  return {
    type: 'FeatureCollection',
    features: boundingBoxes.value.map((bbox, index) => ({
      type: 'Feature',
      properties: {
        index: index,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [bbox.minX, bbox.minY],
            [bbox.maxX, bbox.minY],
            [bbox.maxX, bbox.maxY],
            [bbox.minX, bbox.maxY],
            [bbox.minX, bbox.minY],
          ],
        ],
      },
    })),
  };
});

// Add plane icon to the map
const addPlaneIcon = (mapWrapper) => {
  // In vue-maplibre-gl, the actual map object is in the 'map' property
  const map = mapWrapper.map;

  // Load the plane icon image
  map.loadImage('/plane.png', (error, image) => {
    if (error) {
      console.error('Error loading plane icon:', error);
      return;
    }

    // Add the image to the map
    if (!map.hasImage('plane-icon')) {
      map.addImage('plane-icon', image, { sdf: true });
    }
  });
};

// Fit map to bounds when results change
const fitMapToBounds = (mapWrapper) => {
  // In vue-maplibre-gl, the actual map object is in the 'map' property
  const map = mapWrapper.map;

  if (mapFeatures.value.features.length > 0) {
    const bounds = new maplibregl.LngLatBounds();
    mapFeatures.value.features.forEach((feature) => {
      bounds.extend(feature.geometry.coordinates);
    });
    map.fitBounds(bounds, { padding: 50 });
  }
};

// Handle map load event
const onMapLoad = (mapWrapper) => {
  // Add the plane icon
  addPlaneIcon(mapWrapper);
  
  // Fit the map to the bounds
  fitMapToBounds(mapWrapper);

  // Store map reference for later use
  mapRef.value = mapWrapper.map;
  
  // Initial setup of hover events based on current number of points
  updateHoverEvents();
};

// Store map reference
const mapRef = ref(null);

// Function to update hover events based on number of points
const updateHoverEvents = () => {
  console.log('updateHoverEvents', mapFeatures.value.features.length);
  if (!mapRef.value) return;

  // Remove existing hover events
  mapRef.value.off('mouseenter', 'search-results-points');
  mapRef.value.off('mouseleave', 'search-results-points');
  mapRef.value.getCanvas().style.cursor = '';
  uiStore.setHoveredAircraft(null);

  // Only add hover events if there are 10,000 or fewer points
  if (mapFeatures.value.features.length <= 10000) {
    // Add hover events
    mapRef.value.on('mouseenter', 'search-results-points', (e) => {
      if (e.features && e.features[0]) {
        const hex = e.features[0].properties.hex;
        uiStore.setHoveredAircraft(hex);
      }
    });

    mapRef.value.on('mouseleave', 'search-results-points', () => {
      uiStore.setHoveredAircraft(null);
    });

    // Change cursor on hover
    mapRef.value.on('mouseenter', 'search-results-points', () => {
      mapRef.value.getCanvas().style.cursor = 'pointer';
    });

    mapRef.value.on('mouseleave', 'search-results-points', () => {
      mapRef.value.getCanvas().style.cursor = '';
    });
  }
};

// Watch for changes in the number of points
watch(() => mapFeatures.value.features.length, () => {
  updateHoverEvents();
});

const planePaint = {
  'icon-color': ['get', 'color'],
  'icon-halo-color': '#000000',
  'icon-halo-width': 1.2,
  'icon-halo-blur': 0.5,
};

const planeLayout = {
  'icon-image': 'plane-icon',
  'icon-size': ['case', ['get', 'isHovered'], 1.0, 0.6],
  'icon-allow-overlap': true,
  'icon-ignore-placement': true,
  'icon-rotate': ['get', 'bearing'],
};

const labelLayout = {
  'text-field': ['case', ['get', 'isHovered'], ['concat', ['get', 'hex'], ': ', ['get', 't']], ''],
  'text-size': 12,
  'text-anchor': 'right',
  'text-offset': [-0.5, 0],
  'text-allow-overlap': false,
  'text-ignore-placement': false,
  'visibility': 'visible',
};

const labelPaint = {
  'text-color': '#000000',
  'text-halo-color': '#ffffff',
  'text-halo-width': 2,
  'text-halo-blur': 1,
  'text-opacity': 1
};

const roiPaint = {
  'fill-color': '#3f51b5',
  'fill-opacity': 0.2,
  'fill-outline-color': '#000',
  'fill-antialias': true,
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title>Results Map</v-card-title>
    <v-card-text>
      <div v-if="filteredSearchResults && filteredSearchResults.results && filteredSearchResults.results.length > 0">
        <MglMap :map-style="mapOptions.style" style="height: 500px; width: 100%" @map:load="onMapLoad">
          <MglNavigationControl />

          <!-- Bounding Box Layer -->
          <MglGeoJsonSource sourceId="bounding-boxes" :data="boundingBoxesGeoJSON">
            <MglFillLayer layerId="bounding-boxes-fill" :paint="roiPaint" />
          </MglGeoJsonSource>

          <!-- GeoJSON Source with nested Symbol Layer -->
          <MglGeoJsonSource sourceId="search-results" :data="mapFeatures">
            <!-- Symbol Layer with plane icon -->
            <MglSymbolLayer
              layerId="search-results-points"
              :layout="planeLayout"
              :paint="planePaint"
            />
            <!-- Label Layer for hex codes -->
            <MglSymbolLayer
              layerId="search-results-labels"
              :layout="labelLayout"
              :paint="labelPaint"
            />
          </MglGeoJsonSource>
        </MglMap>
        
        <!-- Altitude Legend -->
        <div class="mt-2">
          <div class="d-flex align-center mb-2">
            <span class="mr-2">Altitude:</span>
            <div
              class="color-gradient"
              style="
                height: 20px;
                flex-grow: 1;
                background: linear-gradient(
                  to right,
                  #1a9850,
                  #fee08b,
                  #fc8d59,
                  #d73027,
                  #b2182b
                );
              "
            ></div>
          </div>
          <div class="d-flex justify-space-between">
            <span style="margin-left: 64px;">0 ft</span>
            <span>10,000 ft</span>
            <span>20,000 ft</span>
            <span>30,000 ft</span>
            <span>40,000+ ft</span>
          </div>
        </div>
      </div>
      <div v-else>
        <p>No search results available to display on the map.</p>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.color-gradient {
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
