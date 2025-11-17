"""
Modern Design System for ETF Monitor UI

Defines unified color palette, typography, spacing, and component styles
following modern design principles (Material Design / Ant Design inspired).
"""

import wx


class Colors:
    """
    Unified color palette with semantic naming.
    
    Palette Structure:
    - 1 Primary color (brand identity)
    - 1 Secondary color (accents)
    - Semantic colors (success, warning, error, info)
    - Neutral grays (backgrounds, borders, text)
    
    Total: 5 color families (within requirement)
    """
    
    # Primary Color - Blue (Professional, Trustworthy)
    PRIMARY_50 = wx.Colour(232, 245, 255)   # Lightest
    PRIMARY_100 = wx.Colour(187, 222, 251)
    PRIMARY_200 = wx.Colour(144, 202, 249)
    PRIMARY_300 = wx.Colour(100, 181, 246)
    PRIMARY_400 = wx.Colour(66, 165, 245)
    PRIMARY_500 = wx.Colour(33, 150, 243)   # Main primary
    PRIMARY_600 = wx.Colour(30, 136, 229)
    PRIMARY_700 = wx.Colour(25, 118, 210)
    PRIMARY_800 = wx.Colour(21, 101, 192)
    PRIMARY_900 = wx.Colour(13, 71, 161)    # Darkest
    
    # Secondary Color - Indigo (Complementary)
    SECONDARY_500 = wx.Colour(63, 81, 181)  # Main secondary
    SECONDARY_700 = wx.Colour(48, 63, 159)
    
    # Semantic Colors
    SUCCESS = wx.Colour(76, 175, 80)        # Green - positive changes
    SUCCESS_LIGHT = wx.Colour(200, 230, 201)
    SUCCESS_DARK = wx.Colour(56, 142, 60)
    
    WARNING = wx.Colour(255, 152, 0)        # Orange - warnings
    WARNING_LIGHT = wx.Colour(255, 224, 178)
    
    ERROR = wx.Colour(244, 67, 54)          # Red - negative changes
    ERROR_LIGHT = wx.Colour(255, 205, 210)
    ERROR_DARK = wx.Colour(198, 40, 40)
    
    INFO = wx.Colour(33, 150, 243)          # Blue - informational
    INFO_LIGHT = wx.Colour(187, 222, 251)
    
    # Neutral Grays (5 shades)
    GRAY_50 = wx.Colour(250, 250, 250)      # Lightest background
    GRAY_100 = wx.Colour(245, 245, 245)     # Light background
    GRAY_200 = wx.Colour(238, 238, 238)     # Border light
    GRAY_300 = wx.Colour(224, 224, 224)     # Border
    GRAY_400 = wx.Colour(189, 189, 189)     # Border dark
    GRAY_500 = wx.Colour(158, 158, 158)     # Disabled text
    GRAY_600 = wx.Colour(117, 117, 117)     # Secondary text
    GRAY_700 = wx.Colour(97, 97, 97)        # Body text
    GRAY_800 = wx.Colour(66, 66, 66)        # Heading text
    GRAY_900 = wx.Colour(33, 33, 33)        # Primary text
    
    # Special Colors
    WHITE = wx.Colour(255, 255, 255)
    BLACK = wx.Colour(0, 0, 0)
    TRANSPARENT = wx.Colour(0, 0, 0, 0)
    
    # Background Colors
    BG_PRIMARY = GRAY_50
    BG_SECONDARY = WHITE
    BG_ELEVATED = WHITE  # For cards, modals
    
    # Text Colors
    TEXT_PRIMARY = GRAY_900
    TEXT_SECONDARY = GRAY_600
    TEXT_DISABLED = GRAY_500
    TEXT_HINT = GRAY_500
    
    # Border Colors
    BORDER_LIGHT = GRAY_200
    BORDER_DEFAULT = GRAY_300
    BORDER_DARK = GRAY_400


