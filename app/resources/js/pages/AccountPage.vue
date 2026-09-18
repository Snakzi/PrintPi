<script setup>
import PasskeysCard from '../components/account/PasskeysCard.vue';
import PasswordCard from '../components/account/PasswordCard.vue';
import ProfileCard from '../components/account/ProfileCard.vue';
</script>

<template>
  <div class="mx-auto flex max-w-3xl flex-col gap-4">
    <ProfileCard />
    <PasswordCard />
    <PasskeysCard />
  </div>
</template>
