/** 플랜 심박존 → 본인 LTHR 기준 bpm 구간(hi=null 은 상한 없음) */
export interface ZoneBpm {
	zone: number;
	lo: number;
	hi: number | null;
	lthr: number;
}
