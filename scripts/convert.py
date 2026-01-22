"""Main CLI and orchestration for ZMK keymap conversion."""

import json
import os
import re
import sys
import argparse
from typing import Dict, List, Any, Optional

from .config_loader import (
    load_keyboard_config,
    load_info_json,
    load_zmk_key_mapping,
    load_behavior_config,
    get_project_root,
)
from .zmk_parser import convert_zmk_key
from .output_formatter import format_compact_json

ZMK_KEY_MAPPING = load_zmk_key_mapping()
BEHAVIOR_CONFIG = load_behavior_config()


def parse_zmk_triggers(dtsi_filepath: str = "keymap.dtsi") -> Dict[str, str]:
    """Parse actual ZMK trigger bindings from keymap.dtsi"""
    triggers = {}

    try:
        with open(dtsi_filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        macro_pattern = r'(\w+_with_[^:]+):\s*\1\s*\{[^}]*bindings\s*=\s*<[^>]*&kp\s+([^>]+)>'
        macro_matches = re.findall(macro_pattern, content, re.MULTILINE | re.DOTALL)

        behavior_to_trigger = {}
        for behavior_name, trigger_combo in macro_matches:
            trigger = trigger_combo.strip().rstrip(';').strip()
            behavior_to_trigger[behavior_name] = trigger

        thumb_pattern = r'thumb_(\w+):\s*thumb_\1\s*\{[^}]*bindings\s*=\s*<&([^,]+)>'
        thumb_matches = re.findall(thumb_pattern, content, re.MULTILINE | re.DOTALL)

        for layer_name, macro_behavior in thumb_matches:
            if macro_behavior in behavior_to_trigger:
                zmk_combo = behavior_to_trigger[macro_behavior]
                readable_trigger = convert_zmk_combo_to_readable(zmk_combo)
                triggers[layer_name.lower()] = readable_trigger

        space_pattern = r'space_(\w+):\s*space_\1\s*\{[^}]*bindings\s*=\s*<&([^,]+)>'
        space_matches = re.findall(space_pattern, content, re.MULTILINE | re.DOTALL)

        for layer_name, macro_behavior in space_matches:
            if macro_behavior in behavior_to_trigger:
                zmk_combo = behavior_to_trigger[macro_behavior]
                readable_trigger = convert_zmk_combo_to_readable(zmk_combo)
                triggers[layer_name.lower()] = readable_trigger

    except FileNotFoundError:
        print(f"Warning: {dtsi_filepath} not found, no triggers will be available")
    except Exception as e:
        print(f"Warning: Error parsing {dtsi_filepath}: {e}, no triggers will be available")

    return triggers


def convert_zmk_combo_to_readable(zmk_combo: str) -> str:
    """Convert ZMK key combination to readable format"""
    combo = zmk_combo.strip()

    if '_C(' in combo:
        inner = combo.split('_C(')[1].rstrip(')').strip()
        if inner == 'A':
            return 'cmd+a'
        elif inner == 'L':
            return 'cmd+l'
        elif inner == 'Z':
            return 'cmd+z'
        else:
            return f'cmd+{inner.lower()}'

    replacements = [
        ('LG(', 'cmd+'), ('LA(', 'alt+'), ('LC(', 'ctrl+'), ('LS(', 'shift+'),
        ('RG(', 'cmd+'), ('RA(', 'alt+'), ('RC(', 'ctrl+'), ('RS(', 'shift+'),
        ('_WORD(', 'alt+'),
    ]

    for zmk_mod, readable_mod in replacements:
        combo = combo.replace(zmk_mod, readable_mod)

    combo = combo.replace(')', '')

    if '+' in combo:
        parts = combo.split('+')
        if len(parts) == 2:
            modifier, key = parts
            combo = f'{modifier}{key.lower()}'

    return combo


def parse_zmk_macro_definitions(dtsi_filepath: str = "keymap.dtsi.erb") -> Dict[str, str]:
    """Parse actual ZMK macro definitions from ERB template to get real key combinations"""
    macro_mappings = {}

    try:
        with open(dtsi_filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        os_pattern = r"#define\s+OPERATING_SYSTEM\s+'([LMW])'"
        os_match = re.search(os_pattern, content)
        is_macos = os_match and os_match.group(1) == 'M'

        print(f"Detected {'macOS' if is_macos else 'Linux/Windows'} mode")

        select_word_pattern = r'ZMK_MACRO\(select_word_right,.*?bindings\s*=\s*<([^>]+)>'
        select_word_match = re.search(select_word_pattern, content, re.DOTALL)
        if select_word_match:
            bindings = select_word_match.group(1)
            if 'LS(_WORD(RIGHT))' in bindings or 'LS' in bindings and '_WORD' in bindings:
                macro_mappings['select_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'
            else:
                macro_mappings['select_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'

        extend_word_pattern = r'ZMK_MACRO\(extend_word_right,.*?bindings\s*=\s*<([^>]+)>'
        extend_word_match = re.search(extend_word_pattern, content, re.DOTALL)
        if extend_word_match:
            bindings = extend_word_match.group(1)
            if 'LS(_WORD(RIGHT))' in bindings or 'LS' in bindings and '_WORD' in bindings:
                macro_mappings['extend_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'

        select_line_pattern = r'ZMK_MACRO\(select_line_right,.*?bindings\s*=\s*<([^>]+)>'
        select_line_match = re.search(select_line_pattern, content, re.DOTALL)
        if select_line_match:
            bindings = select_line_match.group(1)
            if is_macos:
                if '_HOME' in bindings and 'LS(_END)' in bindings:
                    macro_mappings['select_line'] = 'cmd+shift+right'
                else:
                    macro_mappings['select_line'] = 'cmd+shift+right'
            else:
                macro_mappings['select_line'] = 'shift+end'

        extend_line_pattern = r'ZMK_MACRO\(extend_line_right,.*?bindings\s*=\s*<([^>]+)>'
        extend_line_match = re.search(extend_line_pattern, content, re.DOTALL)
        if extend_line_match:
            bindings = extend_line_match.group(1)
            if is_macos:
                macro_mappings['extend_line'] = 'shift+cmd+right'
            else:
                macro_mappings['extend_line'] = 'shift+end'

        select_all_pattern = r'#define\s+select_all\s+kp\s+_C\(A\)'
        if re.search(select_all_pattern, content):
            macro_mappings['select_all'] = 'cmd+a' if is_macos else 'ctrl+a'

        select_none_pattern = r'ZMK_MACRO\(select_none,.*?bindings\s*=\s*<([^>]+)>'
        select_none_match = re.search(select_none_pattern, content, re.DOTALL)
        if select_none_match:
            bindings = select_none_match.group(1)
            if 'ESC' in bindings or 'ESCAPE' in bindings:
                macro_mappings['select_none'] = 'escape'
            elif 'LEFT' in bindings:
                macro_mappings['select_none'] = 'left'
            else:
                macro_mappings['select_none'] = 'escape'

        standard_ops = {
            '_CUT': 'x',
            '_COPY': 'c',
            '_PASTE': 'v',
            '_UNDO': 'z',
            '_FIND': 'f',
        }

        for op_name, key in standard_ops.items():
            pattern = rf'#define\s+{op_name}\s+_C\({key.upper()}\)'
            if re.search(pattern, content, re.IGNORECASE):
                prefix = 'cmd' if is_macos else 'ctrl'
                macro_mappings[op_name.lstrip('_').lower()] = f'{prefix}+{key}'

        if is_macos:
            if re.search(r'#define\s+_REDO\s+LG\(LS\(Z\)\)', content):
                macro_mappings['redo'] = 'cmd+shift+z'
        else:
            if re.search(r'#define\s+_REDO\s+LC\(Y\)', content):
                macro_mappings['redo'] = 'ctrl+y'

        if re.search(r'#define\s+_FIND_NEXT\s+_C\(G\)', content):
            macro_mappings['find_next'] = 'cmd+g' if is_macos else 'ctrl+g'
        if re.search(r'#define\s+_FIND_PREV\s+_C\(LS\(G\)\)', content):
            macro_mappings['find_prev'] = 'cmd+shift+g' if is_macos else 'ctrl+shift+g'

        print(f"Parsed ZMK macro definitions: {len(macro_mappings)} macros found")

    except Exception as e:
        print(f"Warning: Could not parse ZMK macros from {dtsi_filepath}: {e}")

    return macro_mappings


def find_custom_behaviors_in_keymap(data):
    """Scan keymap.json to find all custom behaviors used in layers"""
    custom_behaviors = set()

    def scan_value(obj):
        if isinstance(obj, dict):
            value = obj.get('value', '')
            if isinstance(value, str) and value.startswith('&'):
                standard_behaviors = [
                    '&kp', '&mt', '&mo', '&tog', '&sk', '&trans', '&none',
                    '&lt', '&td', '&rgb_ug', '&ext_power', '&out', '&bt',
                    '&mkp', '&mmv', '&msc', '&mwh', '&caps_word', '&key_repeat'
                ]
                if not any(value.startswith(std) for std in standard_behaviors):
                    behavior_name = value.split()[0][1:]
                    custom_behaviors.add(behavior_name)
            params = obj.get('params', [])
            if params:
                for param in params:
                    scan_value(param)
        elif isinstance(obj, list):
            for item in obj:
                scan_value(item)
        elif isinstance(obj, str) and obj.startswith('&'):
            behavior_name = obj.split()[0][1:]
            custom_behaviors.add(behavior_name)

    layers = data.get('layers', [])
    for layer in layers:
        for key_data in layer:
            scan_value(key_data)

    return custom_behaviors


def scan_generated_display_names(data):
    """Scan all layers for generated display names to find what needs action mappings"""
    display_names = set()

    layers = data.get('layers', [])
    layer_names_list = data.get('layer_names', [])

    for i, layer_data in enumerate(layers):
        layer_name = layer_names_list[i] if i < len(layer_names_list) else f"Layer_{i}"

        for key_data in layer_data:
            if isinstance(key_data, dict):
                display_name = convert_zmk_key(key_data, layer_name)
                if display_name and isinstance(display_name, str):
                    action_keywords = [
                        'Sel ', 'Ext ', 'Clear',
                        'Cut', 'Copy', 'Paste', 'Undo', 'Redo',
                        '\u2318', '\u2325', '\u2303', '\u21e7',
                        '\U0001F50D', '\U0001F512',
                        'Home', 'End', 'PgUp', 'PgDn',
                        '\u2600', '\U0001F50A', '\U0001F509', '\U0001F507',
                        'Scroll', 'Click', 'Btn',
                        'Layer', 'Toggle', 'MAGIC'
                    ]
                    if any(keyword in display_name for keyword in action_keywords):
                        display_names.add(display_name)

    return display_names


def extract_custom_shift_mappings_from_emoji_yaml():
    """Extract custom shift mappings from emoji.yaml characters section"""
    shift_mappings = {}

    try:
        import yaml
        project_root = get_project_root()
        emoji_path = os.path.join(project_root, 'emoji.yaml')
        with open(emoji_path, 'r', encoding='utf-8') as f:
            emoji_data = yaml.safe_load(f)
    except ImportError as e:
        print(f"Warning: PyYAML not available for emoji shift mapping: {e}")
        return {}
    except FileNotFoundError as e:
        print(f"Warning: emoji.yaml not found for shift mapping: {e}")
        return {}

    characters = emoji_data.get('characters', {})

    for group_name, group_items in characters.items():
        for item_name, variants in group_items.items():
            if isinstance(variants, dict) and len(variants) == 2:
                variant_keys = list(variants.keys())
                variant_values = list(variants.values())

                if len(variant_values) == 2:
                    unshifted_emoji = variant_values[0]
                    shifted_emoji = variant_values[1]
                    shift_mappings[unshifted_emoji] = shifted_emoji

    print(f"Found {len(shift_mappings)} emoji shift mappings")
    return shift_mappings


def extract_action_mappings_from_keymap(data):
    """Extract actual key mappings from ZMK keymap data to generate proper actionMappings"""
    mappings = {}

    custom_behaviors = find_custom_behaviors_in_keymap(data)
    if len(custom_behaviors) > 0:
        print(f"Found {len(custom_behaviors)} custom behaviors in keymap")
    print()

    display_names = scan_generated_display_names(data)
    if len(display_names) > 0:
        print(f"Found {len(display_names)} generated display names that may need action mappings")
        relevant_names = [n for n in display_names if any(k in n for k in ['Sel ', 'Ext ', 'Clear', 'Cut', 'Copy', 'Paste', 'Undo', 'Redo'])]
        if relevant_names:
            print(f"  Key editing actions found: {', '.join(sorted(relevant_names)[:10])}")
    print()

    zmk_macros = parse_zmk_macro_definitions()

    behavior_to_display_mappings = {
        "select_all": "Sel All",
        "select_word": "Sel Word",
        "select_line": "Sel Line",
        "extend_word": "Ext Word",
        "extend_line": "Ext Line",
        "select_none": "Clear",
        "cut": "Cut",
        "copy": "Copy",
        "paste": "Paste",
        "undo": "Undo",
        "redo": "Redo",
        "find": "\U0001F50D",
    }

    for zmk_name, display_name in behavior_to_display_mappings.items():
        if zmk_name in zmk_macros:
            mappings[display_name] = zmk_macros[zmk_name]
            print(f"Mapped {display_name} -> {zmk_macros[zmk_name]} (from ZMK macro)")
        elif display_name in display_names:
            print(f"Warning: Found display name '{display_name}' but no ZMK macro '{zmk_name}'")

    standard_mappings = {
        "Cut": zmk_macros.get('cut', 'cmd+x'),
        "Copy": zmk_macros.get('copy', 'cmd+c'),
        "Paste": zmk_macros.get('paste', 'cmd+v'),
        "Undo": zmk_macros.get('undo', 'cmd+z'),
        "Redo": zmk_macros.get('redo', 'cmd+shift+z'),
        "Home": "cmd+up",
        "END": "cmd+down",
        "End": "cmd+down",
        "PgUp": "pageup",
        "PgDn": "pagedown",
        "Insert": "insert",
        "Delete": "delete",
        "\u232b": "backspace",
        "\u2326": "delete",
        "\u21b5": "enter",
        "\u21e5": "tab",
        "\u21e7\u21e5": "shift+tab",
        "\u238b": "escape",
        "\u23b5": "space",
        "\u2190": "left",
        "\u2192": "right",
        "\u2191": "up",
        "\u2193": "down",
        "\U0001F50D": "cmd+f",
        "\U0001F50D\u2190": "cmd+g",
        "\U0001F50D\u2192": "cmd+shift+g",
        "\u2303": "ctrl",
        "\u2325": "alt",
        "\u2318": "cmd",
        "\u21e7": "shift",
        "ALT": "alt",
        "\u2318L": "cmd+l",
        "\u2318K": "cmd+k",
        "\u2318H": "cmd+h",
        "\u2318\u21e7N": "cmd+shift+n",
        "\u2318\u21e7Y": "cmd+shift+y",
        "\u2318\u21e7A": "cmd+shift+a",
        "\u21ea": "capslock",
        "\u21f3": "f14",
        "NumLock": "f6",
        "\u23fb": "power",
        "\U0001F634": "cmd+alt+eject",
        "\U0001F512": "cmd+ctrl+q",
        "\U0001F4F7": "cmd+shift+4",
        "\U0001F3E0": "f3",
        "\U0001F5D1": "clear"
    }
    mappings.update(standard_mappings)

    layer_mappings = {
        "\U0001F512Fn": "layer_toggle_function",
        "\U0001F512Cur": "layer_toggle_cursor",
        "\U0001F512Num": "layer_toggle_number",
        "\U0001F512Sym": "layer_toggle_symbol",
        "\U0001F512Mouse": "layer_toggle_mouse",
        "\U0001F512Sys": "layer_toggle_system",
        "\U0001F512Emoji": "layer_toggle_emoji",
        "\U0001F512World": "layer_toggle_world",
        "Lower": "layer_momentary_lower",
        "Typing": "layer_base",
        "MAGIC": "layer_magic"
    }
    mappings.update(layer_mappings)

    consumer_codes_found = set()

    def scan_behaviors(obj):
        if isinstance(obj, dict):
            if 'value' in obj:
                value = obj['value']
                if isinstance(value, str) and value.startswith('C_'):
                    consumer_codes_found.add(value)
            for v in obj.values():
                scan_behaviors(v)
        elif isinstance(obj, list):
            for item in obj:
                scan_behaviors(item)

    scan_behaviors(data)

    consumer_mappings = {
        'C_BRI_UP': 'f2',
        'C_BRI_DN': 'f1',
        'C_BRI_MAX': 'shift+f2',
        'C_BRI_MIN': 'shift+f1',
        'C_BRI_AUTO': 'f14',
        'C_VOL_UP': 'f12',
        'C_VOL_DN': 'f11',
        'C_MUTE': 'f10',
        'C_PLAY': 'f8',
        'C_PAUSE': 'f8',
        'C_PLAY_PAUSE': 'f8',
        'C_PP': 'f8',
        'C_NEXT': 'f9',
        'C_PREV': 'f7',
        'C_STOP': 'f6',
        'C_REWIND': 'f7',
        'C_FAST_FORWARD': 'f9',
        'C_EJECT': 'f12',
        'C_MEDIA_HOME': 'f3'
    }

    for code in sorted(consumer_codes_found):
        if code in consumer_mappings:
            mappings[code] = consumer_mappings[code]
            display_symbol = ZMK_KEY_MAPPING.get(code)
            if display_symbol:
                mappings[display_symbol] = consumer_mappings[code]

    mouse_mappings = {
        "L Click": "button1",
        "R Click": "button2",
        "M Click": "button3",
        "Btn4": "button4",
        "Btn5": "button5",
        "\u2630": "button3",
        "Slow": "mouseslow",
        "Fast": "mousefast",
        "Warp": "mousewarp",
        "Scroll\u2190": "scrollleft",
        "Scroll\u2192": "scrollright",
        "Scroll\u2191": "scrollup",
        "Scroll\u2193": "scrolldown"
    }
    mappings.update(mouse_mappings)

    print(f"Found consumer codes: {sorted(consumer_codes_found)}")

    return mappings


def convert_keymap(input_file: str, output_file: str, layer_names: Optional[List[str]] = None, info_path: Optional[str] = None):
    """Convert a ZMK keymap JSON to OverKeys split_matrix_explicit format."""

    with open(input_file, 'r', encoding='utf-8') as f:
        keymap = json.load(f)

    keyboard_type = keymap.get('keyboard', 'glove80').lower()

    keyboard_layout = load_keyboard_config(keyboard_type)
    if keyboard_layout:
        print(f"Loaded keyboard config from keyboards/{keyboard_type}/")
    else:
        keyboard_layout = load_keyboard_config('glove80')
        if keyboard_layout:
            print(f"Warning: Unknown keyboard '{keyboard_type}', falling back to glove80")
            keyboard_type = 'glove80'
        else:
            raise ValueError(f"No keyboard config found for '{keyboard_type}' or 'glove80'. "
                           f"Create keyboards/{keyboard_type}/keyboard.json")

    layers = keymap.get('layers', [])
    layer_names_list = keymap.get('layer_names', [])

    print(f"Total layers available: {len(layers)}")
    print(f"Layer names: {layer_names_list}")

    target_layers = layer_names or keyboard_layout.get('default_layers', layer_names_list)
    print(f"Target layers: {', '.join(target_layers)}")

    zmk_triggers = {}
    if keyboard_type == 'glove80':
        print("Parsing ZMK triggers from keymap.dtsi...")
        zmk_triggers = parse_zmk_triggers()
        print(f"Found triggers: {zmk_triggers}")

    print("Scanning keymap for consumer codes...")
    action_mappings = extract_action_mappings_from_keymap(keymap)

    custom_shift_mappings = {}
    try:
        print("Scanning emoji.yaml for shift mappings...")
        custom_shift_mappings = extract_custom_shift_mappings_from_emoji_yaml()
    except FileNotFoundError:
        print("  (emoji.yaml not found, skipping shift mappings)")

    layer_indices = []
    for layer_name in target_layers:
        if layer_name in layer_names_list:
            layer_indices.append(layer_names_list.index(layer_name))
        else:
            print(f"Warning: Layer '{layer_name}' not found")

    user_layouts = []

    for i in layer_indices:
        if i >= len(layers):
            continue

        layer_data = layers[i]
        layer_name = layer_names_list[i] if i < len(layer_names_list) else f"Layer_{i}"

        trigger = None
        layer_triggers = keyboard_layout.get('layer_triggers', {})
        cycle_group = keyboard_layout.get('cycle_group', {})
        cycle_layers = cycle_group.get('layers', [])

        if layer_name in cycle_layers:
            trigger = None
        elif layer_name in layer_triggers:
            trigger = layer_triggers[layer_name]
        elif layer_name.lower() in zmk_triggers:
            trigger = zmk_triggers[layer_name.lower()]

        layout = {
            "name": layer_name,
            "layoutStyle": "split_matrix_explicit",
            "leftHand": {"mainRows": [], "thumbRows": []},
            "rightHand": {"mainRows": [], "thumbRows": []}
        }

        for row_positions in keyboard_layout['left_main_rows']:
            row = []
            for pos in row_positions:
                if pos is None:
                    row.append(None)
                elif pos < len(layer_data):
                    key = convert_zmk_key(layer_data[pos], layer_name)
                    row.append(key)
                else:
                    row.append(None)

            if all(key is None for key in row):
                row = []

            layout["leftHand"]["mainRows"].append(row)

        for row_positions in keyboard_layout['right_main_rows']:
            row = []
            for pos in row_positions:
                if pos is None:
                    row.append(None)
                elif pos < len(layer_data):
                    key = convert_zmk_key(layer_data[pos], layer_name)
                    row.append(key)
                else:
                    row.append(None)

            if all(key is None for key in row):
                row = []

            layout["rightHand"]["mainRows"].append(row)

        for row_positions in keyboard_layout['left_thumb_rows']:
            row = []
            for pos in row_positions:
                if pos is None:
                    row.append(None)
                elif pos < len(layer_data):
                    key = convert_zmk_key(layer_data[pos], layer_name)
                    row.append(key)
                else:
                    row.append(None)
            if all(key is None for key in row):
                row = []

            layout["leftHand"]["thumbRows"].append(row)

        for row_positions in keyboard_layout['right_thumb_rows']:
            row = []
            for pos in row_positions:
                if pos is None:
                    row.append(None)
                elif pos < len(layer_data):
                    key = convert_zmk_key(layer_data[pos], layer_name)
                    row.append(key)
                else:
                    row.append(None)
            if all(key is None for key in row):
                row = []

            layout["rightHand"]["thumbRows"].append(row)

        if trigger:
            layout["trigger"] = trigger
            layout["type"] = "toggle"

        layer_config = keyboard_layout.get('layer_config', {})
        if layer_name in layer_config:
            layout["activeKey"] = layer_config[layer_name]

        user_layouts.append(layout)

    home_row_index = keyboard_layout.get('home_row_index', 3)
    config = {
        "userLayouts": user_layouts,
        "defaultUserLayout": user_layouts[0]["name"] if user_layouts else "Base",
        "homeRow": {
            "rowIndex": home_row_index,
            "leftPosition": 2,
            "rightPosition": 2
        },
        "actionMappings": dict(sorted(action_mappings.items()))
    }

    if custom_shift_mappings:
        config["customShiftMappings"] = dict(sorted(custom_shift_mappings.items()))

    if 'metadata' in keyboard_layout:
        config["metadata"] = keyboard_layout['metadata']

    physical_layout_loaded = False
    if info_path and os.path.exists(info_path):
        try:
            config["physicalLayout"] = load_info_json(info_path)
            print(f"Physical layout loaded from: {info_path}")
            physical_layout_loaded = True
        except Exception as e:
            print(f"Warning: Could not load info.json: {e}")

    if not physical_layout_loaded and 'info_json' in keyboard_layout:
        default_info = keyboard_layout['info_json']
        input_dir = os.path.dirname(input_file) or '.'
        for search_path in [os.path.join(input_dir, default_info), default_info]:
            if os.path.exists(search_path):
                try:
                    config["physicalLayout"] = load_info_json(search_path)
                    print(f"Physical layout loaded from: {search_path}")
                    physical_layout_loaded = True
                    break
                except Exception as e:
                    print(f"Warning: Could not load {search_path}: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(format_compact_json(config))

    print(f"\nSUCCESS! Configuration saved to: {output_file}")
    print(f"   Keyboard: {keyboard_type}")
    print(f"   Layers converted: {len(user_layouts)}")
    if custom_shift_mappings:
        print(f"   Custom shift mappings: {len(custom_shift_mappings)}")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Convert ZMK keymap JSON to OverKeys split_matrix_explicit format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Convert keymap.json (auto-detect keyboard)
  %(prog)s --keyboard go60          # Use keyboards/go60/keymap.json
  %(prog)s go60.json                # Convert Go60 keymap from file
  %(prog)s -o go60_config.json go60.json
  %(prog)s --layers HRM_macOS,Cursor,Symbol go60.json
        """
    )
    parser.add_argument('input', nargs='?', default=None,
                        help='Input keymap JSON file (default: keymap.json or from --keyboard)')
    parser.add_argument('-k', '--keyboard', type=str, default=None,
                        help='Keyboard name to load from keyboards/<name>/keymap.json')
    parser.add_argument('-o', '--output', default=None,
                        help='Output file (default: split_matrix_config.json or <keyboard>_config.json)')
    parser.add_argument('--layers', type=str, default=None,
                        help='Comma-separated list of layer names to convert')
    parser.add_argument('--info', type=str, default=None,
                        help='QMK/ZMK info.json file for physical layout (auto-detected)')

    args = parser.parse_args()

    print("ZMK -> OverKeys Converter")

    input_file = args.input
    keyboard_config = None

    if args.keyboard:
        keyboard_config = load_keyboard_config(args.keyboard)
        if keyboard_config and 'keymap_json' in keyboard_config:
            input_file = keyboard_config['keymap_json']
            print(f"Using keymap from keyboards/{args.keyboard}/")
        else:
            print(f"Warning: No keymap.json found in keyboards/{args.keyboard}/")
            if not input_file:
                input_file = 'keymap.json'
    elif not input_file:
        input_file = 'keymap.json'

    output_file = args.output
    if output_file is None:
        if args.keyboard:
            output_file = f'{args.keyboard}_overkeys.json'
        elif input_file == 'keymap.json':
            output_file = 'glove80_overkeys.json'
        else:
            base = os.path.basename(input_file).rsplit('.', 1)[0]
            output_file = f'{base}_overkeys.json'

    layer_names = None
    if args.layers:
        layer_names = [l.strip() for l in args.layers.split(',')]

    try:
        convert_keymap(input_file, output_file, layer_names, args.info)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
