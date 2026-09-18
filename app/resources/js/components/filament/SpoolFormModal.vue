<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { useToastStore } from '../../stores/toasts';
import { FINISHES, gramsFor, millimetresFor, uniqueSpoolName } from '../../filament/spools';
import { formatLength } from '../../format';
import AppButton from '../AppButton.vue';
import FormSection from '../FormSection.vue';
import Modal from '../Modal.vue';
import SelectOrCustom from '../SelectOrCustom.vue';
import SettingsField from '../settings/SettingsField.vue';
import SpoolPreview from './SpoolPreview.vue';
import { inputClass } from '../settings/styles';

/* Creates a spool, or edits `spool` when given. A vendor from the catalog offers its product
   lines, and a product fills name, material, colour, finish and net weight; without one the
   name is typed. Known materials bring their density and known vendors the weight of their empty spool
   until those are typed, a scale reading turns into the remaining weight, and the preview on
   top follows every keystroke. */
const props = defineProps({ spool: { type: Object, default: null } });
const emit = defineEmits(['close', 'saved']);

const filament = useFilamentStore();
const toasts = useToastStore();

const DIAMETERS = ['1.75', '2.85', '3.00'];
const DEFAULT_COLOR = '#a1a1aa';

const form = reactive({
  vendor: props.spool?.vendor ?? '',
  product: '',
  name: props.spool?.name ?? '',
  material: props.spool?.material ?? 'PLA',
  color: props.spool?.color ?? DEFAULT_COLOR,
  finish: props.spool?.finish ?? '',
  diameter: String(props.spool?.diameter ?? 1.75),
  density: props.spool?.density ?? filament.materials.PLA?.density ?? 1.24,
  weight: props.spool?.weight ?? 1000,
  spool_weight: props.spool?.spool_weight ?? '',
  reading: '',
  remaining: props.spool?.remaining ?? 1000,
  price: props.spool?.price ?? '',
});
// Once a value was typed, the lookups stop overwriting it.
const typed = reactive({
  density: props.spool !== null,
  spoolWeight: props.spool?.spool_weight != null,
  remaining: props.spool !== null,
});
const saving = ref(false);
const errors = ref({});
const first = ref(null);

// The modal is teleported, so the autofocus attribute would not take.
onMounted(() => {
  first.value?.$el?.querySelector('select')?.focus();
  filament.loadCatalog().catch((error) => toasts.error(error.message));
});

const materials = computed(() => Object.keys(filament.materials));
const vendors = computed(() => Object.keys(filament.vendors));
const products = computed(() => filament.vendors[form.vendor]?.products ?? []);
// The vendor's products grouped by line, in catalog order, each with its index as the option value.
const lines = computed(() => {
  const groups = [];
  products.value.forEach((product, index) => {
    let group = groups.find((entry) => entry.line === product.line);
    if (!group) groups.push((group = { line: product.line, items: [] }));
    group.items.push({ index: String(index), name: product.name });
  });
  return groups;
});
const product = computed(() => (form.product === '' ? null : (products.value[Number(form.product)] ?? null)));
const diameters = computed(() => (DIAMETERS.includes(form.diameter) ? DIAMETERS : [...DIAMETERS, form.diameter]));

const geometry = computed(() => ({ diameter: Number(form.diameter), density: Number(form.density) }));
const gramsPerMetre = computed(() => gramsFor(geometry.value, 1000));
const draft = computed(() => {
  const remaining = Math.max(0, Number(form.remaining) || 0);
  return {
    name: form.name,
    vendor: form.vendor,
    material: form.material,
    finish: form.finish || null,
    weight: Number(form.weight) || 0,
    remaining,
    remaining_mm: millimetresFor(geometry.value, remaining),
  };
});

watch(
  () => form.material,
  (material) => {
    const known = filament.materials[material.trim().toUpperCase()];
    if (known && !typed.density) form.density = known.density;
  },
);
watch(
  () => form.vendor,
  (vendor) => {
    form.product = '';
    const known = filament.vendors[vendor]?.spool_weight;
    if (known != null && !typed.spoolWeight) form.spool_weight = known;
  },
);
// A product stands for name, material, colour, finish and net weight; the density follows its material.
// A second spool of the same product is numbered so the two stay apart in every list.
watch(product, (picked) => {
  if (!picked) return;
  form.name = uniqueSpoolName(`${picked.line} ${picked.name}`, filament.items, props.spool?.id ?? null);
  typed.density = false;
  form.material = picked.material;
  form.color = picked.color;
  form.finish = picked.finish ?? '';
  form.weight = picked.weight ?? 1000;
});
watch(
  () => form.weight,
  (weight) => {
    if (!typed.remaining) form.remaining = weight;
  },
);
watch([() => form.reading, () => form.spool_weight], ([reading, spoolWeight]) => {
  if (reading === '' || spoolWeight === '') return;
  form.remaining = Math.max(0, Number(reading) - Number(spoolWeight));
  typed.remaining = true;
});

function remainingTyped() {
  form.reading = '';
  typed.remaining = true;
}

function number(value) {
  return value === '' || value === null ? null : Number(value);
}

