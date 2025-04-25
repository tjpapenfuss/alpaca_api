"""Pagination utilities for GraphQL queries."""
import strawberry
from typing import TypeVar, Generic, List, Optional, Callable, Dict, Any
import base64
import json

T = TypeVar('T')

@strawberry.type
class PageInfo:
    """Information about pagination in a connection."""
    has_next_page: bool
    end_cursor: Optional[str] = None

@strawberry.type
class Edge(Generic[T]):
    """An edge in a connection."""
    cursor: str
    node: T

@strawberry.type
class Connection(Generic[T]):
    """A connection to a list of items."""
    edges: List[Edge[T]]
    page_info: PageInfo

def paginate_results(
    items: List[Dict[str, Any]],
    first: Optional[int] = 10,
    after: Optional[str] = None,
    converter_func: Callable[[Dict[str, Any]], T] = lambda x: x
) -> Connection[T]:
    """
    Paginate a list of items using cursor-based pagination.
    
    Args:
        items: List of items to paginate
        first: Number of items to return
        after: Cursor indicating where to start
        converter_func: Function to convert each item to the desired type
        
    Returns:
        Connection: Paginated connection of items
    """
    start_idx = 0
    
    if after:
        try:
            # Decode cursor
            cursor_data = json.loads(base64.b64decode(after).decode('utf-8'))
            start_idx = cursor_data.get('idx', 0) + 1
        except Exception:
            # If cursor is invalid, start from beginning
            start_idx = 0
    
    # Slice the items
    sliced_items = items[start_idx:start_idx + first] if first else items[start_idx:]
    
    # Create edges
    edges = []
    for i, item in enumerate(sliced_items):
        cursor = base64.b64encode(json.dumps({'idx': start_idx + i}).encode('utf-8')).decode('utf-8')
        edges.append(Edge(cursor=cursor, node=converter_func(item)))
    
    # Create page info
    has_next_page = (start_idx + len(sliced_items)) < len(items)
    end_cursor = edges[-1].cursor if edges else None
    
    return Connection(
        edges=edges,
        page_info=PageInfo(
            has_next_page=has_next_page,
            end_cursor=end_cursor
        )
    )
