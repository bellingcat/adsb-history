import './assets/main.css';

// MapLibre CSS imports
import 'maplibre-gl/dist/maplibre-gl.css';
import 'vue-maplibre-gl/dist/vue-maplibre-gl.css';

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';

// Vuetify
import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

// Import Vue MapLibre GL with explicit components
import VueMaplibreGl from 'vue-maplibre-gl';

const vuetify = createVuetify({
  components,
  directives,
});

const app = createApp(App);

// Register Vue MapLibre GL
app.use(VueMaplibreGl);

app.use(createPinia());
app.use(vuetify);
app.mount('#app');