async function save() {
  const data = {
    name: form.name,
    vendor: form.vendor,
    material: form.material,
    color: form.color,
    finish: form.finish || null,
    diameter: Number(form.diameter),
    density: Number(form.density),
    weight: Number(form.weight),
    spool_weight: number(form.spool_weight),
    remaining: Number(form.remaining),
    price: number(form.price),
  };
  saving.value = true;
  errors.value = {};
  try {
    const saved = props.spool ? await filament.update(props.spool, data) : await filament.create(data);
    toasts.success(`${saved.name} saved`);
    emit('saved', saved);
    emit('close');
  } catch (error) {
    errors.value = error.errors ?? {};
    if (!error.errors) toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}

const error = (field) => errors.value[field]?.[0] ?? null;
const suffix = 'shrink-0 text-xs text-zinc-500 tabular-nums';
</script>

<template>
  <Modal size="md" @close="emit('close')">
    <template #title>
      <h2 class="font-medium">{{ spool ? 'Edit spool' : 'New spool' }}</h2>
    </template>
    <form class="flex max-h-[85vh] flex-col" @submit.prevent="save">
      <div class="min-h-0 flex-1 overflow-y-auto">
        <SpoolPreview :spool="draft" :color="form.color" editable @update:color="form.color = $event" />

        <div class="flex flex-col gap-6 p-4">
          <FormSection title="Spool">
            <div class="grid gap-4 sm:grid-cols-2">
              <SettingsField label="Vendor">
                <SelectOrCustom ref="first" v-model="form.vendor" :options="vendors" none="–" placeholder="Vendor" />
              </SettingsField>
              <SettingsField v-if="lines.length" label="Product">
                <select v-model="form.product" :class="inputClass">
                  <option value="">–</option>
                  <optgroup v-for="group in lines" :key="group.line" :label="group.line">
                    <option v-for="item in group.items" :key="item.index" :value="item.index">{{ item.name }}</option>
                  </optgroup>
                </select>
              </SettingsField>
              <SettingsField v-if="!product" label="Name">
                <input v-model="form.name" required maxlength="100" :class="inputClass">
                <span v-if="error('name')" class="text-xs text-red-400">{{ error('name') }}</span>
              </SettingsField>
              <SettingsField label="Material">
                <SelectOrCustom v-model="form.material" :options="materials" :maxlength="40" placeholder="Material" required />
                <span v-if="error('material')" class="text-xs text-red-400">{{ error('material') }}</span>
              </SettingsField>
              <SettingsField label="Finish">
                <select v-model="form.finish" :class="inputClass">
                  <option value="">–</option>
                  <option v-for="finish in FINISHES" :key="finish.id" :value="finish.id">{{ finish.label }}</option>
                </select>
              </SettingsField>
              <SettingsField label="Price per spool">
                <input v-model="form.price" type="number" min="0" step="0.01" inputmode="decimal" :class="inputClass">
              </SettingsField>
            </div>
          </FormSection>

          <FormSection title="Filament">
            <div class="grid gap-4 sm:grid-cols-2">
              <SettingsField label="Diameter (mm)">
                <select v-model="form.diameter" :class="inputClass">
                  <option v-for="diameter in diameters" :key="diameter" :value="diameter">{{ diameter }}</option>
                </select>
              </SettingsField>
              <SettingsField label="Density (g/cm³)">
                <div class="flex items-center gap-2">
                  <input v-model="form.density" type="number" min="0.5" max="3" step="0.01" inputmode="decimal" class="min-w-0 flex-1" :class="inputClass" @input="typed.density = true">
                  <span :class="suffix">≈ {{ gramsPerMetre?.toFixed(2) ?? '–' }} g/m</span>
                </div>
              </SettingsField>
            </div>
          </FormSection>

          <FormSection title="Weight">
            <div class="grid gap-4 sm:grid-cols-2">
              <SettingsField label="Filament weight (g)">
                <input v-model="form.weight" type="number" min="1" max="20000" step="1" inputmode="numeric" required :class="inputClass">
              </SettingsField>
              <SettingsField label="Empty spool (g)">
                <input v-model="form.spool_weight" type="number" min="0" max="5000" step="1" inputmode="numeric" :class="inputClass" @input="typed.spoolWeight = true">
              </SettingsField>
              <SettingsField label="Scale reading (g)">
                <input v-model="form.reading" type="number" min="0" max="25000" step="1" inputmode="numeric" :class="inputClass">
              </SettingsField>
              <SettingsField label="Remaining (g)">
                <div class="flex items-center gap-2">
                  <input v-model="form.remaining" type="number" min="0" max="20000" step="0.1" inputmode="decimal" required class="min-w-0 flex-1" :class="inputClass" @input="remainingTyped">
                  <span :class="suffix">≈ {{ formatLength(draft.remaining_mm) }}</span>
                </div>
              </SettingsField>
            </div>
          </FormSection>
        </div>
      </div>

      <div class="flex shrink-0 justify-end gap-2 border-t border-zinc-800 px-4 py-3">
        <AppButton variant="ghost" @click="emit('close')">Cancel</AppButton>
        <AppButton type="submit" variant="primary" icon="check" :disabled="saving">Save</AppButton>
      </div>
    </form>
  </Modal>
</template>