class Typography:
    """
    Typography hierarchy with consistent font sizes and weights.
    
    Font Family: System default (Segoe UI on Windows, SF Pro on Mac)
    Scale: Based on 4px grid (12, 14, 16, 20, 24, 32, 40)
    """
    
    # Font Families
    FONT_FAMILY_DEFAULT = wx.FONTFAMILY_DEFAULT
    FONT_FAMILY_MODERN = wx.FONTFAMILY_SWISS  # Sans-serif
    
    # Font Sizes (in points)
    SIZE_H1 = 32        # Page titles
    SIZE_H2 = 24        # Section headings
    SIZE_H3 = 20        # Subsection headings
    SIZE_BODY = 14      # Body text, default
    SIZE_BODY_LARGE = 16  # Emphasized body text
    SIZE_CAPTION = 12   # Secondary text, labels
    SIZE_SMALL = 11     # Helper text, footnotes
    
    # Font Weights
    WEIGHT_LIGHT = wx.FONTWEIGHT_LIGHT
    WEIGHT_NORMAL = wx.FONTWEIGHT_NORMAL
    WEIGHT_MEDIUM = wx.FONTWEIGHT_NORMAL  # wxPython doesn't have medium
    WEIGHT_BOLD = wx.FONTWEIGHT_BOLD
    
    @staticmethod
    def get_font(size: int, weight=wx.FONTWEIGHT_NORMAL, family=wx.FONTFAMILY_DEFAULT) -> wx.Font:
        """
        Create a font with specified parameters.
        
        Args:
            size: Font size in points
            weight: Font weight (WEIGHT_* constants)
            family: Font family (FONT_FAMILY_* constants)
            
        Returns:
            wx.Font object
        """
        return wx.Font(size, family, wx.FONTSTYLE_NORMAL, weight)
    
    @staticmethod
    def h1() -> wx.Font:
        """Page title font (32pt, bold)."""
        return Typography.get_font(Typography.SIZE_H1, Typography.WEIGHT_BOLD)
    
    @staticmethod
    def h2() -> wx.Font:
        """Section heading font (24pt, bold)."""
        return Typography.get_font(Typography.SIZE_H2, Typography.WEIGHT_BOLD)
    
    @staticmethod
    def h3() -> wx.Font:
        """Subsection heading font (20pt, medium)."""
        return Typography.get_font(Typography.SIZE_H3, Typography.WEIGHT_MEDIUM)
    
    @staticmethod
    def body() -> wx.Font:
        """Body text font (14pt, normal)."""
        return Typography.get_font(Typography.SIZE_BODY, Typography.WEIGHT_NORMAL)
    
    @staticmethod
    def body_large() -> wx.Font:
        """Large body text font (16pt, normal)."""
        return Typography.get_font(Typography.SIZE_BODY_LARGE, Typography.WEIGHT_NORMAL)
    
    @staticmethod
    def caption() -> wx.Font:
        """Caption/label font (12pt, normal)."""
        return Typography.get_font(Typography.SIZE_CAPTION, Typography.WEIGHT_NORMAL)

    @staticmethod
    def small() -> wx.Font:
        """Small text font (11pt, normal)."""
        return Typography.get_font(Typography.SIZE_SMALL, Typography.WEIGHT_NORMAL)


class Spacing:
    """
    Standardized spacing units based on 4px grid.

    All spacing should use these constants for consistency.
    """

    # Base unit: 4px
    UNIT = 4

    # Spacing scale
    XS = 4      # 4px - Minimal spacing
    SM = 8      # 8px - Small spacing
    MD = 16     # 16px - Medium spacing (default)
    LG = 24     # 24px - Large spacing
    XL = 32     # 32px - Extra large spacing
    XXL = 48    # 48px - Maximum spacing

    # Semantic spacing
    PADDING_SMALL = SM
    PADDING_DEFAULT = MD
    PADDING_LARGE = LG

    MARGIN_SMALL = SM
    MARGIN_DEFAULT = MD
    MARGIN_LARGE = LG

    GAP_SMALL = SM
    GAP_DEFAULT = MD
    GAP_LARGE = LG


class BorderRadius:
    """Border radius values for rounded corners."""

    NONE = 0
    SMALL = 4
    DEFAULT = 8
    LARGE = 12
    CIRCLE = 9999  # For circular elements


class Shadows:
    """
    Shadow definitions for elevation.

    Note: wxPython has limited shadow support, these are reference values.
    """

    NONE = 0
    SMALL = 1   # Subtle elevation
    MEDIUM = 2  # Default elevation
    LARGE = 3   # High elevation


