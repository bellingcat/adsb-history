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
  MglCircleLayer,
  MglFillLayer,
} from 'vue-maplibre-gl';
import { getConsistentColor } from '../../utils/colors';

const queryStore = useQueryStore();
const uiStore = useUiStore();
const { filteredSearchResults, boundingBoxes } = storeToRefs(queryStore);
const { hoveredAircraft } = storeToRefs(uiStore);

// Color mode: 'altitude', 'day', 'aircraft', or 'aircraftType'
const colorMode = ref('altitude');

// Maximum number of points to render on the map (sampling applied above this)
const MAX_MAP_POINTS = 200000;

// Threshold for switching to performance mode (circles instead of plane icons)
const PERFORMANCE_MODE_THRESHOLD = 50000;

// Threshold for disabling hover effects (too many points to track)
const HOVER_DISABLED_THRESHOLD = 10000;

// Category to icon id (slug). Must match icon filenames in /icons/plane-{slug}.png
const CATEGORY_SLUGS = [
  'airliner', 'business-jet', 'helicopter', 'general-aviation', 'uav', 'transport',
  'fighter', 'bomber', 'trainer', 'tanker', 'reconnaissance', 'liaison', 'maritime-patrol',
  'electronic-warfare', 'glider', 'balloon', 'amphibian', 'torpedo-bomber', 'gyrocopter', 'airship'
];
const categoryToIconId = (category) => {
  if (!category || typeof category !== 'string') return 'plane-icon';
  const slug = category.toLowerCase().trim().replace(/\s+/g, '-');
  return CATEGORY_SLUGS.includes(slug) ? `plane-icon-${slug}` : 'plane-icon';
};

// Computed to determine if we should use performance mode
const usePerformanceMode = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results) {
    return false;
  }
  return filteredSearchResults.value.results.length > PERFORMANCE_MODE_THRESHOLD;
});

// Option to fit altitude range to data bounds
const fitAltitudeToData = ref(false);

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
  const r1 = parseInt(color1.substring(1, 3), 16);
  const g1 = parseInt(color1.substring(3, 5), 16);
  const b1 = parseInt(color1.substring(5, 7), 16);

  const r2 = parseInt(color2.substring(1, 3), 16);
  const g2 = parseInt(color2.substring(3, 5), 16);
  const b2 = parseInt(color2.substring(5, 7), 16);

  const r = Math.round(r1 + (r2 - r1) * factor);
  const g = Math.round(g1 + (g2 - g1) * factor);
  const b = Math.round(b1 + (b2 - b1) * factor);

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
};

// Calculate min and max altitude from data
const altitudeBounds = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return { min: 0, max: 40000 };
  }

  let minAlt = Infinity;
  let maxAlt = -Infinity;

  filteredSearchResults.value.results.forEach((result) => {
    if (result.alt !== null && result.alt !== undefined && result.alt !== -123) {
      if (result.alt < minAlt) minAlt = result.alt;
      if (result.alt > maxAlt) maxAlt = result.alt;
    }
  });

  if (minAlt === Infinity || maxAlt === -Infinity) {
    return { min: 0, max: 40000 };
  }

  minAlt = Math.max(0, minAlt);

  return { min: minAlt, max: maxAlt };
});

// Function to get color based on altitude using continuous scale
const getColorByAltitude = (altitude) => {
  if (altitude === null || altitude === undefined || altitude === -123) {
    return '#1a9850';
  }

  let colorStops;

  if (fitAltitudeToData.value) {
    const bounds = altitudeBounds.value;
    const range = bounds.max - bounds.min;

    const baseStops = [
      { factor: 0, color: '#1a9850' },
      { factor: 0.2, color: '#d9ef8b' },
      { factor: 0.4, color: '#fee08b' },
      { factor: 0.6, color: '#fc8d59' },
      { factor: 0.8, color: '#d73027' },
      { factor: 1.0, color: '#b2182b' },
    ];

    colorStops = baseStops.map(stop => ({
      altitude: bounds.min + (range * stop.factor),
      color: stop.color
    }));
  } else {
    colorStops = [
      { altitude: 0, color: '#1a9850' },
      { altitude: 5000, color: '#d9ef8b' },
      { altitude: 10000, color: '#fee08b' },
      { altitude: 20000, color: '#fc8d59' },
      { altitude: 30000, color: '#d73027' },
      { altitude: 40000, color: '#b2182b' },
    ];
  }

  const clampedAltitude = Math.max(colorStops[0].altitude, Math.min(altitude, colorStops[colorStops.length - 1].altitude));

  for (let i = 0; i < colorStops.length - 1; i++) {
    if (clampedAltitude <= colorStops[i + 1].altitude) {
      const lowerStop = colorStops[i];
      const upperStop = colorStops[i + 1];
      const factor = (clampedAltitude - lowerStop.altitude) / (upperStop.altitude - lowerStop.altitude);
      return interpolateColor(lowerStop.color, upperStop.color, factor);
    }
  }

  return colorStops[colorStops.length - 1].color;
};

