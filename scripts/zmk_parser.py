"""ZMK behavior parsing - converts ZMK key data to display strings.

All patterns and mappings are loaded from mappings/*.json config files.
"""

import re
from typing import Dict, List, Any, Optional

from .config_loader import (
    load_zmk_key_mapping,
    load_display_replacements,
    load_behavior_config,
    get_project_root,
)

ZMK_KEY_MAPPING = load_zmk_key_mapping()
DISPLAY_REPLACEMENTS = load_display_replacements()
BEHAVIOR_CONFIG = load_behavior_config()


def add_spaces_to_long_words(text: str) -> str:
    """Replace long words with icons for compact display."""
    return DISPLAY_REPLACEMENTS.get(text, text)


def handle_shifted_key(inner_key: str) -> Optional[str]:
    """Handle shifted keys using config lookups."""
    shifted_numbers = BEHAVIOR_CONFIG.get('shifted_numbers', {})
    shifted_symbols = BEHAVIOR_CONFIG.get('shifted_symbols', {})
    letters = BEHAVIOR_CONFIG.get('letters', [])

    if inner_key in shifted_numbers:
        return shifted_numbers[inner_key]
    if inner_key in shifted_symbols:
        return shifted_symbols[inner_key]
    if inner_key in letters:
        return inner_key
    if inner_key == 'TAB':
        return '\u21e7\u21e5'
    return None


def handle_modifier_chain(params: List[Any]) -> str:
    """Handle nested modifier combinations like LG(LA(F16)) -> CMD+ALT+F16.

    Detects Hyper (all 4 mods: GUI+Alt+Ctrl+Shift) and Meh (Alt+Ctrl+Shift).
    """
    mod_symbols = BEHAVIOR_CONFIG.get('modifier_symbols', {})
    mod_chain = []
    mod_keys_seen = set()
    current_param = params[0]
    final_key = None

    while current_param and isinstance(current_param, dict):
        mod_key = current_param.get('value', '')

        if mod_key in mod_symbols:
            mod_chain.append(mod_symbols[mod_key])
            base = mod_key[1:] if mod_key.startswith(('L', 'R')) else mod_key
            if base == 'S':
                mod_keys_seen.add('S')
            else:
                mod_keys_seen.add(base)
        elif mod_key in ZMK_KEY_MAPPING:
            final_key = ZMK_KEY_MAPPING.get(mod_key, mod_key)
            break
        elif mod_key in ('LSHFT', 'RSHFT', 'LSHIFT', 'RSHIFT'):
            mod_chain.append('\u21e7')
            mod_keys_seen.add('S')
        else:
            final_key = mod_key
            break

        if current_param.get('params') and len(current_param['params']) > 0:
            current_param = current_param['params'][0]
        else:
            break

    hyper_mods = {'G', 'A', 'C', 'S'}
    meh_mods = {'A', 'C', 'S'}

    if mod_keys_seen == hyper_mods:
        prefix = 'Hyp'
    elif mod_keys_seen == meh_mods:
        prefix = 'Meh'
    else:
        prefix = ''.join(mod_chain)

    if final_key:
        return prefix + final_key if prefix else final_key
    return prefix if prefix else 'MOD'


def extract_tap_key_from_params(params: List[Any], default: str = '') -> str:
    """Extract tap key from params[1] for behaviors like HRM."""
    if len(params) >= 2 and isinstance(params[1], dict):
        tap_key = params[1].get('value', '')
        return ZMK_KEY_MAPPING.get(tap_key, tap_key) or default
    return default


def handle_home_row_mod(behavior: str, is_overlay_layer: bool, params: List[Any]) -> Optional[str]:
    """Handle home row mod behaviors using config lookups."""
    hrm_config = BEHAVIOR_CONFIG.get('home_row_mods', {})

    if '_TKZ' in behavior and 'HRM_' in behavior:
        tap_key = extract_tap_key_from_params(params)
        for finger, symbol in hrm_config.items():
            if finger in behavior:
                return symbol if is_overlay_layer else (tap_key or finger)

    finger_map = [('Pinky', 'pinky'), ('Ringy', 'ring'), ('Middy', 'middy'), ('Index', 'index')]
    for camel, snake in finger_map:
        if f'Left{camel}' in behavior or f'Right{camel}' in behavior:
            if is_overlay_layer:
                return hrm_config.get(snake, '')
            if '(' in behavior and ')' in behavior:
                tap_key = behavior.split('(')[1].split(',')[0].strip()
                return ZMK_KEY_MAPPING.get(tap_key, tap_key)
            return {'pinky': 'N', 'ring': 'R', 'middy': 'T', 'index': 'S'}.get(snake, '')

    return None


