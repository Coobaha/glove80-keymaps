"""Configuration loading from keyboards/ and mappings/ directories."""

import json
import os
import re
from typing import Dict, List, Any, Optional


def get_project_root() -> str:
    """Get project root directory (parent of scripts/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_info_json(info_path: str) -> Dict[str, Any]:
    """Load QMK/ZMK info.json for physical layout. OverKeys parses it directly."""
    with open(info_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_position_mappings_from_info(info_path: str) -> Dict[str, Any]:
    """Generate position mappings from info.json labels.

    Label format: {L|R}_C{col}R{row} for main keys, {L|R}_T{num} for thumb keys
    - L_ = left hand, R_ = right hand
    - C#R# = column and row (all C#R# keys are main rows, R1-R5 -> row indices 0-4)
    - T# = thumb key (only _T keys go to thumbRows)

    Returns dict with left_main_rows, right_main_rows, left_thumb_rows, right_thumb_rows
    """
    with open(info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)

    layout = info['layouts']['LAYOUT']['layout']

    left_main: Dict[int, List[tuple]] = {}
    right_main: Dict[int, List[tuple]] = {}
    left_thumb: List[tuple] = []
    right_thumb: List[tuple] = []

    col_pattern = re.compile(r'^([LR])_C(\d+)R(\d+)$')
    thumb_pattern = re.compile(r'^([LR])_T(\d+)$')

    for idx, key in enumerate(layout):
        label = key['label']

        col_match = col_pattern.match(label)
        if col_match:
            hand, col, row = col_match.groups()
            col, row = int(col), int(row)
            # All C#R# keys are main rows (R1->0, R2->1, ..., R5->4)
            row_idx = row - 1
            if hand == 'L':
                left_main.setdefault(row_idx, []).append((col, idx))
            else:
                right_main.setdefault(row_idx, []).append((col, idx))
            continue

        thumb_match = thumb_pattern.match(label)
        if thumb_match:
            hand, num = thumb_match.groups()
            num = int(num)
            if hand == 'L':
                left_thumb.append((num, idx))
            else:
                right_thumb.append((num, idx))
            continue

    # Find max column for each hand to determine row width
    left_max_col = max((col for row_data in left_main.values() for col, _ in row_data), default=0)
    right_min_col = min((col for row_data in right_main.values() for col, _ in row_data), default=0)
    right_max_col = max((col for row_data in right_main.values() for col, _ in row_data), default=0)

    left_main_rows = []
    for row in sorted(left_main.keys()):
        col_to_idx = {col: idx for col, idx in left_main[row]}
        # Left hand: columns descend from max_col to 1, build row with None padding
        row_data = []
        for c in range(left_max_col, 0, -1):
            row_data.append(col_to_idx.get(c))
        left_main_rows.append(row_data)

    right_main_rows = []
    for row in sorted(right_main.keys()):
        col_to_idx = {col: idx for col, idx in right_main[row]}
        # Right hand: columns ascend from min_col to max_col, build row with None padding
        row_data = []
        for c in range(right_min_col, right_max_col + 1):
            row_data.append(col_to_idx.get(c))
        right_main_rows.append(row_data)

    left_thumb_sorted = sorted(left_thumb, key=lambda x: x[0])
    left_thumb_rows = [[idx for _, idx in left_thumb_sorted]] if left_thumb else []

    right_thumb_sorted = sorted(right_thumb, key=lambda x: -x[0])
    right_thumb_rows = [[idx for _, idx in right_thumb_sorted]] if right_thumb else []

    return {
        'left_main_rows': left_main_rows,
        'right_main_rows': right_main_rows,
        'left_thumb_rows': left_thumb_rows,
        'right_thumb_rows': right_thumb_rows,
    }


def load_keyboard_config(keyboard_type: str) -> Optional[Dict[str, Any]]:
    """Load keyboard config from keyboards/<name>/ directory if it exists.
    Returns None if directory doesn't exist or keyboard.json is missing.

    Supports "auto" for position mappings - generates them from info.json labels.
    """
    project_root = get_project_root()
    keyboards_dir = os.path.join(project_root, 'keyboards', keyboard_type)
    keyboard_json = os.path.join(keyboards_dir, 'keyboard.json')

    if not os.path.exists(keyboard_json):
        return None

    with open(keyboard_json, 'r', encoding='utf-8') as f:
        config = json.load(f)

    info_json = os.path.join(keyboards_dir, 'info.json')
    if os.path.exists(info_json):
        config['info_json'] = info_json

    keymap_json = os.path.join(keyboards_dir, 'keymap.json')
    if os.path.exists(keymap_json):
        config['keymap_json'] = keymap_json

    layer_config_json = os.path.join(keyboards_dir, 'layer_config.json')
    if os.path.exists(layer_config_json):
        with open(layer_config_json, 'r', encoding='utf-8') as f:
            config['layer_config'] = json.load(f)

    if config.get('left_main_rows') == 'auto' and os.path.exists(info_json):
        generated = generate_position_mappings_from_info(info_json)
        config.update(generated)

    return config


def load_zmk_key_mapping() -> Dict[str, str]:
    """Load ZMK key mapping from mappings/zmk_keys.json."""
    project_root = get_project_root()
    mapping_file = os.path.join(project_root, 'mappings', 'zmk_keys.json')

    if os.path.exists(mapping_file):
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mapping = {}
        for key, value in data.items():
            if key.startswith('_'):
                continue
            if isinstance(value, dict):
                mapping.update(value)
        return mapping

    return {
        'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G',
        'H': 'H', 'I': 'I', 'J': 'J', 'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N',
        'O': 'O', 'P': 'P', 'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T', 'U': 'U',
        'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z',
        'N1': '1', 'N2': '2', 'N3': '3', 'N4': '4', 'N5': '5',
        'N6': '6', 'N7': '7', 'N8': '8', 'N9': '9', 'N0': '0',
        'SPACE': '\u23b5', 'TAB': '\u21e5', 'RET': '\u21b5', 'ESC': '\u238b',
        'BSPC': '\u232b', 'DEL': '\u2326', 'LGUI': '\u2318', 'RGUI': '\u2318',
    }


def load_display_replacements() -> Dict[str, str]:
    """Load display replacements from mappings/display_replacements.json."""
    project_root = get_project_root()
    mapping_file = os.path.join(project_root, 'mappings', 'display_replacements.json')

    if os.path.exists(mapping_file):
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mapping = {}
        for key, value in data.items():
            if key.startswith('_'):
                continue
            if isinstance(value, dict):
                mapping.update(value)
        return mapping

    return {}


def load_behavior_config() -> Dict[str, Any]:
    """Load behavior patterns from mappings/behaviors.json."""
    project_root = get_project_root()
    mapping_file = os.path.join(project_root, 'mappings', 'behaviors.json')

    if os.path.exists(mapping_file):
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    return {}