// Get altitude legend labels and positions
const altitudeLegendLabels = computed(() => {
  if (!fitAltitudeToData.value) {
    return [
      { value: 0, position: 0 },
      { value: 10000, position: 25 },
      { value: 20000, position: 50 },
      { value: 30000, position: 75 },
      { value: 40000, position: 100, suffix: '+' },
    ];
  } else {
    const bounds = altitudeBounds.value;
    const range = bounds.max - bounds.min;
    return [
      { value: bounds.min, position: 0 },
      { value: bounds.min + range * 0.2, position: 20 },
      { value: bounds.min + range * 0.4, position: 40 },
      { value: bounds.min + range * 0.6, position: 60 },
      { value: bounds.min + range * 0.8, position: 80 },
      { value: bounds.max, position: 100 },
    ];
  }
});

// Get gradient CSS that matches the actual color stops
const altitudeGradientStyle = computed(() => {
  if (!fitAltitudeToData.value) {
    return {
      height: '20px',
      width: '100%',
      background: 'linear-gradient(to right, #1a9850 0%, #d9ef8b 12.5%, #fee08b 25%, #fc8d59 50%, #d73027 75%, #b2182b 100%)'
    };
  } else {
    return {
      height: '20px',
      width: '100%',
      background: 'linear-gradient(to right, #1a9850 0%, #d9ef8b 20%, #fee08b 40%, #fc8d59 60%, #d73027 80%, #b2182b 100%)'
    };
  }
});

// Color palette for days (distinct colors)
const dayColorPalette = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
  '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
  '#5254a3', '#6b6ecf', '#9c9ede', '#b5cf6b', '#cedb9c',
];

// Get unique days from search results and assign colors
const dayColorMap = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return new Map();
  }

  const days = new Set();
  filteredSearchResults.value.results.forEach((result) => {
    if (result.t) {
      const day = new Date(result.t).toDateString();
      days.add(day);
    }
  });

  const sortedDays = Array.from(days).sort((a, b) => {
    return new Date(a).getTime() - new Date(b).getTime();
  });
  const colorMap = new Map();
  sortedDays.forEach((day, index) => {
    colorMap.set(day, dayColorPalette[index % dayColorPalette.length]);
  });

  return colorMap;
});

// Get sorted unique days for legend
const uniqueDays = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return [];
  }

  const days = new Set();
  filteredSearchResults.value.results.forEach((result) => {
    if (result.t) {
      const day = new Date(result.t).toDateString();
      days.add(day);
    }
  });

  return Array.from(days).sort((a, b) => {
    return new Date(a).getTime() - new Date(b).getTime();
  });
});

const getColorByDay = (dateString) => {
  if (!dateString) return '#000000';
  const day = new Date(dateString).toDateString();
  return dayColorMap.value.get(day) || '#000000';
};

const getDayColor = (day) => {
  return dayColorMap.value.get(day) || '#000000';
};

// Get unique aircraft with their info for legend
const uniqueAircraft = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return [];
  }

  const aircraftMap = new Map();
  filteredSearchResults.value.results.forEach((result) => {
    if (result.hex && !aircraftMap.has(result.hex)) {
      aircraftMap.set(result.hex, {
        hex: result.hex,
        typecode: result.typecode || '-',
      });
    }
  });

  return Array.from(aircraftMap.values()).sort((a, b) =>
    a.hex.localeCompare(b.hex)
  );
});

const getColorByAircraft = (hex) => {
  return getConsistentColor(hex);
};

const getAircraftColor = (hex) => {
  return getConsistentColor(hex);
};

const getColorByAircraftType = (typecode) => {
  const type = typecode || '-';
  return getConsistentColor(type);
};

const getAircraftTypeColor = (typecode) => {
  return getColorByAircraftType(typecode);
};

// Get unique aircraft types for legend
const uniqueAircraftTypes = computed(() => {
  if (
    !filteredSearchResults.value ||
    !filteredSearchResults.value.results ||
    filteredSearchResults.value.results.length === 0
  ) {
    return [];
  }

  const typeSet = new Set();
  filteredSearchResults.value.results.forEach((result) => {
    const typecode = result.typecode || '-';
    typeSet.add(typecode);
  });

  return Array.from(typeSet).sort();
});

