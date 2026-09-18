import { createRouter, createWebHistory } from 'vue-router';
import { useSessionStore } from './stores/session';
import DashboardPage from './pages/DashboardPage.vue';
import FilesPage from './pages/FilesPage.vue';
import PrintsPage from './pages/PrintsPage.vue';
import FilamentPage from './pages/FilamentPage.vue';
import TerminalPage from './pages/TerminalPage.vue';
import CameraPage from './pages/CameraPage.vue';
import PluginsPage from './pages/PluginsPage.vue';
import PluginPage from './pages/PluginPage.vue';
import SettingsPage from './pages/SettingsPage.vue';
import AccountPage from './pages/AccountPage.vue';
import PanelPage from './pages/PanelPage.vue';
import SetupPage from './pages/SetupPage.vue';
import LoginPage from './pages/LoginPage.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardPage, meta: { nav: true, title: 'Dashboard', icon: 'home' } },
    { path: '/files', name: 'files', component: FilesPage, meta: { nav: true, title: 'Files', icon: 'folder' } },
    { path: '/prints', name: 'prints', component: PrintsPage, meta: { nav: true, title: 'Prints', icon: 'photo' } },
    { path: '/filament', name: 'filament', component: FilamentPage, meta: { nav: true, title: 'Filament', icon: 'spool' } },
    { path: '/terminal', name: 'terminal', component: TerminalPage, meta: { nav: true, title: 'Terminal', icon: 'terminal' } },
    { path: '/camera', name: 'camera', component: CameraPage, meta: { nav: true, title: 'Camera', icon: 'camera' } },
    { path: '/plugins', name: 'plugins', component: PluginsPage, meta: { nav: true, title: 'Plugins', icon: 'puzzle' } },
    { path: '/plugins/:plugin', name: 'plugin', component: PluginPage, meta: { title: 'Plugin' } },
    { path: '/settings/:tab?', name: 'settings', component: SettingsPage, meta: { nav: true, title: 'Settings', icon: 'settings' } },
    // Reached from the user menu only, so no `nav`.
    { path: '/account', name: 'account', component: AccountPage, meta: { title: 'Account' } },
    // The touch screen at the printer: no sidebar, no status bar, needs a login like everything else.
    { path: '/panel', name: 'panel', component: PanelPage, meta: { bare: true, panel: true, title: 'Panel' } },
    { path: '/setup', name: 'setup', component: SetupPage, meta: { bare: true, public: true, title: 'Setup' } },
    { path: '/login', name: 'login', component: LoginPage, meta: { bare: true, public: true, title: 'Sign in' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});

router.beforeEach(async (to) => {
  const session = useSessionStore();
  if (!session.loaded) {
    try {
      await session.load();
    } catch {
      // The API is down; let the page render and show its own error.
      return true;
    }
  }
  if (!session.setupComplete) {
    return to.name === 'setup' ? true : { name: 'setup' };
  }
  if (to.name === 'setup') {
    return { name: session.authenticated ? 'dashboard' : 'login' };
  }
  if (!session.authenticated && !to.meta.public) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} };
  }
  if (session.authenticated && to.name === 'login') {
    return { name: 'dashboard' };
  }
  return true;
});

export default router;
