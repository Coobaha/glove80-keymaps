#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///
"""
Glove80 Keymap to Split Matrix Layout Converter
Converts keymap.json to @split-matrix-layouts.md format for OverKeys
Fixed the terrible key mapping issues!
"""

import json
import sys
import re
from typing import Dict, List, Any, Optional

# Glove80 physical layout mapping based on keymap.dtsi
GLOVE80_LAYOUT = {
    'left_main_rows': [
        [0, 1, 2, 3, 4],  # Row 0: F1-F5
        [10, 11, 12, 13, 14, 15],  # Row 1: Numbers + extra
        [22, 23, 24, 25, 26, 27],  # Row 2: Top alpha row + extra
        [34, 35, 36, 37, 38, 39],  # Row 3: Home row + extra
        [46, 47, 48, 49, 50, 51],  # Row 4: Bottom alpha + extra
        [64, 65, 66, 67, 68],  # Row 5: Bottom row (5 keys)
    ],
    'right_main_rows': [
        [5, 6, 7, 8, 9],  # Row 0: F6-F10
        [16, 17, 18, 19, 20, 21],  # Row 1: Numbers + extra
        [28, 29, 30, 31, 32, 33],  # Row 2: Top alpha row + extra
        [40, 41, 42, 43, 44, 45],  # Row 3: Home row + extra
        [58, 59, 60, 61, 62, 63],  # Row 4: Bottom alpha + extra
        [75, 76, 77, 78, 79],  # Row 5: Bottom row (5 keys)
    ],
    'left_thumb_rows': [
        [52, 53, 54],  # Thumb row 0: 3 keys (top row - more accessible)
        [69, 70, 71],  # Thumb row 1: 3 keys (bottom row - less accessible)
    ],
    'right_thumb_rows': [
        [55, 56, 57],  # Thumb row 0: 3 keys (top row) - flipped order
        [72, 73, 74],  # Thumb row 1: 3 keys (bottom row) - flipped order
    ]
}

# ZMK to readable key mapping - NO MORE GARBAGE KEYS!
ZMK_KEY_MAPPING = {
    # Basic keys
    'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G',
    'H': 'H', 'I': 'I', 'J': 'J', 'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N',
    'O': 'O', 'P': 'P', 'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T', 'U': 'U',
    'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z',

    # Numbers
    'N1': '1', 'N2': '2', 'N3': '3', 'N4': '4', 'N5': '5',
    'N6': '6', 'N7': '7', 'N8': '8', 'N9': '9', 'N0': '0',

    # Function keys
    'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4', 'F5': 'F5',
    'F6': 'F6', 'F7': 'F7', 'F8': 'F8', 'F9': 'F9', 'F10': 'F10',
    'F11': 'F11', 'F12': 'F12', 'F13': 'F13', 'F14': 'F14', 'F15': 'F15',
    'F16': 'F16', 'F17': 'F17', 'F18': 'F18', 'F19': 'F19', 'F20': 'F20',

    # Symbols
    'MINUS': '-', 'EQUAL': '=', 'LBKT': '[', 'RBKT': ']', 'BSLH': '\\',
    'SEMI': ';', 'SQT': "'", 'GRAVE': '`', 'COMMA': ',', 'DOT': '.',
    'FSLH': '/', 'EXCL': '!', 'AT': '@', 'HASH': '#', 'DLLR': '$',
    'PRCNT': '%', 'CARET': '^', 'AMPS': '&', 'ASTRK': '*', 'LPAR': '(',
    'RPAR': ')', 'UNDER': '_', 'PLUS': '+', 'LBRC': '{', 'RBRC': '}',
    'PIPE': '|', 'COLON': ':', 'DQT': '"', 'TILDE': '~', 'LT': '<',
    'GT': '>', 'QMARK': '?',

    # Special keys - Icons for compact display
    'SPACE': '⎵', 'TAB': '⇥', 'RET': '↵', 'ESC': '⎋',
    'BSPC': '⌫', 'DEL': '⌦', 'INS': 'Insert',
    'BACKSPACE': '⌫', 'ENTER': '↵', 'INSERT': 'Insert',

    # Navigation - Simple text instead of confusing arrows
    'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓',
    'HOME': 'Home', 'END': 'End', 'PG_UP': 'PgUp', 'PG_DN': 'PgDn',
    'PAGE_UP': 'PgUp', 'PAGE_DOWN': 'PgDn',

    # Modifiers - Fixed LG issue!
    'LSHIFT': 'SHIFT', 'RSHIFT': 'SHIFT', 'LCTRL': 'CTRL', 'RCTRL': 'CTRL',
    'LALT': 'ALT', 'RALT': 'ALT', 'LGUI': '⌘', 'RGUI': '⌘',  # Fixed: CMD not "LG"!
    'LCMD': 'CMD', 'RCMD': 'CMD', 'LWIN': 'WIN', 'RWIN': 'WIN',
    'CTRL': 'CTRL', 'ALT': 'ALT', 'SHIFT': 'SHIFT', 'CMD': 'CMD', 'WIN': 'WIN',

    # Consumer key codes - Icons for media controls
    'C_PLAY': '▶', 'C_PAUSE': '⏸', 'C_PLAY_PAUSE': '⏯', 'C_PP': '⏯',
    'C_STOP': '⏹', 'C_NEXT': '⏭', 'C_PREV': '⏮', 'C_REWIND': '⏪',
    'C_FAST_FORWARD': '⏩', 'C_EJECT': '⏏', 'C_MUTE': '🔇',
    'C_VOL_UP': '🔊', 'C_VOL_DN': '🔉', 'C_BRI_UP': '☀+', 'C_BRI_DN': '☀-',
    'C_BRI_MIN': '☀0', 'C_BRI_MAX': '☀⚡', 'C_BRI_AUTO': '☀🤖',
    'C_MEDIA_HOME': '🏠',

    # Keypad keys - clear readable notation instead of confusing symbols
    'KP_NUM': 'NumLock', 'KP_SLASH': '/', 'KP_MULTIPLY': '*', 'KP_MINUS': '-',
    'KP_PLUS': '+', 'KP_ENTER': '⏎', 'KP_DOT': '.', 'KP_COMMA': ',',
    'KP_EQUAL': '=', 'KP_N0': '0', 'KP_N1': '1', 'KP_N2': '2', 'KP_N3': '3',
    'KP_N4': '4', 'KP_N5': '5', 'KP_N6': '6', 'KP_N7': '7', 'KP_N8': '8', 'KP_N9': '9',

    # System keys - Icons where possible
    'CAPS': '⇪', 'SLCK': '⇳', 'PAUSE_BREAK': '⏸',
    'PSCRN': '📷', 'K_APP': '☰', 'POWER': '⏻', 'SLEEP': '😴',
    'LOCK': '🔒', 'CLEAR': '🗑',

    # Custom symbols
    'DOTDOT': '..', 'STAR': '*',

    # Special underscore-prefixed keys
    '_HOME': 'HOME', '_END': 'END'
}