class ComponentStyles:
    """
    Predefined styles for common UI components.
    """

    @staticmethod
    def button_primary() -> dict:
        """Primary button style."""
        return {
            'bg_color': Colors.PRIMARY_500,
            'fg_color': Colors.WHITE,
            'hover_bg': Colors.PRIMARY_600,
            'active_bg': Colors.PRIMARY_700,
            'disabled_bg': Colors.GRAY_300,
            'disabled_fg': Colors.GRAY_500,
            'border_radius': BorderRadius.DEFAULT,
            'padding': (Spacing.SM, Spacing.MD),
            'font': Typography.body()
        }

    @staticmethod
    def button_secondary() -> dict:
        """Secondary button style."""
        return {
            'bg_color': Colors.WHITE,
            'fg_color': Colors.PRIMARY_500,
            'hover_bg': Colors.PRIMARY_50,
            'active_bg': Colors.PRIMARY_100,
            'disabled_bg': Colors.GRAY_100,
            'disabled_fg': Colors.GRAY_500,
            'border_color': Colors.PRIMARY_500,
            'border_radius': BorderRadius.DEFAULT,
            'padding': (Spacing.SM, Spacing.MD),
            'font': Typography.body()
        }

    @staticmethod
    def button_danger() -> dict:
        """Danger/delete button style."""
        return {
            'bg_color': Colors.ERROR,
            'fg_color': Colors.WHITE,
            'hover_bg': Colors.ERROR_DARK,
            'active_bg': Colors.ERROR_DARK,
            'disabled_bg': Colors.GRAY_300,
            'disabled_fg': Colors.GRAY_500,
            'border_radius': BorderRadius.DEFAULT,
            'padding': (Spacing.SM, Spacing.MD),
            'font': Typography.body()
        }

    @staticmethod
    def input_field() -> dict:
        """Text input field style."""
        return {
            'bg_color': Colors.WHITE,
            'fg_color': Colors.TEXT_PRIMARY,
            'border_color': Colors.BORDER_DEFAULT,
            'focus_border': Colors.PRIMARY_500,
            'error_border': Colors.ERROR,
            'disabled_bg': Colors.GRAY_100,
            'disabled_fg': Colors.TEXT_DISABLED,
            'border_radius': BorderRadius.DEFAULT,
            'padding': Spacing.SM,
            'font': Typography.body()
        }

    @staticmethod
    def card() -> dict:
        """Card/panel style."""
        return {
            'bg_color': Colors.BG_ELEVATED,
            'border_color': Colors.BORDER_LIGHT,
            'border_radius': BorderRadius.LARGE,
            'padding': Spacing.LG,
            'shadow': Shadows.SMALL
        }

    @staticmethod
    def grid_header() -> dict:
        """Grid/table header style."""
        return {
            'bg_color': Colors.GRAY_100,
            'fg_color': Colors.TEXT_PRIMARY,
            'font': Typography.body(),
            'font_weight': Typography.WEIGHT_BOLD,
            'padding': Spacing.MD
        }

    @staticmethod
    def grid_cell() -> dict:
        """Grid/table cell style."""
        return {
            'bg_color': Colors.WHITE,
            'fg_color': Colors.TEXT_PRIMARY,
            'border_color': Colors.BORDER_LIGHT,
            'hover_bg': Colors.GRAY_50,
            'selected_bg': Colors.PRIMARY_50,
            'font': Typography.body(),
            'padding': Spacing.SM
        }


class Animations:
    """
    Animation timing and easing constants.
    """

    # Duration in milliseconds
    DURATION_FAST = 150
    DURATION_DEFAULT = 250
    DURATION_SLOW = 350

    # Easing (reference for custom implementations)
    EASE_IN_OUT = "ease-in-out"
    EASE_OUT = "ease-out"
    EASE_IN = "ease-in"


# Utility functions

def apply_button_style(button: wx.Button, style_dict: dict) -> None:
    """
    Apply style dictionary to a button.

    Args:
        button: wx.Button instance
        style_dict: Style dictionary from ComponentStyles
    """
    button.SetBackgroundColour(style_dict.get('bg_color', Colors.WHITE))
    button.SetForegroundColour(style_dict.get('fg_color', Colors.TEXT_PRIMARY))
    if 'font' in style_dict:
        button.SetFont(style_dict['font'])


def apply_text_style(text_ctrl: wx.TextCtrl, style_dict: dict) -> None:
    """
    Apply style dictionary to a text control.

    Args:
        text_ctrl: wx.TextCtrl instance
        style_dict: Style dictionary from ComponentStyles
    """
    text_ctrl.SetBackgroundColour(style_dict.get('bg_color', Colors.WHITE))
    text_ctrl.SetForegroundColour(style_dict.get('fg_color', Colors.TEXT_PRIMARY))
    if 'font' in style_dict:
        text_ctrl.SetFont(style_dict['font'])


def get_status_color(change_percent: float) -> wx.Colour:
    """
    Get color based on change percentage.

    Args:
        change_percent: Percentage change value

    Returns:
        wx.Colour for the status (green for positive, red for negative, gray for neutral)
    """
    if change_percent > 0:
        return Colors.SUCCESS
    elif change_percent < 0:
        return Colors.ERROR
    else:
        return Colors.GRAY_600


