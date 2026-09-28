// 서버 status(bands.py 어휘: poor/caution/neutral/good/excellent)를
// §C7 CSS 토큰(--color-status-{danger,caution,neutral,good,great})으로 매핑.
const STATUS_VAR: Record<string, string> = {
	poor: 'var(--color-status-danger)',
	caution: 'var(--color-status-caution)',
	neutral: 'var(--color-status-neutral)',
	good: 'var(--color-status-good)',
	excellent: 'var(--color-status-great)'
};

export function statusColorVar(status: string | null | undefined): string {
	return STATUS_VAR[status ?? ''] ?? STATUS_VAR.neutral;
}