def handle_layer_behavior(behavior: str) -> Optional[str]:
    """Handle layer-related behaviors (&mo, &tog, &sk)."""
    layer_abbrev = BEHAVIOR_CONFIG.get('layer_abbreviations', {})
    sticky_mods = BEHAVIOR_CONFIG.get('sticky_modifiers', {})

    if '&mo ' in behavior:
        if 'LAYER_' in behavior:
            layer_part = behavior.split('LAYER_')[1].split()[0]
            return layer_abbrev.get(layer_part, layer_part[:8])
        return 'Layer'

    if '&tog' in behavior:
        if 'LAYER_' in behavior:
            layer_part = behavior.split('LAYER_')[1].split()[0]
            abbr = layer_abbrev.get(layer_part, layer_part[:4])
            return f'\U0001F512{abbr}'
        return '\U0001F504'

    if '&sk' in behavior:
        for pattern, symbol in sticky_mods.items():
            if pattern in behavior:
                return symbol
        parts = behavior.split()
        if len(parts) >= 2:
            mod_key = parts[1]
            return sticky_mods.get(mod_key, '\u26a1\u21e7')
        return '\u26a1\u21e7'

    return None


def handle_mouse_behavior(behavior: str) -> Optional[str]:
    """Handle mouse behaviors using config lookups."""
    scroll_map = BEHAVIOR_CONFIG.get('mouse_scroll', {})
    move_map = BEHAVIOR_CONFIG.get('mouse_move', {})
    click_map = BEHAVIOR_CONFIG.get('mouse_click', {})

    if '&msc' in behavior:
        for pattern, result in scroll_map.items():
            if pattern in behavior:
                return result
        return 'Scroll'

    if '&mmv' in behavior:
        for pattern, result in move_map.items():
            if pattern in behavior:
                return result
        return 'Move'

    if '&mkp' in behavior:
        for pattern, result in click_map.items():
            if pattern in behavior:
                return result
        return 'Click'

    return None


def handle_rgb_behavior(behavior: str) -> Optional[str]:
    """Handle RGB behaviors using config lookups."""
    rgb_map = BEHAVIOR_CONFIG.get('rgb_commands', {})
    if '&rgb_ug' in behavior:
        for pattern, result in rgb_map.items():
            if pattern in behavior:
                return add_spaces_to_long_words(result)
        return 'RGB'
    return None


def handle_bluetooth_behavior(behavior: str) -> Optional[str]:
    """Handle bluetooth behaviors using config lookups."""
    bt_map = BEHAVIOR_CONFIG.get('bluetooth', {})
    if '&bt' in behavior:
        for pattern, result in bt_map.items():
            if pattern in behavior:
                return result
        return 'BT'
    return None


def handle_output_behavior(behavior: str) -> Optional[str]:
    """Handle output behaviors using config lookups."""
    out_map = BEHAVIOR_CONFIG.get('output', {})
    if '&out' in behavior:
        for pattern, result in out_map.items():
            if pattern in behavior:
                return result
        return 'Output'
    return None


def lookup_yaml_character(yaml_file: str, prefix: str, behavior: str) -> str:
    """Look up a character from emoji.yaml or world.yaml."""
    import yaml
    import os

    project_root = get_project_root()
    yaml_path = os.path.join(project_root, yaml_file)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    behavior_name = behavior.replace(prefix, '').strip()

    if 'codepoints' in data:
        if behavior_name in data['codepoints']:
            return data['codepoints'][behavior_name]
        try:
            numeric_key = int(behavior_name)
            if numeric_key in data['codepoints']:
                return data['codepoints'][numeric_key]
        except ValueError:
            pass

    if 'transforms' in data and '_base' in behavior_name:
        letter_orig = behavior_name.replace('_base', '')
        for letter in [letter_orig.upper(), letter_orig.lower()]:
            if letter in data.get('transforms', {}):
                base_transform = data['transforms'][letter].get('base')
                if base_transform and letter in data.get('characters', {}):
                    char = data['characters'][letter].get(base_transform)
                    if isinstance(char, dict):
                        return char.get('lower', char.get('regular', list(char.values())[0]))
                    return char

    for group_name, group_items in data.get('characters', {}).items():
        for item_name, variants in group_items.items():
            if behavior_name == f'{group_name}_{item_name}':
                if isinstance(variants, dict):
                    return list(variants.values())[0]
                return variants

    raise ValueError(f"Character '{behavior_name}' not found in {yaml_file}")


