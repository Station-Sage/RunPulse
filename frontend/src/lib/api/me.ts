import { apiFetch } from './client';

export type OnboardingState = 'pending' | 'skipped' | 'done';
export interface Preferences {
	ui_default: 'v1' | 'v2';
	onboarding: OnboardingState;
	onboarding_step: number;
}

export const getPreferences = () => apiFetch<Preferences>('/me/preferences');
export const patchPreferences = (patch: Partial<Pick<Preferences, 'onboarding' | 'onboarding_step'>>) =>
	apiFetch<Preferences>('/me/preferences', { method: 'PATCH', body: JSON.stringify(patch) });
