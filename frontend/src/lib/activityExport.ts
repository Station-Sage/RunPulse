export function gpxUrl(id: number): string {
	return `/api/v1/library/activities/${id}/export.gpx`;
}
