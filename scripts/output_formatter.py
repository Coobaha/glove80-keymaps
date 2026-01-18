"""Output formatting for JSON and other output formats."""

import json
from typing import Any


def format_compact_json(data: Any) -> str:
    """Format JSON with compact arrays for key rows."""

    def format_json_with_compact_arrays(obj, indent=0):
        indent_str = "  " * indent

        if isinstance(obj, dict):
            lines = ["{"]
            items = list(obj.items())
            for i, (key, value) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                key_line = f'{indent_str}  "{key}": '

                if key in ['mainRows', 'thumbRows'] and isinstance(value, list):
                    array_lines = ["["]
                    for j, row in enumerate(value):
                        row_comma = "," if j < len(value) - 1 else ""
                        if isinstance(row, list):
                            row_items = []
                            for item in row:
                                if item is None:
                                    row_items.append("null")
                                else:
                                    row_items.append(json.dumps(item, ensure_ascii=False))
                            array_lines.append(f'{indent_str}    [{", ".join(row_items)}]{row_comma}')
                        else:
                            array_lines.append(f'{indent_str}    {json.dumps(row, ensure_ascii=False)}{row_comma}')
                    array_lines.append(f'{indent_str}  ]')
                    value_str = '\n'.join(array_lines)
                    lines.append(f'{key_line}{value_str}{comma}')
                else:
                    if isinstance(value, (dict, list)) and value:
                        value_str = format_json_with_compact_arrays(value, indent + 1)
                        lines.append(f'{key_line}{value_str}{comma}')
                    else:
                        lines.append(f'{key_line}{json.dumps(value, ensure_ascii=False)}{comma}')
            lines.append(f'{indent_str}}}')
            return '\n'.join(lines)

        elif isinstance(obj, list):
            if not obj:
                return "[]"
            lines = ["["]
            for i, item in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                if isinstance(item, (dict, list)):
                    item_str = format_json_with_compact_arrays(item, indent + 1)
                    lines.append(f'{indent_str}  {item_str}{comma}')
                else:
                    lines.append(f'{indent_str}  {json.dumps(item, ensure_ascii=False)}{comma}')
            lines.append(f'{indent_str}]')
            return '\n'.join(lines)
        else:
            return json.dumps(obj, ensure_ascii=False)

    return format_json_with_compact_arrays(data)
