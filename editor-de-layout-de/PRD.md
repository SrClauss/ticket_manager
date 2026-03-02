# Planning Guide

A professional ticket layout editor that empowers users to visually design custom event tickets with precision control over text, QR codes, dividers, and nested groups.

**Experience Qualities**: 
1. **Professional** - Feels like enterprise design software with precise controls and a polished interface
2. **Intuitive** - Complex canvas operations are accessible through clear visual feedback and smart defaults
3. **Efficient** - Rapid iteration with undo/redo, keyboard shortcuts, and instant visual updates

**Complexity Level**: Complex Application (advanced functionality, likely with multiple views)
This is a sophisticated canvas-based design tool with nested editing modes, state management, persistence, keyboard shortcuts, and real-time preview generation with template variable replacement.

## Essential Features

**Canvas-Based Element Positioning**
- Functionality: Drag elements vertically on a mm-accurate canvas with horizontal alignment controls
- Purpose: Provides precise layout control for print-ready ticket designs
- Trigger: User adds elements or clicks existing ones
- Progression: Add element → Appears on canvas → Drag vertically → Adjust properties → See instant update
- Success criteria: Elements position accurately with mm precision, visual guides show padding zones

**Nested Group Editing**
- Functionality: Create container groups that can be edited in isolation with their own canvas
- Purpose: Allows complex composite elements (header sections, info blocks) to be treated as units
- Trigger: User clicks "Add Group" or double-clicks existing group
- Progression: Create group → Enter edit mode → Add child elements → Exit to see snapshot → Position as unit
- Success criteria: Groups render as visual snapshots on main canvas, double-click enters isolated edit mode

**Template Variable System**
- Functionality: Use tags like {NOME}, {CPF}, {EVENTO_NOME} that get replaced in preview
- Purpose: Design once, generate many tickets with dynamic data
- Trigger: User types tags in text elements, clicks "Update Preview"
- Progression: Type {NOME} → Element shows tag → Click preview → See "João da Silva Sauro"
- Success criteria: All tags replaced with mock data in preview, one-click copy tags to clipboard

**Undo/Redo with State Persistence**
- Functionality: Full history tracking with localStorage auto-save
- Purpose: Safe experimentation without losing work
- Trigger: Any modification, or Ctrl+Z / Ctrl+Shift+Z
- Progression: Make change → Auto-saved → Undo → State restored → Close app → Reopen → Draft restored
- Success criteria: 30-step history, keyboard shortcuts work, draft survives page refresh

**Property Panel Controls**
- Functionality: Context-sensitive sidebar showing properties of selected element/group
- Purpose: Fine-tune positioning, sizing, alignment, and styling without cluttering canvas
- Trigger: Select element or group
- Progression: Click element → Properties appear → Adjust values → Canvas updates instantly
- Success criteria: All properties editable, changes reflect immediately, inputs show current values

## Edge Case Handling

- **Empty Canvas**: Show helpful overlay with "Add your first element" prompt
- **Overlapping Elements**: Z-index maintained, latest-added on top, visual selection borders prevent confusion
- **Invalid Dimensions**: Prevent negative values, auto-clamp to min/max, show validation feedback
- **Group Nesting Attempt**: Block groups within groups with toast notification
- **Missing Template Data**: Preview shows tags as-is if no replacement data available
- **Long Text Overflow**: Text extends naturally, designer responsible for layout testing

## Design Direction

Professional design tool aesthetic with dark UI to make the white canvas pop, accented with vibrant blues and ambers that communicate hierarchy (blue for elements, amber for groups).

## Color Selection

Dark slate workspace with vibrant accent colors for clear visual hierarchy:

- **Primary Color**: Vivid Blue `oklch(0.6 0.22 250)` - Commands attention for primary actions and selected elements, conveys precision and professionalism
- **Secondary Colors**: Deep Slate grays `oklch(0.18 0.01 240)` for panels, `oklch(0.26 0.01 240)` for hover states - Creates depth without distraction
- **Accent Color**: Warm Amber `oklch(0.72 0.15 75)` - Highlights group-related actions and editing mode, creates visual distinction from standard elements
- **Foreground/Background Pairings**: 
  - Primary Blue `oklch(0.6 0.22 250)`: White text `oklch(0.98 0 0)` - Ratio 7.2:1 ✓
  - Slate Panel `oklch(0.18 0.01 240)`: Light slate text `oklch(0.88 0.01 240)` - Ratio 12.4:1 ✓
  - Accent Amber `oklch(0.72 0.15 75)`: Dark amber text `oklch(0.25 0.08 75)` - Ratio 8.6:1 ✓
  - Canvas Background: Pure white `oklch(1 0 0)` for accurate design work

## Font Selection

Crisp system fonts for clarity and precision, with monospace for technical elements like IDs and measurements.

- **Typographic Hierarchy**: 
  - H1 (App Title): Inter Bold/24px/tight tracking - Commands attention in header
  - H2 (Section Headers): Inter SemiBold/11px/uppercase/wide tracking - Subtle hierarchy markers
  - Body (Controls): Inter Regular/14px/normal - Maximum readability for dense interfaces
  - Labels: Inter Medium/12px/slight opacity - Guides without overwhelming
  - Code (IDs, Tags): JetBrains Mono Regular/11px - Technical precision for technical content

## Animations

Purposeful micro-interactions reinforce actions without delaying workflow:
- Toast notifications slide in from right with 300ms ease-out, reinforcing successful actions
- Canvas element selection shows instant blue border highlight (no delay)
- Mode transitions (entering/exiting group edit) use 200ms fade to maintain spatial context
- Property changes trigger immediate canvas re-render (no animation - precision over polish)
- Button hover states transition background in 150ms for tactile feedback

## Component Selection

- **Components**: 
  - Button (shadcn) for all actions with variants (default, outline, destructive)
  - Input (shadcn) for all numeric/text fields with focus states
  - Select (shadcn) for alignment dropdowns
  - Separator (shadcn) for panel section divisions
  - Badge (shadcn) for copyable template tags
  - Toast (sonner) for ephemeral feedback
  - Card (shadcn) for property panels and layer lists
- **Customizations**: 
  - Custom Canvas component wrapping HTML5 canvas with Fabric.js integration
  - LayerItem custom component with drag indicators and action buttons
  - PropertyPanel dynamic component that switches based on selection type
- **States**: 
  - Buttons: Slate hover for secondary, blue hover for primary, red hover for destructive
  - Inputs: Blue focus ring, validation red border for invalid
  - Canvas elements: Blue selection border, amber for groups
  - Disabled states: 50% opacity for unavailable actions (preview during group edit)
- **Icon Selection**: 
  - Phosphor icons throughout: Plus, Trash, ArrowCounterClockwise, ArrowClockwise, FloppyDisk, PencilSimple, Package, TextT, QrCode, Minus
- **Spacing**: 
  - Consistent 16px (p-4) panel padding
  - 8px (gap-2) between related controls
  - 12px (gap-3) between form sections
  - 4px (gap-1) for tight icon button groups
- **Mobile**: 
  - Tablet (768px): Collapsible sidebars, canvas scales to fit
  - Phone (<768px): Single-column stacked layout, bottom sheet for properties, simplified toolbar
  - Touch: Larger hit areas (44px min), no hover states, tap-to-select on canvas
