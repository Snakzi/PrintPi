<script setup>
import { computed } from 'vue';
import { formatDate, formatDateTime } from '../../format';
import Icon from '../Icon.vue';
import IconButton from '../IconButton.vue';
import InlineEdit from '../InlineEdit.vue';

/* One passkey: its name (editable in place), the authenticator that made it, when it was
   added and last used. */
const props = defineProps({ passkey: { type: Object, required: true } });
const emit = defineEmits(['rename', 'remove']);

const detail = computed(() => {
  const parts = [props.passkey.authenticator, `Added ${formatDate(props.passkey.created_at)}`];
  parts.push(props.passkey.last_used_at ? `Last used ${formatDateTime(props.passkey.last_used_at)}` : 'Never used');
  return parts.filter(Boolean).join(' · ');
});
</script>

<template>
  <li class="flex items-center gap-3 py-3">
    <Icon name="key" class="size-5 shrink-0 text-zinc-500" />
    <div class="min-w-0 flex-1">
      <InlineEdit :model-value="passkey.name" label="Rename" :maxlength="100" class="text-sm font-medium text-zinc-100" @update:model-value="emit('rename', $event)" />
      <div class="truncate text-xs text-zinc-500">{{ detail }}</div>
    </div>
    <IconButton icon="trash" title="Remove" @click="emit('remove')" />
  </li>
</template>
