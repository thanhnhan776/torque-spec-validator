# Torque Specification Validator

## Torque range

The default plausible range is **0–1000 Nm**, inclusive. Positive values outside this range receive a warning; zero and negative values are invalid. Set `PLAUSIBLE_TORQUE_MIN` and `PLAUSIBLE_TORQUE_MAX` to change the bounds. This is a review threshold, not a manufacturer-approved specification.

## Known limitations

- **Upload size:** Uploads have no size limit and are read into memory. Large files can exhaust server resources; enforce upload limits or use streaming before production deployment.
- **Torque precision in API responses:** Validation compares exact decimal values, but the API returns torque as a floating-point number. Extreme values may be rounded or underflow to zero; values too large for a finite float are returned as `null`. Consider a decimal string representation if exact display is required.
