<script setup>
import { computed } from 'vue';

const props = defineProps({
  minBearing: {
    type: Number,
    default: 0,
  },
  maxBearing: {
    type: Number,
    default: 360,
  },
  size: {
    type: Number,
    default: 100,
  },
});

// Helper function to clip value to 0-360 range
const clipToRange = (value) => {
  const num = Number(value) || 0;
  return Math.min(Math.max(num, 0), 360);
};

// Computed properties for the compass dial
const compassStyle = computed(() => {
  // Treat empty/null values as 0 and 360 for full circle case
  const min =
    props.minBearing === null || props.minBearing === '' ? 0 : clipToRange(props.minBearing);
  const max =
    props.maxBearing === null || props.maxBearing === '' ? 360 : clipToRange(props.maxBearing);

  // Calculate radius once for both cases
  const radius = props.size / 2 - 1;
  const center = props.size / 2;
  
  // Special case: full circle
  if (min === 0 && max === 360) {
    return {
      path: `M ${center} ${center} m -${radius} 0 a ${radius} ${radius} 0 1 0 ${radius * 2} 0 a ${radius} ${radius} 0 1 0 -${radius * 2} 0`,
    };
  }

  // Calculate the arc for the highlighted section
  const startAngle = min;
  const endAngle = max;
  const isLargeArc = (max - min > 180) || (min > max) ? 1 : 0;

  // Convert angles to SVG path coordinates
  const startX = center + radius * Math.cos(((startAngle - 90) * Math.PI) / 180);
  const startY = center + radius * Math.sin(((startAngle - 90) * Math.PI) / 180);
  const endX = center + radius * Math.cos(((endAngle - 90) * Math.PI) / 180);
  const endY = center + radius * Math.sin(((endAngle - 90) * Math.PI) / 180);

  return {
    path: `M ${center} ${center} L ${startX} ${startY} A ${radius} ${radius} 0 ${isLargeArc} 1 ${endX} ${endY} Z`,
  };
});

const svgStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}));

const labelStyle = computed(() => ({
  fontSize: `${props.size * 0.12}px`,
}));
</script>

<template>
  <div class="compass-container">
    <svg :style="svgStyle" :viewBox="`0 0 ${size} ${size}`">
      <!-- Compass circle -->
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="size / 2 - 1"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      />

      <!-- Cardinal points -->
      <text :x="size / 2" :y="size * 0.1" :dy="4" text-anchor="middle" :style="labelStyle">N</text>
      <text :x="size * 0.9" :y="size / 2" :dy="3" dx="-1" text-anchor="middle" :style="labelStyle">E</text>
      <text :x="size / 2" :y="size * 0.9" :dy="2" text-anchor="middle" :style="labelStyle">S</text>
      <text :x="size * 0.1" :y="size / 2" :dy="3" :dx="1" text-anchor="middle" :style="labelStyle">W</text>

      <!-- Degree markers -->
      <line
        :x1="size / 2"
        y1="0"
        :x2="size / 2"
        :y2="size * 0.05"
        stroke="currentColor"
        stroke-width="1"
      />
      <line
        :x1="size"
        :y1="size / 2"
        :x2="size * 0.95"
        :y2="size / 2"
        stroke="currentColor"
        stroke-width="1"
      />
      <line
        :x1="size / 2"
        :y1="size"
        :x2="size / 2"
        :y2="size * 0.95"
        stroke="currentColor"
        stroke-width="1"
      />
      <line
        x1="0"
        :y1="size / 2"
        :x2="size * 0.05"
        :y2="size / 2"
        stroke="currentColor"
        stroke-width="1"
      />

      <!-- Highlighted range -->
      <path
        :d="compassStyle.path"
        fill="rgba(var(--v-theme-primary), 0.2)"
        stroke="rgb(var(--v-theme-primary))"
        stroke-width="2"
      />
    </svg>
  </div>
</template>

<style scoped>
.compass-container {
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
