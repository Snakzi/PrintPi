import { useConfirmStore } from '../stores/confirm';

/**
 * A yes/no question as a modal: `await confirm('Delete part.gcode?')`, or with options
 * `{ message, danger }` for a second line and a red Confirm button.
 */
export function useConfirm() {
  const store = useConfirmStore();

  return (title, options = {}) => store.ask({ title, ...options });
}
