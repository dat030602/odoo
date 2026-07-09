import { patch } from "@web/core/utils/patch";
import { FloatField } from "@web/views/fields/float/float_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";

// Helper functions to avoid code duplication
function isMathExpression(value) {
    if (!value || typeof value !== 'string') {
        return false;
    }
    // Check for mathematical operators (excluding scientific notation)
    const mathOperators = /[+\-*/]/;
    // Avoid matching negative numbers at the start
    const hasOperator = mathOperators.test(value) && !/^[-+]\d/.test(value);
    return hasOperator;
}

function safeEvaluate(expression) {
    // Remove any whitespace
    expression = expression.replace(/\s/g, '');
    
    // Validate expression - only allow numbers, operators, and parentheses
    if (!/^[0-9+\-*/().]+$/.test(expression)) {
        throw new Error('Invalid characters in expression');
    }

    // Use Function constructor for safe evaluation
    try {
        const result = new Function('return ' + expression)();
        return result;
    } catch (e) {
        throw new Error('Calculation error');
    }
}

/**
 * Patch FloatField to add inline calculator functionality
 */
patch(FloatField.prototype, {
    parse(value) {
        // Check if the value is a mathematical expression
        if (isMathExpression(value)) {
            try {
                const result = safeEvaluate(value);
                if (result !== null && !isNaN(result)) {
                    // Return the calculated result as a number
                    return result;
                }
            } catch (error) {
                // Fall back to original parsing if calculation fails
            }
        }
        // Use original parsing for normal values
        return this._super(...arguments);
    },
});

/**
 * Patch IntegerField to add inline calculator functionality
 */
patch(IntegerField.prototype, {
    parse(value) {
        // Check if the value is a mathematical expression
        if (isMathExpression(value)) {
            try {
                const result = safeEvaluate(value);
                if (result !== null && !isNaN(result)) {
                    // Return the calculated result rounded to integer
                    return Math.round(result);
                }
            } catch (error) {
                // Fall back to original parsing if calculation fails
            }
        }
        // Use original parsing for normal values
        return this._super(...arguments);
    },
});

/**
 * Patch MonetaryField to add inline calculator functionality
 */
patch(MonetaryField.prototype, {
    parse(value) {
        // Check if the value is a mathematical expression
        if (isMathExpression(value)) {
            try {
                const result = safeEvaluate(value);
                if (result !== null && !isNaN(result)) {
                    const roundedResult = Math.round(result * 100) / 100;
                    // Return the calculated result rounded to 2 decimal places for currency
                    return roundedResult;
                }
            } catch (error) {
                // Fall back to original parsing if calculation fails
            }
        }
        // Use original parsing for normal values
        return this._super(...arguments);
    },
});
