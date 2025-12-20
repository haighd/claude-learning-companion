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

  // If already has timezone indicator, parse directly
  if (timestamp.endsWith('Z') || timestamp.includes('+') || timestamp.includes('-')) {
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
 * @returns Formatted local time string or fallback
 */
export function formatLocalTime(
  timestamp: string | null | undefined,
  formatStr: string = 'MMM d, HH:mm:ss'
): string {
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return 'No date'
  return format(date, formatStr)
}

/**
 * Format a UTC timestamp as relative time (e.g., "5 minutes ago").
 * @param timestamp - UTC timestamp from backend
 * @param options - formatDistanceToNow options
 */
export function formatRelativeTime(
  timestamp: string | null | undefined,
  options: { addSuffix?: boolean } = { addSuffix: true }
): string {
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return 'Unknown'
  return formatDistanceToNow(date, options)
}

/**
 * Format a UTC timestamp to full local datetime string.
 * Uses browser's locale settings.
 */
export function formatLocalDateTime(timestamp: string | null | undefined): string {
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return 'No date'
  return date.toLocaleString()
}

/**
 * Format a UTC timestamp to local date only.
 */
export function formatLocalDate(timestamp: string | null | undefined): string {
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return 'No date'
  return date.toLocaleDateString()
}

/**
 * Format a UTC timestamp to local time only.
 */
export function formatLocalTimeOnly(timestamp: string | null | undefined): string {
  const date = parseUTCTimestamp(timestamp)
  if (!date || isNaN(date.getTime())) return 'No time'
  return date.toLocaleTimeString()
}