// Track if we're sampling data for UI feedback
const isSampled = computed(() => {
  if (!filteredSearchResults.value || !filteredSearchResults.value.results) {
    return false;
  }
  return filteredSearchResults.value.results.length > MAX_MAP_POINTS;
});

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

  const allResults = filteredSearchResults.value.results;
  const resultsCount = allResults.length;

  let resultsToRender;
  if (resultsCount > MAX_MAP_POINTS) {
    const sampleRate = Math.ceil(resultsCount / MAX_MAP_POINTS);
    resultsToRender = [];
    for (let i = 0; i < resultsCount; i += sampleRate) {
      resultsToRender.push(allResults[i]);
    }
  } else {
    resultsToRender = allResults;
  }

  const hoverEnabled = resultsCount <= HOVER_DISABLED_THRESHOLD;
  const currentHoveredHex = hoverEnabled ? hoveredAircraft.value : null;

  const features = resultsToRender
    .filter((result) => result.lat != null && result.lon != null)
    .map((result) => ({
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
        t: result.t ? result.t.replace('T', '\n').slice(0, 16) : '',
        typecode: result.typecode || '-',
        iconImage: categoryToIconId(result.category),
        color: colorMode.value === 'day'
          ? getColorByDay(result.t)
          : colorMode.value === 'aircraft'
          ? getColorByAircraft(result.hex)
          : colorMode.value === 'aircraftType'
          ? getColorByAircraftType(result.typecode)
          : getColorByAltitude(result.alt),
        isHovered: currentHoveredHex === result.hex,
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

// Add plane icons (default + per-category) to the map
const addPlaneIcons = (mapWrapper) => {
  const map = mapWrapper.map;

  const loadImage = (url) =>
    new Promise((resolve, reject) => {
      map.loadImage(url, (err, image) => (err ? reject(err) : resolve(image)));
    });

  const addImage = (id, image) => {
    if (!map.hasImage(id)) {
      map.addImage(id, image, { sdf: true });
    }
  };

  loadImage('/plane.png')
    .then((image) => {
      addImage('plane-icon', image);
      return Promise.all(
        CATEGORY_SLUGS.map((slug) =>
          loadImage(`/icons/plane-${slug}.png`)
            .then((img) => addImage(`plane-icon-${slug}`, img))
            .catch(() => { /* missing icon falls back to plane-icon via coalesce */ })
        )
      );
    })
    .catch((err) => console.error('Error loading plane icon:', err));
};

// Fit map to bounds when results change
const fitMapToBounds = (mapWrapper) => {
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
  addPlaneIcons(mapWrapper);
  fitMapToBounds(mapWrapper);

  mapRef.value = mapWrapper.map;

  updateHoverEvents();
};

// Store map reference
const mapRef = ref(null);

// Function to update hover events based on number of points
const updateHoverEvents = () => {
  if (!mapRef.value) return;

  mapRef.value.off('mouseenter', 'search-results-points');
  mapRef.value.off('mouseleave', 'search-results-points');
  mapRef.value.getCanvas().style.cursor = '';
  uiStore.setHoveredAircraft(null);

  if (mapFeatures.value.features.length <= HOVER_DISABLED_THRESHOLD) {
    mapRef.value.on('mouseenter', 'search-results-points', (e) => {
      if (e.features && e.features[0]) {
        const hex = e.features[0].properties.hex;
        uiStore.setHoveredAircraft(hex);
      }
    });

    mapRef.value.on('mouseleave', 'search-results-points', () => {
      uiStore.setHoveredAircraft(null);
    });

    mapRef.value.on('mouseenter', 'search-results-points', () => {
      mapRef.value.getCanvas().style.cursor = 'pointer';
    });

    mapRef.value.on('mouseleave', 'search-results-points', () => {
      mapRef.value.getCanvas().style.cursor = '';
    });
  }
};

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
  'icon-image': ['coalesce', ['image', ['get', 'iconImage']], 'plane-icon'],
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

// Circle layer paint for performance mode (large datasets)
const circlePaint = {
  'circle-radius': 3,
  'circle-color': ['get', 'color'],
  'circle-stroke-color': '#000000',
  'circle-stroke-width': 0.5,
  'circle-opacity': 0.8,
};
</script>

<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>
        Results Map
        <v-chip v-if="isSampled" size="x-small" color="warning" class="ml-2">
          Showing ~{{ MAX_MAP_POINTS.toLocaleString() }} of {{ filteredSearchResults?.count?.toLocaleString() }} points
        </v-chip>
        <v-chip v-else-if="usePerformanceMode" size="x-small" color="info" class="ml-2">
          {{ filteredSearchResults?.count?.toLocaleString() }} points
        </v-chip>
      </span>
      <v-btn-toggle
        v-model="colorMode"
        mandatory
        density="compact"
        variant="outlined"
      >
        <v-btn value="altitude" size="small">
          Color by Altitude
        </v-btn>
        <v-btn value="day" size="small">
          Color by Day
        </v-btn>
        <v-btn value="aircraft" size="small">
          Color by Aircraft
        </v-btn>
        <v-btn value="aircraftType" size="small">
          Color by Type
        </v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-card-text>
      <div v-if="filteredSearchResults && filteredSearchResults.results && filteredSearchResults.results.length > 0">
        <MglMap :map-style="mapOptions.style" style="height: 500px; width: 100%" @map:load="onMapLoad">
          <MglNavigationControl />

          <!-- Bounding Box Layer -->
          <MglGeoJsonSource sourceId="bounding-boxes" :data="boundingBoxesGeoJSON">
            <MglFillLayer layerId="bounding-boxes-fill" :paint="roiPaint" />
          </MglGeoJsonSource>

          <!-- GeoJSON Source with nested Symbol Layer or Circle Layer (performance mode) -->
          <MglGeoJsonSource sourceId="search-results" :data="mapFeatures">
            <!-- Circle Layer for performance mode (large datasets) -->
            <MglCircleLayer
              v-if="usePerformanceMode"
              layerId="search-results-points"
              :paint="circlePaint"
            />
            <!-- Symbol Layer with plane icon (normal mode) -->
            <template v-else>
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
            </template>
          </MglGeoJsonSource>
        </MglMap>

        <!-- Altitude Legend -->
        <div v-if="colorMode === 'altitude'" class="mt-2">
          <div class="d-flex align-center mb-2">
            <span class="mr-2">Altitude:</span>
            <v-checkbox
              v-model="fitAltitudeToData"
              label="Fit to data range"
              density="compact"
              hide-details
              class="mr-2"
              style="flex-shrink: 0;"
            ></v-checkbox>
            <div class="legend-container" style="flex-grow: 1; position: relative;">
              <div
                class="color-gradient"
                :style="altitudeGradientStyle"
              ></div>
              <div class="legend-labels">
                <span
                  v-for="(label, index) in altitudeLegendLabels"
                  :key="index"
                  :style="{
                    left: label.position + '%',
                    transform: index === 0 ? 'translateX(0)' : index === altitudeLegendLabels.length - 1 ? 'translateX(-100%)' : 'translateX(-50%)'
                  }"
                >
                  {{ Math.round(label.value).toLocaleString() }}{{ label.suffix || '' }} ft
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Day Legend -->
        <div v-if="colorMode === 'day'" class="mt-2">
          <div class="mb-2">
            <span class="mr-2">Day:</span>
          </div>
          <div class="d-flex flex-wrap gap-2">
            <div
              v-for="day in uniqueDays"
              :key="day"
              class="d-flex align-center mr-3 mb-1"
            >
              <div
                class="day-color-box mr-1"
                :style="{ backgroundColor: getDayColor(day) }"
              ></div>
              <span style="font-size: 12px;">{{ day }}</span>
            </div>
          </div>
        </div>

        <!-- Aircraft Legend -->
        <div v-if="colorMode === 'aircraft'" class="mt-2">
          <div class="mb-2">
            <span class="mr-2">Aircraft:</span>
          </div>
          <div class="d-flex flex-wrap gap-2" style="max-height: 200px; overflow-y: auto;">
            <div
              v-for="aircraft in uniqueAircraft"
              :key="aircraft.hex"
              class="d-flex align-center mr-3 mb-1"
            >
              <div
                class="day-color-box mr-1"
                :style="{ backgroundColor: getAircraftColor(aircraft.hex) }"
              ></div>
              <span style="font-size: 12px;">{{ aircraft.hex }} ({{ aircraft.typecode }})</span>
            </div>
          </div>
        </div>

        <!-- Aircraft Type Legend -->
        <div v-if="colorMode === 'aircraftType'" class="mt-2">
          <div class="mb-2">
            <span class="mr-2">Aircraft Type:</span>
          </div>
          <div class="d-flex flex-wrap gap-2" style="max-height: 200px; overflow-y: auto;">
            <div
              v-for="typecode in uniqueAircraftTypes"
              :key="typecode"
              class="d-flex align-center mr-3 mb-1"
            >
              <div
                class="day-color-box mr-1"
                :style="{ backgroundColor: getAircraftTypeColor(typecode) }"
              ></div>
              <span style="font-size: 12px;">{{ typecode }}</span>
            </div>
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

.day-color-box {
  width: 16px;
  height: 16px;
  border: 1px solid #ccc;
  border-radius: 3px;
  display: inline-block;
}

.legend-container {
  position: relative;
}

.legend-labels {
  position: relative;
  width: 100%;
  margin-top: 4px;
}

.legend-labels span {
  position: absolute;
  font-size: 12px;
  white-space: nowrap;
}
</style>
