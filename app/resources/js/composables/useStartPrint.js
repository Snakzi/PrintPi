import { useFileStore } from '../stores/files';
import { usePrintStartStore } from '../stores/printStart';

/**
 * Starts a print the same way from every page: the spool picker opens for the
 * file and starts the print once a spool is chosen. `file` may be the row of
 * the files list or the bare {id, name} of a past print; the metadata the
 * picker compares against the spools is looked up when it is missing.
 */
export function useStartPrint() {
  const files = useFileStore();
  const printStart = usePrintStartStore();

  async function withMetadata(file) {
    if (file.metadata) return file;
    if (!files.items.length) await files.load().catch(() => {});
    return files.items.find((item) => item.id === file.id) ?? file;
  }

  async function startPrint(file) {
    printStart.request(await withMetadata(file));
  }

  return { startPrint };
}
