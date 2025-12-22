/**
 * Date formatting utilities for CLC Dashboard
 *
 * All timestamps from the backend are stored in UTC (via SQLite CURRENT_TIMESTAMP).
 * These utilities convert UTC timestamps to the browser's local timezone for display.
 */

import { format, formatDistanceToNow } from 'date-fns'

/**
 * Parse a UTC timestamp string from the backend.
 * Backend returns timestamps like "2025-12-19 20:36:04" (UTC, no timezone indicator).
 * We append 'Z' to ensure JavaScript parses it as UTC.
 */
export function parseUTCTimestamp(timestamp: string | null | undefined): Date | null {
  if (!timestamp) return null

  // If already has timezone indicator (Z suffix or +HH:MM / -HH:MM offset), parse directly
  const timezoneOffsetRegex = /[+-]\d{2}:\d{2}$/
  if (timestamp.endsWith('Z') || timezoneOffsetRegex.test(timestamp)) {
    return new Date(timestamp)
  }

  // Replace space with 'T' for ISO format and append 'Z' for UTC
  const isoString = timestamp.replace(' ', 'T') + 'Z'
  return new Date(isoString)
}

/**
 * Format a UTC timestamp to local time string.
 * @param timestamp - UTC timestamp from backend
 * @param formatStr - date-fns format string (default: 'MMM d, HH:mm:ss')
 * @returns Formatted local time string or original timestamp on failure (for debugging)
 */
export function formatLocalTime(
  timestamp: string | null | undefined,
  formatStr: string = 'MMM d, HH:mm:ss'
): string {
  if (!timestamp) return 'No date'
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return timestamp // Return original for debugging
  return format(date, formatStr)
}

/**
 * Format a UTC timestamp as relative time (e.g., "5 minutes ago").
 * @param timestamp - UTC timestamp from backend
 * @param options - formatDistanceToNow options
 * @returns Relative time string or original timestamp on failure (for debugging)
 */
export function formatRelativeTime(
  timestamp: string | null | undefined,
  options: { addSuffix?: boolean } = { addSuffix: true }
): string {
  if (!timestamp) return 'Unknown'
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return timestamp // Return original for debugging
  return formatDistanceToNow(date, options)
}

/**
 * Format a UTC timestamp to full local datetime string.
 * Uses browser's locale settings.
 * @returns Formatted datetime or original timestamp on failure (for debugging)
 */
export function formatLocalDateTime(timestamp: string | null | undefined): string {
  if (!timestamp) return 'No date'
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return timestamp
  return date.toLocaleString()
}

/**
 * Format a UTC timestamp to local date only.
 * @returns Formatted date or original timestamp on failure (for debugging)
 */
export function formatLocalDate(timestamp: string | null | undefined): string {
  if (!timestamp) return 'No date'
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return timestamp
  return date.toLocaleDateString()
}

/**
 * Format a UTC timestamp to local time only.
 * @returns Formatted time or original timestamp on failure (for debugging)
 */
export function formatLocalTimeOnly(timestamp: string | null | undefined): string {
  if (!timestamp) return 'No time'
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return timestamp
  return date.toLocaleTimeString()
}