def parse_custom_behavior(behavior_str: str, layer_name: str = '', params: List[Any] = None) -> str:
    """Parse custom ZMK behaviors using config-driven lookups."""
    if not behavior_str:
        raise ValueError("Empty behavior string provided")
    if params is None:
        params = []

    behavior = behavior_str.strip()
    base_layers = BEHAVIOR_CONFIG.get('base_layer_names', ['', 'GRAPHITE', 'HRM_macOS', 'HRM_WinLinx', 'Typing'])
    is_overlay_layer = layer_name not in base_layers

    if '_TKZ' in behavior:
        hrm_result = handle_home_row_mod(behavior, is_overlay_layer, params)
        if hrm_result:
            return hrm_result

        if 'AS_' in behavior:
            return 'AS'

        selection_map = BEHAVIOR_CONFIG.get('selection_behaviors', {})
        for pattern, result in selection_map.items():
            if pattern in behavior:
                return result

        if 'thumb_' in behavior or 'space_' in behavior:
            return extract_tap_key_from_params(params, '\u23b5')

        if 'mstr' in behavior:
            return 'Mouse'

        parts = behavior.replace('&', '').split('_')
        for part in parts:
            if part.upper() in ZMK_KEY_MAPPING:
                return ZMK_KEY_MAPPING[part.upper()]
        return behavior.replace('&', '').replace('_v1_TKZ', '').replace('_v2_TKZ', '').replace('_v3_TKZ', '')

    hrm_result = handle_home_row_mod(behavior, is_overlay_layer, params)
    if hrm_result:
        return hrm_result

    graphite_map = BEHAVIOR_CONFIG.get('graphite_morphs', {})
    for pattern, result in graphite_map.items():
        if pattern in behavior:
            return result

    if 'parang_left' in behavior:
        return '('
    if 'parang_right' in behavior:
        return ')'

    if '&kp ' in behavior:
        parts = behavior.split()
        if len(parts) >= 2:
            key_code = parts[1]

            match = re.search(r'_?C\(([A-Z])\)', key_code)
            if match:
                return f'\u2318{match.group(1)}'

            if is_overlay_layer:
                hrm_config = BEHAVIOR_CONFIG.get('home_row_mods', {})
                mod_patterns = [('PINKY_MOD', 'pinky'), ('RINGY_MOD', 'ring'), ('MIDDY_MOD', 'middy'), ('INDEX_MOD', 'index')]
                for pattern, finger in mod_patterns:
                    if pattern in key_code:
                        return hrm_config.get(finger, '')
                if 'LGUI' in key_code or 'RGUI' in key_code:
                    return '\u2318'

            return ZMK_KEY_MAPPING.get(key_code.replace('_', ''), key_code)

    layer_result = handle_layer_behavior(behavior)
    if layer_result:
        return layer_result

    special_map = BEHAVIOR_CONFIG.get('special_behaviors', {})
    for pattern, result in special_map.items():
        if pattern in behavior:
            return result

    mouse_result = handle_mouse_behavior(behavior)
    if mouse_result:
        return mouse_result

    rgb_result = handle_rgb_behavior(behavior)
    if rgb_result:
        return rgb_result

    bt_result = handle_bluetooth_behavior(behavior)
    if bt_result:
        return bt_result

    out_result = handle_output_behavior(behavior)
    if out_result:
        return out_result

    selection_map = BEHAVIOR_CONFIG.get('selection_behaviors', {})
    for pattern, result in selection_map.items():
        if pattern in behavior:
            return result

    if '&to ' in behavior:
        parts = behavior.split()
        if len(parts) >= 2:
            return f'Layer {parts[1]}'
        return 'Layer'

    if '&thumb' in behavior:
        parts = behavior.split()
        if len(parts) >= 3:
            return ZMK_KEY_MAPPING.get(parts[-1], parts[-1])
        return 'THUMB'

    if '_HOME' in behavior:
        return 'HOME'
    if '_END' in behavior:
        return 'END'

    match = re.search(r'_?C\(([A-Z])\)', behavior)
    if match:
        return f'\u2318{match.group(1)}'

    if '&emoji_' in behavior:
        preset_map = {'skin_tone_preset': '\U0001F3FC', 'gender_sign_preset': '\u2640\ufe0f', 'hair_style_preset': '\U0001F9B1'}
        behavior_name = behavior.replace('&emoji_', '').strip()
        if behavior_name in preset_map:
            return preset_map[behavior_name]
        return lookup_yaml_character('emoji.yaml', '&emoji_', behavior)

    if '&world_' in behavior:
        return lookup_yaml_character('world.yaml', '&world_', behavior)

    if behavior.startswith('&bt_'):
        return f'BT {behavior.replace("&bt_", "")}'

    clean_behavior = behavior.replace('&', '').replace('_', '').upper()
    if clean_behavior in ZMK_KEY_MAPPING:
        return ZMK_KEY_MAPPING[clean_behavior]

    clean_name = behavior.replace('&', '').replace('_', ' ').strip()
    return clean_name[:12] if len(clean_name) > 12 else clean_name


