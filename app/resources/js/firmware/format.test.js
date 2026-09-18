import { test } from 'node:test';
import assert from 'node:assert/strict';
import { phaseLabel, plainNotes, progressLabel } from './format.js';

test('plainNotes strips the Markdown GitHub release bodies carry', () => {
  const body = '## Summary\r\n\r\n- **New features and improvements**\r\n  - Improved [filament change](https://example.test) between *materials*\r\n- `M997` support\r\n\r\n\r\n\r\n### Fixes\n* Support for older boards';
  assert.equal(
    plainNotes(body),
    'Summary\n\n• New features and improvements\n• Improved filament change between materials\n• M997 support\n\nFixes\n• Support for older boards',
  );
  assert.equal(plainNotes(''), '');
  assert.equal(plainNotes(null), '');
  assert.equal(plainNotes('2 * 3 * 4 and snake_case_names stay'), '2 * 3 * 4 and snake_case_names stay');
});

test('progressLabel prefers the daemon step over the phase', () => {
  assert.equal(progressLabel({ phase: 'rebooting', step: 'Waiting for the printer to come back' }), 'Waiting for the printer to come back');
  assert.equal(progressLabel({ phase: 'rebooting', step: null }), 'Restarting the printer');
  assert.equal(phaseLabel('unknown'), '');
});
