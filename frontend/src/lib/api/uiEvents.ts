import { apiFetch } from './client';
import { patchPreferences } from './me';
import { rollbackToV1, type RollbackReason } from '../rollback';

const post = (body: Record<string, unknown>) =>
	apiFetch<{ recorded: boolean }>('/me/ui-events', { method: 'POST', body: JSON.stringify(body) });

export const recordVisit = () => post({ kind: 'v2_visit' });

export const rollback = (reason: RollbackReason | null, note: string, navigate: (url: string) => void) =>
	rollbackToV1(reason, note, {
		sendEvent: post,
		setV1: () => patchPreferences({ ui_default: 'v1' }),
		navigate
	});