def convert_zmk_key(key_data: Dict[str, Any], layer_name: str = '') -> str:
    """Convert ZMK key data to readable string using config-driven lookups."""
    value = key_data.get('value', '')
    params = key_data.get('params', [])

    if value in ('&trans', '&none'):
        return None

    if value == '&kp':
        if not (params and isinstance(params[0], dict)):
            raise ValueError(f"Unknown keypress behavior: {key_data}")

        key_code = params[0].get('value', '')
        inner_params = params[0].get('params', [])

        if key_code in ('LS', 'RS') and inner_params:
            inner_key = inner_params[0].get('value', '')
            mod_symbols = BEHAVIOR_CONFIG.get('modifier_symbols', {})

            if inner_key in mod_symbols:
                return handle_modifier_chain(params)

            result = handle_shifted_key(inner_key)
            if result:
                return result
            return f'\u21e7{ZMK_KEY_MAPPING.get(inner_key, inner_key)}'

        mod_symbols = BEHAVIOR_CONFIG.get('modifier_symbols', {})
        if key_code in mod_symbols and inner_params:
            return handle_modifier_chain(params)

        for prefix in ('LS(', 'RS('):
            if key_code.startswith(prefix) and key_code.endswith(')'):
                inner_key = key_code[3:-1]
                result = handle_shifted_key(inner_key)
                if result:
                    return result
                return ZMK_KEY_MAPPING.get(inner_key, inner_key)

        result = ZMK_KEY_MAPPING.get(key_code, key_code)
        return add_spaces_to_long_words(result)

    if value == '&to':
        if params and isinstance(params[0], dict):
            layer_num = params[0].get('value', '')
            return f'Layer {layer_num}'
        return 'Layer'

    if value == '&layer':
        layer_map = BEHAVIOR_CONFIG.get('layer_momentary', {})
        if params and isinstance(params[0], dict):
            layer_idx = params[0].get('value', '')
            if str(layer_idx) in layer_map:
                return layer_map[str(layer_idx)]
            return f'Layer {layer_idx}'
        return 'Layer'

    if value == '&mo':
        layer_map = BEHAVIOR_CONFIG.get('layer_momentary', {})
        if params and isinstance(params[0], dict):
            layer_idx = params[0].get('value', '')
            if str(layer_idx) in layer_map:
                return layer_map[str(layer_idx)]
            return f'mo{layer_idx}'
        return 'mo'

    if value == '&mt':
        if len(params) >= 2 and isinstance(params[1], dict):
            key_code = params[1].get('value', '')
            return ZMK_KEY_MAPPING.get(key_code, key_code)
        raise ValueError(f"Invalid mod-tap behavior: {key_data}")

    if value == '&msc':
        scroll_map = BEHAVIOR_CONFIG.get('mouse_scroll', {})
        if params and isinstance(params[0], dict):
            scroll_type = params[0].get('value', '')
            return scroll_map.get(scroll_type, 'Scroll')
        return 'Scroll'

    if value == '&mmv':
        move_map = BEHAVIOR_CONFIG.get('mouse_move', {})
        if params and isinstance(params[0], dict):
            move_type = params[0].get('value', '')
            return move_map.get(move_type, 'Move')
        return 'Move'

    if value == '&mkp':
        click_map = BEHAVIOR_CONFIG.get('mouse_click', {})
        if params and isinstance(params[0], dict):
            click_type = params[0].get('value', '')
            return click_map.get(click_type, 'Click')
        return 'Click'

    if value == '&rgb_ug':
        rgb_map = BEHAVIOR_CONFIG.get('rgb_commands', {})
        if params and isinstance(params[0], dict):
            rgb_cmd = params[0].get('value', '')
            result = rgb_map.get(rgb_cmd, 'RGB')
            return add_spaces_to_long_words(result)
        return 'RGB'

    if value == 'Custom':
        if params and isinstance(params[0], dict):
            custom_behavior = params[0].get('value', '')
            result = parse_custom_behavior(custom_behavior, layer_name)
            return add_spaces_to_long_words(result)
        raise ValueError(f"Unknown custom behavior: {key_data}")

    if value.startswith('&'):
        result = parse_custom_behavior(value, layer_name, params)
        return add_spaces_to_long_words(result)

    result = ZMK_KEY_MAPPING.get(value, value)
    return add_spaces_to_long_words(result)