def add_spaces_to_long_words(text: str) -> str:
    """Replace long words with icons for compact display"""
    # Replace long compound words with icons/short forms
    replacements = {
        # Selection operations with clear short text
        'SelectAll': 'Sel All',
        'SelectLine': 'Sel Line',
        'SelectWord': 'Sel Word',
        'ExtendWord': 'Ext Word',
        'ExtendLine': 'Ext Line',
        'ClearSelect': 'Clear',

        # Media with icons (already handled in ZMK_KEY_MAPPING but for completeness)
        'MediaHome': '🏠',
        'PlayPause': '⏯',
        'BrightMax': '☀⚡',
        'BrightMin': '☀0',
        'AutoBright': '☀🤖',

        # Mouse operations - simple text
        'FastMouse': 'Fast',
        'SlowMouse': 'Slow',
        'WarpMouse': 'Warp',
        'LeftClick': 'L Click',
        'RightClick': 'R Click',
        'MiddleClick': 'M Click',

        # System operations with icons
        'RGBToggle': '🌈',
        'ScrollLock': '⇳',
        'CapsLock': '⇪',
        'PrintScreen': '📷',

        # Find operations
        'FINDPREV': '🔍←',
        'FINDNEXT': '🔍→',
        'FIND': '🔍',

        # Common operations - keep text for clarity
        'UNDO': 'Undo',
        'REDO': 'Redo',
        'CUT': 'Cut',
        'COPY': 'Copy',
        'PASTE': 'Paste',
        'TOGGLE': '🔄',
        'DELETE': 'Delete',
        'BACKSPACE': 'Bksp',
        'INSERT': 'Insert'
    }

    return replacements.get(text, text)


def convert_zmk_key(key_data: Dict[str, Any], layer_name: str = '') -> str:
    """Convert ZMK key data to readable string - MUCH BETTER!"""
    value = key_data.get('value', '')
    params = key_data.get('params', [])

    if value == '&trans':
        return None  # Transparent key
    elif value == '&none':
        return None  # No key
    elif value == '&kp':
        # Standard keypress
        if params and isinstance(params[0], dict):
            key_code = params[0].get('value', '')

            # Handle simple shift combinations FIRST (LS(G) -> G or LS(TAB) -> ⇧Tab)
            if key_code == 'LS' and params[0].get('params'):
                inner_key = params[0]['params'][0].get('value', '')
                # For letters, LS(G) should render as just G since it's a capital letter
                if inner_key in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q',
                                 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']:
                    return inner_key  # Capital letters (shifted) - just show the letter
                elif inner_key == 'TAB':
                    return '⇧⇥'  # Use compact symbols
                else:
                    return f'⇧{ZMK_KEY_MAPPING.get(inner_key, inner_key)}'

            # Handle nested mod combinations like LG(LA(F16)) -> CMD+ALT+F16 (but skip simple LS cases)
            elif key_code in ['LG', 'LA', 'LC'] and params[0].get('params'):
                # Build modifier chain
                mod_chain = []
                current_param = params[0]

                while current_param and isinstance(current_param, dict):
                    mod_key = current_param.get('value', '')
                    if mod_key == 'LG':
                        mod_chain.append('⌘')
                    elif mod_key == 'LA':
                        mod_chain.append('⌥')
                    elif mod_key == 'LC':
                        mod_chain.append('⌃')
                    elif mod_key == 'LS':
                        mod_chain.append('⇧')
                    elif mod_key in ZMK_KEY_MAPPING:
                        # Final key reached
                        if mod_chain:
                            return ''.join(mod_chain) + ZMK_KEY_MAPPING.get(mod_key, mod_key)
                        else:
                            return ZMK_KEY_MAPPING.get(mod_key, mod_key)
                    else:
                        # Final key reached
                        if mod_chain:
                            return ''.join(mod_chain) + mod_key
                        else:
                            return mod_key

                    # Move to next nested parameter
                    if current_param.get('params') and len(current_param['params']) > 0:
                        current_param = current_param['params'][0]
                    else:
                        break

                return ''.join(mod_chain) if mod_chain else 'MOD'
            elif key_code == 'RS' and params[0].get('params'):
                inner_key = params[0]['params'][0].get('value', '')
                return ZMK_KEY_MAPPING.get(inner_key, inner_key)
            # Handle string-based combinations
            elif key_code.startswith('LS(') and key_code.endswith(')'):
                inner_key = key_code[3:-1]
                if inner_key == 'TAB':
                    return '⇧⇥'  # Use compact symbols
                elif inner_key in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q',
                                   'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']:
                    return inner_key  # Capital letters (shifted) - just show the letter
                return ZMK_KEY_MAPPING.get(inner_key, inner_key)
            elif key_code.startswith('RS(') and key_code.endswith(')'):
                inner_key = key_code[3:-1]
                return ZMK_KEY_MAPPING.get(inner_key, inner_key)

            result = ZMK_KEY_MAPPING.get(key_code, key_code)
            return add_spaces_to_long_words(result)
        raise ValueError(f"Unknown keypress behavior: {key_data}")
    elif value == '&to':
        # Layer switch - show layer number/name
        if params and isinstance(params[0], dict):
            layer_num = params[0].get('value', '')
            return f'Layer {layer_num}'
        return 'Layer'
    elif value == '&mt':
        # Mod-tap - show the tap action (the key you actually see)
        if len(params) >= 2 and isinstance(params[1], dict):
            key_code = params[1].get('value', '')
            return ZMK_KEY_MAPPING.get(key_code, key_code)
        raise ValueError(f"Invalid mod-tap behavior: {key_data}")
    elif value == '&msc':
        # Mouse scroll - extract the direction from params
        if params and isinstance(params[0], dict):
            scroll_type = params[0].get('value', '')
            if scroll_type == 'SCRL_UP':
                return 'Scroll↑'
            elif scroll_type == 'SCRL_DOWN':
                return 'Scroll↓'
            elif scroll_type == 'SCRL_LEFT':
                return 'Scroll←'
            elif scroll_type == 'SCRL_RIGHT':
                return 'Scroll→'
        return 'Scroll'
    elif value == '&mmv':
        # Mouse movement - extract the direction from params (no "Move" prefix needed!)
        if params and isinstance(params[0], dict):
            move_type = params[0].get('value', '')
            if move_type == 'MOVE_UP':
                return '↑'
            elif move_type == 'MOVE_DOWN':
                return '↓'
            elif move_type == 'MOVE_LEFT':
                return '←'
            elif move_type == 'MOVE_RIGHT':
                return '→'
        return 'Move'
    elif value == '&mkp':
        # Mouse click - extract the button from params
        if params and isinstance(params[0], dict):
            click_type = params[0].get('value', '')
            if click_type == 'LCLK':
                return 'L Click'
            elif click_type == 'RCLK':
                return 'R Click'
            elif click_type == 'MCLK':
                return 'M Click'
            elif click_type == 'MB4':
                return 'Btn4'
            elif click_type == 'MB5':
                return 'Btn5'
        return 'Click'
    elif value == '&rgb_ug':
        # RGB underglow controls - extract the command from params
        if params and isinstance(params[0], dict):
            rgb_cmd = params[0].get('value', '')
            if rgb_cmd == 'RGB_TOG':
                return 'RGBToggle'
            elif rgb_cmd == 'RGB_HUI':
                return 'Hue+'
            elif rgb_cmd == 'RGB_HUD':
                return 'Hue-'
            elif rgb_cmd == 'RGB_SAI':
                return 'Sat+'
            elif rgb_cmd == 'RGB_SAD':
                return 'Sat-'
            elif rgb_cmd == 'RGB_BRI':
                return 'Bright+'
            elif rgb_cmd == 'RGB_BRD':
                return 'Bright-'
            elif rgb_cmd == 'RGB_SPI':
                return 'Speed+'
            elif rgb_cmd == 'RGB_SPD':
                return 'Speed-'
            elif rgb_cmd == 'RGB_EFF':
                return 'Effect+'
            elif rgb_cmd == 'RGB_EFR':
                return 'Effect-'
        return 'RGB'
    elif value == 'Custom':
        # Custom behavior - extract from params
        if params and isinstance(params[0], dict):
            custom_behavior = params[0].get('value', '')
            result = parse_custom_behavior_properly(custom_behavior, layer_name)
            return add_spaces_to_long_words(result)
        raise ValueError(f"Unknown custom behavior: {key_data}")
    elif value.startswith('&'):
        # Direct behavior reference
        result = parse_custom_behavior_properly(value, layer_name)
        return add_spaces_to_long_words(result)
    else:
        # Direct key value
        result = ZMK_KEY_MAPPING.get(value, value)
        return add_spaces_to_long_words(result)


