# Inline Calculator for Odoo 19

## Overview

This module provides in-line calculator functionality for numeric input fields in Odoo 19. Users can enter mathematical expressions directly into fields and have them automatically calculated.

## Features

- **Direct Expression Entry**: Type mathematical expressions like `15*1.1` directly into numeric fields
- **Automatic Calculation**: Results are calculated when pressing Tab or leaving the field
- **Support for Multiple Field Types**: Works with Float, Integer, and Monetary fields
- **Basic Arithmetic Operations**: Supports addition (+), subtraction (-), multiplication (*), and division (/)
- **Decimal Support**: Handles decimal numbers and parentheses
- **Safe Evaluation**: Uses safe evaluation methods to prevent code injection

## Usage

1. Install the module from the Apps menu
2. Navigate to any form with numeric fields (quantity, price, etc.)
3. Type a mathematical expression in any numeric field:
   - Simple: `15*1.1`
   - Complex: `100+50*0.1`
   - With parentheses: `(10+5)*2`
4. Press Tab or click outside the field (or simply move to another field)
5. The result will be automatically calculated and validated without errors

## Examples

- Quantity field: Type `15*1.1` → Result: `16.5`
- Price field: Type `100+50*0.1` → Result: `105`
- Discount calculation: Type `(100-20)*0.9` → Result: `72`

## Technical Details

### Field Types Supported

- **Float Fields**: Extended with calculator functionality, respects field precision
- **Integer Fields**: Results are rounded to whole numbers
- **Monetary Fields**: Uses 2 decimal places for currency formatting

### Implementation

The module uses Odoo 19's `patch` utility to modify the existing field classes:
- Patches `FloatField.prototype` 
- Patches `IntegerField.prototype`
- Patches `MonetaryField.prototype`

The patch approach:
- Extends the existing field classes without creating new registry entries
- Overrides the `parse()` method which is called when field values are processed
- Prevents validation errors (red borders) because calculated values are properly parsed
- Integrates seamlessly with Odoo's existing field validation system
- Works consistently across all field types that use numeric parsing

### Security

- Expression validation: Only allows numbers, operators, and parentheses
- Safe evaluation: Uses `Function` constructor instead of `eval()`
- Error handling: Invalid expressions fall back to standard parsing without breaking the UI

## Installation

1. Copy the `dn_inline_calculator` folder to your Odoo `addons` directory
2. Update the Odoo addons list
3. Install the module from the Apps menu
4. Restart Odoo server

## Configuration

No configuration required. The module works automatically after installation.

## Dependencies

- `base`
- `web`

## Compatibility

- Odoo 19.0

## License

LGPL-3

## Author

Your Company

## Support

For issues or questions, please contact your system administrator.
