import { apiFetch } from './client';

export type OnboardingState = 'pending' | 'skipped' | 'done';
export type UiDefault = 'v1' | 'v2';
export interface Preferences {
	ui_default: UiDefault;
	ui_default_global: UiDefault;
	onboarding: OnboardingState;
	onboarding_step: number;
}

export const getPreferences = () => apiFetch<Preferences>('/me/preferences');
export const patchPreferences = (patch: Partial<Pick<Preferences, 'ui_default' | 'onboarding' | 'onboarding_step'>>) =>
	apiFetch<Preferences>('/me/preferences', { method: 'PATCH', body: JSON.stringify(patch) });
