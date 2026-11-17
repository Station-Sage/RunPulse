// Button variant → Tailwind class (순수). 테스트: frontend/tests/backNavB1.test.mjs
export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

const BASE = 'inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm disabled:opacity-50';
const VARIANT: Record<ButtonVariant, string> = {
	primary: 'bg-fg-primary font-medium text-surface-1',
	secondary: 'border border-border-subtle bg-surface-2 text-fg-primary hover:bg-surface-3',
	ghost: 'text-fg-secondary hover:bg-surface-3',
	danger: 'border border-semantic-red/50 text-semantic-red hover:bg-surface-3'
};

export function buttonClass(variant: ButtonVariant, full = false): string {
	return `${BASE} ${VARIANT[variant]}${full ? ' w-full' : ''}`;
}