def parse_custom_behavior_properly(behavior_str: str, layer_name: str = '') -> str:
    """Parse custom ZMK behaviors PROPERLY - no more garbage!"""
    if not behavior_str:
        raise ValueError("Empty behavior string provided")

    behavior = behavior_str.strip()

    # HOME ROW MODS: Show modifier symbols on overlay layers, tap keys on base layer
    is_overlay_layer = layer_name not in ['', 'GRAPHITE']

    if 'LeftPinky' in behavior or 'RightPinky' in behavior:
        if is_overlay_layer:
            return '⌃'  # Control symbol for macOS-style keymap
        if '(' in behavior and ')' in behavior:
            tap_key = behavior.split('(')[1].split(',')[0].strip()
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        return 'N'  # Default Graphite pinky tap key
    elif 'LeftRingy' in behavior or 'RightRingy' in behavior:
        if is_overlay_layer:
            return '⌥'  # Alt/Option symbol
        if '(' in behavior and ')' in behavior:
            tap_key = behavior.split('(')[1].split(',')[0].strip()
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        return 'R'  # Default Graphite ring tap key
    elif 'LeftMiddy' in behavior or 'RightMiddy' in behavior:
        if is_overlay_layer:
            return '⌘'  # Command symbol for macOS
        if '(' in behavior and ')' in behavior:
            tap_key = behavior.split('(')[1].split(',')[0].strip()
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        return 'T'  # Default Graphite middle tap key
    elif 'LeftIndex' in behavior or 'RightIndex' in behavior:
        if is_overlay_layer:
            return '⇧'  # Shift symbol
        if '(' in behavior and ')' in behavior:
            tap_key = behavior.split('(')[1].split(',')[0].strip()
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        return 'S'  # Default Graphite index tap key
    elif 'left_pinky' in behavior or 'left_ringy_tap' in behavior or 'left_middy_tap' in behavior or 'left_index_tap' in behavior or 'right_pinky_tap' in behavior or 'right_ringy_tap' in behavior or 'right_middy_tap' in behavior or 'right_index_tap' in behavior:
        # Handle tap behaviors with key extraction
        parts = behavior.split()
        if len(parts) >= 2:
            tap_key = parts[-1]  # Last part should be tap key
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        # Fallback for specific behaviors without parameters
        if 'left_pinky' in behavior:
            return 'Q'  # Default left pinky tap
        elif 'left_ringy_tap' in behavior:
            return 'F1'  # Default for left ring finger on function row
        elif 'left_middy_tap' in behavior:
            return 'F2'  # Default for left middle finger on function row  
        elif 'left_index_tap' in behavior:
            return 'F3'  # Default for left index finger on function row
        elif 'right_pinky_tap' in behavior:
            return 'F10'  # Default for right pinky on function row
        elif 'right_ringy_tap' in behavior:
            return 'F9'  # Default for right ring finger on function row
        elif 'right_middy_tap' in behavior:
            return 'F8'  # Default for right middle finger on function row  
        elif 'right_index_tap' in behavior:
            return 'F7'  # Default for right index finger on function row
        raise ValueError(f"Unknown tap behavior: {behavior}")

    # Handle Graphite mod-morph behaviors (show the base character)
    elif '&gr_au' in behavior:
        return "'"  # Graphite apostrophe/underscore
    elif '&gr_cm' in behavior:
        return ','  # Graphite comma/question_mark
    elif '&gr_pd' in behavior:
        return '.'  # Graphite period/greater_than
    elif '&gr_fs' in behavior:
        return '/'  # Graphite forward_slash/less_than
    elif '&gr_mi' in behavior:
        return '-'  # Graphite minus/double_quote

    # Handle special symbols (parang = parenthesis)
    elif 'parang_left' in behavior:
        return '('  # left_parenthesis_and_less_than
    elif 'parang_right' in behavior:
        return ')'  # right_parenthesis_and_greater_than

    # Handle direct keypresses that were showing mod names
    elif '&kp ' in behavior:
        parts = behavior.split()
        if len(parts) >= 2:
            key_code = parts[1]

            # Handle CMD combinations like _C(L), C(K), etc. FIRST
            if '_C(' in key_code or 'C(' in key_code:
                import re
                match = re.search(r'_?C\(([A-Z])\)', key_code)
                if match:
                    return f'⌘{match.group(1)}'
                return '⌘'

            # For home row mod constants on overlay layers, show modifier symbols
            if is_overlay_layer:
                if 'LEFT_PINKY_MOD' in key_code or 'RIGHT_PINKY_MOD' in key_code:
                    return '⌃'  # Control symbol for macOS-style keymap
                elif 'LEFT_RINGY_MOD' in key_code or 'RIGHT_RINGY_MOD' in key_code:
                    return '⌥'  # Alt/Option symbol
                elif 'LEFT_MIDDY_MOD' in key_code or 'RIGHT_MIDDY_MOD' in key_code:
                    return '⌘'  # Command symbol for macOS
                elif 'LEFT_INDEX_MOD' in key_code or 'RIGHT_INDEX_MOD' in key_code:
                    return '⇧'  # Shift symbol
                elif 'LGUI' in key_code or 'RGUI' in key_code:
                    return '⌘'  # Fixed: CMD not "LG"!
            # For home row mod constants on base layer, show the tap key
            key_code_clean = key_code.replace('_', '')
            if 'LEFTPINKYMOD' in key_code_clean or 'RIGHTPINKYMOD' in key_code_clean:
                return 'N'
            elif 'LEFTRINGYMOD' in key_code_clean or 'RIGHTRINGYMOD' in key_code_clean:
                return 'R'
            elif 'LEFTMIDDYMOD' in key_code_clean or 'RIGHTMIDDYMOD' in key_code_clean:
                return 'T'
            elif 'LEFTINDEXMOD' in key_code_clean or 'RIGHTINDEXMOD' in key_code_clean:
                return 'S'
            return ZMK_KEY_MAPPING.get(key_code_clean, key_code_clean)

    # Handle layer switching behaviors
    elif '&to ' in behavior:
        # Extract layer number from &to behavior
        parts = behavior.split()
        if len(parts) >= 2:
            layer_num = parts[1]
            return f'Layer {layer_num}'
        return 'Layer'
    # Handle other behaviors
    elif '&magic' in behavior:
        return 'MAGIC'
    elif '&lower' in behavior:
        return 'LOWER'
    elif '&mo ' in behavior:
        # Layer access - extract layer name
        if 'LAYER_MouseSlow' in behavior:
            return 'SlowMouse'
        elif 'LAYER_MouseFast' in behavior:
            return 'FastMouse'
        elif 'LAYER_MouseWarp' in behavior:
            return 'WarpMouse'
        elif 'LAYER_' in behavior:
            # Extract layer name
            layer_part = behavior.split('LAYER_')[1].split()[0]
            return layer_part[:8]  # Truncate long names
        return 'Layer'
    elif '&sk' in behavior:
        # Sticky keys - use lightning bolt ⚡ like your Dart code
        if 'RIGHT_INDEX_MOD' in behavior or 'LEFT_INDEX_MOD' in behavior:
            return '⚡⇧'  # Sticky Shift
        elif 'RIGHT_MIDDY_MOD' in behavior or 'LEFT_MIDDY_MOD' in behavior:
            return '⚡⌘'  # Sticky CMD (macOS)
        elif 'RIGHT_RINGY_MOD' in behavior or 'LEFT_RINGY_MOD' in behavior:
            return '⚡⌥'  # Sticky ALT (macOS)
        elif 'RIGHT_PINKY_MOD' in behavior or 'LEFT_PINKY_MOD' in behavior:
            return '⚡⌃'  # Sticky CTRL (macOS)
        elif 'LSHIFT' in behavior or 'RSHIFT' in behavior:
            return '⚡⇧'
        elif 'LGUI' in behavior or 'RGUI' in behavior:
            return '⚡⌘'
        elif 'LALT' in behavior or 'RALT' in behavior:
            return '⚡⌥'
        elif 'LCTRL' in behavior or 'RCTRL' in behavior:
            return '⚡⌃'
        # Check if it's a standard ZMK modifier
        parts = behavior.split()
        if len(parts) >= 2:
            mod_key = parts[1]
            if mod_key in ['LSHIFT', 'RSHIFT', 'SHIFT']:
                return '⚡⇧'
            elif mod_key in ['LGUI', 'RGUI', 'LCMD', 'RCMD', 'CMD']:
                return '⚡⌘'
            elif mod_key in ['LALT', 'RALT', 'ALT']:
                return '⚡⌥'
            elif mod_key in ['LCTRL', 'RCTRL', 'CTRL']:
                return '⚡⌃'
        return '⚡⇧'  # Most common case
    elif '&tog' in behavior:
        # Layer toggles - show what they toggle
        if 'LAYER_Function' in behavior:
            return '🔒Fn'
        elif 'LAYER_Cursor' in behavior:
            return '🔒Cur'
        elif 'LAYER_Number' in behavior:
            return '🔒Num'
        elif 'LAYER_Symbol' in behavior:
            return '🔒Sym'
        elif 'LAYER_Mouse' in behavior:
            return '🔒Mouse'
        elif 'LAYER_System' in behavior:
            return '🔒Sys'
        elif 'LAYER_Emoji' in behavior:
            return '🔒Emoji'
        elif 'LAYER_World' in behavior:
            return '🔒World'
        elif 'LAYER_' in behavior:
            # Extract layer name
            layer_part = behavior.split('LAYER_')[1].split()[0]
            return f'🔒{layer_part[:4]}'  # Truncate to 4 chars
        return '🔄'
    elif '&rgb_ug' in behavior:
        # RGB underglow controls
        if 'RGB_TOG' in behavior:
            return '🌈'
        elif 'RGB_HUI' in behavior:
            return 'Hue+'
        elif 'RGB_HUD' in behavior:
            return 'Hue-'
        elif 'RGB_SAI' in behavior:
            return 'Sat+'
        elif 'RGB_SAD' in behavior:
            return 'Sat-'
        elif 'RGB_BRI' in behavior:
            return 'Bright+'
        elif 'RGB_BRD' in behavior:
            return 'Bright-'
        elif 'RGB_SPI' in behavior:
            return 'Speed+'
        elif 'RGB_SPD' in behavior:
            return 'Speed-'
        elif 'RGB_EFF' in behavior:
            return 'Effect+'
        elif 'RGB_EFR' in behavior:
            return 'Effect-'
        return 'RGB'
    elif '&msc' in behavior:
        # Mouse scroll - extract the direction
        if 'SCRL_UP' in behavior:
            return 'Scroll↑'
        elif 'SCRL_DOWN' in behavior:
            return 'Scroll↓'
        elif 'SCRL_LEFT' in behavior:
            return 'Scroll←'
        elif 'SCRL_RIGHT' in behavior:
            return 'Scroll→'
        return 'Scroll'
    elif '&mmv' in behavior:
        # Mouse movement - extract direction (no "Move" prefix!)
        if 'MOVE_UP' in behavior:
            return '↑'
        elif 'MOVE_DOWN' in behavior:
            return '↓'
        elif 'MOVE_LEFT' in behavior:
            return '←'
        elif 'MOVE_RIGHT' in behavior:
            return '→'
        return 'Move'
    elif '&mkp' in behavior:
        # Mouse click - extract button
        if 'LCLK' in behavior:
            return 'LeftClick'
        elif 'RCLK' in behavior:
            return 'RightClick'
        elif 'MCLK' in behavior:
            return 'MiddleClick'
        elif 'MB4' in behavior:
            return 'Button4'
        elif 'MB5' in behavior:
            return 'Button5'
        return 'Click'
    elif '&linux_magic_sysrq' in behavior:
        return 'SysRq'  # Linux Magic SysRq key
    elif '&bt' in behavior:
        # Bluetooth behavior - extract the command from params
        if 'BT_CLR' in behavior:
            return 'BT Clear'
        elif 'BT_SEL' in behavior:
            # Extract bluetooth profile number
            if '0' in behavior:
                return 'BT 0'
            elif '1' in behavior:
                return 'BT 1'
            elif '2' in behavior:
                return 'BT 2'
            elif '3' in behavior:
                return 'BT 3'
            elif '4' in behavior:
                return 'BT 4'
            return 'BT Sel'
        elif 'BT_NXT' in behavior:
            return 'BT Next'
        elif 'BT_PRV' in behavior:
            return 'BT Prev'
        return 'BT'
    elif '&abc' in behavior:
        return 'ABC'  # Input method switch to alphabetic
    elif '&cyrilic' in behavior:
        return 'АБВ'  # Cyrillic input method
    elif '&bootloader' in behavior:
        return 'Bootldr'  # Bootloader mode
    elif '&reset' in behavior:
        return 'Reset'  # Keyboard reset
    elif '&out' in behavior:
        # Output selection behavior
        if 'OUT_USB' in behavior:
            return 'USB Out'
        elif 'OUT_BLE' in behavior:
            return 'BT Out'
        elif 'OUT_TOG' in behavior:
            return 'Out Toggle'
        return 'Output'
    elif '&space' in behavior:
        return '⎵'
    elif '&thumb' in behavior:
        # Extract tap action from thumb behavior
        parts = behavior.split()
        if len(parts) >= 3:
            tap_key = parts[-1]
            return ZMK_KEY_MAPPING.get(tap_key, tap_key)
        return 'THUMB'
    elif '&thumb_kp' in behavior:
        if '_END' in behavior:
            return 'END'
        elif '_HOME' in behavior:
            return 'HOME'
        return 'THUMBKP'
    elif '&kp _HOME' in behavior:
        return 'HOME'
    elif '&kp _END' in behavior:
        return 'END'
    elif '_HOME' in behavior:
        return 'HOME'
    elif '_END' in behavior:
        return 'END'
    elif '_C(' in behavior or 'C(' in behavior:
        # Handle any CMD combinations like _C(L), C(K), etc.
        import re
        match = re.search(r'_?C\(([A-Z])\)', behavior)
        if match:
            return f'⌘{match.group(1)}'
        return '⌘'  # CMD key for macOS
    elif '&extend_' in behavior:
        # Text selection extension functions
        if '&extend_word' in behavior:
            return 'Ext Word'
        elif '&extend_line' in behavior:
            return 'Ext Line'
        elif '&extend_all' in behavior:
            return 'Ext All'
        return 'Extend'
    elif '&select_' in behavior:
        # Text selection functions
        if '&select_word' in behavior:
            return 'Sel Word'
        elif '&select_line' in behavior:
            return 'Sel Line'
        elif '&select_all' in behavior:
            return 'Sel All'
        elif '&select_none' in behavior:
            return 'Clear'
        return 'Select'
    elif '&emoji_' in behavior:
        # Load emoji mappings from emoji.yaml file
        try:
            import yaml
            with open('emoji.yaml', 'r', encoding='utf-8') as f:
                emoji_data = yaml.safe_load(f)
        except ImportError as e:
            raise ImportError(f"PyYAML module not available for emoji parsing: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"emoji.yaml file not found: {e}")

        # Extract behavior name without &emoji_ prefix
        behavior_name = behavior.replace('&emoji_', '').strip()

        # Handle special preset behaviors first
        preset_mappings = {
            'skin_tone_preset': '🏼',  # medium_light_skin_tone
            'gender_sign_preset': '♀️',  # female_sign 
            'hair_style_preset': '🦱',  # curly_hair
        }
        if behavior_name in preset_mappings:
            return preset_mappings[behavior_name]

        # First check direct codepoints (handle both string and numeric keys)
        if 'codepoints' in emoji_data:
            if behavior_name in emoji_data['codepoints']:
                return emoji_data['codepoints'][behavior_name]
            # Also try converting behavior_name to int for numeric keys like "100"
            try:
                numeric_key = int(behavior_name)
                if numeric_key in emoji_data['codepoints']:
                    return emoji_data['codepoints'][numeric_key]
            except ValueError:
                pass

        # Then check character groups (these have shift variants)
        if 'characters' in emoji_data:
            for group_name, group_items in emoji_data['characters'].items():
                for item_name, variants in group_items.items():
                    # Check if behavior matches group_item pattern
                    expected_behavior = f'{group_name}_{item_name}'
                    if behavior_name == expected_behavior:
                        # Return the first variant (without shift)
                        if isinstance(variants, dict):
                            return list(variants.values())[0]
                        return variants

        # Raise exception for unknown emoji behaviors
        raise ValueError(f"Emoji behavior '{behavior_name}' not found in emoji.yaml. Available codepoints: {list(emoji_data.get('codepoints', {}).keys())[:10]}...")

    elif '&world_' in behavior:
        # Load world character mappings from world.yaml file
        try:
            import yaml
            with open('world.yaml', 'r', encoding='utf-8') as f:
                world_data = yaml.safe_load(f)
        except ImportError as e:
            raise ImportError(f"PyYAML module not available for world character parsing: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"world.yaml file not found: {e}")

        # Extract behavior name without &world_ prefix
        behavior_name = behavior.replace('&world_', '').strip()

        # First check direct codepoints
        if 'codepoints' in world_data and behavior_name in world_data['codepoints']:
            return world_data['codepoints'][behavior_name]

        # Handle transform-based behaviors like y_base, e_base, etc.
        if 'transforms' in world_data and '_base' in behavior_name:
            # Extract the letter (e.g., "y" from "y_base")
            letter_orig = behavior_name.replace('_base', '')
            letter_upper = letter_orig.upper()
            letter_lower = letter_orig.lower()
            
            # Try both uppercase and lowercase (for letters vs words like "sign")
            letter = None
            if letter_upper in world_data['transforms']:
                letter = letter_upper
            elif letter_lower in world_data['transforms']:
                letter = letter_lower
            
            if letter:
                base_transform = world_data['transforms'][letter].get('base')
                if base_transform and 'characters' in world_data:
                    # Look up the base character
                    if letter in world_data['characters'] and base_transform in world_data['characters'][letter]:
                        char_variants = world_data['characters'][letter][base_transform]
                        if isinstance(char_variants, dict):
                            # Return the appropriate base version (without shift)
                            return char_variants.get('lower', char_variants.get('regular', list(char_variants.values())[0]))
                        return char_variants

        # Then check character groups (these have shift variants)
        if 'characters' in world_data:
            for group_name, group_items in world_data['characters'].items():
                for item_name, variants in group_items.items():
                    # Check if behavior matches group_item pattern
                    expected_behavior = f'{group_name}_{item_name}'
                    if behavior_name == expected_behavior:
                        # Return the first variant (without shift)
                        if isinstance(variants, dict):
                            return list(variants.values())[0]
                        return variants

        # Raise exception for unknown world behaviors
        raise ValueError(f"World character '{behavior_name}' not found in world.yaml. Available codepoints: {list(world_data.get('codepoints', {}).keys())[:10]}...")

    # Try direct mapping after cleaning up
    clean_behavior = behavior.replace('&', '').replace('_', '').upper()
    if clean_behavior in ZMK_KEY_MAPPING:
        return ZMK_KEY_MAPPING[clean_behavior]

    # Unknown behavior - fail explicitly
    raise ValueError(f"Unknown behavior '{behavior_str}' (cleaned: '{clean_behavior}'). Available in ZMK_KEY_MAPPING: {list(ZMK_KEY_MAPPING.keys())[:20]}...")


def parse_zmk_triggers(dtsi_filepath: str = "keymap.dtsi") -> Dict[str, str]:
    """Parse actual ZMK trigger bindings from keymap.dtsi"""
    triggers = {}

    try:
        with open(dtsi_filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern to match the macro behaviors and extract the key combination
        macro_pattern = r'(\w+_with_[^:]+):\s*\1\s*\{[^}]*bindings\s*=\s*<[^>]*&kp\s+([^>]+)>'
        macro_matches = re.findall(macro_pattern, content, re.MULTILINE | re.DOTALL)

        # Create mapping from behavior name to trigger
        behavior_to_trigger = {}
        for behavior_name, trigger_combo in macro_matches:
            trigger = trigger_combo.strip().rstrip(';').strip()
            behavior_to_trigger[behavior_name] = trigger

        # Find which thumb behaviors use which macros
        thumb_pattern = r'thumb_(\w+):\s*thumb_\1\s*\{[^}]*bindings\s*=\s*<&([^,]+)>'
        thumb_matches = re.findall(thumb_pattern, content, re.MULTILINE | re.DOTALL)

        for layer_name, macro_behavior in thumb_matches:
            if macro_behavior in behavior_to_trigger:
                zmk_combo = behavior_to_trigger[macro_behavior]
                readable_trigger = convert_zmk_combo_to_readable(zmk_combo)
                triggers[layer_name.lower()] = readable_trigger

        # Also look for space behaviors (for Symbol layer)
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

    # Handle _C() macro (CMD key combination)
    if '_C(' in combo:
        # Extract what's inside _C()
        inner = combo.split('_C(')[1].rstrip(')').strip()
        if inner == 'A':
            return 'cmd+a'
        elif inner == 'L':
            return 'cmd+l'
        elif inner == 'Z':
            return 'cmd+z'
        else:
            return f'cmd+{inner.lower()}'

    # Replace ZMK modifiers with readable names
    replacements = [
        ('LG(', 'cmd+'), ('LA(', 'alt+'), ('LC(', 'ctrl+'), ('LS(', 'shift+'),
        ('RG(', 'cmd+'), ('RA(', 'alt+'), ('RC(', 'ctrl+'), ('RS(', 'shift+'),
        ('_WORD(', 'alt+'),  # _WORD is defined as LA (ALT) in macOS mode
    ]

    for zmk_mod, readable_mod in replacements:
        combo = combo.replace(zmk_mod, readable_mod)

    combo = combo.replace(')', '')

    # Convert key codes to lowercase
    if '+' in combo:
        parts = combo.split('+')
        if len(parts) == 2:
            modifier, key = parts
            combo = f'{modifier}{key.lower()}'

    return combo


def format_compact_json(data):
    """Format JSON with compact arrays for key rows"""

    def format_json_with_compact_arrays(obj, indent=0):
        indent_str = "  " * indent

        if isinstance(obj, dict):
            lines = ["{"]
            items = list(obj.items())
            for i, (key, value) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                key_line = f'{indent_str}  "{key}": '

                if key in ['mainRows', 'thumbRows'] and isinstance(value, list):
                    # Format as compact arrays
                    array_lines = ["["]
                    for j, row in enumerate(value):
                        row_comma = "," if j < len(value) - 1 else ""
                        if isinstance(row, list):
                            # Format row as single line
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
                    # Regular formatting
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


# Layer names to convert (hardcoded)
LAYER_NAMES = [
    "GRAPHITE",
    "Function",
    "Cursor",
    "Number",
    "Symbol",
    "Mouse",
    "System",
    "Lower",
    "Emoji"
]


def parse_zmk_macro_definitions(dtsi_filepath: str = "keymap.dtsi.erb") -> Dict[str, str]:
    """Parse actual ZMK macro definitions from ERB template to get real key combinations"""
    macro_mappings = {}

    try:
        with open(dtsi_filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # First, extract OS-specific macro definitions for _WORD, _HOME, _END
        os_macros = {}

        # Check which OS mode is active by looking for the actual setting
        os_pattern = r"#define\s+OPERATING_SYSTEM\s+'([LMW])'"
        os_match = re.search(os_pattern, content)
        is_macos = os_match and os_match.group(1) == 'M'

        if is_macos:
            # macOS definitions
            os_macros['_WORD'] = 'LA'      # Alt key
            os_macros['_HOME'] = 'LG(LEFT)'  # Cmd+Left
            os_macros['_END'] = 'LG(RIGHT)'  # Cmd+Right
            os_macros['_C'] = 'LG'          # Cmd key
        else:
            # Linux/Windows definitions
            os_macros['_WORD'] = 'LC'      # Ctrl key
            os_macros['_HOME'] = 'HOME'    # Home key
            os_macros['_END'] = 'END'      # End key
            os_macros['_C'] = 'LC'         # Ctrl key

        print(f"🔍 Detected {'macOS' if is_macos else 'Linux/Windows'} mode")
        print(f"  _WORD → {os_macros['_WORD']}, _HOME → {os_macros['_HOME']}, _END → {os_macros['_END']}")

        # Parse the actual ZMK_MACRO definitions for select/extend behaviors
        # These contain the real key sequences, not simplified versions

        # Parse select_word_right and select_word_left
        select_word_pattern = r'ZMK_MACRO\(select_word_right,.*?bindings\s*=\s*<([^>]+)>'
        select_word_match = re.search(select_word_pattern, content, re.DOTALL)
        if select_word_match:
            bindings = select_word_match.group(1)
            # Extract the key sequence (usually _WORD(RIGHT) with LS modifier)
            if 'LS(_WORD(RIGHT))' in bindings or 'LS' in bindings and '_WORD' in bindings:
                macro_mappings['select_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'
            else:
                # Fallback to basic word selection
                macro_mappings['select_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'

        # Parse extend_word behaviors
        extend_word_pattern = r'ZMK_MACRO\(extend_word_right,.*?bindings\s*=\s*<([^>]+)>'
        extend_word_match = re.search(extend_word_pattern, content, re.DOTALL)
        if extend_word_match:
            bindings = extend_word_match.group(1)
            if 'LS(_WORD(RIGHT))' in bindings or 'LS' in bindings and '_WORD' in bindings:
                macro_mappings['extend_word'] = 'alt+shift+right' if is_macos else 'ctrl+shift+right'

        # Parse select_line behaviors - looking for actual key sequences
        select_line_pattern = r'ZMK_MACRO\(select_line_right,.*?bindings\s*=\s*<([^>]+)>'
        select_line_match = re.search(select_line_pattern, content, re.DOTALL)
        if select_line_match:
            bindings = select_line_match.group(1)
            # macOS: Cmd+Shift+Right to select to end of line
            # Linux/Windows: Shift+End
            if is_macos:
                if '_HOME' in bindings and 'LS(_END)' in bindings:
                    # Move to start of line, then shift+select to end
                    macro_mappings['select_line'] = 'cmd+shift+right'
                else:
                    macro_mappings['select_line'] = 'cmd+shift+right'
            else:
                macro_mappings['select_line'] = 'shift+end'

        # Parse extend_line behaviors
        extend_line_pattern = r'ZMK_MACRO\(extend_line_right,.*?bindings\s*=\s*<([^>]+)>'
        extend_line_match = re.search(extend_line_pattern, content, re.DOTALL)
        if extend_line_match:
            bindings = extend_line_match.group(1)
            if is_macos:
                # Extend selection by line
                macro_mappings['extend_line'] = 'shift+cmd+right'
            else:
                macro_mappings['extend_line'] = 'shift+end'

        # Parse select_all - simple #define
        select_all_pattern = r'#define\s+select_all\s+kp\s+_C\(A\)'
        if re.search(select_all_pattern, content):
            macro_mappings['select_all'] = 'cmd+a' if is_macos else 'ctrl+a'

        # Parse select_none (clear selection)
        select_none_pattern = r'ZMK_MACRO\(select_none,.*?bindings\s*=\s*<([^>]+)>'
        select_none_match = re.search(select_none_pattern, content, re.DOTALL)
        if select_none_match:
            bindings = select_none_match.group(1)
            if 'ESC' in bindings or 'ESCAPE' in bindings:
                macro_mappings['select_none'] = 'escape'
            elif 'LEFT' in bindings:
                macro_mappings['select_none'] = 'left'  # Move cursor to deselect
            else:
                macro_mappings['select_none'] = 'escape'

        # Add standard editing operations that use _C macro
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

        # Parse _REDO which is OS-specific
        if is_macos:
            if re.search(r'#define\s+_REDO\s+LG\(LS\(Z\)\)', content):
                macro_mappings['redo'] = 'cmd+shift+z'
        else:
            if re.search(r'#define\s+_REDO\s+LC\(Y\)', content):
                macro_mappings['redo'] = 'ctrl+y'

        # Also handle _FIND_NEXT and _FIND_PREV
        if re.search(r'#define\s+_FIND_NEXT\s+_C\(G\)', content):
            macro_mappings['find_next'] = 'cmd+g' if is_macos else 'ctrl+g'
        if re.search(r'#define\s+_FIND_PREV\s+_C\(LS\(G\)\)', content):
            macro_mappings['find_prev'] = 'cmd+shift+g' if is_macos else 'ctrl+shift+g'

        print(f"🔍 Parsed ZMK macro definitions: {len(macro_mappings)} macros found")
        for name, combo in sorted(macro_mappings.items())[:15]:  # Show first 15
            print(f"  {name} → {combo}")

    except Exception as e:
        print(f"Warning: Could not parse ZMK macros from {dtsi_filepath}: {e}")

    return macro_mappings


def find_custom_behaviors_in_keymap(data):
    """Scan keymap.json to find all custom behaviors used in layers"""
    custom_behaviors = set()

    def scan_value(obj):
        """Recursively scan for custom behaviors"""
        if isinstance(obj, dict):
            value = obj.get('value', '')
            if isinstance(value, str) and value.startswith('&'):
                # Check for standard ZMK behaviors vs custom ones
                standard_behaviors = [
                    '&kp', '&mt', '&mo', '&tog', '&sk', '&trans', '&none',
                    '&lt', '&td', '&rgb_ug', '&ext_power', '&out', '&bt',
                    '&mkp', '&mmv', '&msc', '&mwh', '&caps_word', '&key_repeat'
                ]
                if not any(value.startswith(std) for std in standard_behaviors):
                    # This is a custom behavior
                    behavior_name = value.split()[0][1:]  # Remove & prefix and get first word
                    custom_behaviors.add(behavior_name)
            # Recurse into params
            params = obj.get('params', [])
            if params:
                for param in params:
                    scan_value(param)
        elif isinstance(obj, list):
            for item in obj:
                scan_value(item)
        elif isinstance(obj, str) and obj.startswith('&'):
            # Direct string reference to behavior
            behavior_name = obj.split()[0][1:]
            custom_behaviors.add(behavior_name)

    # Scan all layers
    layers = data.get('layers', [])
    for layer in layers:
        for key_data in layer:
            scan_value(key_data)

    return custom_behaviors


def scan_generated_display_names(data):
    """Scan all layers for generated display names (like 'Sel All', 'Ext Word') to find what needs action mappings"""
    display_names = set()

    # Convert each layer to see what display names are generated
    layers = data.get('layers', [])
    layer_names_list = data.get('layer_names', [])

    for i, layer_data in enumerate(layers):
        layer_name = layer_names_list[i] if i < len(layer_names_list) else f"Layer_{i}"

        for key_data in layer_data:
            if isinstance(key_data, dict):
                display_name = convert_zmk_key(key_data, layer_name)
                if display_name and isinstance(display_name, str):
                    # Look for actions that need mappings
                    action_keywords = [
                        'Sel ', 'Ext ', 'Clear',  # Selection
                        'Cut', 'Copy', 'Paste', 'Undo', 'Redo',  # Editing
                        '⌘', '⌥', '⌃', '⇧',  # Modifier keys
                        '🔍', '🔒',  # Special actions
                        'Home', 'End', 'PgUp', 'PgDn',  # Navigation
                        '☀', '🔊', '🔉', '🔇',  # Media controls
                        'Scroll', 'Click', 'Btn',  # Mouse
                        'Layer', 'Toggle', 'MAGIC'  # Layer controls
                    ]
                    if any(keyword in display_name for keyword in action_keywords):
                        display_names.add(display_name)

    return display_names


def extract_action_mappings_from_keymap(data):
    """Extract actual key mappings from ZMK keymap data to generate proper actionMappings"""
    mappings = {}

    # Step 1: Find all custom behaviors used in the keymap layers
    custom_behaviors = find_custom_behaviors_in_keymap(data)
    if len(custom_behaviors) > 0:
        print(f"🔍 Found {len(custom_behaviors)} custom behaviors in keymap")
        # Don't print all behaviors as it's too verbose
    print()

    # Step 2: Find all generated display names that need action mappings
    display_names = scan_generated_display_names(data)
    if len(display_names) > 0:
        print(f"🔍 Found {len(display_names)} generated display names that may need action mappings")
        # Only print the most relevant ones
        relevant_names = [n for n in display_names if any(k in n for k in ['Sel ', 'Ext ', 'Clear', 'Cut', 'Copy', 'Paste', 'Undo', 'Redo'])]
        if relevant_names:
            print(f"  Key editing actions found: {', '.join(sorted(relevant_names)[:10])}")
    print()

    # Step 3: Parse ZMK macro definitions from keymap.dtsi.erb
    zmk_macros = parse_zmk_macro_definitions()

    # Step 4: Create mappings for text selection/editing behaviors
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
        "find": "🔍",
    }

    # Map behaviors to display names using parsed ZMK macros
    for zmk_name, display_name in behavior_to_display_mappings.items():
        if zmk_name in zmk_macros:
            mappings[display_name] = zmk_macros[zmk_name]
            print(f"✅ Mapped {display_name} → {zmk_macros[zmk_name]} (from ZMK macro)")
        elif display_name in display_names:
            print(f"⚠️  Found display name '{display_name}' but no ZMK macro '{zmk_name}'")

    # Standard text editing operations (add if not already mapped)
    # These are fallbacks for when ZMK macros aren't found
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
        "⌫": "backspace",
        "⌦": "delete",
        "↵": "enter",
        "⇥": "tab",
        "⇧⇥": "shift+tab",
        "⎋": "escape",
        "⎵": "space",
        "←": "left",
        "→": "right",
        "↑": "up",
        "↓": "down",
        "🔍": "cmd+f",
        "🔍←": "cmd+g",
        "🔍→": "cmd+shift+g",
        "⌃": "ctrl",
        "⌥": "alt",
        "⌘": "cmd",
        "⇧": "shift",
        "ALT": "alt",
        "⌘L": "cmd+l",
        "⌘K": "cmd+k",
        "⌘H": "cmd+h",
        "⌘⇧N": "cmd+shift+n",
        "⌘⇧Y": "cmd+shift+y",
        "⌘⇧A": "cmd+shift+a",
        "⇪": "capslock",
        "⇳": "f14",
        "NumLock": "f6",
        "⏻": "power",
        "😴": "cmd+alt+eject",
        "🔒": "cmd+ctrl+q",
        "📷": "cmd+shift+4",
        "🏠": "f3",
        "🗑": "clear"
    }
    mappings.update(standard_mappings)

    # Layer toggles (OverKeys handles these specially)
    layer_mappings = {
        "🔒Fn": "layer_toggle_function",
        "🔒Cur": "layer_toggle_cursor",
        "🔒Num": "layer_toggle_number",
        "🔒Sym": "layer_toggle_symbol",
        "🔒Mouse": "layer_toggle_mouse",
        "🔒Sys": "layer_toggle_system",
        "🔒Emoji": "layer_toggle_emoji",
        "🔒World": "layer_toggle_world",
        "Lower": "layer_momentary_lower",
        "Typing": "layer_base",
        "MAGIC": "layer_magic"
    }
    mappings.update(layer_mappings)

    # Extract actual consumer codes from keymap data
    consumer_codes_found = set()

    def scan_behaviors(obj):
        """Recursively scan for consumer codes in keymap behaviors"""
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

    # Scan the entire keymap
    scan_behaviors(data)

    # Map found consumer codes to actual system keys
    consumer_mappings = {
        # Brightness controls - actual macOS brightness keys
        'C_BRI_UP': 'f2',
        'C_BRI_DN': 'f1',
        'C_BRI_MAX': 'shift+f2',
        'C_BRI_MIN': 'shift+f1',
        'C_BRI_AUTO': 'f14',

        # Volume controls - actual macOS volume keys
        'C_VOL_UP': 'f12',
        'C_VOL_DN': 'f11',
        'C_MUTE': 'f10',

        # Media controls - actual macOS media keys
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

    # Add mappings for found consumer codes and their display symbols
    for code in consumer_codes_found:
        if code in consumer_mappings:
            # Add the actual consumer code
            mappings[code] = consumer_mappings[code]

            # Add the display symbol from ZMK_KEY_MAPPING
            display_symbol = ZMK_KEY_MAPPING.get(code)
            if display_symbol:
                mappings[display_symbol] = consumer_mappings[code]

    # Mouse controls (if present)
    mouse_mappings = {
        "L Click": "button1",
        "R Click": "button2",
        "M Click": "button3",
        "Btn4": "button4",
        "Btn5": "button5",
        "☰": "button3",
        "Slow": "mouseslow",
        "Fast": "mousefast",
        "Warp": "mousewarp",
        "Scroll←": "scrollleft",
        "Scroll→": "scrollright",
        "Scroll↑": "scrollup",
        "Scroll↓": "scrolldown"
    }
    mappings.update(mouse_mappings)

    print(f"🔍 Found consumer codes: {sorted(consumer_codes_found)}")

    return mappings


def main():
    print("🔥 Glove80 → OverKeys Converter 🔥")
    print("No more garbage key names!")
    print(f"Target layers: {', '.join(LAYER_NAMES)}")

    try:
        # Load keymap
        with open("keymap.json", 'r', encoding='utf-8') as f:
            keymap = json.load(f)

        layers = keymap.get('layers', [])
        layer_names_list = keymap.get('layer_names', [])

        print(f"Total layers available: {len(layers)}")
        print(f"Layer names: {layer_names_list}")

        # Parse ZMK triggers
        print("Parsing ZMK triggers from keymap.dtsi...")
        zmk_triggers = parse_zmk_triggers()
        print(f"Found triggers: {zmk_triggers}")

        # Generate action mappings from actual keymap data
        print("🔍 Scanning keymap for consumer codes...")
        action_mappings = extract_action_mappings_from_keymap(keymap)

        # Find layer indices by name
        layer_indices = []
        for layer_name in LAYER_NAMES:
            if layer_name in layer_names_list:
                layer_indices.append(layer_names_list.index(layer_name))
            else:
                print(f"Warning: Layer '{layer_name}' not found")

        user_layouts = []

        # Convert each layer
        for i in layer_indices:
            if i >= len(layers):
                continue

            layer_data = layers[i]
            layer_name = layer_names_list[i] if i < len(layer_names_list) else f"Layer_{i}"

            # Get trigger from parsed ZMK configuration
            trigger = None
            layer_name_lower = layer_name.lower()
            if layer_name_lower in zmk_triggers:
                trigger = zmk_triggers[layer_name_lower]
            elif i > 0:
                trigger = f"Layer_{layer_name}"

            # Build layer layout
            layout = {
                "name": layer_name,
                "layoutStyle": "split_matrix_explicit",
                "leftHand": {"mainRows": [], "thumbRows": []},
                "rightHand": {"mainRows": [], "thumbRows": []}
            }

            # Build left hand main rows
            for row_positions in GLOVE80_LAYOUT['left_main_rows']:
                row = []
                for pos in row_positions:
                    if pos < len(layer_data):
                        key = convert_zmk_key(layer_data[pos], layer_name)
                        row.append(key)
                    else:
                        row.append(None)

                # Normalize row length and clean up
                if len(row) == 5:
                    row.append(None)  # Add null at end for left hand 5-key rows

                # Replace all-null rows with empty arrays
                if all(key is None for key in row):
                    row = []

                layout["leftHand"]["mainRows"].append(row)

            # Build right hand main rows
            for row_positions in GLOVE80_LAYOUT['right_main_rows']:
                row = []
                for pos in row_positions:
                    if pos < len(layer_data):
                        key = convert_zmk_key(layer_data[pos], layer_name)
                        row.append(key)
                    else:
                        row.append(None)

                # Normalize row length and clean up
                if len(row) == 5:
                    row.insert(0, None)  # Add null at start for right hand 5-key rows

                # Replace all-null rows with empty arrays
                if all(key is None for key in row):
                    row = []

                layout["rightHand"]["mainRows"].append(row)

            # Build thumb rows
            for row_positions in GLOVE80_LAYOUT['left_thumb_rows']:
                row = []
                for pos in row_positions:
                    if pos < len(layer_data):
                        key = convert_zmk_key(layer_data[pos], layer_name)
                        row.append(key)
                    else:
                        row.append(None)
                # Replace all-null rows with empty arrays
                if all(key is None for key in row):
                    row = []

                layout["leftHand"]["thumbRows"].append(row)

            for row_positions in GLOVE80_LAYOUT['right_thumb_rows']:
                row = []
                for pos in row_positions:
                    if pos < len(layer_data):
                        key = convert_zmk_key(layer_data[pos], layer_name)
                        row.append(key)
                    else:
                        row.append(None)
                # Replace all-null rows with empty arrays
                if all(key is None for key in row):
                    row = []

                layout["rightHand"]["thumbRows"].append(row)

            # Add trigger if specified
            if trigger:
                layout["trigger"] = trigger
                layout["type"] = "toggle"

            user_layouts.append(layout)

        # Create final configuration
        config = {
            "userLayouts": user_layouts,
            "defaultUserLayout": user_layouts[0]["name"] if user_layouts else "Base",
            "homeRow": {
                "rowIndex": 4,
                "leftPosition": 2,
                "rightPosition": 2
            },
            "actionMappings": action_mappings
        }

        # Save to file with compact arrays
        with open("split_matrix_config.json", 'w', encoding='utf-8') as f:
            f.write(format_compact_json(config))

        print("\n🎉 SUCCESS! configuration saved to:")
        print("- split_matrix_config.json")
        print("\nKey improvements:")
        print("✅ Consumer keys: C_PLAY → Play, C_MEDIA_HOME → MediaHome")
        print("✅ Home row mods: Show tap keys (N, R, T, S) not mod names (LGUI)")
        print("✅ Better system keys: KP_NUM → NumLock, PSCRN → PrintScreen")
        print("✅ Clean keypad notation: ⁷⁸⁹ → 789, ⊖⊕⊗ → -+*")
        print("✅ Dynamic action mappings: Extracted from actual ZMK consumer codes")
        print("✅ Layer toggles: Semantic actions for OverKeys integration")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
