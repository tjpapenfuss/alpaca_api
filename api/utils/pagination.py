import json
import strawberry
from typing import List, Optional, TypeVar, Generic, Callable, Any, Dict
import base64

# Create generic types
T = TypeVar('T')

@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None

@strawberry.type
class Edge(Generic[T]):
    cursor: str
    node: T

@strawberry.type
class Connection(Generic[T]):
    edges: List[Edge[T]]
    page_info: PageInfo
    total_count: int

@strawberry.type
class Connection(Generic[T]):
    edges: List[Edge[T]]
    page_info: PageInfo
    total_count: int

# Pagination utility function
def paginate_results(
    items: List[Dict[str, Any]],
    first: Optional[int] = 10,
    after: Optional[str] = None,
    converter_func: Callable[[Dict[str, Any]], T] = lambda x: x
) -> Connection[T]:
    """
    Create a paginated connection from a list of items.
    
    Args:
        items: List of items to paginate
        first: Number of items to return
        after: Cursor to start after
        converter_func: Function to convert a dict item to the target type
        
    Returns:
        A connection object with pagination info
    """
    total_count = len(items)
    
    # Decode the cursor to get the index
    start_index = 0
    if after:
        try:
            cursor_data = decode_cursor(after)
            start_index = cursor_data['index'] + 1
        except (ValueError, KeyError):
            start_index = 0
    
    # Get the requested slice
    end_index = start_index + first if first else len(items)
    sliced_items = items[start_index:end_index]
    
    # Create edges
    edges = []
    for i, item in enumerate(sliced_items):
        cursor = encode_cursor({"index": start_index + i})
        edges.append(Edge(
            cursor=cursor,
            node=converter_func(item)
        ))
    
    # Create page info
    has_next = end_index < total_count
    has_previous = start_index > 0
    start_cursor = edges[0].cursor if edges else None
    end_cursor = edges[-1].cursor if edges else None
    
    page_info = PageInfo(
        has_next_page=has_next,
        has_previous_page=has_previous,
        start_cursor=start_cursor,
        end_cursor=end_cursor
    )
    
    # Return connection
    return Connection(
        edges=edges,
        page_info=page_info,
        total_count=total_count
    )

# Cursor encoding/decoding functions
def encode_cursor(data: Dict[str, Any]) -> str:
    """Encode data into a base64 cursor string."""
    json_string = json.dumps(data)
    base64_bytes = base64.b64encode(json_string.encode("utf-8"))
    return base64_bytes.decode("utf-8")

def decode_cursor(cursor: str) -> Dict[str, Any]:
    """Decode a base64 cursor string back into data."""
    base64_bytes = cursor.encode("utf-8")
    json_bytes = base64.b64decode(base64_bytes)
    return json.loads(json_bytes.decode("utf-8"))