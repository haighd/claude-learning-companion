"""
Time filtering utilities for historical data queries.

Provides functions to build SQL WHERE clauses for time-based filtering.
"""

from datetime import datetime
from typing import Optional, Tuple


def parse_time_params(at_time: Optional[str] = None, time_range: Optional[str] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse time filter parameters.

    Args:
        at_time: ISO timestamp for point-in-time query (e.g., "2025-12-19T15:00:00Z")
        time_range: Time range as "start/end" (e.g., "2025-12-19T00:00:00Z/2025-12-19T23:59:59Z")

    Returns:
        Tuple of (start_time, end_time). If at_time is provided, end_time = at_time.
    """
    if at_time:
        # Point-in-time query: return data as it existed at that moment
        end = datetime.fromisoformat(at_time.replace('Z', '+00:00'))
        return (None, end)

    if time_range:
        # Range query: return data within the range
        parts = time_range.split('/')
        if len(parts) != 2:
            raise ValueError("time_range must be in format 'start/end'")

        start = datetime.fromisoformat(parts[0].replace('Z', '+00:00'))
        end = datetime.fromisoformat(parts[1].replace('Z', '+00:00'))
        return (start, end)

    return (None, None)


def build_time_filter(
    timestamp_column: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Tuple[str, list]:
    """
    Build SQL WHERE clause for time filtering.

    Args:
        timestamp_column: Name of the timestamp column (e.g., "created_at")
        start_time: Filter for records after this time
        end_time: Filter for records before/at this time

    Returns:
        Tuple of (where_clause, params) to use in SQL query
    """
    conditions = []
    params = []

    if start_time:
        conditions.append(f"{timestamp_column} >= ?")
        params.append(start_time.isoformat())

    if end_time:
        conditions.append(f"{timestamp_column} <= ?")
        params.append(end_time.isoformat())

    if conditions:
        return (" AND ".join(conditions), params)

    return ("", [])


def apply_time_filter(
    base_query: str,
    timestamp_column: str,
    at_time: Optional[str] = None,
    time_range: Optional[str] = None,
    existing_where: bool = True
) -> Tuple[str, list]:
    """
    Apply time filtering to a SQL query.

    Args:
        base_query: The base SQL query
        timestamp_column: Name of the timestamp column
        at_time: Optional point-in-time filter
        time_range: Optional range filter
        existing_where: Whether the query already has a WHERE clause

    Returns:
        Tuple of (modified_query, params)
    """
    start_time, end_time = parse_time_params(at_time, time_range)

    if start_time is None and end_time is None:
        return (base_query, [])

    where_clause, params = build_time_filter(timestamp_column, start_time, end_time)

    if where_clause:
        connector = " AND " if existing_where else " WHERE "
        modified_query = base_query + connector + where_clause
        return (modified_query, params)

    return (base_query, [])
